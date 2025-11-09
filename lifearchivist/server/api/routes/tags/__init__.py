"""
Tag and topic management endpoints.

Provides functionality for:
- Tag extraction and management
- Topic landscape visualization
- Document categorization by tags/topics

Note: Tag extraction is currently a placeholder.
Full implementation will extract tags from document metadata and content.
"""

from fastapi import APIRouter

from . import list

router = APIRouter(prefix="/tags", tags=["tags"])

router.include_router(list.router)

__all__ = ["router"]
