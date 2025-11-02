"""
Timeline API routes for temporal document visualization.
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from lifearchivist.utils.logging import log_event, track

from ..dependencies import get_server
from .utils import (
    parse_date_filter,
    process_summary_document,
    process_timeline_document,
)

router = APIRouter(prefix="/api", tags=["timeline"])


@router.get("/timeline/data")
@track(
    operation="get_timeline_data",
    track_performance=True,
    frequency="low_frequency",
)
async def get_timeline_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
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
        raise HTTPException(status_code=503, detail="LlamaIndex service not available")

    try:
        # Get all documents with metadata
        documents_result = await server.llamaindex_service.query_documents_by_metadata(
            filters={}, limit=10000  # Get all documents for timeline
        )

        if documents_result.is_failure():
            raise HTTPException(
                status_code=500,
                detail=f"Failed to query documents: {documents_result.error}",
            )

        documents: List[Dict[str, Any]] = documents_result.unwrap()

        filter_start = parse_date_filter(start_date, "start_date")
        filter_end = parse_date_filter(end_date, "end_date")

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

        # Set date range
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

    except HTTPException:
        raise
    except Exception as e:
        log_event(
            "timeline_endpoint_error",
            {"error": str(e), "error_type": type(e).__name__},
            level=logging.ERROR,
        )
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        ) from e


@router.get("/timeline/summary")
@track(
    operation="get_timeline_summary",
    track_performance=True,
    frequency="low_frequency",
)
async def get_timeline_summary() -> Dict[str, Any]:
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
        raise HTTPException(status_code=503, detail="LlamaIndex service not available")

    try:
        # Get all documents
        documents_result = await server.llamaindex_service.query_documents_by_metadata(
            filters={}, limit=10000
        )

        if documents_result.is_failure():
            raise HTTPException(
                status_code=500,
                detail=f"Failed to query documents: {documents_result.error}",
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

        # Set date range
        if earliest_date is not None:
            summary["date_range"]["earliest"] = earliest_date.isoformat()
        if latest_date is not None:
            summary["date_range"]["latest"] = latest_date.isoformat()

        return summary

    except HTTPException:
        raise
    except Exception as e:
        log_event("timeline_summary_error", {"error": str(e)}, level=logging.ERROR)
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        ) from e
