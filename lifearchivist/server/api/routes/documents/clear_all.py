"""
Clear all documents endpoint.
"""

from fastapi import APIRouter, HTTPException

from ..constants import (
    ErrorMessages,
    HTTPStatus,
)
from ..shared.dependencies import get_server
from ..utils import extract_result_value, unwrap_result_to_json_response

router = APIRouter()


@router.delete("/")
async def clear_all_documents():
    """
    Comprehensive clear all documents operation with progress tracking.

    Clears data from:
    - LlamaIndex (vectors, metadata, docstore)
    - Vault (files)
    - Progress tracking
    """
    server = get_server()

    try:
        if server.llamaindex_service:
            clear_result = await server.llamaindex_service.clear_all_data()

            error_response = unwrap_result_to_json_response(clear_result)
            if error_response:
                return error_response

            llamaindex_metrics = extract_result_value(clear_result, dict, {})
        else:
            llamaindex_metrics = {"skipped": True}

        if not server.vault:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail=ErrorMessages.VAULT_NOT_INITIALIZED,
            )
        vault_metrics = await server.vault.clear_all_files([])

        if server.progress_manager:
            try:
                progress_metrics = await server.progress_manager.clear_all_progress()
            except Exception as progress_error:
                progress_metrics = {"error": str(progress_error)}
        else:
            progress_metrics = {"skipped": True}

        vault_files_deleted = vault_metrics["files_deleted"] + vault_metrics.get(
            "orphaned_files_deleted", 0
        )
        vault_bytes_reclaimed = vault_metrics["bytes_reclaimed"] + vault_metrics.get(
            "orphaned_bytes_reclaimed", 0
        )
        total_files_deleted = vault_files_deleted + llamaindex_metrics.get(
            "storage_files_deleted", 0
        )
        total_bytes_reclaimed = vault_bytes_reclaimed + llamaindex_metrics.get(
            "storage_bytes_reclaimed", 0
        )

        return {
            "success": True,
            "operation": "comprehensive_clear_all",
            "summary": {
                "total_files_deleted": total_files_deleted,
                "total_bytes_reclaimed": total_bytes_reclaimed,
                "total_mb_reclaimed": round(total_bytes_reclaimed / (1024 * 1024), 2),
            },
            "vault_metrics": vault_metrics,
            "llamaindex_metrics": llamaindex_metrics,
            "progress_metrics": progress_metrics,
            "errors": (
                vault_metrics.get("errors", [])
                + llamaindex_metrics.get("errors", [])
                + progress_metrics.get("errors", [])
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e)
        ) from None
