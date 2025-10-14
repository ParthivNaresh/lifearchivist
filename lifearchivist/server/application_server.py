"""
Application server managing high-level application services.

This server coordinates application-level services (progress tracking,
background tasks, tool registry) while delegating core infrastructure
to the ServiceContainer.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import WebSocket

from ..config import get_settings
from ..tools.exceptions import ToolExecutionError, ToolNotFoundError, ValidationError
from ..tools.registry import ToolRegistry
from ..utils.logging import log_event
from .background_tasks import BackgroundTaskManager
from .enrichment_queue import EnrichmentQueue
from .progress_manager import ProgressManager
from .service_container import ServiceConfig, ServiceContainer


class SessionManager:
    """Manages WebSocket sessions for real-time updates."""

    def __init__(self):
        self.sessions: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Register a new WebSocket session."""
        await websocket.accept()
        self.sessions[session_id] = websocket
        log_event("websocket_session_connected", {"session_id": session_id})

    def disconnect(self, session_id: str):
        """Remove a WebSocket session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            log_event("websocket_session_disconnected", {"session_id": session_id})

    async def send_to_session(self, session_id: str, message: Dict[str, Any]):
        """Send message to specific session."""
        if session_id in self.sessions:
            try:
                await self.sessions[session_id].send_json(message)
            except Exception as e:
                log_event(
                    "websocket_send_failed",
                    {"session_id": session_id, "error": str(e)},
                    level=logging.WARNING,
                )
                self.disconnect(session_id)


class ApplicationServer:
    """
    Main application server coordinating all services.

    This server manages:
    - Core infrastructure (via ServiceContainer)
    - WebSocket sessions
    - Progress tracking
    - Background task processing
    - Tool registry and execution
    - Optional agents (if enabled)

    The server ensures proper initialization order and cleanup.
    """

    def __init__(self):
        """Initialize application server."""
        self.settings = get_settings()

        # Core infrastructure (will be initialized)
        self.service_container: Optional[ServiceContainer] = None

        # Application services (will be initialized)
        self.session_manager: SessionManager = SessionManager()
        self.progress_manager: Optional[ProgressManager] = None
        self.enrichment_queue: Optional[EnrichmentQueue] = None
        self.background_tasks: Optional[BackgroundTaskManager] = None
        self.tool_registry: Optional[ToolRegistry] = None

        # Optional agents (only if enabled)
        self.ingestion_agent = None
        self.query_agent = None

        self._initialized = False

    async def initialize(self):
        """
        Initialize all server components in correct order.

        Initialization phases:
        1. Core infrastructure (ServiceContainer)
        2. Vault reconciliation
        3. Application services (progress, enrichment, background tasks)
        4. Tool registry
        5. Optional agents
        """
        if self._initialized:
            log_event(
                "application_server_already_initialized",
                level=logging.WARNING,
            )
            return

        try:
            log_event("application_server_init_start")

            # Phase 1: Initialize core infrastructure
            await self._init_service_container()

            # Phase 2: Run startup reconciliation
            await self._run_startup_reconciliation()

            # Phase 3: Initialize application services
            self._init_progress_manager()  # Synchronous - uses sync Redis
            await self._init_enrichment_queue()
            await self._init_background_tasks()

            # Phase 4: Initialize tool registry
            await self._init_tool_registry()

            # Phase 5: Initialize agents (if enabled)
            if self.settings.enable_agents:
                await self._init_agents()

            self._initialized = True

            log_event(
                "application_server_initialized",
                {
                    "agents_enabled": self.settings.enable_agents,
                    "websockets_enabled": self.settings.enable_websockets,
                    "background_tasks_enabled": self.background_tasks is not None,
                },
            )

        except Exception as e:
            log_event(
                "application_server_init_failed",
                {"error": str(e), "error_type": type(e).__name__},
                level=logging.ERROR,
            )
            # Cleanup on failure
            await self.cleanup()
            raise

    async def cleanup(self):
        """Cleanup all services in reverse initialization order."""
        log_event("application_server_cleanup_start")

        # Stop background tasks first
        if self.background_tasks:
            try:
                await self.background_tasks.stop()
                log_event("background_tasks_stopped")
            except Exception as e:
                log_event(
                    "background_tasks_stop_error",
                    {"error": str(e)},
                    level=logging.WARNING,
                )

        # Cleanup enrichment queue
        if self.enrichment_queue:
            try:
                await self.enrichment_queue.cleanup()
                log_event("enrichment_queue_cleaned_up")
            except Exception as e:
                log_event(
                    "enrichment_queue_cleanup_error",
                    {"error": str(e)},
                    level=logging.WARNING,
                )

        # Cleanup core infrastructure
        if self.service_container:
            try:
                await self.service_container.cleanup()
                log_event("service_container_cleaned_up")
            except Exception as e:
                log_event(
                    "service_container_cleanup_error",
                    {"error": str(e)},
                    level=logging.WARNING,
                )

        self._initialized = False
        log_event("application_server_cleanup_complete")

    # Initialization methods

    async def _init_service_container(self):
        """Initialize core infrastructure services."""
        config = ServiceConfig(
            redis_url=self.settings.redis_url,
            qdrant_url=self.settings.qdrant_url,
            vault_path=self.settings.vault_path,
            settings=self.settings,
        )

        self.service_container = ServiceContainer(config)
        await self.service_container.initialize()

        log_event(
            "service_container_ready",
            {
                "vault_path": str(self.settings.vault_path),
                "redis_url": self.settings.redis_url,
                "qdrant_url": self.settings.qdrant_url,
            },
        )

    async def _run_startup_reconciliation(self):
        """
        Run vault reconciliation on startup to ensure data consistency.

        This handles cases where users manually delete vault files,
        ensuring Redis/Qdrant metadata stays in sync with actual files.
        """
        try:
            from ..storage.vault_reconciliation import VaultReconciliationService

            if not self.service_container:
                return

            vault = self.service_container.vault
            doc_tracker = self.service_container.doc_tracker
            qdrant_client = self.service_container.qdrant_client

            if not vault or not doc_tracker or not qdrant_client:
                return

            # Create reconciliation service
            reconciliation_service = VaultReconciliationService(
                vault=vault,
                doc_tracker=doc_tracker,
                qdrant_client=qdrant_client,
            )

            # Run reconciliation
            result = await reconciliation_service.reconcile()

            # Log results
            if result["cleaned"] > 0:
                log_event(
                    "startup_reconciliation_cleanup",
                    {
                        "checked": result["checked"],
                        "cleaned": result["cleaned"],
                        "errors": result["errors"],
                    },
                    level=logging.WARNING,
                )
            else:
                log_event(
                    "startup_reconciliation_complete",
                    {
                        "checked": result["checked"],
                        "status": "consistent",
                    },
                )

        except Exception as e:
            log_event(
                "startup_reconciliation_failed",
                {"error": str(e), "error_type": type(e).__name__},
                level=logging.ERROR,
            )
            # Don't fail startup if reconciliation fails

    def _init_progress_manager(self):
        """
        Initialize progress tracking manager.

        Note: This is synchronous because ProgressManager uses the synchronous
        Redis client. This is acceptable for progress tracking which is not
        on the critical path. For proper async implementation, ProgressManager
        should be refactored to use redis.asyncio.
        """
        if not self.settings.enable_websockets:
            log_event("progress_manager_disabled", {"reason": "websockets_disabled"})
            return

        try:
            self.progress_manager = ProgressManager(
                redis_url=self.settings.redis_url,
                session_manager=self.session_manager,
            )
            log_event("progress_manager_initialized")
        except Exception as e:
            log_event(
                "progress_manager_init_failed",
                {"error": str(e)},
                level=logging.WARNING,
            )
            self.progress_manager = None

    async def _init_enrichment_queue(self):
        """Initialize enrichment queue for background processing."""
        try:
            self.enrichment_queue = EnrichmentQueue(redis_url=self.settings.redis_url)
            await self.enrichment_queue.initialize()
            log_event("enrichment_queue_initialized")
        except Exception as e:
            log_event(
                "enrichment_queue_init_failed",
                {"error": str(e)},
                level=logging.WARNING,
            )
            self.enrichment_queue = None

    async def _init_background_tasks(self):
        """Initialize background task manager."""
        if not self.enrichment_queue:
            log_event(
                "background_tasks_disabled",
                {"reason": "enrichment_queue_not_available"},
            )
            return

        if not self.service_container:
            return

        try:
            self.background_tasks = BackgroundTaskManager(
                llamaindex_service=self.service_container.llamaindex_service,
                vault=self.service_container.vault,
            )
            await self.background_tasks.start()
            log_event("background_tasks_initialized")
        except Exception as e:
            log_event(
                "background_tasks_init_failed",
                {"error": str(e)},
                level=logging.WARNING,
            )
            self.background_tasks = None

    async def _init_tool_registry(self):
        """Initialize tool registry with all dependencies."""
        if not self.service_container:
            raise RuntimeError("ServiceContainer must be initialized first")

        self.tool_registry = ToolRegistry(
            vault=self.service_container.vault,
            llamaindex_service=self.service_container.llamaindex_service,
            progress_manager=self.progress_manager,
            enrichment_queue=self.enrichment_queue,
        )
        await self.tool_registry.register_all()

        tool_count = len(self.tool_registry.tools)
        log_event("tool_registry_initialized", {"tools_registered": tool_count})

    async def _init_agents(self):
        """Initialize agents (if enabled)."""
        try:
            from ..agents.ingestion import IngestionAgent
            from ..agents.query import QueryAgent

            if not self.service_container or not self.tool_registry:
                return

            self.ingestion_agent = IngestionAgent(
                database=None,
                vault=self.service_container.vault,
                tool_registry=self.tool_registry,
            )

            self.query_agent = QueryAgent(
                llamaindex_service=self.service_container.llamaindex_service,
                tool_registry=self.tool_registry,
            )

            log_event("agents_initialized", {"ingestion": True, "query": True})
        except Exception as e:
            log_event(
                "agents_init_failed",
                {"error": str(e)},
                level=logging.WARNING,
            )

    # Tool execution

    async def execute_tool(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool with input/output validation.

        Args:
            tool_name: Name of the tool to execute
            params: Tool parameters

        Returns:
            Dict with success status and result or error
        """
        try:
            # Check tool registry initialization
            if not self.tool_registry:
                raise ToolExecutionError("Tool registry not initialized")

            # Get the tool
            tool = self.tool_registry.get_tool(tool_name)
            if not tool:
                raise ToolNotFoundError(f"Tool '{tool_name}' not found")

            # Validate input
            try:
                validated_params = await tool.validate_input(params)
            except ValidationError as e:
                return {"success": False, "error": f"Invalid input: {str(e)}"}

            # Execute tool
            try:
                result = await tool.execute(**validated_params)
            except Exception as e:
                raise ToolExecutionError(f"Tool execution failed: {str(e)}") from e

            # Validate output
            try:
                validated_result = await tool.validate_output(result)
            except ValidationError as e:
                return {"success": False, "error": f"Invalid tool output: {str(e)}"}

            return {"success": True, "result": validated_result}

        except (ToolNotFoundError, ToolExecutionError) as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            log_event(
                "tool_execution_unexpected_error",
                {"tool": tool_name, "error": str(e)},
                level=logging.ERROR,
            )
            return {"success": False, "error": f"Internal server error: {str(e)}"}

    # Agent execution

    async def query_agent_async(self, agent_name: str, query: str) -> Dict[str, Any]:
        """
        Query an agent asynchronously.

        Args:
            agent_name: Name of the agent ("query" or "ingestion")
            query: Query string

        Returns:
            Dict with success status and result or error
        """
        try:
            if not self.settings.enable_agents:
                return {
                    "success": False,
                    "error": "Agents are disabled in current mode",
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
            log_event(
                "agent_query_error",
                {"agent": agent_name, "error": str(e)},
                level=logging.ERROR,
            )
            return {"success": False, "error": str(e)}

    # Convenience properties for backward compatibility

    @property
    def vault(self):
        """Get vault from service container."""
        return self.service_container.vault if self.service_container else None

    @property
    def llamaindex_service(self):
        """Get LlamaIndex service from service container."""
        return (
            self.service_container.llamaindex_service
            if self.service_container
            else None
        )

    @property
    def is_initialized(self) -> bool:
        """Check if server is initialized."""
        return self._initialized
