"""
Get timeline summary endpoint.
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from lifearchivist.utils.logging import log_event, track

from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response, service_unavailable_response
from .utils import process_summary_document

router = APIRouter()


@router.get("/summary", response_model=None)
@track(
    operation="get_timeline_summary",
    track_performance=True,
    frequency="low_frequency",
)
async def get_timeline_summary() -> Union[Dict[str, Any], JSONResponse]:
    """
    Get high-level timeline summary statistics.

    Lightweight endpoint for quick overview without full document details.

    Returns:
        {
            "total_documents": int,
            "date_range": {"earliest": str, "latest": str},
            "by_year": {"2024": 45, "2023": 120, ...},
            "data_quality": {
                "with_document_created_at": int,
                "with_platform_dates": int,
                "fallback_to_disk": int
            }
        }
    """
    server = get_server()

    if not server.llamaindex_service:
        return service_unavailable_response("LlamaIndex service")

    try:
        documents_result = await server.llamaindex_service.query_documents_by_metadata(
            filters={}, limit=10000
        )

        if documents_result.is_failure():
            return internal_error_response(
                "Query documents",
                RuntimeError(f"Failed to query documents: {documents_result.error}"),
            )

        documents: List[Dict[str, Any]] = documents_result.unwrap()

        summary: Dict[str, Any] = {
            "total_documents": len(documents),
            "date_range": {"earliest": None, "latest": None},
            "by_year": {},
            "data_quality": {
                "with_document_created_at": 0,
                "with_platform_dates": 0,
                "fallback_to_disk": 0,
                "no_dates": 0,
            },
        }

        earliest_date: Optional[date] = None
        latest_date: Optional[date] = None

        for doc in documents:
            earliest_date, latest_date = process_summary_document(
                doc, summary, earliest_date, latest_date
            )

        if earliest_date is not None:
            summary["date_range"]["earliest"] = earliest_date.isoformat()
        if latest_date is not None:
            summary["date_range"]["latest"] = latest_date.isoformat()

        return summary

    except Exception as e:
        log_event("timeline_summary_error", {"error": str(e)}, level=logging.ERROR)
        return internal_error_response("Get timeline summary", e)
