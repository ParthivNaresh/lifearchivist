"""
Provider Router - Routes requests to appropriate providers.

Responsible for:
- Request routing logic
- Provider selection strategies
- Fallback handling
- Load balancing
"""

import logging
from enum import Enum
from typing import List, Optional

from ..utils.logging import log_event
from ..utils.result import Failure, Result, Success
from .base_provider import BaseLLMProvider, ProviderType
from .provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    """Provider routing strategies."""

    DEFAULT = "default"  # Use default provider
    EXPLICIT = "explicit"  # Use explicitly specified provider
    LEAST_COST = "least_cost"  # Route to cheapest provider
    ROUND_ROBIN = "round_robin"  # Distribute load evenly
    FASTEST = "fastest"  # Route to fastest provider (requires metrics)
    FALLBACK_CHAIN = "fallback_chain"  # Try providers in order until success


class ProviderRouter:
    """
    Routes LLM requests to appropriate providers.

    Implements various routing strategies and fallback logic.
    Does NOT execute requests - only selects which provider to use.
    """

    def __init__(self, registry: ProviderRegistry):
        """
        Initialize router with provider registry.

        Args:
            registry: Provider registry instance
        """
        self.registry = registry
        self._round_robin_index = 0

    def route(
        self,
        provider_id: Optional[str] = None,
        strategy: RoutingStrategy = RoutingStrategy.DEFAULT,
        model: Optional[str] = None,
        provider_type: Optional[ProviderType] = None,
    ) -> Result[BaseLLMProvider, str]:
        """
        Route request to appropriate provider.

        Args:
            provider_id: Explicit provider ID (overrides strategy)
            strategy: Routing strategy to use
            model: Model name (for model-based routing)
            provider_type: Provider type filter

        Returns:
            Result with selected provider or error
        """
        # Explicit provider ID takes precedence
        if provider_id is not None:
            return self._route_explicit(provider_id)

        # Apply routing strategy
        if strategy == RoutingStrategy.DEFAULT:
            return self._route_default()
        elif strategy == RoutingStrategy.LEAST_COST:
            return self._route_least_cost(model, provider_type)
        elif strategy == RoutingStrategy.ROUND_ROBIN:
            return self._route_round_robin(provider_type)
        elif strategy == RoutingStrategy.FASTEST:
            return self._route_fastest(provider_type)
        else:
            return Failure(
                error=f"Unsupported routing strategy: {strategy}",
                error_type="InvalidStrategy",
                status_code=400,
            )

    def route_with_fallback(
        self,
        provider_ids: List[str],
    ) -> Result[List[BaseLLMProvider], str]:
        """
        Get fallback chain of providers.

        Args:
            provider_ids: Ordered list of provider IDs to try

        Returns:
            Result with list of available providers in order
        """
        providers = []

        for provider_id in provider_ids:
            provider = self.registry.get(provider_id)
            if provider is not None:
                providers.append(provider)
            else:
                log_event(
                    "fallback_provider_not_found",
                    {"provider_id": provider_id},
                    level=logging.WARNING,
                )

        if not providers:
            return Failure(
                error="No providers available in fallback chain",
                error_type="NoProvidersAvailable",
                status_code=503,
                context={"requested_ids": provider_ids},
            )

        return Success(providers)

    def _route_explicit(self, provider_id: str) -> Result[BaseLLMProvider, str]:
        """Route to explicitly specified provider with fallback to default."""
        provider = self.registry.get(provider_id)

        if provider is None:
            log_event(
                "provider_not_found_falling_back",
                {
                    "requested_provider_id": provider_id,
                    "reason": "Provider deleted or unavailable",
                },
                level=logging.WARNING,
            )

            default_provider = self.registry.get(None)
            if default_provider is None:
                available = [p.provider_id for p in self.registry.list_all()]
                return Failure(
                    error=f"Provider '{provider_id}' not found and no default provider available",
                    error_type="ProviderNotFound",
                    status_code=404,
                    context={
                        "provider_id": provider_id,
                        "available_providers": available,
                        "fallback_attempted": True,
                    },
                )

            log_event(
                "provider_fallback_to_default",
                {
                    "requested_provider_id": provider_id,
                    "fallback_provider_id": default_provider.provider_id,
                    "fallback_provider_type": default_provider.provider_type.value,
                },
            )

            return Success(default_provider)

        log_event(
            "provider_routed_explicit",
            {
                "provider_id": provider_id,
                "provider_type": provider.provider_type.value,
            },
        )

        return Success(provider)

    def _route_default(self) -> Result[BaseLLMProvider, str]:
        """Route to default provider."""
        provider = self.registry.get(None)  # None gets default

        if provider is None:
            return Failure(
                error="No default provider configured",
                error_type="NoDefaultProvider",
                status_code=503,
                context={
                    "available_providers": [
                        p.provider_id for p in self.registry.list_all()
                    ]
                },
            )

        log_event(
            "provider_routed_default",
            {
                "provider_id": provider.provider_id,
                "provider_type": provider.provider_type.value,
            },
        )

        return Success(provider)

    def _route_least_cost(
        self,
        model: Optional[str],
        provider_type: Optional[ProviderType],
    ) -> Result[BaseLLMProvider, str]:
        """
        Route to provider with lowest cost for given model.

        Note: This is a simplified implementation. Production would need
        actual cost data and model availability checks.
        """
        providers = self.registry.list_all()

        if provider_type is not None:
            providers = [p for p in providers if p.provider_type == provider_type]

        if not providers:
            return Failure(
                error="No providers available for least-cost routing",
                error_type="NoProvidersAvailable",
                status_code=503,
            )

        # For now, prioritize free providers (Ollama), then others
        # In production, this would use actual cost estimation
        free_providers = [
            p for p in providers if p.provider_type == ProviderType.OLLAMA
        ]

        if free_providers:
            provider = free_providers[0]
        else:
            provider = providers[0]

        log_event(
            "provider_routed_least_cost",
            {
                "provider_id": provider.provider_id,
                "provider_type": provider.provider_type.value,
                "model": model,
            },
        )

        return Success(provider)

    def _route_round_robin(
        self,
        provider_type: Optional[ProviderType],
    ) -> Result[BaseLLMProvider, str]:
        """
        Route using round-robin load balancing.

        Distributes requests evenly across available providers.
        """
        providers = self.registry.list_all()

        if provider_type is not None:
            providers = [p for p in providers if p.provider_type == provider_type]

        if not providers:
            return Failure(
                error="No providers available for round-robin routing",
                error_type="NoProvidersAvailable",
                status_code=503,
            )

        # Select provider using round-robin
        provider = providers[self._round_robin_index % len(providers)]
        self._round_robin_index += 1

        log_event(
            "provider_routed_round_robin",
            {
                "provider_id": provider.provider_id,
                "provider_type": provider.provider_type.value,
                "index": self._round_robin_index - 1,
            },
        )

        return Success(provider)

    def _route_fastest(
        self,
        provider_type: Optional[ProviderType],
    ) -> Result[BaseLLMProvider, str]:
        """
        Route to fastest provider based on historical metrics.

        Note: This requires integration with a metrics/monitoring system.
        For now, falls back to default routing.
        """
        log_event(
            "fastest_routing_not_implemented",
            {"fallback": "default"},
            level=logging.WARNING,
        )

        # TODO: Implement with actual performance metrics
        return self._route_default()

    def get_available_providers(
        self,
        provider_type: Optional[ProviderType] = None,
    ) -> List[BaseLLMProvider]:
        """
        Get list of available providers, optionally filtered by type.

        Args:
            provider_type: Optional provider type filter

        Returns:
            List of available providers
        """
        if provider_type is None:
            return self.registry.list_all()

        return self.registry.get_by_type(provider_type)

    def __repr__(self) -> str:
        """String representation."""
        return f"ProviderRouter(providers={self.registry.count()})"
