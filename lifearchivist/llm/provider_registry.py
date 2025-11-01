"""
Provider Registry - Manages provider instances and lifecycle.

Responsible for:
- Storing and retrieving provider instances
- Managing provider lifecycle (initialization, cleanup)
- Provider validation and health status
"""

import logging
from typing import Dict, List, Optional

from ..utils.logging import log_event
from ..utils.result import Failure, Result, Success
from .base_provider import BaseLLMProvider, ProviderType

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Registry for managing LLM provider instances.

    Handles provider storage, retrieval, and lifecycle management.
    Does NOT handle routing, cost tracking, or health monitoring.

    Supports async context manager protocol for automatic cleanup:
        async with ProviderRegistry() as registry:
            await registry.register(provider)
            # ... use registry ...
        # All providers automatically cleaned up on exit
    """

    def __init__(self):
        """Initialize empty provider registry."""
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._default_provider_id: Optional[str] = None

    async def __aenter__(self) -> "ProviderRegistry":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager and cleanup all providers."""
        await self.clear()

    async def register(
        self,
        provider: BaseLLMProvider,
        set_as_default: bool = False,
    ) -> Result[None, str]:
        """
        Register a provider instance.

        Initializes the provider before registration to ensure it's ready for use.
        If initialization fails, the provider is not registered.

        Args:
            provider: Provider instance to register
            set_as_default: Whether to set as default provider

        Returns:
            Result indicating success or failure

        Raises:
            ValueError: If provider_id already exists
        """
        if provider.provider_id in self._providers:
            return Failure(
                error=f"Provider already registered: {provider.provider_id}",
                error_type="DuplicateProvider",
                status_code=409,
                context={"provider_id": provider.provider_id},
            )

        # Initialize provider before registration
        try:
            await provider.initialize()
        except Exception as e:
            log_event(
                "provider_initialization_failed",
                {
                    "provider_id": provider.provider_id,
                    "provider_type": provider.provider_type.value,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
            return Failure(
                error=f"Failed to initialize provider: {e}",
                error_type="InitializationError",
                status_code=500,
                context={
                    "provider_id": provider.provider_id,
                    "original_error": str(e),
                },
            )

        # Register provider after successful initialization
        self._providers[provider.provider_id] = provider

        # Set as default if requested or if this is the first provider
        if set_as_default or self._default_provider_id is None:
            self._default_provider_id = provider.provider_id

        log_event(
            "provider_registered",
            {
                "provider_id": provider.provider_id,
                "provider_type": provider.provider_type.value,
                "is_default": provider.provider_id == self._default_provider_id,
                "initialized": provider.is_initialized,
            },
        )

        return Success(None)

    async def unregister(self, provider_id: str) -> Result[BaseLLMProvider, str]:
        """
        Unregister a provider.

        Cleans up provider resources before removal. If cleanup fails, the provider
        is still removed from the registry to prevent resource leaks.

        Args:
            provider_id: Provider identifier

        Returns:
            Result with removed provider or error
        """
        if provider_id not in self._providers:
            return Failure(
                error=f"Provider not found: {provider_id}",
                error_type="ProviderNotFound",
                status_code=404,
            )

        provider = self._providers.pop(provider_id)

        # Clear default if this was the default provider
        if self._default_provider_id == provider_id:
            # Set new default to first available provider
            self._default_provider_id = (
                next(iter(self._providers.keys())) if self._providers else None
            )

        # Clean up provider resources
        # Note: We still remove from registry even if cleanup fails to prevent leaks
        cleanup_error = None
        try:
            await provider.cleanup()
        except Exception as e:
            cleanup_error = str(e)
            log_event(
                "provider_cleanup_failed",
                {
                    "provider_id": provider_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.WARNING,
            )

        log_event(
            "provider_unregistered",
            {
                "provider_id": provider_id,
                "new_default": self._default_provider_id,
                "cleanup_successful": cleanup_error is None,
            },
        )

        return Success(provider)

    def get(self, provider_id: Optional[str] = None) -> Optional[BaseLLMProvider]:
        """
        Get provider by ID, or default if None.

        Args:
            provider_id: Provider ID, or None for default

        Returns:
            Provider instance or None if not found
        """
        if provider_id is None:
            provider_id = self._default_provider_id

        if provider_id is None:
            return None

        return self._providers.get(provider_id)

    def get_by_type(self, provider_type: ProviderType) -> List[BaseLLMProvider]:
        """
        Get all providers of a specific type.

        Args:
            provider_type: Provider type to filter by

        Returns:
            List of matching providers
        """
        return [
            provider
            for provider in self._providers.values()
            if provider.provider_type == provider_type
        ]

    def list_all(self) -> List[BaseLLMProvider]:
        """
        Get all registered providers.

        Returns:
            List of all provider instances
        """
        return list(self._providers.values())

    def get_default_id(self) -> Optional[str]:
        """
        Get the default provider ID.

        Returns:
            Default provider ID or None
        """
        return self._default_provider_id

    def set_default(self, provider_id: str) -> Result[None, str]:
        """
        Set the default provider.

        Args:
            provider_id: Provider ID to set as default

        Returns:
            Result indicating success or failure
        """
        if provider_id not in self._providers:
            return Failure(
                error=f"Provider not found: {provider_id}",
                error_type="ProviderNotFound",
                status_code=404,
            )

        old_default = self._default_provider_id
        self._default_provider_id = provider_id

        log_event(
            "default_provider_changed",
            {
                "old_default": old_default,
                "new_default": provider_id,
            },
        )

        return Success(None)

    def exists(self, provider_id: str) -> bool:
        """
        Check if provider exists.

        Args:
            provider_id: Provider identifier

        Returns:
            True if provider exists
        """
        return provider_id in self._providers

    def count(self) -> int:
        """
        Get count of registered providers.

        Returns:
            Number of registered providers
        """
        return len(self._providers)

    async def clear(self) -> int:
        """
        Clear all providers (use with caution).

        Cleans up all provider resources before clearing the registry.
        Cleanup failures are logged but don't prevent removal.

        Returns:
            Number of providers removed
        """
        count = len(self._providers)
        cleanup_failures = 0

        # Clean up all providers
        for provider_id, provider in self._providers.items():
            try:
                await provider.cleanup()
            except Exception as e:
                cleanup_failures += 1
                log_event(
                    "provider_cleanup_failed_during_clear",
                    {
                        "provider_id": provider_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    level=logging.WARNING,
                )

        self._providers.clear()
        self._default_provider_id = None

        log_event(
            "registry_cleared",
            {
                "providers_removed": count,
                "cleanup_failures": cleanup_failures,
            },
            level=logging.WARNING,
        )

        return count

    def __len__(self) -> int:
        """Get count of registered providers."""
        return len(self._providers)

    def __contains__(self, provider_id: str) -> bool:
        """Check if provider exists."""
        return provider_id in self._providers

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ProviderRegistry(providers={len(self._providers)}, "
            f"default={self._default_provider_id})"
        )
