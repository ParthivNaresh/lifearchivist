"""
Search and query endpoints with Result type unwrapping.
"""

from fastapi import APIRouter

from . import search_get, search_post

router = APIRouter(prefix="/search", tags=["search"])

router.include_router(search_post.router)
router.include_router(search_get.router)

__all__ = ["router"]
