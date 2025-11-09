"""
Reconcile vault endpoint.
"""

from fastapi import APIRouter, status

from lifearchivist.storage.vault_reconciliation import VaultReconciliationService

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError
from .misc_models import ReconciliationResult
from .response_models import ReconcileVaultResponse

router = APIRouter()


@router.post(
    "/reconcile",
    response_model=ReconcileVaultResponse,
    status_code=status.HTTP_200_OK,
    responses={
        503: {
            "description": "Service unavailable",
            "content": {
                "application/json": {"example": {"detail": "Vault not available"}}
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Vault reconciliation failed: <error>"}
                }
            },
        },
    },
)
async def reconcile_vault() -> ReconcileVaultResponse:
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
        raise ServiceUnavailableError("Vault")

    if not server.llamaindex_service:
        raise ServiceUnavailableError("LlamaIndex service")

    try:
        reconciliation_service = VaultReconciliationService(
            vault=server.vault,
            doc_tracker=server.llamaindex_service.doc_tracker,
            qdrant_client=server.llamaindex_service.qdrant_client,
        )

        result = await reconciliation_service.reconcile()

        reconciliation = ReconciliationResult(**result)

        return ReconcileVaultResponse(reconciliation=reconciliation)

    except (ServiceUnavailableError, AttributeError) as e:
        if isinstance(e, AttributeError):
            raise InternalServerError(
                "Reconciliation service",
                RuntimeError(f"Configuration error: {str(e)}"),
            ) from e
        raise
    except Exception as e:
        raise InternalServerError("Vault reconciliation", e) from e
