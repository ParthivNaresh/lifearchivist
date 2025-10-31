"""
Provider Loader - Instantiates providers from stored credentials.

This is the critical bridge between credential storage and the provider manager.
Handles deserialization, validation, and instantiation of provider instances.
"""

import logging
from typing import Dict, List, cast

from ..storage.credential_service import CredentialService
from ..utils.logging import log_event, track
from ..utils.result import Failure, Result, Success
from .base_provider import BaseLLMProvider, ProviderType
from .provider_config import BaseProviderConfig
from .providers import PROVIDER_REGISTRY

logger = logging.getLogger(__name__)


class ProviderLoader:
    """
    Loads and instantiates LLM providers from credential storage.

    Responsibilities:
    - Retrieve encrypted credentials from storage
    - Deserialize and validate provider configurations
    - Instantiate provider classes with proper configs
    - Handle errors gracefully with detailed context

    This class is the bridge between CredentialService (storage) and
    ProviderManager (runtime). It ensures type safety and proper error handling
    during the credential → provider transformation.
    """

    def __init__(self, credential_service: CredentialService):
        """
        Initialize provider loader.

        Args:
            credential_service: Service for encrypted credential storage
        """
        self.credential_service = credential_service

    @track(
        operation="provider_loader_load_provider",
        include_args=["provider_id"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def load_provider(
        self,
        provider_id: str,
    ) -> Result[BaseLLMProvider, str]:
        """
        Load and instantiate a provider from stored credentials.

        This is the main entry point for converting stored credentials into
        a running provider instance. The process:
        1. Retrieve encrypted credentials from storage
        2. Deserialize into typed config object
        3. Instantiate appropriate provider class
        4. Return provider (NOT initialized - caller must initialize)

        Args:
            provider_id: Unique identifier for the provider

        Returns:
            Result with instantiated provider or detailed error

        Example:
            >>> loader = ProviderLoader(credential_service)
            >>> result = await loader.load_provider("my-openai")
            >>> if result.is_success():
            ...     provider = result.unwrap()
            ...     await provider.initialize()  # Caller must initialize
        """
        # Get provider metadata for type
        metadata_result = await self.credential_service.get_provider_metadata(
            provider_id
        )

        if metadata_result.is_failure():
            log_event(
                "provider_load_metadata_failed",
                {
                    "provider_id": provider_id,
                    "error": metadata_result.error,
                },
                level=logging.ERROR,
            )
            return Failure(
                error=f"Failed to retrieve provider metadata: {metadata_result.error}",
                error_type=metadata_result.error_type,
                status_code=metadata_result.status_code,
                context={"provider_id": provider_id},
            )

        provider_data = metadata_result.unwrap()

        # Extract and validate provider type
        try:
            provider_type = ProviderType(provider_data["provider_type"])
        except (KeyError, ValueError) as e:
            log_event(
                "provider_load_invalid_type",
                {
                    "provider_id": provider_id,
                    "provider_type": provider_data.get("provider_type"),
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            return Failure(
                error=f"Invalid provider type: {provider_data.get('provider_type')}",
                error_type="InvalidProviderType",
                status_code=400,
                context={"provider_id": provider_id},
            )

        # Get decrypted, typed config
        config_result = await self.credential_service.get_provider_config(provider_id)

        if config_result.is_failure():
            log_event(
                "provider_load_config_failed",
                {
                    "provider_id": provider_id,
                    "error": config_result.error,
                },
                level=logging.ERROR,
            )
            return cast(Result[BaseLLMProvider, str], config_result)

        config = config_result.unwrap()

        # Instantiate provider
        provider_result = self._instantiate_provider(
            provider_id,
            provider_type,
            config,
        )

        if provider_result.is_failure():
            return provider_result

        provider = provider_result.unwrap()

        log_event(
            "provider_loaded",
            {
                "provider_id": provider_id,
                "provider_type": provider_type.value,
            },
        )

        return Success(provider)

    @track(
        operation="provider_loader_load_all",
        track_performance=True,
        frequency="low_frequency",
    )
    async def load_all_providers(
        self,
        user_id: str = "default",
    ) -> Result[List[BaseLLMProvider], str]:
        """
        Load all providers for a user from storage.

        Useful for initializing the provider manager on application startup.
        Failures for individual providers are logged but don't stop the process.

        Args:
            user_id: User identifier to filter providers

        Returns:
            Result with list of successfully loaded providers

        Example:
            >>> loader = ProviderLoader(credential_service)
            >>> result = await loader.load_all_providers()
            >>> if result.is_success():
            ...     providers = result.unwrap()
            ...     for provider in providers:
            ...         await manager.add_provider(provider)
        """
        # Get all stored provider configs
        list_result = await self.credential_service.list_providers(user_id)

        if list_result.is_failure():
            log_event(
                "provider_load_all_list_failed",
                {
                    "user_id": user_id,
                    "error": list_result.error,
                },
                level=logging.ERROR,
            )
            return Failure(
                error=f"Failed to list providers: {list_result.error}",
                error_type=list_result.error_type,
                status_code=list_result.status_code,
            )

        provider_data_list = list_result.unwrap()

        if not provider_data_list:
            log_event(
                "provider_load_all_empty",
                {"user_id": user_id},
            )
            return Success([])

        # Load each provider
        providers = []
        failed_count = 0

        for provider_data in provider_data_list:
            provider_id = provider_data.get("id")

            if not provider_id:
                log_event(
                    "provider_load_all_missing_id",
                    {"provider_data": str(provider_data)[:200]},
                    level=logging.WARNING,
                )
                failed_count += 1
                continue

            result = await self.load_provider(provider_id)

            if result.is_success():
                providers.append(result.unwrap())
            else:
                # Log but continue - don't let one bad provider break everything
                log_event(
                    "provider_load_all_individual_failed",
                    {
                        "provider_id": provider_id,
                        "error": result.error,
                    },
                    level=logging.WARNING,
                )
                failed_count += 1

        log_event(
            "provider_load_all_complete",
            {
                "user_id": user_id,
                "loaded": len(providers),
                "failed": failed_count,
                "total": len(provider_data_list),
            },
        )

        return Success(providers)

    def _instantiate_provider(
        self,
        provider_id: str,
        provider_type: ProviderType,
        config: BaseProviderConfig,
    ) -> Result[BaseLLMProvider, str]:
        """
        Instantiate provider class with configuration.

        Args:
            provider_id: Unique provider identifier
            provider_type: Type of provider
            config: Typed provider configuration

        Returns:
            Result with provider instance or error
        """
        # Get provider class from registry
        provider_class = PROVIDER_REGISTRY.get(provider_type)

        if provider_class is None:
            log_event(
                "provider_instantiate_no_class",
                {
                    "provider_id": provider_id,
                    "provider_type": provider_type.value,
                },
                level=logging.ERROR,
            )
            return Failure(
                error=f"No provider class registered for type: {provider_type.value}",
                error_type="ProviderClassNotFound",
                status_code=500,
                context={
                    "provider_id": provider_id,
                    "provider_type": provider_type.value,
                },
            )

        # Instantiate provider
        try:
            provider = provider_class(provider_id, config)

            log_event(
                "provider_instantiated",
                {
                    "provider_id": provider_id,
                    "provider_type": provider_type.value,
                    "provider_class": provider_class.__name__,
                },
            )

            return Success(provider)

        except Exception as e:
            log_event(
                "provider_instantiate_failed",
                {
                    "provider_id": provider_id,
                    "provider_type": provider_type.value,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
            return Failure(
                error=f"Failed to instantiate provider: {e}",
                error_type="ProviderInstantiationError",
                status_code=500,
                context={
                    "provider_id": provider_id,
                    "provider_type": provider_type.value,
                    "original_error": str(e),
                },
            )

    async def reload_provider(
        self,
        provider_id: str,
    ) -> Result[BaseLLMProvider, str]:
        """
        Reload a provider with fresh credentials from storage.

        Useful when credentials have been updated and the provider needs
        to be recreated with new configuration.

        Args:
            provider_id: Provider identifier

        Returns:
            Result with new provider instance or error

        Note:
            This creates a NEW provider instance. The caller is responsible
            for removing the old instance from the manager and adding the new one.
        """
        log_event(
            "provider_reload_started",
            {"provider_id": provider_id},
        )

        result = await self.load_provider(provider_id)

        if result.is_success():
            log_event(
                "provider_reload_complete",
                {"provider_id": provider_id},
            )
        else:
            log_event(
                "provider_reload_failed",
                {
                    "provider_id": provider_id,
                    "error": result.error,
                },
                level=logging.ERROR,
            )

        return cast(Result[BaseLLMProvider, str], result)

    def validate_config(
        self,
        provider_type: ProviderType,
        config_dict: Dict,
    ) -> Result[BaseProviderConfig, str]:
        """
        Validate a configuration without loading from storage.

        Useful for validating user input before saving credentials.
        Delegates to CredentialService's deserialization logic.

        Args:
            provider_type: Type of provider
            config_dict: Configuration dictionary to validate

        Returns:
            Result with validated config or error

        Example:
            >>> loader = ProviderLoader(credential_service)
            >>> result = loader.validate_config(
            ...     ProviderType.OPENAI,
            ...     {"api_key": "sk-...", "base_url": "https://api.openai.com/v1"}
            ... )
            >>> if result.is_success():
            ...     # Config is valid, safe to save
        """
        try:
            from .provider_config import create_provider_config

            config = create_provider_config(provider_type, **config_dict)
            return Success(config)
        except Exception as e:
            return Failure(
                error=f"Invalid configuration: {e}",
                error_type="ConfigValidationError",
                status_code=400,
                context={
                    "provider_type": provider_type.value,
                    "error": str(e),
                },
            )

    def __repr__(self) -> str:
        """String representation."""
        return f"ProviderLoader(credential_service={self.credential_service})"
