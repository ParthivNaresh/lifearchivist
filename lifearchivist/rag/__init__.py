"""
RAG (Retrieval-Augmented Generation) components for Life Archivist.

This module provides the integration layer between document retrieval
and LLM generation, enabling context-aware responses.
"""

from .prompts import PromptBuilder
from .service import ConversationRAGService
from .types import (
    Citation,
    ContextConfig,
    ContextData,
    ErrorInfo,
    IntentData,
    MetadataInfo,
    StreamEvent,
    StreamEventType,
)

__all__ = [
    "Citation",
    "ConversationRAGService",
    "ContextConfig",
    "ContextData",
    "ErrorInfo",
    "IntentData",
    "MetadataInfo",
    "PromptBuilder",
    "StreamEvent",
    "StreamEventType",
]
