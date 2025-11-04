"""
Get timeline data endpoint.
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from lifearchivist.utils.logging import log_event, track

from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response, service_unavailable_response
from .utils import parse_date_filter, process_timeline_document

router = APIRouter()


@router.get("/data")
@track(
    operation="get_timeline_data",
    track_performance=True,
    frequency="low_frequency",
)
async def get_timeline_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Union[Dict[str, Any], JSONResponse]:
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
        return service_unavailable_response("LlamaIndex service")

    try:
        filter_start, error_response = parse_date_filter(start_date, "start_date")
        if error_response:
            return error_response

        filter_end, error_response = parse_date_filter(end_date, "end_date")
        if error_response:
            return error_response

        documents_result = await server.llamaindex_service.query_documents_by_metadata(
            filters={}, limit=10000
        )

        if documents_result.is_failure():
            return internal_error_response(
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

        return timeline_data

    except Exception as e:
        log_event(
            "timeline_endpoint_error",
            {"error": str(e), "error_type": type(e).__name__},
            level=logging.ERROR,
        )
        return internal_error_response("Get timeline data", e)
