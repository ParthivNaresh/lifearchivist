"""
Get timeline data endpoint.
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, status

from lifearchivist.utils.logging import log_event, track

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError
from .constants import MAX_DOCUMENTS_QUERY
from .misc_models import DateRange, DocumentSummary, MonthData, YearData
from .response_models import TimelineDataResponse
from .utils import parse_date_filter, process_timeline_document

router = APIRouter()


@router.get(
    "/data",
    response_model=TimelineDataResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Invalid date format",
            "content": {
                "application/json": {"example": {"detail": "Invalid start_date format"}}
            },
        },
        503: {
            "description": "Service unavailable",
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
                    "example": {"detail": "Get timeline data failed: <error message>"}
                }
            },
        },
    },
)
@track(
    operation="get_timeline_data",
    track_performance=True,
    frequency="low_frequency",
)
async def get_timeline_data(
    start_date: Optional[str] = Query(
        None, description="Start date filter (ISO format: YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(
        None, description="End date filter (ISO format: YYYY-MM-DD)"
    ),
) -> TimelineDataResponse:
    """
    Get timeline data for document visualization.

    Returns documents grouped by year and month with their creation dates.
    Uses document_created_at as primary date, falls back to file_modified_at_disk.

    Args:
        start_date: Optional ISO date string (YYYY-MM-DD) to filter from
        end_date: Optional ISO date string (YYYY-MM-DD) to filter to
        container: Service container with dependencies

    Returns:
        {
            "total_documents": int,
            "date_range": {"earliest": str, "latest": str},
            "by_year": {
                "2024": {
                    "count": int,
                    "months": {
                        "01": {"count": int, "documents": [...]},
                        ...
                    }
                }
            }
        }
    """
    server = get_server()

    if not server.llamaindex_service:
        raise ServiceUnavailableError("LlamaIndex service")

    try:
        filter_start = parse_date_filter(start_date, "start_date")
        filter_end = parse_date_filter(end_date, "end_date")

        documents_result = await server.llamaindex_service.query_documents_by_metadata(
            filters={}, limit=MAX_DOCUMENTS_QUERY
        )

        if documents_result.is_failure():
            raise InternalServerError(
                "Query documents",
                RuntimeError(f"Failed to query documents: {documents_result.error}"),
            )

        documents: List[Dict[str, Any]] = documents_result.unwrap()

        timeline_data: Dict[str, Any] = {
            "total_documents": 0,
            "date_range": {"earliest": None, "latest": None},
            "by_year": {},
            "documents_without_dates": 0,
        }

        earliest_date: Optional[date] = None
        latest_date: Optional[date] = None

        for doc in documents:
            earliest_date, latest_date, _ = process_timeline_document(
                doc, timeline_data, filter_start, filter_end, earliest_date, latest_date
            )

        if earliest_date is not None:
            timeline_data["date_range"]["earliest"] = earliest_date.isoformat()
        if latest_date is not None:
            timeline_data["date_range"]["latest"] = latest_date.isoformat()

        log_event(
            "timeline_data_generated",
            {
                "total_documents": timeline_data["total_documents"],
                "years": len(timeline_data["by_year"]),
                "date_range": timeline_data["date_range"],
            },
        )

        by_year_typed: Dict[str, YearData] = {}
        for year, year_data in timeline_data["by_year"].items():
            months_typed: Dict[str, MonthData] = {}
            for month, month_data in year_data["months"].items():
                documents_typed = [
                    DocumentSummary(**doc) for doc in month_data["documents"]
                ]
                months_typed[month] = MonthData(
                    count=month_data["count"],
                    documents=documents_typed,
                )
            by_year_typed[year] = YearData(
                count=year_data["count"],
                months=months_typed,
            )

        return TimelineDataResponse(
            total_documents=timeline_data["total_documents"],
            date_range=DateRange(
                earliest=timeline_data["date_range"]["earliest"],
                latest=timeline_data["date_range"]["latest"],
            ),
            by_year=by_year_typed,
            documents_without_dates=timeline_data["documents_without_dates"],
        )

    except ServiceUnavailableError:
        raise
    except Exception as e:
        log_event(
            "timeline_endpoint_error",
            {"error": str(e), "error_type": type(e).__name__},
            level=logging.ERROR,
        )
        raise InternalServerError("Get timeline data", e) from e
