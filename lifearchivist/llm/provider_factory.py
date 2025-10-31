"""
Provider Factory - Constructs provider manager with dependencies.

Provides convenient factory methods for creating fully-configured
provider managers with all necessary services.
"""

import logging
from typing import Optional

from redis.asyncio import Redis

from ..storage.credential_service import CredentialService
from ..utils.logging import log_event
from .cost_tracker import CostTracker
from .provider_health_monitor import ProviderHealthMonitor
from .provider_loader import ProviderLoader
from .provider_manager import LLMProviderManager
from .provider_registry import ProviderRegistry
from .provider_router import ProviderRouter

logger = logging.getLogger(__name__)


class ProviderManagerFactory:
    """
    Factory for creating configured LLMProviderManager instances.

    Handles dependency injection and configuration of all services.
    """

    @staticmethod
    def create(
        redis_client: Optional[Redis] = None,
        enable_cost_tracking: bool = True,
        enable_health_monitoring: bool = True,
        health_check_interval: int = 60,
        health_failure_threshold: int = 3,
        auto_disable_unhealthy: bool = True,
    ) -> LLMProviderManager:
        """
        Create a fully-configured provider manager.

        Args:
            redis_client: Redis client for cost tracking (required if cost tracking enabled)
            enable_cost_tracking: Enable cost tracking and budget enforcement
            enable_health_monitoring: Enable provider health monitoring
            health_check_interval: Seconds between health checks
            health_failure_threshold: Consecutive failures before marking unhealthy
            auto_disable_unhealthy: Automatically disable unhealthy providers

        Returns:
            Configured LLMProviderManager instance

        Raises:
            ValueError: If cost tracking enabled but no Redis client provided

        Example:
            >>> from redis.asyncio import Redis
            >>> redis = Redis.from_url("redis://localhost:6379")
            >>> manager = ProviderManagerFactory.create(
            ...     redis_client=redis,
            ...     enable_cost_tracking=True,
            ...     enable_health_monitoring=True,
            ... )
        """
        # Create core services
        registry = ProviderRegistry()
        router = ProviderRouter(registry)

        # Create optional services
        cost_tracker = None
        if enable_cost_tracking:
            if redis_client is None:
                raise ValueError(
                    "Redis client required for cost tracking. "
                    "Either provide redis_client or set enable_cost_tracking=False"
                )
            cost_tracker = CostTracker(redis_client)

        health_monitor = None
        if enable_health_monitoring:
            health_monitor = ProviderHealthMonitor(
                registry=registry,
                check_interval_seconds=health_check_interval,
                failure_threshold=health_failure_threshold,
                auto_disable=auto_disable_unhealthy,
            )

        # Create manager
        manager = LLMProviderManager(
            registry=registry,
            router=router,
            cost_tracker=cost_tracker,
            health_monitor=health_monitor,
        )

        log_event(
            "provider_manager_created",
            {
                "cost_tracking": enable_cost_tracking,
                "health_monitoring": enable_health_monitoring,
            },
        )

        return manager

    @staticmethod
    def create_minimal() -> LLMProviderManager:
        """
        Create a minimal provider manager without optional services.

        Useful for testing or simple use cases that don't need
        cost tracking or health monitoring.

        Returns:
            Minimal LLMProviderManager instance

        Example:
            >>> manager = ProviderManagerFactory.create_minimal()
            >>> # Add providers manually
            >>> manager.add_provider(my_provider)
        """
        registry = ProviderRegistry()
        router = ProviderRouter(registry)

        manager = LLMProviderManager(
            registry=registry,
            router=router,
            cost_tracker=None,
            health_monitor=None,
        )

        log_event("provider_manager_created_minimal")

        return manager

    @staticmethod
    def create_with_cost_tracking(redis_client: Redis) -> LLMProviderManager:
        """
        Create provider manager with cost tracking only.

        Args:
            redis_client: Redis client for cost persistence

        Returns:
            LLMProviderManager with cost tracking enabled

        Example:
            >>> from redis.asyncio import Redis
            >>> redis = Redis.from_url("redis://localhost:6379")
            >>> manager = ProviderManagerFactory.create_with_cost_tracking(redis)
        """
        return ProviderManagerFactory.create(
            redis_client=redis_client,
            enable_cost_tracking=True,
            enable_health_monitoring=False,
        )

    @staticmethod
    def create_with_health_monitoring(
        health_check_interval: int = 60,
        failure_threshold: int = 3,
    ) -> LLMProviderManager:
        """
        Create provider manager with health monitoring only.

        Args:
            health_check_interval: Seconds between health checks
            failure_threshold: Consecutive failures before marking unhealthy

        Returns:
            LLMProviderManager with health monitoring enabled

        Example:
            >>> manager = ProviderManagerFactory.create_with_health_monitoring(
            ...     health_check_interval=30,
            ...     failure_threshold=5,
            ... )
        """
        return ProviderManagerFactory.create(
            redis_client=None,
            enable_cost_tracking=False,
            enable_health_monitoring=True,
            health_check_interval=health_check_interval,
            health_failure_threshold=failure_threshold,
        )

    @staticmethod
    async def create_with_stored_providers(
        credential_service: CredentialService,
        redis_client: Optional[Redis] = None,
        enable_cost_tracking: bool = True,
        enable_health_monitoring: bool = True,
        user_id: str = "default",
    ) -> LLMProviderManager:
        """
        Create provider manager and load all stored providers.

        This is the recommended way to initialize the provider manager
        in production. It creates the manager with all services and
        automatically loads all stored provider configurations.

        Args:
            credential_service: Service for credential storage
            redis_client: Redis client for cost tracking
            enable_cost_tracking: Enable cost tracking
            enable_health_monitoring: Enable health monitoring
            user_id: User ID to load providers for

        Returns:
            Initialized LLMProviderManager with loaded providers

        Raises:
            RuntimeError: If manager initialization fails

        Example:
            >>> from redis.asyncio import Redis
            >>> redis = Redis.from_url("redis://localhost:6379")
            >>> manager = await ProviderManagerFactory.create_with_stored_providers(
            ...     credential_service=credential_service,
            ...     redis_client=redis,
            ... )
            >>> # Manager is ready with all stored providers loaded
        """
        # Create manager
        manager = ProviderManagerFactory.create(
            redis_client=redis_client,
            enable_cost_tracking=enable_cost_tracking,
            enable_health_monitoring=enable_health_monitoring,
        )

        # Initialize manager
        init_result = await manager.initialize()
        if init_result.is_failure():
            error_msg = init_result.error_or("Unknown error")
            raise RuntimeError(f"Failed to initialize manager: {error_msg}")

        # Load all stored providers
        loader = ProviderLoader(credential_service)
        load_result = await loader.load_all_providers(user_id)

        if load_result.is_failure():
            error_msg = load_result.error_or("Unknown error")
            log_event(
                "provider_factory_load_failed",
                {
                    "error": error_msg,
                    "user_id": user_id,
                },
                level=logging.ERROR,
            )
            # Don't fail - manager is still usable, just no providers loaded
            providers = []
        else:
            providers = load_result.unwrap()

        # Add each provider to manager
        for provider in providers:
            add_result = await manager.add_provider(provider)
            if add_result.is_failure():
                error_msg = add_result.error_or("Unknown error")
                log_event(
                    "provider_factory_add_failed",
                    {
                        "provider_id": provider.provider_id,
                        "error": error_msg,
                    },
                    level=logging.WARNING,
                )
                # Continue with other providers

        # If no providers loaded, create default Ollama provider
        if len(providers) == 0:
            try:
                from ..config import get_settings
                from .base_provider import ProviderType
                from .provider_config import OllamaConfig
                from .providers.ollama_provider import OllamaProvider

                settings = get_settings()

                # Create typed config
                ollama_config = OllamaConfig(
                    base_url=settings.ollama_url,
                )

                # Create provider instance
                ollama_provider = OllamaProvider(
                    provider_id="ollama-default",
                    config=ollama_config,
                )

                # Initialize provider
                await ollama_provider.initialize()

                # Add to manager
                add_result = await manager.add_provider(
                    ollama_provider, set_as_default=True
                )
                if add_result.is_success():
                    # Store in credential service for persistence
                    store_result = await credential_service.add_provider(
                        provider_id="ollama-default",
                        provider_type=ProviderType.OLLAMA,
                        config=ollama_config,
                        is_default=True,
                        user_id=user_id,
                    )
                    if store_result.is_success():
                        log_event(
                            "default_ollama_provider_created",
                            {
                                "provider_id": "ollama-default",
                                "base_url": settings.ollama_url,
                            },
                        )
                    else:
                        error_msg = store_result.error_or("Unknown error")
                        log_event(
                            "default_ollama_provider_store_failed",
                            {"error": error_msg},
                            level=logging.WARNING,
                        )
                else:
                    error_msg = add_result.error_or("Unknown error")
                    log_event(
                        "default_ollama_provider_add_failed",
                        {"error": error_msg},
                        level=logging.WARNING,
                    )
            except Exception as e:
                import traceback

                tb = traceback.format_exc()
                # Print to stderr so it shows in logs
                print(
                    f"ERROR: Failed to create default Ollama provider: {e}", flush=True
                )
                print(f"Traceback:\n{tb}", flush=True)
                log_event(
                    "default_ollama_provider_creation_failed",
                    {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "traceback": tb,
                    },
                    level=logging.ERROR,
                )

        log_event(
            "provider_factory_created_with_providers",
            {
                "providers_loaded": len(providers),
                "user_id": user_id,
            },
        )

        return manager
