"""
Get queue statistics endpoint.
"""

from typing import Optional

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError

router = APIRouter()


class QueueStatsResponse(BaseModel):
    """Response containing enrichment queue statistics."""

    status: str = Field(..., description="Queue operational status")
    queue_length: int = Field(..., description="Number of tasks waiting in queue")
    processing: int = Field(..., description="Number of tasks currently processing")
    completed: int = Field(..., description="Number of recently completed tasks")
    failed: int = Field(..., description="Number of recently failed tasks")
    error: Optional[str] = Field(None, description="Error message if status is 'error'")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "operational",
                "queue_length": 5,
                "processing": 2,
                "completed": 150,
                "failed": 3,
                "error": None,
            }
        }


@router.get(
    "/queue/stats",
    response_model=QueueStatsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        503: {
            "description": "Enrichment queue service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "Enrichment queue not available"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Get queue stats failed: <error message>"}
                }
            },
        },
    },
)
async def get_queue_stats() -> QueueStatsResponse:
    """
    Get enrichment queue statistics and operational metrics.

    Returns real-time statistics about the background enrichment queue including
    pending tasks, processing status, and completion metrics.

    ## Response Fields

    - **status**: Queue operational status
      - `operational`: Queue is running normally
      - `not_initialized`: Queue hasn't been initialized
      - `error`: Queue encountered an error
    - **queue_length**: Number of tasks waiting to be processed
    - **processing**: Number of tasks currently being processed
    - **completed**: Number of recently completed tasks (last 1000)
    - **failed**: Number of recently failed tasks (last 1000)
    - **error**: Error message (only present if status is 'error')

    ## Example Response (Operational)

    ```json
    {
        "status": "operational",
        "queue_length": 5,
        "processing": 2,
        "completed": 150,
        "failed": 3,
        "error": null
    }
    ```

    ## Example Response (Not Initialized)

    ```json
    {
        "status": "not_initialized",
        "queue_length": 0,
        "processing": 0,
        "completed": 0,
        "failed": 0,
        "error": null
    }
    ```

    ## Example Response (Error)

    ```json
    {
        "status": "error",
        "queue_length": 0,
        "processing": 0,
        "completed": 0,
        "failed": 0,
        "error": "Redis connection failed"
    }
    ```

    ## Queue Metrics Explained

    ### queue_length
    - Tasks waiting to be picked up by workers
    - Higher numbers indicate backlog
    - Zero means queue is empty (good)

    ### processing
    - Tasks currently being processed by workers
    - Should match number of active workers
    - Stuck tasks may indicate worker issues

    ### completed
    - Recently completed tasks (rolling window of last 1000)
    - Indicates successful processing
    - Used for success rate calculations

    ### failed
    - Recently failed tasks (rolling window of last 1000)
    - Tasks that exceeded max retries
    - Monitor for recurring failures

    ## Use Cases

    - Monitor queue health and backlog
    - Check if enrichment is processing
    - Identify processing bottlenecks
    - Track success/failure rates
    - Dashboard metrics display
    - Alerting on queue depth

    ## Queue Status Values

    - **operational**: Queue is functioning normally
    - **not_initialized**: Queue service hasn't started (check server startup)
    - **error**: Queue encountered an error (check Redis connection)

    ## Performance Notes

    - Fast operation (just Redis list lengths)
    - Safe to poll frequently for monitoring
    - No heavy computation
    - Suitable for dashboard updates
    - Minimal Redis overhead

    ## Important Notes

    - Completed/failed counts are rolling windows (last 1000 each)
    - Processing count should match active worker count
    - High queue_length indicates backlog or slow processing
    - Status 'error' indicates Redis connectivity issues
    - All counts are current snapshots (not cumulative)

    ## Monitoring Guidelines

    - **Healthy**: queue_length < 10, processing > 0, status = operational
    - **Backlog**: queue_length > 50 (consider scaling workers)
    - **Stuck**: processing > 0 but not changing (check workers)
    - **Failing**: failed count increasing rapidly (check logs)
    - **Down**: status = error or not_initialized (check service)
    """
    server = get_server()

    if not server.enrichment_queue:
        raise ServiceUnavailableError("Enrichment queue")

    try:
        stats = await server.enrichment_queue.get_stats()

        return QueueStatsResponse(
            status=stats.get("status", "unknown"),
            queue_length=stats.get("queue_length", 0),
            processing=stats.get("processing", 0),
            completed=stats.get("completed", 0),
            failed=stats.get("failed", 0),
            error=stats.get("error"),
        )

    except ServiceUnavailableError:
        raise
    except Exception as e:
        raise InternalServerError("Get queue stats", e) from e
