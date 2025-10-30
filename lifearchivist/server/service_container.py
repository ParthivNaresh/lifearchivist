"""
Service container for dependency injection and lifecycle management.

This module provides centralized service initialization and management,
ensuring all services are properly initialized before use and cleaned up on shutdown.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import asyncpg
import redis.asyncio as redis
from qdrant_client import QdrantClient

from ..config.settings import Settings
from ..llm import LLMProviderManager
from ..storage.bm25_index_service import BM25IndexService
from ..storage.credential_service import CredentialService
from ..storage.database import ConversationService, MessageService
from ..storage.redis_document_tracker import RedisDocumentTracker
from ..storage.vault.vault import Vault
from ..utils.logging import log_event

if TYPE_CHECKING:
    # Import for type checking only to avoid runtime circular import
    from ..rag import ConversationRAGService
    from ..storage.llamaindex_service import LlamaIndexService
    from .activity_manager import ActivityManager


@dataclass
class ServiceConfig:
    """
    Configuration for all core services.

    This centralizes configuration needed to initialize services,
    making dependencies explicit and easy to modify.
    """

    redis_url: str
    qdrant_url: str
    database_url: str
    vault_path: Path
    settings: Settings


class ServiceInitializationError(Exception):
    """Raised when service initialization fails."""

    pass


class ServiceContainer:
    """
    Container for core infrastructure services.

    Manages the lifecycle of:
    - Redis client (metadata storage)
    - Qdrant client (vector storage)
    - Vault (file storage)
    - Document tracker (Redis-based)
    - BM25 service (keyword search)
    - LlamaIndex service (orchestration)

    All services are guaranteed to be initialized (never None) after
    calling initialize(). Services are initialized in dependency order
    and cleaned up in reverse order.

    Usage:
        config = ServiceConfig(...)
        container = ServiceContainer(config)
        await container.initialize()

        # All services guaranteed to exist
        result = await container.llamaindex_service.add_document(...)

        # Cleanup
        await container.cleanup()

    Or use as async context manager:
        async with ServiceContainer(config) as container:
            await container.llamaindex_service.add_document(...)
    """

    def __init__(self, config: ServiceConfig):
        """
        Initialize container with configuration.

        Args:
            config: Service configuration
        """
        self.config = config
        self._initialized = False

        # Core services - will be initialized, never None after initialize()
        self.redis_client: Optional[redis.Redis] = None
        self.qdrant_client: Optional[QdrantClient] = None
        self.db_pool: Optional[asyncpg.Pool] = None
        self.vault: Optional[Vault] = None
        self.doc_tracker: Optional[RedisDocumentTracker] = None
        self.bm25_service: Optional[BM25IndexService] = None
        self.llamaindex_service: Optional["LlamaIndexService"] = None

        # Conversation services
        self.conversation_service: Optional["ConversationService"] = None
        self.message_service: Optional["MessageService"] = None

        # LLM provider services
        self.credential_service: Optional["CredentialService"] = None
        self.llm_provider_manager: Optional["LLMProviderManager"] = None

        # RAG service
        self.rag_service: Optional["ConversationRAGService"] = None

    async def initialize(self) -> None:
        """
        Initialize all services in correct dependency order.

        Initialization phases:
        1. External connections (Redis, Qdrant)
        2. Storage services (Vault)
        3. Index services (DocTracker, BM25) - depend on Redis
        4. High-level services (LlamaIndex) - depend on everything

        Raises:
            ServiceInitializationError: If any service fails to initialize
        """
        if self._initialized:
            log_event(
                "service_container_already_initialized",
                level=logging.WARNING,
            )
            return

        try:
            log_event(
                "service_container_init_start",
                {
                    "redis_url": self.config.redis_url,
                    "qdrant_url": self.config.qdrant_url,
                    "database_url": self._mask_db_password(self.config.database_url),
                    "vault_path": str(self.config.vault_path),
                },
            )

            # Phase 1: External connections
            await self._init_redis()
            self._init_qdrant()  # Synchronous - Qdrant client is not async
            await self._init_database()

            # Phase 2: Storage services
            await self._init_vault()

            # Phase 3: Index services (depend on Redis/Qdrant)
            await self._init_doc_tracker()
            await self._init_bm25()

            # Phase 3.5: LLM provider services (depend on Redis)
            await self._init_credential_service()
            await self._init_llm_provider_manager()

            # Phase 4: High-level services (depend on everything)
            await self._init_llamaindex()
            self._init_conversation_service()
            self._init_message_service()

            # Note: RAG service will be initialized later with activity_manager from ApplicationServer

            self._initialized = True

            log_event(
                "service_container_initialized",
                {
                    "services": [
                        "redis",
                        "qdrant",
                        "database",
                        "vault",
                        "doc_tracker",
                        "bm25",
                        "credential_service",
                        "llm_provider_manager",
                        "llamaindex",
                        "conversation",
                        "message",
                        "rag_service",
                    ],
                    "status": "ready",
                },
            )

        except Exception as e:
            log_event(
                "service_container_init_failed",
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
            # Cleanup on failure
            await self.cleanup()
            raise ServiceInitializationError(
                f"Failed to initialize services: {str(e)}"
            ) from e

    async def cleanup(self) -> None:
        """
        Cleanup all services in reverse initialization order.

        This ensures proper resource cleanup even if some services
        failed to initialize.
        """
        log_event("service_container_cleanup_start")

        # Cleanup in reverse order
        # RAG service doesn't need explicit cleanup
        # Conversation service doesn't need explicit cleanup (uses db_pool)

        if self.llamaindex_service:
            try:
                await self.llamaindex_service.cleanup()
                log_event("llamaindex_service_cleaned_up")
            except Exception as e:
                log_event(
                    "llamaindex_cleanup_error",
                    {"error": str(e)},
                    level=logging.WARNING,
                )

        if self.bm25_service:
            try:
                await self.bm25_service.close()
                log_event("bm25_service_cleaned_up")
            except Exception as e:
                log_event(
                    "bm25_cleanup_error",
                    {"error": str(e)},
                    level=logging.WARNING,
                )

        if self.doc_tracker:
            try:
                await self.doc_tracker.close()
                log_event("doc_tracker_cleaned_up")
            except Exception as e:
                log_event(
                    "doc_tracker_cleanup_error",
                    {"error": str(e)},
                    level=logging.WARNING,
                )

        # Vault doesn't need explicit cleanup currently

        if self.db_pool:
            try:
                await self.db_pool.close()
                log_event("database_pool_cleaned_up")
            except Exception as e:
                log_event(
                    "database_cleanup_error",
                    {"error": str(e)},
                    level=logging.WARNING,
                )

        if self.redis_client:
            try:
                await self.redis_client.aclose()
                log_event("redis_client_cleaned_up")
            except Exception as e:
                log_event(
                    "redis_cleanup_error",
                    {"error": str(e)},
                    level=logging.WARNING,
                )

        # Qdrant client doesn't need explicit cleanup

        self._initialized = False
        log_event("service_container_cleanup_complete")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
        return False  # Don't suppress exceptions

    # Private initialization methods

    async def _init_redis(self) -> None:
        """Initialize Redis client with connection pooling."""
        try:
            self.redis_client = redis.from_url(
                self.config.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_keepalive=True,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                max_connections=50,  # Explicit pool size for high concurrency
            )

            # Test connection
            await self.redis_client.ping()

            log_event("redis_initialized", {"url": self.config.redis_url})

        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to initialize Redis: {str(e)}"
            ) from e

    def _init_qdrant(self) -> None:
        """
        Initialize Qdrant client.

        Note: This is synchronous because the official qdrant-client library
        uses synchronous operations for client initialization and connection
        testing. The blocking is minimal (one HTTP call to get collections).

        For truly async Qdrant operations, consider using AsyncQdrantClient
        when it becomes available in the official library.
        """
        try:
            self.qdrant_client = QdrantClient(
                url=self.config.qdrant_url,
                check_compatibility=False,  # Suppress version warnings
            )

            # Test connection by getting collections (synchronous HTTP call)
            collections = self.qdrant_client.get_collections()

            log_event(
                "qdrant_initialized",
                {
                    "url": self.config.qdrant_url,
                    "collections": len(collections.collections),
                },
            )

        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to initialize Qdrant: {str(e)}"
            ) from e

    async def _init_database(self) -> None:
        """
        Initialize PostgreSQL connection pool.

        Creates an asyncpg connection pool with production-grade settings:
        - Connection pooling for performance
        - Automatic reconnection on failure
        - Statement caching for repeated queries
        - Prepared statement support
        - Connection timeout handling
        """
        try:
            self.db_pool = await asyncpg.create_pool(
                self.config.database_url,
                min_size=5,  # Minimum connections to maintain
                max_size=20,  # Maximum connections (adjust based on load)
                max_queries=50000,  # Recycle connection after N queries
                max_inactive_connection_lifetime=300.0,  # 5 minutes
                command_timeout=60.0,  # Query timeout
                server_settings={
                    "application_name": "lifearchivist",
                    "jit": "off",  # Disable JIT for faster simple queries
                    "timezone": "UTC",
                },
            )

            # Test connection
            async with self.db_pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                pool_size = self.db_pool.get_size()

                log_event(
                    "database_initialized",
                    {
                        "url": self._mask_db_password(self.config.database_url),
                        "pool_min_size": 5,
                        "pool_max_size": 20,
                        "pool_current_size": pool_size,
                        "postgres_version": (
                            version.split(",")[0] if version else "unknown"
                        ),
                    },
                )

        except asyncpg.InvalidCatalogNameError:
            # Database doesn't exist - provide helpful error
            raise ServiceInitializationError(
                "Database does not exist. Please ensure PostgreSQL is running "
                "and the database has been created. "
                "Run: docker-compose up postgres -d"
            ) from None
        except asyncpg.InvalidPasswordError:
            raise ServiceInitializationError(
                "Invalid database credentials. Check LIFEARCH_DATABASE_URL."
            ) from None
        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to initialize database pool: {str(e)}"
            ) from e

    async def _init_vault(self) -> None:
        """Initialize vault storage."""
        try:
            self.vault = Vault(self.config.vault_path)
            await self.vault.initialize()

            log_event("vault_initialized", {"path": str(self.config.vault_path)})

        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to initialize Vault: {str(e)}"
            ) from e

    async def _init_doc_tracker(self) -> None:
        """Initialize Redis document tracker."""
        try:
            self.doc_tracker = RedisDocumentTracker(redis_url=self.config.redis_url)
            await self.doc_tracker.initialize()

            doc_count = await self.doc_tracker.get_document_count()

            log_event("doc_tracker_initialized", {"document_count": doc_count})

        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to initialize document tracker: {str(e)}"
            ) from e

    async def _init_bm25(self) -> None:
        """Initialize BM25 index service."""
        try:
            self.bm25_service = BM25IndexService(
                redis_url=self.config.redis_url,
                use_stemming=False,  # Can enable if nltk is installed
                remove_stop_words=True,
            )
            await self.bm25_service.initialize()

            doc_count = await self.bm25_service.get_document_count()

            log_event("bm25_initialized", {"document_count": doc_count})

        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to initialize BM25 service: {str(e)}"
            ) from e

    async def _init_llamaindex(self) -> None:
        """Initialize LlamaIndex service with all dependencies."""
        try:
            # Import here to avoid circular dependencies
            from ..storage.llamaindex_service import LlamaIndexService

            # Create service with all dependencies
            self.llamaindex_service = LlamaIndexService(
                database=None,  # Not used currently
                vault=self.vault,
            )

            # Ensure async initialization
            li = self.llamaindex_service
            if li is None:
                raise ServiceInitializationError(
                    "LlamaIndex service failed to construct"
                )
            await li.ensure_initialized()

            # Get document count for logging
            count_result = await li.get_document_count()
            if count_result.is_success() and hasattr(count_result, "value"):
                doc_count = count_result.value
            else:
                doc_count = 0

            log_event("llamaindex_initialized", {"document_count": doc_count})

        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to initialize LlamaIndex service: {str(e)}"
            ) from e

    def _init_conversation_service(self) -> None:
        """Initialize conversation service with database pool."""
        try:
            from ..storage.database import ConversationService

            if not self.db_pool:
                raise ServiceInitializationError(
                    "Database pool must be initialized before conversation service"
                )

            self.conversation_service = ConversationService(db_pool=self.db_pool)

            log_event("conversation_service_initialized")

        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to initialize conversation service: {str(e)}"
            ) from e

    def _init_message_service(self) -> None:
        """Initialize message service with database pool."""
        try:
            from ..storage.database import MessageService

            if not self.db_pool:
                raise ServiceInitializationError(
                    "Database pool must be initialized before message service"
                )

            self.message_service = MessageService(db_pool=self.db_pool)

            log_event("message_service_initialized")

        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to initialize message service: {str(e)}"
            ) from e

    async def _init_credential_service(self) -> None:
        """
        Initialize credential service for API key storage.

        Stores provider credentials in Redis for persistence across restarts.
        """
        try:
            from ..storage.credential_service import CredentialService

            if not self.redis_client:
                raise ServiceInitializationError(
                    "Redis client must be initialized before credential service"
                )

            self.credential_service = CredentialService(redis_client=self.redis_client)

            log_event("credential_service_initialized")

        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to initialize credential service: {str(e)}"
            ) from e

    async def _init_llm_provider_manager(self) -> None:
        """Initialize LLM provider manager with stored providers."""
        try:
            from ..llm import ProviderManagerFactory

            if not self.credential_service:
                raise ServiceInitializationError(
                    "Credential service must be initialized before provider manager"
                )

            if not self.redis_client:
                raise ServiceInitializationError(
                    "Redis client must be initialized before provider manager"
                )

            # Create manager with all services and load stored providers
            self.llm_provider_manager = (
                await ProviderManagerFactory.create_with_stored_providers(
                    credential_service=self.credential_service,
                    redis_client=self.redis_client,
                    enable_cost_tracking=True,
                    enable_health_monitoring=True,
                )
            )

            provider_count = self.llm_provider_manager.registry.count()
            default_provider = self.llm_provider_manager.registry.get_default_id()

            log_event(
                "llm_provider_manager_initialized",
                {
                    "providers_loaded": provider_count,
                    "default_provider": default_provider,
                    "cost_tracking": True,
                    "health_monitoring": True,
                },
            )

        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to initialize LLM provider manager: {str(e)}"
            ) from e

    @property
    def is_initialized(self) -> bool:
        """Check if container is initialized."""
        return self._initialized

    def require_initialized(self) -> None:
        """
        Raise error if container not initialized.

        Use this in methods that require initialized services.

        Raises:
            RuntimeError: If container not initialized
        """
        if not self._initialized:
            raise RuntimeError(
                "ServiceContainer not initialized. "
                "Call await container.initialize() first."
            )

    def _mask_db_password(self, url: str) -> str:
        """
        Mask password in database URL for logging.

        Args:
            url: Database URL (e.g., postgresql://user:pass@host:port/db)

        Returns:
            URL with password masked (e.g., postgresql://user:****@host:port/db)
        """
        try:
            if "://" not in url:
                return url

            protocol, rest = url.split("://", 1)

            if "@" not in rest:
                return url  # No credentials

            credentials, host_part = rest.split("@", 1)

            if ":" in credentials:
                username, _ = credentials.split(":", 1)
                return f"{protocol}://{username}:****@{host_part}"

            return url
        except Exception:
            return "postgresql://****:****@****:****/****"

    async def init_rag_service(
        self, activity_manager: Optional["ActivityManager"] = None
    ) -> None:
        """
        Initialize RAG service with dependencies.

        This is called separately after ServiceContainer initialization
        to allow passing in the ActivityManager from ApplicationServer.

        Args:
            activity_manager: Optional activity manager for event tracking
        """
        try:
            from ..rag import ConversationRAGService

            if not self._initialized:
                raise ServiceInitializationError(
                    "ServiceContainer must be initialized before RAG service"
                )

            if not self.llamaindex_service:
                raise ServiceInitializationError(
                    "LlamaIndex service must be initialized before RAG service"
                )

            if not self.llm_provider_manager:
                raise ServiceInitializationError(
                    "LLM provider manager must be initialized before RAG service"
                )

            if not self.conversation_service:
                raise ServiceInitializationError(
                    "Conversation service must be initialized before RAG service"
                )

            if not self.message_service:
                raise ServiceInitializationError(
                    "Message service must be initialized before RAG service"
                )

            if not self.llamaindex_service.query_service:
                raise ServiceInitializationError(
                    "LlamaIndex query service must be initialized before RAG service"
                )

            self.rag_service = ConversationRAGService(
                query_service=self.llamaindex_service.query_service,
                provider_manager=self.llm_provider_manager,
                conversation_service=self.conversation_service,
                message_service=self.message_service,
                activity_manager=activity_manager,
            )

            log_event(
                "rag_service_initialized",
                {"has_activity_manager": activity_manager is not None},
            )

        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to initialize RAG service: {str(e)}"
            ) from e
