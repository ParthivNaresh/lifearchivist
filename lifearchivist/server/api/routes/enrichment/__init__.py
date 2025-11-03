"""
Enrichment queue status and management endpoints.

These endpoints provide visibility into the background enrichment system,
including worker status, queue statistics, and processing metrics.
"""

from fastapi import APIRouter

from . import queue_stats, status

router = APIRouter(prefix="/enrichment", tags=["enrichment"])

router.include_router(status.router)
router.include_router(queue_stats.router)

__all__ = ["router"]
