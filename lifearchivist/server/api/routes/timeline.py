"""
Timeline API routes for temporal document visualization.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from lifearchivist.utils.logging import log_event, track

from ..dependencies import get_server

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

        # Parse date filters if provided
        filter_start = None
        filter_end = None
        if start_date:
            try:
                filter_start = datetime.fromisoformat(start_date).date()
            except ValueError as err:
                raise HTTPException(
                    status_code=400, detail="Invalid start_date format"
                ) from err
        if end_date:
            try:
                filter_end = datetime.fromisoformat(end_date).date()
            except ValueError as err:
                raise HTTPException(
                    status_code=400, detail="Invalid end_date format"
                ) from err

        # Process documents and extract temporal data
        by_year: Dict[str, Dict[str, Any]] = {}
        timeline_data: Dict[str, Any] = {
            "total_documents": 0,
            "date_range": {"earliest": None, "latest": None},
            "by_year": by_year,
            "documents_without_dates": 0,
        }

        earliest_date: Optional[date] = None
        latest_date: Optional[date] = None

        for doc in documents:
            metadata: Dict[str, Any] = doc.get("metadata", {})

            # Get the best available date (priority order)
            doc_date_str = (
                metadata.get("document_created_at")
                or metadata.get("file_modified_at_disk")
                or metadata.get("uploaded_at")
            )

            if not doc_date_str:
                timeline_data["documents_without_dates"] += 1
                continue

            try:
                # Parse ISO date string
                doc_date = datetime.fromisoformat(doc_date_str.replace("Z", "+00:00"))
                doc_date_only = doc_date.date()

                # Apply date filters
                if filter_start and doc_date_only < filter_start:
                    continue
                if filter_end and doc_date_only > filter_end:
                    continue

                # Track earliest/latest
                if earliest_date is None or doc_date_only < earliest_date:
                    earliest_date = doc_date_only
                if latest_date is None or doc_date_only > latest_date:
                    latest_date = doc_date_only

                # Extract year and month
                year = str(doc_date.year)
                month = f"{doc_date.month:02d}"

                # Initialize year if needed
                if year not in timeline_data["by_year"]:
                    timeline_data["by_year"][year] = {"count": 0, "months": {}}

                # Initialize month if needed
                if month not in timeline_data["by_year"][year]["months"]:
                    timeline_data["by_year"][year]["months"][month] = {
                        "count": 0,
                        "documents": [],
                    }

                # Add document summary
                doc_summary = {
                    "id": doc.get("document_id"),
                    "title": metadata.get("title", "Untitled"),
                    "date": doc_date_str,
                    "mime_type": metadata.get("mime_type"),
                    "theme": metadata.get("classifications", {}).get("theme"),
                }

                timeline_data["by_year"][year]["months"][month]["documents"].append(
                    doc_summary
                )
                timeline_data["by_year"][year]["months"][month]["count"] += 1
                timeline_data["by_year"][year]["count"] += 1
                timeline_data["total_documents"] += 1

            except (ValueError, AttributeError) as e:
                log_event(
                    "timeline_date_parse_error",
                    {
                        "document_id": doc.get("document_id"),
                        "date_string": doc_date_str,
                        "error": str(e),
                    },
                    level=logging.WARNING,
                )
                continue

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

        by_year: Dict[str, int] = {}
        data_quality: Dict[str, int] = {
            "with_document_created_at": 0,
            "with_platform_dates": 0,
            "fallback_to_disk": 0,
            "no_dates": 0,
        }
        summary: Dict[str, Any] = {
            "total_documents": len(documents),
            "date_range": {"earliest": None, "latest": None},
            "by_year": by_year,
            "data_quality": data_quality,
        }

        earliest_date: Optional[date] = None
        latest_date: Optional[date] = None

        for doc in documents:
            metadata: Dict[str, Any] = doc.get("metadata", {})

            # Track data quality and get best date
            doc_date_str = metadata.get("document_created_at")
            if doc_date_str:
                summary["data_quality"]["with_document_created_at"] += 1
            else:
                doc_date_str = metadata.get("file_modified_at_disk")
                if doc_date_str:
                    summary["data_quality"]["fallback_to_disk"] += 1
                else:
                    summary["data_quality"]["no_dates"] += 1
                    continue

            try:
                # Type guard: doc_date_str is guaranteed to be str here due to continue above
                if not isinstance(doc_date_str, str):
                    continue
                doc_date = datetime.fromisoformat(doc_date_str.replace("Z", "+00:00"))
                doc_date_only = doc_date.date()

                # Track earliest/latest
                if earliest_date is None:
                    earliest_date = doc_date_only
                elif doc_date_only < earliest_date:
                    earliest_date = doc_date_only

                if latest_date is None:
                    latest_date = doc_date_only
                elif doc_date_only > latest_date:
                    latest_date = doc_date_only

                # Count by year
                year = str(doc_date.year)
                by_year[year] = by_year.get(year, 0) + 1

            except (ValueError, AttributeError):
                continue

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
