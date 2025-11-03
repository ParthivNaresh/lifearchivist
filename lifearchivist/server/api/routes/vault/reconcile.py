"""
Reconcile vault endpoint.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from lifearchivist.storage.vault_reconciliation import VaultReconciliationService

from ..shared.dependencies import get_server

router = APIRouter()


@router.post("/reconcile")
async def reconcile_vault():
    """
    Reconcile vault files with metadata stores.

    Self-healing operation that:
    - Scans all documents in Redis metadata store
    - Checks if corresponding vault files exist
    - Removes orphaned metadata for missing files
    - Ensures data consistency across storage layers

    Vault files are the source of truth.

    Triggered by:
    - UI refresh button
    - Manual file operations
    - System maintenance

    Returns:
    - Documents checked
    - Orphaned metadata removed
    - Reconciliation statistics
    """
    server = get_server()

    if not server.vault:
        return JSONResponse(
            content={
                "success": False,
                "error": "Vault not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    if not server.llamaindex_service:
        return JSONResponse(
            content={
                "success": False,
                "error": "LlamaIndex service not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        reconciliation_service = VaultReconciliationService(
            vault=server.vault,
            doc_tracker=server.llamaindex_service.doc_tracker,
            qdrant_client=server.llamaindex_service.qdrant_client,
        )

        result = await reconciliation_service.reconcile()

        return {
            "success": True,
            "reconciliation": result,
        }

    except AttributeError as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Reconciliation service configuration error: {str(e)}",
                "error_type": "ConfigurationError",
            },
            status_code=500,
        )
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Vault reconciliation failed: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )
