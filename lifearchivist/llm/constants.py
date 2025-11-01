from enum import Enum
from typing import Final


class ProviderDefaults:
    OLLAMA_BASE_URL: Final[str] = "http://localhost:11434"
    OLLAMA_TIMEOUT: Final[int] = 300
    OLLAMA_DEFAULT_ID: Final[str] = "ollama-default"

    OPENAI_BASE_URL: Final[str] = "https://api.openai.com/v1"
    OPENAI_TIMEOUT: Final[int] = 120
    OPENAI_MAX_RETRIES: Final[int] = 3

    ANTHROPIC_BASE_URL: Final[str] = "https://api.anthropic.com/v1"
    ANTHROPIC_TIMEOUT: Final[int] = 120
    ANTHROPIC_MAX_RETRIES: Final[int] = 3

    GOOGLE_BASE_URL: Final[str] = "https://generativelanguage.googleapis.com/v1"
    GOOGLE_TIMEOUT: Final[int] = 120
    GOOGLE_MAX_RETRIES: Final[int] = 3

    GROQ_BASE_URL: Final[str] = "https://api.groq.com/openai/v1"
    GROQ_TIMEOUT: Final[int] = 30
    GROQ_MAX_RETRIES: Final[int] = 3

    MISTRAL_BASE_URL: Final[str] = "https://api.mistral.ai/v1"
    MISTRAL_TIMEOUT: Final[int] = 60
    MISTRAL_MAX_RETRIES: Final[int] = 3


class HealthMonitorDefaults:
    CHECK_INTERVAL_SECONDS: Final[int] = 60
    FAILURE_THRESHOLD: Final[int] = 3
    AUTO_DISABLE_UNHEALTHY: Final[bool] = True


class UserDefaults:
    DEFAULT_USER_ID: Final[str] = "default"


class TokenEstimation:
    CHARS_PER_TOKEN: Final[int] = 4
    PROMPT_COMPLETION_SPLIT_RATIO: Final[int] = 2


class APIKeyPrefix(str, Enum):
    OPENAI = "sk-"
    ANTHROPIC = "sk-ant-"


class ProtocolScheme(str, Enum):
    HTTP = "http://"
    HTTPS = "https://"


class ValidationMessages:
    TIMEOUT_POSITIVE: Final[str] = "timeout_seconds must be positive"
    API_KEY_REQUIRED: Final[str] = "api_key is required for {provider} provider"
    BASE_URL_EMPTY: Final[str] = "base_url cannot be empty"
    BASE_URL_PROTOCOL: Final[str] = "base_url must start with http:// or https://"
    MAX_RETRIES_NEGATIVE: Final[str] = "max_retries cannot be negative"
    INVALID_KEY_PREFIX: Final[str] = "{provider} API key must start with '{prefix}'"


class ErrorMessages:
    REDIS_REQUIRED_FOR_COST_TRACKING: Final[str] = (
        "Redis client required for cost tracking. "
        "Either provide redis_client or set enable_cost_tracking=False"
    )
    MANAGER_INIT_FAILED: Final[str] = "Failed to initialize manager: {error}"
    NO_PROVIDER_AVAILABLE: Final[str] = "No provider available"
    PROVIDER_UNHEALTHY: Final[str] = "Provider unhealthy: {provider_id}"
    PROVIDER_NO_METADATA_SUPPORT: Final[str] = (
        "Provider {provider_id} does not support metadata"
    )
    PROVIDER_NO_WORKSPACES_SUPPORT: Final[str] = (
        "Provider {provider_id} does not support workspaces"
    )
    PROVIDER_NO_USAGE_TRACKING: Final[str] = (
        "Provider {provider_id} does not support usage tracking"
    )
    PROVIDER_NO_COST_TRACKING: Final[str] = (
        "Provider {provider_id} does not support cost tracking"
    )
