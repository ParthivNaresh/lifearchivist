"""
Activity feed API endpoints.

Provides endpoints for retrieving system activity events.
"""

from fastapi import APIRouter

from . import clear, count, events

router = APIRouter(prefix="/activity", tags=["activity"])

router.include_router(events.router)
router.include_router(count.router)
router.include_router(clear.router)

__all__ = ["router"]
