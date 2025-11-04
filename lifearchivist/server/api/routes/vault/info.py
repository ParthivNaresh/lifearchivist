"""
Get vault info endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import (
    internal_error_response,
    service_unavailable_response,
    success_response,
)

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
        return service_unavailable_response("Vault")

    try:
        stats = await server.vault.get_vault_statistics()
        return success_response(stats)
    except AttributeError as e:
        return internal_error_response(
            "Get vault statistics",
            RuntimeError(f"Vault statistics unavailable: {str(e)}"),
        )
    except Exception as e:
        return internal_error_response("Get vault info", e)
