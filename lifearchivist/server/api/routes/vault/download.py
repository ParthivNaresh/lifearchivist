"""
Download file from vault endpoint.
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ..shared.dependencies import get_server
from ..shared.responses import (
    error_response,
    internal_error_response,
    service_unavailable_response,
)
from .utils import (
    get_mime_type_and_disposition,
    get_original_filename,
    resolve_vault_file_path,
    validate_file_hash,
)

router = APIRouter()


@router.get("/file/{file_hash}")
async def download_file_from_vault(file_hash: str):
    """
    Download or view a file from vault by its SHA256 hash.

    Args:
        file_hash: Full SHA256 hash of the file (64 characters)

    Returns:
        FileResponse with appropriate Content-Disposition:
        - inline: PDFs, images, text files (viewable in browser)
        - attachment: Office docs, other files (force download)

    Process:
    1. Validates hash format
    2. Locates file in content-addressed storage
    3. Retrieves original filename from metadata
    4. Sets appropriate MIME type
    5. Returns file with proper headers

    Vault structure: content/XX/YY/ZZZZ...{ext}
    where XXYYZZZZ... is the SHA256 hash split for directory sharding.
    """
    server = get_server()

    try:
        if not server.vault:
            return service_unavailable_response("Vault")

        error_response_obj = validate_file_hash(file_hash)
        if error_response_obj:
            return error_response_obj

        file_path, error_response_obj = resolve_vault_file_path(
            server.vault.content_dir, file_hash
        )
        if error_response_obj:
            return error_response_obj

        assert file_path is not None

        filename = await get_original_filename(
            server.llamaindex_service,
            file_hash,
            file_path.name,
        )

        mime_type, disposition = get_mime_type_and_disposition(file_path.suffix)

        return FileResponse(
            path=str(file_path),
            media_type=mime_type,
            headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
        )

    except PermissionError as e:
        return error_response(
            error=f"Permission denied accessing file: {str(e)}",
            error_type="PermissionError",
            status_code=403,
        )
    except Exception as e:
        return internal_error_response("Download file", e)
