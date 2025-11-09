"""
Settings management endpoints.

Provides configuration management for:
- Document processing settings
- Search and AI model configuration
- File management preferences
- UI appearance settings
- System information
"""

from fastapi import APIRouter

from . import export, get, models_list, reset, update

router = APIRouter(prefix="/settings", tags=["settings"])

router.include_router(get.router)
router.include_router(update.router)
router.include_router(models_list.router)
router.include_router(reset.router)
router.include_router(export.router)

__all__ = ["router"]
