"""
RAG (Retrieval-Augmented Generation) components for Life Archivist.

This module provides the integration layer between document retrieval
and LLM generation, enabling context-aware responses.
"""

from .service import ConversationRAGService
from .types import Citation, ContextConfig, StreamEvent

__all__ = [
    "ConversationRAGService",
    "ContextConfig",
    "StreamEvent",
    "Citation",
]
