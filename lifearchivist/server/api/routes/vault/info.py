"""
Get vault info endpoint.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server

router = APIRouter()


@router.get("/info")
async def get_vault_info():
    """
    Get vault information and statistics.

    Returns:
    - Total file count
    - Total storage size
    - File type distribution
    - Directory structure info

    Useful for:
    - Monitoring storage usage
    - Debugging storage issues
    - System health checks
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

    try:
        stats = await server.vault.get_vault_statistics()
        return {"success": True, **stats}
    except AttributeError as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Vault statistics unavailable: {str(e)}",
                "error_type": "ServiceError",
            },
            status_code=500,
        )
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Failed to retrieve vault info: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )
