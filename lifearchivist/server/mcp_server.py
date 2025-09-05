"""
Main MCP server implementation.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import WebSocket

from ..config import get_settings
from ..storage.llamaindex_service import LlamaIndexService
from ..storage.vault.vault import Vault
from ..tools.exceptions import ToolExecutionError, ToolNotFoundError, ValidationError
from ..tools.registry import ToolRegistry
from ..utils.logging import log_context
from ..utils.logging.structured import MetricsCollector
from .progress_manager import ProgressManager

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages WebSocket sessions."""

    def __init__(self):
        self.sessions: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Register a new session."""
        await websocket.accept()
        self.sessions[session_id] = websocket
        logger.info(f"Session {session_id} connected")

    def disconnect(self, session_id: str):
        """Remove a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Session {session_id} disconnected")

    async def send_to_session(self, session_id: str, message: Dict[str, Any]):
        """Send message to specific session."""
        if session_id in self.sessions:
            try:
                await self.sessions[session_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to session {session_id}: {e}")
                self.disconnect(session_id)


class MCPServer:
    """Main MCP server class."""

    def __init__(self):
        self.settings = get_settings()
        self.session_manager = SessionManager()
        self.progress_manager: Optional[ProgressManager] = None
        self.llamaindex_service: Optional[LlamaIndexService] = None
        self.vault: Optional[Vault] = None
        self.tool_registry: Optional[ToolRegistry] = None
        # Agents only created when enabled
        self.ingestion_agent = None
        self.query_agent = None

    async def initialize(self):
        """Initialize server components."""
        logger.error("Initializing MCP server...")

        # Initialize storage
        vault_path = self.settings.vault_path
        if not vault_path:
            raise ValueError("Vault path not configured")
        self.vault = Vault(vault_path)
        await self.vault.initialize()

        # Initialize LlamaIndex service
        self.llamaindex_service = LlamaIndexService(vault=self.vault)

        # Initialize progress manager only if websockets enabled
        # if self.settings.enable_websockets:
        try:
            self.progress_manager = ProgressManager(
                redis_url="redis://localhost:6379",
                session_manager=self.session_manager,
            )
        except Exception:
            self.progress_manager = None
        # else:
        #     logger.info("Progress manager disabled (websockets off)")
        #     self.progress_manager = None

        # Initialize tool registry with dependencies
        self.tool_registry = ToolRegistry(
            vault=self.vault,
            llamaindex_service=self.llamaindex_service,
            progress_manager=self.progress_manager,
        )
        await self.tool_registry.register_all()

        # Initialize agents only if enabled
        if self.settings.enable_agents:
            logger.info("Initializing agents...")
            from ..agents.ingestion import IngestionAgent
            from ..agents.query import QueryAgent

            self.ingestion_agent = IngestionAgent(
                database=None,
                vault=self.vault,
                tool_registry=self.tool_registry,
            )

            self.query_agent = QueryAgent(
                llamaindex_service=self.llamaindex_service,
                tool_registry=self.tool_registry,
            )
        else:
            logger.info("Agents disabled (API-only mode)")

        logger.info("MCP server initialized successfully")

    async def execute_tool(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool with input/output validation."""
        with log_context(
            operation="execute_tool",
            tool_name=tool_name,
            param_keys=list(params.keys()) if params else [],
        ):
            metrics = MetricsCollector("execute_tool")
            metrics.start()
            metrics.add_metric("tool_name", tool_name)
            metrics.add_metric("param_count", len(params) if params else 0)

            try:
                # Check tool registry initialization
                if not self.tool_registry:
                    metrics.set_error(
                        ToolExecutionError("Tool registry not initialized")
                    )
                    metrics.report("tool_execution_failed")
                    raise ToolExecutionError("Tool registry not initialized")

                # Get the tool
                tool = self.tool_registry.get_tool(tool_name)
                if not tool:
                    metrics.set_error(
                        ToolNotFoundError(f"Tool '{tool_name}' not found")
                    )
                    metrics.report("tool_execution_failed")
                    raise ToolNotFoundError(f"Tool '{tool_name}' not found")

                try:
                    validated_params = await tool.validate_input(params)
                    metrics.add_metric("input_validation", "passed")
                except ValidationError as e:
                    metrics.set_error(e)
                    metrics.add_metric("input_validation", "failed")
                    metrics.report("tool_execution_failed")
                    return {"success": False, "error": f"Invalid input: {str(e)}"}

                try:
                    result = await tool.execute(**validated_params)
                    metrics.add_metric("tool_execution", "completed")
                except Exception as e:
                    metrics.set_error(e)
                    metrics.add_metric("tool_execution", "failed")
                    metrics.report("tool_execution_failed")
                    raise ToolExecutionError(f"Tool execution failed: {str(e)}") from e

                try:
                    validated_result = await tool.validate_output(result)
                    metrics.add_metric("output_validation", "passed")
                except ValidationError as e:
                    metrics.set_error(e)
                    metrics.add_metric("output_validation", "failed")
                    metrics.report("tool_execution_failed")
                    return {"success": False, "error": f"Invalid tool output: {str(e)}"}

                metrics.set_success(True)
                metrics.report("tool_execution_completed")
                return {"success": True, "result": validated_result}

            except (ToolNotFoundError, ToolExecutionError) as e:
                metrics.set_error(e)
                metrics.report("tool_execution_failed")
                return {"success": False, "error": str(e)}
            except Exception as e:
                metrics.set_error(e)
                metrics.report("tool_execution_failed")
                return {"success": False, "error": f"Internal server error: {str(e)}"}

    async def query_agent_async(self, agent_name: str, query: str) -> Dict[str, Any]:
        """Query an agent asynchronously."""
        try:
            if not self.settings.enable_agents:
                return {
                    "success": False,
                    "error": "Agents are disabled in API-only mode",
                }

            if agent_name == "query" and self.query_agent:
                result = await self.query_agent.process(query)
            elif agent_name == "ingestion" and self.ingestion_agent:
                result = await self.ingestion_agent.process(query)
            else:
                available_agents = []
                if self.query_agent:
                    available_agents.append("query")
                if self.ingestion_agent:
                    available_agents.append("ingestion")
                return {
                    "success": False,
                    "error": f"Agent '{agent_name}' not found. Available: {available_agents}",
                }

            return {"success": True, "result": result}

        except Exception as e:
            logger.error(f"Agent query failed: {e}")
            return {"success": False, "error": str(e)}
