"""
Multi-folder watching API endpoints.

Provides RESTful endpoints for managing multiple watched folders
and automatic document ingestion.
"""

from fastapi import APIRouter

from . import add, folder_status, get, list, remove, scan, status, update

router = APIRouter(prefix="/folder-watch", tags=["folder-watch"])

router.include_router(add.router)
router.include_router(list.router)
router.include_router(get.router)
router.include_router(remove.router)
router.include_router(update.router)
router.include_router(scan.router)
router.include_router(status.router)
router.include_router(folder_status.router)

__all__ = ["router"]
