"""
Main MCP server implementation.
"""

from typing import Any, Dict, Optional

from fastapi import WebSocket

from ..config import get_settings
from ..storage.llamaindex_service import LlamaIndexService
from ..storage.vault.vault import Vault
from ..tools.exceptions import ToolExecutionError, ToolNotFoundError, ValidationError
from ..tools.registry import ToolRegistry
from .progress_manager import ProgressManager


class SessionManager:
    """Manages WebSocket sessions."""

    def __init__(self):
        self.sessions: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Register a new session."""
        await websocket.accept()
        self.sessions[session_id] = websocket

    def disconnect(self, session_id: str):
        """Remove a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]

    async def send_to_session(self, session_id: str, message: Dict[str, Any]):
        """Send message to specific session."""
        if session_id in self.sessions:
            try:
                await self.sessions[session_id].send_json(message)
            except Exception as e:
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

        # Initialize tool registry with dependencies
        self.tool_registry = ToolRegistry(
            vault=self.vault,
            llamaindex_service=self.llamaindex_service,
            progress_manager=self.progress_manager,
        )
        await self.tool_registry.register_all()

        # Initialize agents only if enabled
        if self.settings.enable_agents:
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

    async def execute_tool(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool with input/output validation."""
        try:
            # Check tool registry initialization
            if not self.tool_registry:
                raise ToolExecutionError("Tool registry not initialized")

            # Get the tool
            tool = self.tool_registry.get_tool(tool_name)
            if not tool:
                raise ToolNotFoundError(f"Tool '{tool_name}' not found")

            try:
                validated_params = await tool.validate_input(params)
            except ValidationError as e:
                return {"success": False, "error": f"Invalid input: {str(e)}"}

            try:
                result = await tool.execute(**validated_params)
            except Exception as e:
                raise ToolExecutionError(f"Tool execution failed: {str(e)}") from e

            try:
                validated_result = await tool.validate_output(result)
            except ValidationError as e:
                return {"success": False, "error": f"Invalid tool output: {str(e)}"}
            return {"success": True, "result": validated_result}

        except (ToolNotFoundError, ToolExecutionError) as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
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
            return {"success": False, "error": str(e)}
