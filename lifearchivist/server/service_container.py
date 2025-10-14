"""
Service container for dependency injection and lifecycle management.

This module provides centralized service initialization and management,
ensuring all services are properly initialized before use and cleaned up on shutdown.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import redis.asyncio as redis
from qdrant_client import QdrantClient

from ..config.settings import Settings
from ..storage.bm25_index_service import BM25IndexService
from ..storage.redis_document_tracker import RedisDocumentTracker
from ..storage.vault.vault import Vault
from ..utils.logging import log_event


@dataclass
class ServiceConfig:
    """
    Configuration for all core services.

    This centralizes configuration needed to initialize services,
    making dependencies explicit and easy to modify.
    """

    redis_url: str
    qdrant_url: str
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
        self.vault: Optional[Vault] = None
        self.doc_tracker: Optional[RedisDocumentTracker] = None
        self.bm25_service: Optional[BM25IndexService] = None
        self.llamaindex_service = None  # Will be LlamaIndexQdrantService

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
                    "vault_path": str(self.config.vault_path),
                },
            )

            # Phase 1: External connections
            await self._init_redis()
            self._init_qdrant()  # Synchronous - Qdrant client is not async

            # Phase 2: Storage services
            await self._init_vault()

            # Phase 3: Index services (depend on Redis/Qdrant)
            await self._init_doc_tracker()
            await self._init_bm25()

            # Phase 4: High-level services (depend on everything)
            await self._init_llamaindex()

            self._initialized = True

            log_event(
                "service_container_initialized",
                {
                    "services": [
                        "redis",
                        "qdrant",
                        "vault",
                        "doc_tracker",
                        "bm25",
                        "llamaindex",
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
            await self.llamaindex_service.ensure_initialized()

            # Get document count for logging
            count_result = await self.llamaindex_service.get_document_count()
            doc_count = count_result.value if count_result.is_success() else 0

            log_event("llamaindex_initialized", {"document_count": doc_count})

        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to initialize LlamaIndex service: {str(e)}"
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
