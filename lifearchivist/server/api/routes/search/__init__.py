"""
Search and query endpoints with Result type unwrapping.
"""

from fastapi import APIRouter

from . import ask, search_get

router = APIRouter(prefix="/search", tags=["search"])

router.include_router(search_get.router)
router.include_router(ask.router)

__all__ = ["router"]
