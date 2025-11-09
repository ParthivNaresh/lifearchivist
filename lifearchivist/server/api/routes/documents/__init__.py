"""
Document management endpoints with Result type unwrapping.

Provides CRUD operations for documents including:
- Listing and filtering documents
- Deleting documents from index and vault
- Updating document metadata
- Analyzing document structure and chunks
- Finding similar documents
"""

from fastapi import APIRouter

from . import analysis, chunks, clear_all, delete, list, neighbors, update_subtheme

router = APIRouter(prefix="/documents", tags=["documents"])

router.include_router(list.router)
router.include_router(delete.router)
router.include_router(update_subtheme.router)
router.include_router(clear_all.router)
router.include_router(analysis.router)
router.include_router(chunks.router)
router.include_router(neighbors.router)

__all__ = ["router"]
