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
from ..storage.vault_reconciliation import VaultReconciliationService
from ..tools.exceptions import ToolExecutionError, ToolNotFoundError, ValidationError
from ..tools.registry import ToolRegistry
from ..utils.logx import log_event
from .activity_manager import ActivityManager
from .api.routes.websocket.broadcaster import WebSocketBroadcaster
from .background_tasks import BackgroundTaskManager
from .enrichment_queue import EnrichmentQueue
from .progress_manager import ProgressManager
from .service_container import ServiceConfig, ServiceContainer


class SessionManager:
    """Manages WebSocket sessions for real-time updates."""

    def __init__(self):
        self.sessions: Dict[str, WebSocket] = {}

    def connect(self, session_id: str, websocket: WebSocket):
        """Register a new WebSocket session."""
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

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected sessions."""
        disconnected_sessions = []

        for session_id, websocket in self.sessions.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                log_event(
                    "websocket_broadcast_failed",
                    {"session_id": session_id, "error": str(e)},
                    level=logging.WARNING,
                )
                disconnected_sessions.append(session_id)

        # Clean up disconnected sessions
        for session_id in disconnected_sessions:
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
        self.session_manager: Optional[SessionManager] = SessionManager()
        self.websocket_broadcaster = None
        self.activity_manager: Optional[ActivityManager] = None
        self.progress_manager: Optional[ProgressManager] = None
        self.enrichment_queue: Optional[EnrichmentQueue] = None
        self.background_tasks: Optional[BackgroundTaskManager] = None
        self.tool_registry: Optional[ToolRegistry] = None
        self.agent_tool_registry = None
        self.folder_watcher = None

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
            # log_event("application_server_init_start")

            # Phase 1: Initialize core infrastructure
            await self._init_service_container()

            # Phase 2: Run startup reconciliation
            await self._run_startup_reconciliation()

            # Phase 3: Initialize application services
            self._init_websocket_broadcaster()
            await self._init_activity_manager()
            await self._init_progress_manager()
            await self._init_enrichment_queue()
            await self._init_background_tasks()

            # Phase 4: Initialize tool registry
            await self._init_tool_registry()

            # Phase 5: Initialize agent orchestrator with tool registry
            await self._init_agent_orchestrator()

            # Phase 6: Initialize RAG service with activity manager
            self._init_rag_service()

            # Phase 6: Initialize folder watcher
            await self._init_folder_watcher()

            self._initialized = True

            # log_event(
            #     "application_server_initialized",
            #     {
            #         "websockets_enabled": self.settings.enable_websockets,
            #         "background_tasks_enabled": self.background_tasks is not None,
            #     },
            # )

        except Exception as e:
            log_event(
                "application_server_init_failed",
                {"error": str(e), "error_type": type(e).__name__},
                level=logging.ERROR,
            )
            # Cleanup on failure
            await self.cleanup()
            raise

    async def _cleanup_service(
        self,
        service: Any,
        cleanup_method: str,
        service_name: str,
    ) -> None:
        """
        Safely cleanup a service with error handling and logging.

        Args:
            service: Service instance to cleanup
            cleanup_method: Name of the cleanup method to call
            service_name: Human-readable service name for logging
        """
        if service is None:
            return

        try:
            cleanup_fn = getattr(service, cleanup_method)
            await cleanup_fn()
            log_event(f"{service_name}_cleaned_up")
        except Exception as e:
            log_event(
                f"{service_name}_cleanup_error",
                {"error": str(e)},
                level=logging.WARNING,
            )

    async def cleanup(self):
        """Cleanup all services in reverse initialization order."""
        # log_event("application_server_cleanup_start")

        await self._cleanup_service(
            self.background_tasks,
            "stop",
            "background_tasks",
        )

        await self._cleanup_service(
            self.enrichment_queue,
            "cleanup",
            "enrichment_queue",
        )

        await self._cleanup_service(
            self.progress_manager,
            "close",
            "progress_manager",
        )

        await self._cleanup_service(
            self.activity_manager,
            "close",
            "activity_manager",
        )

        if self.service_container:
            await self._cleanup_service(
                self.service_container.llm_provider_manager,
                "shutdown",
                "llm_provider_manager",
            )

        await self._cleanup_service(
            self.service_container,
            "cleanup",
            "service_container",
        )

        self._initialized = False
        log_event("application_server_cleanup_complete")

    # Initialization methods

    async def _init_service_container(self):
        """Initialize core infrastructure services."""
        vault_path = self.settings.vault_path
        if vault_path is None:
            raise RuntimeError("Vault path not configured in settings")

        config = ServiceConfig(
            redis_url=self.settings.redis_url,
            qdrant_url=self.settings.qdrant_url,
            database_url=self.settings.database_url,
            vault_path=vault_path,
            settings=self.settings,
        )

        self.service_container = ServiceContainer(config)
        await self.service_container.initialize()

        # log_event(
        #     "service_container_ready",
        #     {
        #         "vault_path": str(self.settings.vault_path),
        #         "redis_url": self.settings.redis_url,
        #         "qdrant_url": self.settings.qdrant_url,
        #     },
        # )

    async def _run_startup_reconciliation(self):
        """
        Run vault reconciliation on startup to ensure data consistency.

        This handles cases where users manually delete vault files,
        ensuring Redis/Qdrant metadata stays in sync with actual files.
        """
        try:
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

    def _init_websocket_broadcaster(self):
        """Initialize WebSocket broadcaster for conversation updates."""
        try:
            self.websocket_broadcaster = WebSocketBroadcaster()
            # log_event("websocket_broadcaster_initialized")
        except Exception as e:
            log_event(
                "websocket_broadcaster_init_failed",
                {"error": str(e)},
                level=logging.WARNING,
            )
            self.websocket_broadcaster = None

    async def _init_activity_manager(self):
        """Initialize activity event manager."""
        try:
            self.activity_manager = ActivityManager(redis_url=self.settings.redis_url)
            await self.activity_manager.initialize()
            # Link to session manager for WebSocket broadcasting
            self.activity_manager.session_manager = self.session_manager
            # log_event("activity_manager_initialized")
        except Exception as e:
            log_event(
                "activity_manager_init_failed",
                {"error": str(e)},
                level=logging.WARNING,
            )
            self.activity_manager = None

    async def _init_progress_manager(self):
        """Initialize progress tracking manager with async Redis."""
        if not self.settings.enable_websockets:
            log_event("progress_manager_disabled", {"reason": "websockets_disabled"})
            return

        try:
            self.progress_manager = ProgressManager(
                redis_url=self.settings.redis_url,
                session_manager=self.session_manager,
            )
            await self.progress_manager.initialize()
            # log_event("progress_manager_initialized")
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
            # log_event("enrichment_queue_initialized")
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
            # log_event("background_tasks_initialized")
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
            activity_manager=self.activity_manager,
        )
        await self.tool_registry.register_all()

    async def _init_agent_orchestrator(self):
        """Initialize agent orchestrator with hierarchical planning."""
        if not self.service_container:
            log_event(
                "agent_orchestrator_init_skipped",
                {"reason": "service_container_not_available"},
                level=logging.WARNING,
            )
            return

        try:
            self.service_container.init_agent_orchestrator()

            # log_event(
            #     "agent_orchestrator_initialized",
            #     {
            #         "has_tactical_planner": hasattr(self.service_container, "tactical_planner"),
            #         "has_phase_coordinator": hasattr(self.service_container, "phase_coordinator"),
            #     },
            # )
        except Exception as e:
            log_event(
                "agent_orchestrator_init_failed",
                {"error": str(e)},
                level=logging.WARNING,
            )
            raise

    def _init_rag_service(self):
        """Initialize RAG service with activity manager."""
        if not self.service_container:
            log_event(
                "rag_service_init_skipped",
                {"reason": "service_container_not_available"},
                level=logging.WARNING,
            )
            return

        try:
            self.service_container.init_rag_service(
                activity_manager=self.activity_manager
            )
            # log_event("rag_service_initialized_with_activity_manager")
        except Exception as e:
            log_event(
                "rag_service_init_failed",
                {"error": str(e)},
                level=logging.WARNING,
            )

    async def _init_folder_watcher(self):
        """Initialize folder watching service."""
        try:
            from ..storage.folder_watcher import FolderWatcherService

            if not self.service_container:
                return

            self.folder_watcher = FolderWatcherService(
                vault=self.service_container.vault,
                server=self,  # Pass self for tool execution
                redis_url=self.settings.redis_url,
                debounce_seconds=self.settings.folder_watch_debounce_seconds,
                ingestion_concurrency=self.settings.folder_watch_concurrency,
                max_folders=self.settings.folder_watch_max_folders,
            )

            # Initialize the service (async)
            await self.folder_watcher.initialize()

            # log_event(
            #     "folder_watcher_initialized",
            #     {
            #         "debounce_seconds": self.settings.folder_watch_debounce_seconds,
            #         "ingestion_concurrency": self.settings.folder_watch_concurrency,
            #         "max_folders": self.settings.folder_watch_max_folders,
            #         "auto_resume": self.settings.folder_watch_auto_resume,
            #     },
            # )
        except Exception as e:
            log_event(
                "folder_watcher_init_failed",
                {"error": str(e)},
                level=logging.WARNING,
            )
            self.folder_watcher = None

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
    def credential_service(self):
        """Get credential service from service container."""
        return (
            self.service_container.credential_service
            if self.service_container
            else None
        )

    @property
    def llm_manager(self):
        """Get LLM provider manager from service container (alias for compatibility)."""
        return (
            self.service_container.llm_provider_manager
            if self.service_container
            else None
        )

    @property
    def provider_loader(self):
        """Get provider loader (created on-demand from credential service)."""
        if not self.credential_service:
            return None

        # Create loader on-demand
        from ..llm import ProviderLoader

        return ProviderLoader(self.credential_service)

    @property
    def is_initialized(self) -> bool:
        """Check if server is initialized."""
        return self._initialized
