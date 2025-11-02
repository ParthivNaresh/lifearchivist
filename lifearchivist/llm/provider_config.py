"""
Typed configuration classes for LLM providers.

Provides type-safe configuration with validation and defaults.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Type

from .base_provider import ProviderType
from .constants import (
    APIKeyPrefix,
    ProtocolScheme,
    ProviderDefaults,
    ValidationMessages,
)


@dataclass(frozen=True)
class BaseProviderConfig:
    """
    Base configuration for all providers.

    Frozen dataclass ensures immutability after creation.
    Validation is done in subclasses.

    Note: No fields defined here to avoid dataclass ordering issues.
    Each subclass defines its own fields including timeout_seconds.
    """

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize config to dict for storage.

        Returns:
            Dictionary representation of config
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseProviderConfig":
        """
        Deserialize config from dict.

        Args:
            data: Dictionary with config data

        Returns:
            Config instance

        Raises:
            TypeError: If data doesn't match config fields
        """
        return cls(**data)

    def _validate_timeout(self, timeout: int) -> None:
        if timeout <= 0:
            raise ValueError(ValidationMessages.TIMEOUT_POSITIVE)

    def _validate_base_url(self, base_url: str) -> None:
        if not base_url:
            raise ValueError(ValidationMessages.BASE_URL_EMPTY)

        if not base_url.startswith(
            (ProtocolScheme.HTTP.value, ProtocolScheme.HTTPS.value)
        ):
            raise ValueError(ValidationMessages.BASE_URL_PROTOCOL)

    def _validate_max_retries(self, max_retries: int) -> None:
        if max_retries < 0:
            raise ValueError(ValidationMessages.MAX_RETRIES_NEGATIVE)

    def _validate_api_key(
        self, api_key: str, provider: str, prefix: Optional[str] = None
    ) -> None:
        if not api_key:
            raise ValueError(
                ValidationMessages.API_KEY_REQUIRED.format(provider=provider)
            )

        if prefix and not api_key.startswith(prefix):
            raise ValueError(
                ValidationMessages.INVALID_KEY_PREFIX.format(
                    provider=provider, prefix=prefix
                )
            )


@dataclass(frozen=True)
class OllamaConfig(BaseProviderConfig):
    """
    Configuration for Ollama provider.

    Attributes:
        base_url: Ollama server URL
        timeout_seconds: Request timeout in seconds
        keep_alive: Keep model loaded in memory (Ollama-specific)
    """

    base_url: str = ProviderDefaults.OLLAMA_BASE_URL
    timeout_seconds: int = ProviderDefaults.OLLAMA_TIMEOUT
    keep_alive: Optional[str] = None

    def __post_init__(self):
        """Validate Ollama-specific configuration."""
        self._validate_timeout(self.timeout_seconds)
        self._validate_base_url(self.base_url)


@dataclass(frozen=True)
class OpenAIConfig(BaseProviderConfig):
    """
    Configuration for OpenAI provider.

    Attributes:
        api_key: OpenAI API key (required)
        base_url: API base URL (for Azure or custom endpoints)
        organization: Optional organization ID
        timeout_seconds: Request timeout in seconds
        max_retries: Maximum retry attempts for failed requests
    """

    api_key: str
    base_url: str = ProviderDefaults.OPENAI_BASE_URL
    organization: Optional[str] = None
    max_retries: int = ProviderDefaults.OPENAI_MAX_RETRIES
    timeout_seconds: int = ProviderDefaults.OPENAI_TIMEOUT

    def __post_init__(self):
        """Validate OpenAI-specific configuration."""
        self._validate_timeout(self.timeout_seconds)
        self._validate_api_key(self.api_key, "OpenAI", APIKeyPrefix.OPENAI.value)
        self._validate_base_url(self.base_url)
        self._validate_max_retries(self.max_retries)


@dataclass(frozen=True)
class AnthropicConfig(BaseProviderConfig):
    """
    Configuration for Anthropic provider.

    Attributes:
        api_key: Anthropic API key (required)
        base_url: API base URL
        timeout_seconds: Request timeout in seconds
        max_retries: Maximum retry attempts
    """

    api_key: str
    base_url: str = ProviderDefaults.ANTHROPIC_BASE_URL
    max_retries: int = ProviderDefaults.ANTHROPIC_MAX_RETRIES
    timeout_seconds: int = ProviderDefaults.ANTHROPIC_TIMEOUT

    def __post_init__(self):
        """Validate Anthropic-specific configuration."""
        self._validate_timeout(self.timeout_seconds)
        self._validate_api_key(self.api_key, "Anthropic", APIKeyPrefix.ANTHROPIC.value)
        self._validate_base_url(self.base_url)
        self._validate_max_retries(self.max_retries)


@dataclass(frozen=True)
class GoogleConfig(BaseProviderConfig):
    """
    Configuration for Google (Gemini) provider.

    Attributes:
        api_key: Google API key (required)
        base_url: API base URL
        timeout_seconds: Request timeout in seconds
        max_retries: Maximum retry attempts
    """

    api_key: str
    base_url: str = ProviderDefaults.GOOGLE_BASE_URL
    max_retries: int = ProviderDefaults.GOOGLE_MAX_RETRIES
    timeout_seconds: int = ProviderDefaults.GOOGLE_TIMEOUT

    def __post_init__(self):
        """Validate Google-specific configuration."""
        self._validate_timeout(self.timeout_seconds)
        self._validate_api_key(self.api_key, "Google")
        self._validate_base_url(self.base_url)
        self._validate_max_retries(self.max_retries)


@dataclass(frozen=True)
class GroqConfig(BaseProviderConfig):
    """
    Configuration for Groq provider.

    Attributes:
        api_key: Groq API key (required)
        base_url: API base URL
        timeout_seconds: Request timeout in seconds
        max_retries: Maximum retry attempts
    """

    api_key: str
    base_url: str = ProviderDefaults.GROQ_BASE_URL
    max_retries: int = ProviderDefaults.GROQ_MAX_RETRIES
    timeout_seconds: int = ProviderDefaults.GROQ_TIMEOUT

    def __post_init__(self):
        """Validate Groq-specific configuration."""
        self._validate_timeout(self.timeout_seconds)
        self._validate_api_key(self.api_key, "Groq")
        self._validate_base_url(self.base_url)
        self._validate_max_retries(self.max_retries)


@dataclass(frozen=True)
class MistralConfig(BaseProviderConfig):
    """
    Configuration for Mistral provider.

    Attributes:
        api_key: Mistral API key (required)
        base_url: API base URL
        timeout_seconds: Request timeout in seconds
        max_retries: Maximum retry attempts
    """

    api_key: str
    base_url: str = ProviderDefaults.MISTRAL_BASE_URL
    max_retries: int = ProviderDefaults.MISTRAL_MAX_RETRIES
    timeout_seconds: int = ProviderDefaults.MISTRAL_TIMEOUT

    def __post_init__(self):
        """Validate Mistral-specific configuration."""
        self._validate_timeout(self.timeout_seconds)
        self._validate_api_key(self.api_key, "Mistral")
        self._validate_base_url(self.base_url)
        self._validate_max_retries(self.max_retries)


PROVIDER_CONFIG_TYPES: Dict[ProviderType, Type[BaseProviderConfig]] = {
    ProviderType.OLLAMA: OllamaConfig,
    ProviderType.OPENAI: OpenAIConfig,
    ProviderType.ANTHROPIC: AnthropicConfig,
    ProviderType.GOOGLE: GoogleConfig,
    ProviderType.GROQ: GroqConfig,
    ProviderType.MISTRAL: MistralConfig,
}


def create_provider_config(provider_type: ProviderType, **kwargs) -> BaseProviderConfig:
    """
    Factory function to create typed provider config.

    Args:
        provider_type: Type of provider
        **kwargs: Configuration parameters

    Returns:
        Typed provider config instance

    Raises:
        ValueError: If provider type not supported or config invalid

    Example:
        >>> config = create_provider_config(
        ...     ProviderType.OPENAI,
        ...     api_key="sk-...",
        ...     organization="org-..."
        ... )
    """
    config_class = PROVIDER_CONFIG_TYPES.get(provider_type)

    if not config_class:
        raise ValueError(
            f"Unsupported provider type: {provider_type}. "
            f"Supported types: {list(PROVIDER_CONFIG_TYPES.keys())}"
        )

    try:
        return config_class(**kwargs)
    except TypeError as e:
        raise ValueError(f"Invalid configuration for {provider_type.value}: {e}") from e
