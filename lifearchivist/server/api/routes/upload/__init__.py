"""
File upload and ingestion endpoints.
"""

from fastapi import APIRouter

from . import file_upload, progress

router = APIRouter(prefix="/upload", tags=["upload"])

router.include_router(file_upload.router)
router.include_router(progress.router)

__all__ = ["router"]
