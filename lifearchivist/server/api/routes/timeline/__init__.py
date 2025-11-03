"""
Timeline API routes for temporal document visualization.
"""

from fastapi import APIRouter

from . import data, summary

router = APIRouter(prefix="/timeline", tags=["timeline"])

router.include_router(data.router)
router.include_router(summary.router)

__all__ = ["router"]
