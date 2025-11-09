"""
Activity events endpoint.
"""

from fastapi import APIRouter, Query, status

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError
from .constants import DEFAULT_LIMIT, MAX_LIMIT, MIN_LIMIT
from .misc_models import ActivityEvent
from .response_models import ActivityEventsResponse

router = APIRouter()


@router.get(
    "/events",
    response_model=ActivityEventsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        503: {
            "description": "Activity manager unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "Activity manager not available"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Retrieve activity events failed: <error message>"
                    }
                }
            },
        },
    },
)
async def get_activity_events(
    limit: int = Query(
        default=DEFAULT_LIMIT,
        ge=MIN_LIMIT,
        le=MAX_LIMIT,
        description="Maximum number of events to return",
    ),
) -> ActivityEventsResponse:
    """
    Get recent activity events ordered by newest first.

    Returns activity events from Redis including folder watch operations, uploads,
    deletions, Q&A queries, and other system activities.

    ## Query Parameters

    - **limit**: Maximum events to return (1-1000, default: 200)

    ## Response Fields

    - **events**: Array of activity event objects
    - **count**: Number of events returned

    ## Example Response

    ```json
    {
        "events": [
            {
                "type": "document_uploaded",
                "timestamp": "2025-01-08T14:30:00Z",
                "details": {
                    "document_id": "doc_123",
                    "filename": "report.pdf",
                    "size_bytes": 1024000
                }
            },
            {
                "type": "folder_scan_completed",
                "timestamp": "2025-01-08T14:25:00Z",
                "details": {
                    "folder_id": "folder_456",
                    "files_found": 10
                }
            },
            {
                "type": "qa_query",
                "timestamp": "2025-01-08T14:20:00Z",
                "details": {
                    "query": "What is AI?",
                    "response_time_ms": 1500
                }
            }
        ],
        "count": 3
    }
    ```

    ## Event Types

    Activity events include:
    - **document_uploaded**: Document added to system
    - **document_deleted**: Document removed
    - **folder_scan_completed**: Folder scan finished
    - **folder_added**: New folder added to watch
    - **folder_removed**: Folder removed from watch
    - **qa_query**: Q&A query processed
    - **enrichment_completed**: Document enrichment finished
    - **error_occurred**: System error logged

    ## Event Structure

    Each event contains:
    - **type**: Event type identifier
    - **timestamp**: ISO 8601 timestamp
    - **details**: Event-specific data (varies by type)

    ## Use Cases

    - Display activity feed in UI
    - Monitor system operations
    - Track user actions
    - Debug system behavior
    - Audit trail

    ## Ordering

    - Events ordered by timestamp (newest first)
    - Most recent activity at top
    - Chronological reverse order

    ## Storage

    - Events stored in Redis
    - Rolling window (oldest removed when full)
    - Maximum capacity enforced
    - Real-time updates via WebSocket

    ## Real-time Updates

    - WebSocket available for live updates
    - Event type: "activity_event"
    - Push notifications for new events
    - No polling needed

    ## Performance Notes

    - Fast Redis retrieval
    - Limit enforced for performance
    - Efficient pagination
    - Safe to poll frequently

    ## Notes

    - Returns 503 if activity manager unavailable
    - Empty array if no events
    - Limit enforced: 1-1000 per request
    - Events may be pruned based on capacity
    """
    server = get_server()

    if not server.activity_manager:
        raise ServiceUnavailableError("Activity manager")

    try:
        events_data = await server.activity_manager.get_recent_events(limit)

        events = [ActivityEvent(**event) for event in events_data]

        return ActivityEventsResponse(
            events=events,
            count=len(events),
        )

    except ServiceUnavailableError:
        raise
    except Exception as e:
        raise InternalServerError("Retrieve activity events", e) from e
