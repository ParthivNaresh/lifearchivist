"""
Get enrichment status endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError
from .response_models import EnrichmentStatusResponse

router = APIRouter()


@router.get(
    "/status",
    response_model=EnrichmentStatusResponse,
    status_code=status.HTTP_200_OK,
    responses={
        503: {
            "description": "Background enrichment service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "Background enrichment not available"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Get enrichment status failed: <error message>"
                    }
                }
            },
        },
    },
)
async def get_enrichment_status() -> EnrichmentStatusResponse:
    """
    Get enrichment service and worker status.

    Returns operational status of the background enrichment system including
    whether it's enabled and detailed worker metrics if available.

    ## Response Fields

    - **enabled**: Whether enrichment service is enabled and running
    - **enrichment_worker**: Worker status details (null if disabled)
      - Contains worker-specific metrics like tasks processed, uptime, etc.
      - Structure depends on worker implementation

    ## Example Response (Enabled)

    ```json
    {
        "enabled": true,
        "enrichment_worker": {
            "status": "running",
            "tasks_processed": 150,
            "uptime_seconds": 3600,
            "last_task_at": "2025-01-08T14:30:00Z"
        }
    }
    ```

    ## Example Response (Disabled)

    ```json
    {
        "enabled": false,
        "enrichment_worker": null
    }
    ```

    ## Use Cases

    - Check if enrichment is operational
    - Monitor worker health
    - Verify service startup
    - Dashboard status display
    - Health check endpoints

    ## Status Interpretation

    - **enabled: true, enrichment_worker: {...}**: Service running normally
    - **enabled: false, enrichment_worker: null**: Service disabled or stopped
    - **enabled: true, enrichment_worker: null**: Service starting or restarting

    ## Notes

    - Fast operation (just status check)
    - Safe to poll frequently
    - Worker details vary by implementation
    - Returns 503 if service not available
    """
    server = get_server()

    if not server.background_tasks:
        raise ServiceUnavailableError("Background enrichment")

    try:
        status_data = await server.background_tasks.get_status()

        return EnrichmentStatusResponse(
            enabled=status_data.get("enabled", False),
            enrichment_worker=status_data.get("enrichment_worker"),
        )

    except ServiceUnavailableError:
        raise
    except Exception as e:
        raise InternalServerError("Get enrichment status", e) from e
