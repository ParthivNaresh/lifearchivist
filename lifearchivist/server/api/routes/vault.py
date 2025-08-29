"""
Vault management endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException

from ..dependencies import get_server

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["vault"])


@router.get("/vault/info")
async def get_vault_info():
    """Get vault information for development/debugging."""
    server = get_server()

    try:
        stats = await server.vault.get_vault_statistics()
        return stats

    except Exception as e:
        logger.error(f"Failed to get vault info: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/vault/files")
async def list_vault_files(
    directory: str = "content", limit: int = 100, offset: int = 0
):
    """List files in vault for development/debugging."""
    server = get_server()

    try:
        vault_path = server.settings.vault_path
        target_dir = vault_path / directory

        if not target_dir.exists():
            return {"files": [], "total": 0, "directory": directory}

        # Get all files in the directory
        all_files = []
        for file_path in target_dir.rglob("*"):
            if file_path.is_file():
                stat = file_path.stat()

                # Extract hash from filename (remove extension)
                file_hash = file_path.stem
                if directory == "content":
                    # For content files, the hash is the full filename without extension
                    full_hash = file_path.parent.name + file_hash
                else:
                    full_hash = file_hash

                all_files.append(
                    {
                        "path": str(file_path.relative_to(vault_path)),
                        "full_path": str(file_path),
                        "hash": full_hash,
                        "extension": file_path.suffix.lstrip("."),
                        "size_bytes": stat.st_size,
                        "created_at": stat.st_ctime,
                        "modified_at": stat.st_mtime,
                    }
                )

        # Sort by creation time (newest first)
        all_files.sort(key=lambda x: x["created_at"], reverse=True)

        # Apply pagination
        paginated_files = all_files[offset : offset + limit]

        return {
            "files": paginated_files,
            "total": len(all_files),
            "directory": directory,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Failed to list vault files: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None
