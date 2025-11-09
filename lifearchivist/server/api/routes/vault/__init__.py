"""
Vault management endpoints.
"""

from fastapi import APIRouter

from . import download, info, list_files, reconcile

router = APIRouter(prefix="/vault", tags=["vault"])

router.include_router(info.router)
router.include_router(list_files.router)
router.include_router(reconcile.router)
router.include_router(download.router)

__all__ = ["router"]
