"""
Vault management endpoints.
"""

from fastapi import APIRouter, HTTPException

from ..dependencies import get_server

router = APIRouter(prefix="/api", tags=["vault"])


@router.get("/vault/info")
async def get_vault_info():
    """Get vault information for development/debugging."""
    server = get_server()

    try:
        if not server.vault:
            raise HTTPException(status_code=500, detail="Vault not initialized")
        stats = await server.vault.get_vault_statistics()
        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/vault/files")
async def list_vault_files(
    directory: str = "content", limit: int = 100, offset: int = 0
):
    """List files in vault for development/debugging with database record linking."""
    server = get_server()

    try:
        vault_path = server.settings.vault_path
        if not vault_path:
            raise HTTPException(status_code=500, detail="Vault path not configured")
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
                    # For content files, reconstruct the full hash from directory structure
                    # Path structure: content/93/31/eb7c1d80252e853314bfcb5eba2effb7b163378503f39be03f9dc66fc5d6.pdf
                    # Full hash: 9331eb7c1d80252e853314bfcb5eba2effb7b163378503f39be03f9dc66fc5d6
                    parent_dir = file_path.parent.name  # "31"
                    grandparent_dir = file_path.parent.parent.name  # "93"
                    full_hash = grandparent_dir + parent_dir + file_hash
                else:
                    full_hash = file_hash

                # Look up database record by file_hash
                database_record = None
                if server.llamaindex_service:
                    try:
                        # Query LlamaIndex for documents with this file hash
                        matching_docs = await server.llamaindex_service.query_documents_by_metadata(
                            filters={"file_hash": full_hash}, limit=1
                        )
                        if matching_docs:
                            doc = matching_docs[0]
                            metadata = doc.get("metadata", {})
                            database_record = {
                                "id": doc.get("document_id"),
                                "original_path": metadata.get("original_path"),
                                "status": metadata.get("status"),
                            }
                    except Exception:
                        # If lookup fails, continue without database record
                        pass

                all_files.append(
                    {
                        "path": (
                            str(file_path.relative_to(vault_path))
                            if vault_path
                            else str(file_path)
                        ),
                        "full_path": str(file_path),
                        "hash": full_hash,
                        "extension": file_path.suffix.lstrip("."),
                        "size_bytes": stat.st_size,
                        "created_at": stat.st_ctime,
                        "modified_at": stat.st_mtime,
                        "database_record": database_record,
                    }
                )

        # Sort by creation time (newest first)
        all_files.sort(key=lambda x: float(str(x.get("created_at", 0))), reverse=True)

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
        raise HTTPException(status_code=500, detail=str(e)) from None
