"""
LLM Provider Manager - Orchestrates provider operations.

Coordinates between registry, router, cost tracker, and health monitor.
This is the main entry point for all LLM operations.
"""

import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, cast

from ..utils.logging import log_event, track
from ..utils.result import Failure, Result, Success
from .base_provider import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
    ModelInfo,
)
from .constants import ErrorMessages, TokenEstimation, UserDefaults
from .cost_tracker import CostRecord, CostTracker
from .provider_health_monitor import ProviderHealthMonitor
from .provider_metadata import (
    CostReport,
    MetadataCapability,
    UsageReport,
    Workspace,
)
from .provider_registry import ProviderRegistry
from .provider_router import ProviderRouter, RoutingStrategy

logger = logging.getLogger(__name__)


class LLMProviderManager:
    """
    Orchestrates LLM provider operations.

    Delegates responsibilities to specialized services:
    - ProviderRegistry: Manages provider instances
    - ProviderRouter: Routes requests to providers
    - CostTracker: Tracks and enforces costs
    - ProviderHealthMonitor: Monitors provider health

    This class focuses on coordination and high-level operations.

    Supports async context manager protocol for automatic lifecycle management:
        async with manager:
            await manager.initialize()
            # ... use manager ...
        # Automatically calls shutdown() on exit
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        router: ProviderRouter,
        cost_tracker: Optional[CostTracker] = None,
        health_monitor: Optional[ProviderHealthMonitor] = None,
    ):
        """
        Initialize provider manager with dependencies.

        Args:
            registry: Provider registry instance
            router: Provider router instance
            cost_tracker: Optional cost tracker
            health_monitor: Optional health monitor
        """
        self.registry = registry
        self.router = router
        self.cost_tracker = cost_tracker
        self.health_monitor = health_monitor
        self._initialized = False

    async def __aenter__(self) -> "LLMProviderManager":
        """Enter async context manager."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager and cleanup resources."""
        await self.shutdown()

    async def initialize(self) -> Result[None, str]:
        """
        Initialize the provider manager.

        Starts health monitoring if configured.

        Returns:
            Result indicating success or failure
        """
        if self._initialized:
            log_event(
                "provider_manager_already_initialized",
                level=logging.WARNING,
            )
            return Success(None)

        try:
            # Start health monitoring if available
            if self.health_monitor:
                await self.health_monitor.start()

            self._initialized = True

            log_event(
                "provider_manager_initialized",
                {
                    "providers": self.registry.count(),
                    "has_cost_tracker": self.cost_tracker is not None,
                    "has_health_monitor": self.health_monitor is not None,
                },
            )

            return Success(None)

        except Exception as e:
            log_event(
                "provider_manager_init_failed",
                {"error": str(e), "error_type": type(e).__name__},
                level=logging.ERROR,
            )
            return Failure(
                error=f"Failed to initialize provider manager: {e}",
                error_type=type(e).__name__,
                status_code=500,
            )

    async def shutdown(self) -> None:
        """
        Shutdown the provider manager.

        Stops health monitoring and cleans up all provider resources.
        """
        if not self._initialized:
            return

        try:
            # Stop health monitoring
            if self.health_monitor:
                await self.health_monitor.stop()

            # Clean up all providers
            providers_cleaned = await self.registry.clear()

            self._initialized = False

            log_event(
                "provider_manager_shutdown",
                {"providers_cleaned": providers_cleaned},
            )

        except Exception as e:
            log_event(
                "provider_manager_shutdown_error",
                {"error": str(e)},
                level=logging.ERROR,
            )

    async def add_provider(
        self,
        provider: BaseLLMProvider,
        set_as_default: bool = False,
    ) -> Result[None, str]:
        """
        Add a provider to the manager.

        Initializes the provider before adding it to the registry.

        Args:
            provider: Provider instance to add
            set_as_default: Whether to set as default provider

        Returns:
            Result indicating success or failure
        """
        result = await self.registry.register(provider, set_as_default)

        if result.is_success():
            log_event(
                "provider_added",
                {
                    "provider_id": provider.provider_id,
                    "provider_type": provider.provider_type.value,
                    "is_default": set_as_default,
                },
            )

        return result

    async def remove_provider(self, provider_id: str) -> Result[BaseLLMProvider, str]:
        """
        Remove a provider from the manager.

        Cleans up provider resources before removal.

        Args:
            provider_id: Provider identifier

        Returns:
            Result with removed provider or error
        """
        return await self.registry.unregister(provider_id)

    def get_provider(
        self, provider_id: Optional[str] = None
    ) -> Optional[BaseLLMProvider]:
        """
        Get a provider by ID, or default if None.

        Args:
            provider_id: Provider ID, or None for default

        Returns:
            Provider instance or None if not found
        """
        return self.registry.get(provider_id)

    def list_providers(self) -> List[Dict[str, Any]]:
        """
        List all registered providers with metadata.

        Returns:
            List of provider information dictionaries
        """
        providers = self.registry.list_all()
        default_id = self.registry.get_default_id()

        return [
            {
                "id": provider.provider_id,
                "type": provider.provider_type.value,
                "name": provider.get_provider_name(),
                "is_default": provider.provider_id == default_id,
                "is_healthy": (
                    self.health_monitor.is_healthy(provider.provider_id)
                    if self.health_monitor
                    else True
                ),
                "is_admin": (
                    getattr(provider.metadata, "is_admin_key", False)
                    if provider.metadata
                    else False
                ),
            }
            for provider in providers
        ]

    def set_default_provider(self, provider_id: str) -> Result[None, str]:
        """
        Set the default provider.

        Args:
            provider_id: Provider ID to set as default

        Returns:
            Result indicating success or failure
        """
        return self.registry.set_default(provider_id)

    @track(
        operation="llm_generate",
        include_args=["model", "provider_id"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def generate(
        self,
        messages: List[LLMMessage],
        model: str,
        provider_id: Optional[str] = None,
        routing_strategy: RoutingStrategy = RoutingStrategy.DEFAULT,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        user_id: str = UserDefaults.DEFAULT_USER_ID,
        **kwargs,
    ) -> Result[LLMResponse, str]:
        """
        Generate a response using specified or routed provider.

        Args:
            messages: Conversation messages
            model: Model identifier
            provider_id: Explicit provider ID (overrides routing)
            routing_strategy: Strategy for provider selection
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            user_id: User making the request
            **kwargs: Additional provider-specific parameters

        Returns:
            Result with LLMResponse or error
        """
        # Route to provider
        route_result = self.router.route(
            provider_id=provider_id,
            strategy=routing_strategy,
            model=model,
        )

        if route_result.is_failure():
            error_msg = route_result.error_or("Failed to route request")
            return Failure(
                error=error_msg,
                error_type="RoutingError",
                status_code=503,
            )

        provider = route_result.unwrap()

        # Check provider health
        if self.health_monitor and not self.health_monitor.is_healthy(
            provider.provider_id
        ):
            log_event(
                "provider_unhealthy",
                {"provider_id": provider.provider_id},
                level=logging.WARNING,
            )
            return Failure(
                error=ErrorMessages.PROVIDER_UNHEALTHY.format(
                    provider_id=provider.provider_id
                ),
                error_type="ProviderUnhealthy",
                status_code=503,
            )

        # Estimate cost and check budget
        if self.cost_tracker:
            # Rough estimate: assume average tokens
            estimated_tokens = (
                len(str(messages)) // TokenEstimation.CHARS_PER_TOKEN
            )  # Rough token estimate
            estimated_cost = provider.estimate_cost(estimated_tokens, max_tokens, model)

            budget_check = await self.cost_tracker.check_budget(user_id, estimated_cost)
            if budget_check.is_failure():
                error_msg = budget_check.error_or("Budget check failed")
                return Failure(
                    error=error_msg,
                    error_type="BudgetExceeded",
                    status_code=402,
                )

        # Execute request
        try:
            log_event(
                "llm_generate_start",
                {
                    "provider_id": provider.provider_id,
                    "provider_type": provider.provider_type.value,
                    "model": model,
                    "message_count": len(messages),
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )

            response = await provider.generate(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            # Record cost
            if self.cost_tracker and response.cost_usd is not None:
                cost_record = CostRecord(
                    provider_id=provider.provider_id,
                    provider_type=provider.provider_type.value,
                    model=model,
                    prompt_tokens=response.prompt_tokens or 0,
                    completion_tokens=response.completion_tokens or 0,
                    cost_usd=response.cost_usd,
                    timestamp=datetime.now(),
                    user_id=user_id,
                )
                await self.cost_tracker.record_cost(cost_record)

            log_event(
                "llm_generate_success",
                {
                    "provider_id": provider.provider_id,
                    "model": model,
                    "tokens_used": response.tokens_used,
                    "cost_usd": response.cost_usd,
                    "finish_reason": response.finish_reason,
                },
            )

            return Success(response)

        except Exception as e:
            log_event(
                "llm_generate_failed",
                {
                    "provider_id": provider.provider_id,
                    "model": model,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )

            return Failure(
                error=str(e),
                error_type=type(e).__name__,
                status_code=500,
                context={
                    "provider_id": provider.provider_id,
                    "model": model,
                },
            )

    @track(
        operation="llm_generate_stream",
        include_args=["model", "provider_id"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def generate_stream(
        self,
        messages: List[LLMMessage],
        model: str,
        provider_id: Optional[str] = None,
        routing_strategy: RoutingStrategy = RoutingStrategy.DEFAULT,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        user_id: str = UserDefaults.DEFAULT_USER_ID,
        **kwargs,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Stream a response using specified or routed provider.

        Args:
            messages: Conversation messages
            model: Model identifier
            provider_id: Explicit provider ID (overrides routing)
            routing_strategy: Strategy for provider selection
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            user_id: User making the request
            **kwargs: Additional provider-specific parameters

        Yields:
            LLMStreamChunk objects with incremental content

        Raises:
            RuntimeError: If provider not available or unhealthy
        """
        # Route to provider
        route_result = self.router.route(
            provider_id=provider_id,
            strategy=routing_strategy,
            model=model,
        )

        if route_result.is_failure():
            error_msg = route_result.error_or("Failed to route request")
            log_event(
                "llm_stream_routing_failed",
                {"error": error_msg},
                level=logging.ERROR,
            )
            raise RuntimeError(f"Failed to route request: {error_msg}")

        provider = route_result.unwrap()

        # Note: We don't check health here - let the actual error from the provider
        # bubble up so users get the real error message (e.g., "insufficient credits")
        # Health checks are for routing decisions, not for blocking requests

        # Check budget (rough estimate)
        if self.cost_tracker:
            estimated_tokens = len(str(messages)) // TokenEstimation.CHARS_PER_TOKEN
            estimated_cost = provider.estimate_cost(estimated_tokens, max_tokens, model)

            budget_check = await self.cost_tracker.check_budget(user_id, estimated_cost)
            if budget_check.is_failure():
                error_msg = budget_check.error_or("Budget exceeded")
                raise RuntimeError(f"Budget exceeded: {error_msg}")

        log_event(
            "llm_stream_start",
            {
                "provider_id": provider.provider_id,
                "provider_type": provider.provider_type.value,
                "model": model,
                "message_count": len(messages),
            },
        )

        chunk_count = 0
        total_tokens = 0

        try:
            stream = cast(
                AsyncGenerator[LLMStreamChunk, None],
                provider.generate_stream(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                ),
            )
            async for chunk in stream:
                chunk_count += 1
                if chunk.tokens_used:
                    total_tokens = chunk.tokens_used
                yield chunk

            # Record cost after streaming completes
            if self.cost_tracker and total_tokens > 0:
                # Estimate cost based on total tokens
                estimated_cost = provider.estimate_cost(
                    total_tokens
                    // TokenEstimation.PROMPT_COMPLETION_SPLIT_RATIO,  # Rough split
                    total_tokens // TokenEstimation.PROMPT_COMPLETION_SPLIT_RATIO,
                    model,
                )

                cost_record = CostRecord(
                    provider_id=provider.provider_id,
                    provider_type=provider.provider_type.value,
                    model=model,
                    prompt_tokens=total_tokens
                    // TokenEstimation.PROMPT_COMPLETION_SPLIT_RATIO,
                    completion_tokens=total_tokens
                    // TokenEstimation.PROMPT_COMPLETION_SPLIT_RATIO,
                    cost_usd=estimated_cost,
                    timestamp=datetime.now(),
                    user_id=user_id,
                )
                await self.cost_tracker.record_cost(cost_record)

            log_event(
                "llm_stream_complete",
                {
                    "provider_id": provider.provider_id,
                    "model": model,
                    "chunks_generated": chunk_count,
                    "total_tokens": total_tokens,
                },
            )

        except Exception as e:
            log_event(
                "llm_stream_failed",
                {
                    "provider_id": provider.provider_id,
                    "model": model,
                    "error": str(e),
                    "chunks_generated": chunk_count,
                },
                level=logging.ERROR,
            )
            raise

    async def list_models(
        self,
        provider_id: Optional[str] = None,
    ) -> Result[List[ModelInfo], str]:
        """
        List available models for a provider.

        Args:
            provider_id: Provider ID (uses default if None)

        Returns:
            Result with list of ModelInfo or error
        """
        provider = self.registry.get(provider_id)

        if provider is None:
            return Failure(
                error=ErrorMessages.NO_PROVIDER_AVAILABLE,
                error_type="ProviderNotFound",
                status_code=503,
            )

        try:
            models = await provider.list_models()
            return Success(models)

        except Exception as e:
            log_event(
                "list_models_failed",
                {
                    "provider_id": provider.provider_id,
                    "error": str(e),
                },
                level=logging.ERROR,
            )

            return Failure(
                error=str(e),
                error_type=type(e).__name__,
                status_code=500,
            )

    async def get_workspaces(
        self,
        provider_id: Optional[str] = None,
    ) -> Result[List[Workspace], str]:
        """
        Get workspaces for a provider.

        Args:
            provider_id: Provider ID (uses default if None)

        Returns:
            Result with list of Workspace or error
        """
        provider = self.registry.get(provider_id)

        if provider is None:
            return Failure(
                error=ErrorMessages.NO_PROVIDER_AVAILABLE,
                error_type="ProviderNotFound",
                status_code=404,
            )

        if provider.metadata is None:
            return Failure(
                error=ErrorMessages.PROVIDER_NO_METADATA_SUPPORT.format(
                    provider_id=provider.provider_id
                ),
                error_type="MetadataNotSupported",
                status_code=501,
            )

        if not provider.metadata.supports_capability(MetadataCapability.WORKSPACES):
            return Failure(
                error=ErrorMessages.PROVIDER_NO_WORKSPACES_SUPPORT.format(
                    provider_id=provider.provider_id
                ),
                error_type="WorkspacesNotSupported",
                status_code=501,
            )

        try:
            workspaces = provider.metadata.get_workspaces()
            return Success(workspaces)

        except Exception as e:
            log_event(
                "get_workspaces_failed",
                {
                    "provider_id": provider.provider_id,
                    "error": str(e),
                },
                level=logging.ERROR,
            )

            return Failure(
                error=str(e),
                error_type=type(e).__name__,
                status_code=500,
            )

    async def get_usage(
        self,
        provider_id: Optional[str],
        start_time: datetime,
        end_time: datetime,
        **filters,
    ) -> Result[UsageReport, str]:
        """
        Get usage report for a provider.

        Args:
            provider_id: Provider ID (uses default if None)
            start_time: Report start time
            end_time: Report end time
            **filters: Additional provider-specific filters

        Returns:
            Result with UsageReport or error
        """
        provider = self.registry.get(provider_id)

        if provider is None:
            return Failure(
                error=ErrorMessages.NO_PROVIDER_AVAILABLE,
                error_type="ProviderNotFound",
                status_code=404,
            )

        if provider.metadata is None:
            return Failure(
                error=ErrorMessages.PROVIDER_NO_METADATA_SUPPORT.format(
                    provider_id=provider.provider_id
                ),
                error_type="MetadataNotSupported",
                status_code=501,
            )

        if not provider.metadata.supports_capability(MetadataCapability.USAGE_TRACKING):
            return Failure(
                error=ErrorMessages.PROVIDER_NO_USAGE_TRACKING.format(
                    provider_id=provider.provider_id
                ),
                error_type="UsageTrackingNotSupported",
                status_code=501,
            )

        try:
            usage = await provider.metadata.get_usage(start_time, end_time, **filters)
            return Success(usage)

        except Exception as e:
            log_event(
                "get_usage_failed",
                {
                    "provider_id": provider.provider_id,
                    "error": str(e),
                },
                level=logging.ERROR,
            )

            return Failure(
                error=str(e),
                error_type=type(e).__name__,
                status_code=500,
            )

    async def get_costs(
        self,
        provider_id: Optional[str],
        start_time: datetime,
        end_time: datetime,
        **filters,
    ) -> Result[CostReport, str]:
        """
        Get cost report for a provider.

        Args:
            provider_id: Provider ID (uses default if None)
            start_time: Report start time
            end_time: Report end time
            **filters: Additional provider-specific filters

        Returns:
            Result with CostReport or error
        """
        provider = self.registry.get(provider_id)

        if provider is None:
            return Failure(
                error=ErrorMessages.NO_PROVIDER_AVAILABLE,
                error_type="ProviderNotFound",
                status_code=404,
            )

        if provider.metadata is None:
            return Failure(
                error=ErrorMessages.PROVIDER_NO_METADATA_SUPPORT.format(
                    provider_id=provider.provider_id
                ),
                error_type="MetadataNotSupported",
                status_code=501,
            )

        if not provider.metadata.supports_capability(MetadataCapability.COST_TRACKING):
            return Failure(
                error=ErrorMessages.PROVIDER_NO_COST_TRACKING.format(
                    provider_id=provider.provider_id
                ),
                error_type="CostTrackingNotSupported",
                status_code=501,
            )

        try:
            costs = provider.metadata.get_costs(start_time, end_time, **filters)
            return Success(costs)

        except Exception as e:
            log_event(
                "get_costs_failed",
                {
                    "provider_id": provider.provider_id,
                    "error": str(e),
                },
                level=logging.ERROR,
            )

            return Failure(
                error=str(e),
                error_type=type(e).__name__,
                status_code=500,
            )

    def get_metadata_capabilities(
        self,
        provider_id: Optional[str] = None,
    ) -> Result[List[str], str]:
        """
        Get metadata capabilities for a provider.

        Args:
            provider_id: Provider ID (uses default if None)

        Returns:
            Result with list of capability names or error
        """
        provider = self.registry.get(provider_id)

        if provider is None:
            return Failure(
                error=ErrorMessages.NO_PROVIDER_AVAILABLE,
                error_type="ProviderNotFound",
                status_code=404,
            )

        if provider.metadata is None:
            return Success([])

        capabilities = [
            cap.value
            for cap in MetadataCapability
            if provider.metadata.supports_capability(cap)
        ]

        return Success(capabilities)

    @property
    def is_initialized(self) -> bool:
        """Check if manager is initialized."""
        return self._initialized

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"LLMProviderManager(providers={self.registry.count()}, "
            f"default={self.registry.get_default_id()}, "
            f"initialized={self._initialized})"
        )
