"""
Typed configuration classes for LLM providers.

Provides type-safe configuration with validation and defaults.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from .base_provider import ProviderType


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


@dataclass(frozen=True)
class OllamaConfig(BaseProviderConfig):
    """
    Configuration for Ollama provider.

    Attributes:
        base_url: Ollama server URL
        timeout_seconds: Request timeout in seconds
        keep_alive: Keep model loaded in memory (Ollama-specific)
    """

    base_url: str = "http://localhost:11434"
    timeout_seconds: int = 300  # Ollama can be slow for large models
    keep_alive: Optional[str] = None  # e.g., "5m" to keep model loaded

    def __post_init__(self):
        """Validate Ollama-specific configuration."""
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        if not self.base_url:
            raise ValueError("base_url cannot be empty")

        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")


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
    base_url: str = "https://api.openai.com/v1"
    organization: Optional[str] = None
    max_retries: int = 3
    timeout_seconds: int = 120  # Override parent default

    def __post_init__(self):
        """Validate OpenAI-specific configuration."""
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        if not self.api_key:
            raise ValueError("api_key is required for OpenAI provider")

        # Validate key format (supports standard, project, and service account keys)
        if not self.api_key.startswith("sk-"):
            raise ValueError("OpenAI API key must start with 'sk-'")

        if not self.base_url:
            raise ValueError("base_url cannot be empty")

        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")

        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")


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
    base_url: str = "https://api.anthropic.com/v1"
    max_retries: int = 3
    timeout_seconds: int = 120  # Override parent default

    def __post_init__(self):
        """Validate Anthropic-specific configuration."""
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        if not self.api_key:
            raise ValueError("api_key is required for Anthropic provider")

        # Anthropic keys can be sk-ant-api03-... or sk-ant-...
        if not self.api_key.startswith("sk-ant-"):
            raise ValueError("Anthropic API key must start with 'sk-ant-'")

        if not self.base_url:
            raise ValueError("base_url cannot be empty")

        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")


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
    base_url: str = "https://generativelanguage.googleapis.com/v1"
    max_retries: int = 3
    timeout_seconds: int = 120  # Override parent default

    def __post_init__(self):
        """Validate Google-specific configuration."""
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        if not self.api_key:
            raise ValueError("api_key is required for Google provider")

        if not self.base_url:
            raise ValueError("base_url cannot be empty")

        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")


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
    base_url: str = "https://api.groq.com/openai/v1"
    max_retries: int = 3
    timeout_seconds: int = 30  # Groq is fast, lower timeout

    def __post_init__(self):
        """Validate Groq-specific configuration."""
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        if not self.api_key:
            raise ValueError("api_key is required for Groq provider")

        if not self.base_url:
            raise ValueError("base_url cannot be empty")

        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")


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
    base_url: str = "https://api.mistral.ai/v1"
    max_retries: int = 3
    timeout_seconds: int = 60  # Standard timeout

    def __post_init__(self):
        """Validate Mistral-specific configuration."""
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        if not self.api_key:
            raise ValueError("api_key is required for Mistral provider")

        if not self.base_url:
            raise ValueError("base_url cannot be empty")

        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")


# Type mapping for provider configs
PROVIDER_CONFIG_TYPES = {
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
