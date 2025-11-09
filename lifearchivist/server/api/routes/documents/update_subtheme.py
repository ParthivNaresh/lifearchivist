"""
Update document subtheme endpoint.
"""

from typing import Any, Dict

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi import status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from .response_models import SubthemeUpdateResponse

router = APIRouter()


@router.patch(
    "/{document_id}/subtheme",
    response_model=SubthemeUpdateResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "description": "Document not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Document not found: invalid-id"}
                }
            },
        },
        503: {
            "description": "LlamaIndex service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "LlamaIndex service not available"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Update document subtheme failed: <error message>"
                    }
                }
            },
        },
    },
)
async def update_document_subtheme(
    subtheme_data: Dict[str, Any],
    document_id: str = PathParam(..., description="Unique document identifier"),
) -> SubthemeUpdateResponse:
    """
    Update document classification and subtheme metadata.

    Allows updating theme classification fields including classification category,
    theme, and subtheme information. Uses merge mode to preserve other metadata.

    ## Path Parameters

    - **document_id**: Unique identifier of the document to update

    ## Request Body

    Flexible JSON object with classification fields:
    - **classification**: Document classification category
    - **theme**: Primary theme
    - **subtheme**: Specific subtheme
    - Any other metadata fields to update

    ## Example Request

    ```json
    {
        "classification": "work",
        "theme": "project_management",
        "subtheme": "sprint_planning"
    }
    ```

    ## Response Fields

    - **document_id**: ID of updated document
    - **updated_fields**: List of field names that were updated
    - **success**: Whether update succeeded

    ## Example Response

    ```json
    {
        "document_id": "doc_123",
        "updated_fields": ["classification", "theme", "subtheme"],
        "success": true
    }
    ```

    ## Use Cases

    - Update document classification
    - Correct theme assignments
    - Refine subtheme categorization
    - Bulk metadata updates
    - Manual classification override

    ## Update Behavior

    - **Merge Mode**: Updates only specified fields
    - **Preserves Other Metadata**: Doesn't affect other fields
    - **Immediate Effect**: Changes apply immediately
    - **Searchable**: Updated metadata immediately searchable
    - **Idempotent**: Safe to call multiple times

    ## Performance Notes

    - Fast metadata update
    - No re-embedding required
    - No re-chunking needed
    - Metadata-only operation

    ## Notes

    - Returns 404 if document doesn't exist
    - Flexible schema (accepts any fields)
    - Merge mode preserves existing metadata
    - Changes reflected in search immediately
    - No validation on field values
    """
    server = get_server()

    if not server.llamaindex_service:
        raise ServiceUnavailableError("LlamaIndex service")

    try:
        result = await server.llamaindex_service.update_document_metadata(
            document_id=document_id, metadata_updates=subtheme_data, merge_mode="update"
        )

        if result.is_failure():
            error_msg = result.error
            if "not found" in error_msg.lower():
                raise ResourceNotFoundError("Document", document_id)
            raise InternalServerError("Update document subtheme", Exception(error_msg))

        update_info = result.value or {}

        return SubthemeUpdateResponse(
            document_id=document_id,
            updated_fields=list(subtheme_data.keys()),
            success=update_info.get("success", True),
        )

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("Update document subtheme", e) from e
