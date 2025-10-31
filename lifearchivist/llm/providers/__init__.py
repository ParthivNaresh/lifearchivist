"""
LLM provider implementations.

Each provider implements the BaseLLMProvider interface for their specific service.
"""

from ..base_provider import ProviderType
from .anthropic_provider import AnthropicProvider
from .google_provider import GoogleProvider
from .groq_provider import GroqProvider
from .mistral_provider import MistralProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider

# Provider registry - maps ProviderType to provider class
PROVIDER_REGISTRY = {
    ProviderType.OLLAMA: OllamaProvider,
    ProviderType.OPENAI: OpenAIProvider,
    ProviderType.ANTHROPIC: AnthropicProvider,
    ProviderType.GOOGLE: GoogleProvider,
    ProviderType.GROQ: GroqProvider,
    ProviderType.MISTRAL: MistralProvider,
}

__all__ = [
    "AnthropicProvider",
    "GoogleProvider",
    "GroqProvider",
    "MistralProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "PROVIDER_REGISTRY",
]
