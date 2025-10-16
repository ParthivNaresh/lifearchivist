"""
Life Archivist - Local-first, privacy-preserving personal knowledge system.

A comprehensive document management and search system with MCP architecture
that keeps your data local while providing advanced AI-powered features.
"""

__version__ = "0.1.0"
__author__ = "Parthiv Naresh"
__email__ = "parthivnaresh@gmail.com"

from .models.core import Document, SearchResult
from .storage.llamaindex_service import LlamaIndexService

__all__ = [
    "Document",
    "SearchResult",
    "LlamaIndexService",
]
