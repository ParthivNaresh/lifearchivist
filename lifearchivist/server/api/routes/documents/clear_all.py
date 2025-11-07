"""
Clear all documents endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError
from .misc_models import ClearAllSummary
from .response_models import ClearAllResponse

router = APIRouter()


@router.delete(
    "/",
    response_model=ClearAllResponse,
    status_code=status.HTTP_200_OK,
    responses={
        503: {
            "description": "Required service unavailable",
            "content": {
                "application/json": {"example": {"detail": "Vault not available"}}
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Clear all documents failed: <error message>"}
                }
            },
        },
    },
)
async def clear_all_documents() -> ClearAllResponse:
    """
    Clear all documents from the system.

    Performs comprehensive cleanup across all storage systems including vector database,
    file vault, and progress tracking. This is a destructive operation that cannot be undone.

    ## Response Fields

    - **operation**: Operation identifier
    - **summary**: Aggregate metrics
      - total_files_deleted: Total files removed
      - total_bytes_reclaimed: Total bytes freed
      - total_mb_reclaimed: Total MB freed
    - **vault_metrics**: File vault clearing details
    - **llamaindex_metrics**: Vector database clearing details
    - **progress_metrics**: Progress tracking clearing details
    - **errors**: List of any errors encountered

    ## Example Response

    ```json
    {
        "operation": "comprehensive_clear_all",
        "summary": {
            "total_files_deleted": 150,
            "total_bytes_reclaimed": 52428800,
            "total_mb_reclaimed": 50.0
        },
        "vault_metrics": {
            "files_deleted": 150,
            "bytes_reclaimed": 52428800,
            "orphaned_files_deleted": 0
        },
        "llamaindex_metrics": {
            "vectors_deleted": 150,
            "metadata_cleared": true,
            "storage_files_deleted": 0
        },
        "progress_metrics": {
            "progress_cleared": true
        },
        "errors": []
    }
    ```

    ## What Gets Cleared

    ### LlamaIndex (if available)
    - Vector embeddings from Qdrant
    - Document metadata
    - Document store entries
    - Index structures

    ### Vault (required)
    - All stored document files
    - Orphaned files
    - File metadata

    ### Progress Tracking (if available)
    - All progress records
    - Activity logs

    ## Use Cases

    - Reset system to clean state
    - Clear test data
    - Free up storage space
    - Troubleshoot data corruption
    - Development/testing cleanup

    ## Important Warnings

    - **DESTRUCTIVE**: Cannot be undone
    - **ALL DATA LOST**: Every document removed
    - **NO BACKUP**: No automatic backup created
    - **IMMEDIATE**: Takes effect immediately
    - **SYSTEM-WIDE**: Affects all users/documents

    ## Safety Considerations

    - Backup important data before running
    - Verify you want to delete everything
    - Consider selective deletion instead
    - Check errors array in response
    - Monitor summary metrics

    ## Performance Notes

    - Operation time depends on document count
    - Large datasets may take several seconds
    - Progress not tracked during operation
    - Atomic per-service (not globally atomic)
    - Partial failures possible (check errors)

    ## Notes

    - Returns 503 if vault unavailable (required)
    - LlamaIndex optional (skipped if unavailable)
    - Progress manager optional (skipped if unavailable)
    - Errors collected but don't fail operation
    - Summary aggregates all metrics
    """
    server = get_server()

    if not server.vault:
        raise ServiceUnavailableError("Vault")

    try:
        if server.llamaindex_service:
            clear_result = await server.llamaindex_service.clear_all_data()

            if clear_result.is_failure():
                llamaindex_metrics = {
                    "skipped": True,
                    "error": clear_result.error,
                }
            else:
                llamaindex_metrics = clear_result.value or {}
        else:
            llamaindex_metrics = {"skipped": True}

        vault_metrics = await server.vault.clear_all_files([])

        if server.progress_manager:
            try:
                progress_metrics = await server.progress_manager.clear_all_progress()
            except Exception as progress_error:
                progress_metrics = {"error": str(progress_error)}
        else:
            progress_metrics = {"skipped": True}

        vault_files_deleted = vault_metrics.get("files_deleted", 0) + vault_metrics.get(
            "orphaned_files_deleted", 0
        )
        vault_bytes_reclaimed = vault_metrics.get(
            "bytes_reclaimed", 0
        ) + vault_metrics.get("orphaned_bytes_reclaimed", 0)
        total_files_deleted = vault_files_deleted + llamaindex_metrics.get(
            "storage_files_deleted", 0
        )
        total_bytes_reclaimed = vault_bytes_reclaimed + llamaindex_metrics.get(
            "storage_bytes_reclaimed", 0
        )

        errors = (
            vault_metrics.get("errors", [])
            + llamaindex_metrics.get("errors", [])
            + (
                [progress_metrics.get("error")]
                if progress_metrics.get("error")
                else progress_metrics.get("errors", [])
            )
        )

        return ClearAllResponse(
            operation="comprehensive_clear_all",
            summary=ClearAllSummary(
                total_files_deleted=total_files_deleted,
                total_bytes_reclaimed=total_bytes_reclaimed,
                total_mb_reclaimed=round(total_bytes_reclaimed / (1024 * 1024), 2),
            ),
            vault_metrics=vault_metrics,
            llamaindex_metrics=llamaindex_metrics,
            progress_metrics=progress_metrics,
            errors=errors,
        )

    except ServiceUnavailableError:
        raise
    except Exception as e:
        raise InternalServerError("Clear all documents", e) from e
