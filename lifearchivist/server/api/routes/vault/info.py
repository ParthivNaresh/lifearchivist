"""
Get vault info endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError
from .response_models import VaultInfoResponse

router = APIRouter()


@router.get(
    "/info",
    response_model=VaultInfoResponse,
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
                    "example": {"detail": "Get vault info failed: <error>"}
                }
            },
        },
    },
)
async def get_vault_info() -> VaultInfoResponse:
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
        raise ServiceUnavailableError("Vault")

    try:
        stats = await server.vault.get_vault_statistics()
        return VaultInfoResponse(**stats)
    except AttributeError as e:
        raise InternalServerError(
            "Get vault statistics",
            RuntimeError(f"Vault statistics unavailable: {str(e)}"),
        ) from e
    except Exception as e:
        raise InternalServerError("Get vault info", e) from e
