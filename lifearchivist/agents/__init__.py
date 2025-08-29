"""
Processing agents for Life Archivist.
"""

from .ingestion import IngestionAgent
from .query import QueryAgent

__all__ = ["IngestionAgent", "QueryAgent"]
