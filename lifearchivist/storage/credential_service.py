"""
Credential Service for storage of LLM provider credentials.

Stores API keys and provider configurations in Redis.
For local desktop apps, credentials are stored in plain text.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from redis.asyncio import Redis

from ..utils.logging import log_event, track
from ..utils.result import Failure, Result, Success

if TYPE_CHECKING:
    from ..llm.base_provider import ProviderType
    from ..llm.provider_config import BaseProviderConfig

logger = logging.getLogger(__name__)

# Redis key prefixes
PROVIDER_KEY_PREFIX = "llm:provider:"
PROVIDER_LIST_KEY = "llm:providers"


class CredentialService:
    """
    Manages storage of LLM provider credentials.

    Stores provider configurations in Redis for persistence across restarts.
    For local desktop applications, credentials are stored in plain text
    since the user's machine is the security boundary.
    """

    def __init__(self, redis_client: Redis):
        """
        Initialize credential service.

        Args:
            redis_client: Async Redis client
        """
        self.redis = redis_client

        log_event(
            "credential_service_initialized",
            {"storage": "redis", "encryption": False},
        )

    def _get_provider_key(self, provider_id: str) -> str:
        """Get Redis key for provider."""
        return f"{PROVIDER_KEY_PREFIX}{provider_id}"

    @track(
        operation="credential_service_add_provider",
        include_args=["provider_id", "provider_type"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def add_provider(
        self,
        provider_id: str,
        provider_type: "ProviderType",
        config: "BaseProviderConfig",
        is_default: bool = False,
        user_id: str = "default",
    ) -> Result[Dict, str]:
        """
        Add or update a provider configuration.

        Args:
            provider_id: Unique identifier for provider
            provider_type: Type of provider (OLLAMA, OPENAI, etc.)
            config: Typed provider configuration
            is_default: Whether this is the default provider
            user_id: User ID (for multi-user support)

        Returns:
            Result with provider data or error
        """
        try:
            redis_key = self._get_provider_key(provider_id)
            existing = await self.redis.get(redis_key)

            if existing:
                return Failure(
                    error=f"Provider ID '{provider_id}' already exists. Please choose a unique identifier.",
                    error_type="DuplicateProvider",
                    status_code=409,
                )
            # Serialize config to dict
            config_dict = config.to_dict()

            # Build provider data
            provider_data = {
                "id": provider_id,
                "provider_type": provider_type.value,
                "config": config_dict,
                "is_default": is_default,
                "user_id": user_id,
            }

            # Store in Redis
            redis_key = self._get_provider_key(provider_id)
            await self.redis.set(redis_key, json.dumps(provider_data))

            # Add to provider list
            await cast(Any, self.redis.sadd(PROVIDER_LIST_KEY, provider_id))

            log_event(
                "provider_added",
                {
                    "provider_id": provider_id,
                    "provider_type": provider_type.value,
                    "is_default": is_default,
                },
            )

            return Success(provider_data)

        except Exception as e:
            log_event(
                "provider_add_failed",
                {
                    "provider_id": provider_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
            return Failure(
                error=f"Failed to add provider: {e}",
                error_type=type(e).__name__,
                status_code=500,
            )

    @track(
        operation="credential_service_get_provider_metadata",
        include_args=["provider_id"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def get_provider_metadata(self, provider_id: str) -> Result[Dict, str]:
        """
        Get provider metadata.

        Args:
            provider_id: Provider identifier

        Returns:
            Result with provider metadata or error
        """
        try:
            redis_key = self._get_provider_key(provider_id)
            data = await self.redis.get(redis_key)

            if not data:
                return Failure(
                    error=f"Provider not found: {provider_id}",
                    error_type="ProviderNotFound",
                    status_code=404,
                )

            provider_data = json.loads(data)
            return Success(provider_data)

        except Exception as e:
            log_event(
                "provider_get_metadata_failed",
                {"provider_id": provider_id, "error": str(e)},
                level=logging.ERROR,
            )
            return Failure(
                error=f"Failed to get provider metadata: {e}",
                error_type=type(e).__name__,
                status_code=500,
            )

    @track(
        operation="credential_service_get_provider_config",
        include_args=["provider_id"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def get_provider_config(
        self, provider_id: str
    ) -> Result["BaseProviderConfig", str]:
        """
        Get typed provider configuration.

        Args:
            provider_id: Provider identifier

        Returns:
            Result with typed provider config or error
        """
        try:
            redis_key = self._get_provider_key(provider_id)
            data = await self.redis.get(redis_key)

            if not data:
                return Failure(
                    error=f"Provider not found: {provider_id}",
                    error_type="ProviderNotFound",
                    status_code=404,
                )

            provider_data = json.loads(data)

            # Get provider type
            try:
                from ..llm.base_provider import ProviderType

                provider_type = ProviderType(provider_data["provider_type"])
            except (KeyError, ValueError):
                return Failure(
                    error=f"Invalid provider type: {provider_data.get('provider_type')}",
                    error_type="InvalidProviderType",
                    status_code=400,
                )

            # Deserialize into typed config
            from ..llm.provider_config import create_provider_config

            config = create_provider_config(provider_type, **provider_data["config"])

            return Success(config)

        except Exception as e:
            log_event(
                "provider_get_config_failed",
                {"provider_id": provider_id, "error": str(e)},
                level=logging.ERROR,
            )
            return Failure(
                error=f"Failed to get provider config: {e}",
                error_type=type(e).__name__,
                status_code=500,
            )

    @track(
        operation="credential_service_list_providers",
        track_performance=True,
        frequency="medium_frequency",
    )
    async def list_providers(self, user_id: str = "default") -> Result[List[Dict], str]:
        """
        List all providers for a user.

        Args:
            user_id: User ID to filter by

        Returns:
            Result with list of provider metadata
        """
        try:
            # Get all provider IDs
            provider_ids = await cast(Any, self.redis.smembers(PROVIDER_LIST_KEY))

            if not provider_ids:
                return Success([])

            providers = []
            for provider_id in provider_ids:
                provider_id_str = (
                    provider_id.decode()
                    if isinstance(provider_id, bytes)
                    else provider_id
                )
                result = await self.get_provider_metadata(provider_id_str)

                if result.is_success():
                    provider_data = result.unwrap()
                    # Filter by user_id
                    if provider_data.get("user_id") == user_id:
                        providers.append(provider_data)

            return Success(providers)

        except Exception as e:
            log_event(
                "provider_list_failed",
                {"error": str(e), "user_id": user_id},
                level=logging.ERROR,
            )
            return Failure(
                error=f"Failed to list providers: {e}",
                error_type=type(e).__name__,
                status_code=500,
            )

    @track(
        operation="credential_service_delete_provider",
        include_args=["provider_id"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def delete_provider(self, provider_id: str) -> Result[bool, str]:
        """
        Delete a provider configuration.

        Args:
            provider_id: Provider identifier

        Returns:
            Result with True if deleted, or error
        """
        try:
            redis_key = self._get_provider_key(provider_id)

            # Check if exists
            exists = await self.redis.exists(redis_key)
            if not exists:
                return Failure(
                    error=f"Provider not found: {provider_id}",
                    error_type="ProviderNotFound",
                    status_code=404,
                )

            # Delete from Redis
            await self.redis.delete(redis_key)

            # Remove from provider list
            await cast(Any, self.redis.srem(PROVIDER_LIST_KEY, provider_id))

            log_event(
                "provider_deleted",
                {"provider_id": provider_id},
            )

            return Success(True)

        except Exception as e:
            log_event(
                "provider_delete_failed",
                {"provider_id": provider_id, "error": str(e)},
                level=logging.ERROR,
            )
            return Failure(
                error=f"Failed to delete provider: {e}",
                error_type=type(e).__name__,
                status_code=500,
            )

    @track(
        operation="credential_service_update_provider",
        include_args=["provider_id"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def update_provider(
        self,
        provider_id: str,
        config: Optional["BaseProviderConfig"] = None,
        is_default: Optional[bool] = None,
    ) -> Result[Dict, str]:
        """
        Update provider configuration.

        Args:
            provider_id: Provider identifier
            config: New configuration (if updating)
            is_default: New default status (if updating)

        Returns:
            Result with updated provider metadata or error
        """
        try:
            # Get existing provider metadata
            result = await self.get_provider_metadata(provider_id)
            if result.is_failure():
                return cast(Result[Dict, str], result)

            provider_data = result.unwrap()

            # Update fields
            if config is not None:
                provider_data["config"] = config.to_dict()

            if is_default is not None:
                provider_data["is_default"] = is_default

            # Save updated data
            redis_key = self._get_provider_key(provider_id)
            await self.redis.set(redis_key, json.dumps(provider_data))

            log_event(
                "provider_updated",
                {"provider_id": provider_id},
            )

            return Success(provider_data)

        except Exception as e:
            log_event(
                "provider_update_failed",
                {"provider_id": provider_id, "error": str(e)},
                level=logging.ERROR,
            )
            return Failure(
                error=f"Failed to update provider: {e}",
                error_type=type(e).__name__,
                status_code=500,
            )

    async def clear_all_providers(self, user_id: str = "default") -> Result[int, str]:
        """
        Clear all providers for a user (DANGEROUS - use with caution).

        Args:
            user_id: User ID to clear providers for

        Returns:
            Result with count of deleted providers or error
        """
        try:
            result = await self.list_providers(user_id)
            if result.is_failure():
                return Failure(
                    error="Failed to list providers for deletion",
                    error_type="ListError",
                    status_code=500,
                )

            providers = result.unwrap()
            count = 0

            for provider in providers:
                delete_result = await self.delete_provider(provider["id"])
                if delete_result.is_success():
                    count += 1

            log_event(
                "providers_cleared",
                {"user_id": user_id, "count": count},
                level=logging.WARNING,
            )

            return Success(count)

        except Exception as e:
            log_event(
                "providers_clear_failed",
                {"user_id": user_id, "error": str(e)},
                level=logging.ERROR,
            )
            return Failure(
                error=f"Failed to clear providers: {e}",
                error_type=type(e).__name__,
                status_code=500,
            )
