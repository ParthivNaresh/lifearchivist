"""
Search and query endpoints with Result type unwrapping.
"""

from fastapi import APIRouter

from . import search_get

router = APIRouter(prefix="/search", tags=["search"])

router.include_router(search_get.router)

__all__ = ["router"]
