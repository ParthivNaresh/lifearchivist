from typing import Any, Dict, Optional, Tuple

from fastapi.responses import JSONResponse

from ..shared.responses import validation_error_response


def parse_date_filter(
    date_str: Optional[str], filter_name: str
) -> Tuple[Optional[Any], Optional[JSONResponse]]:
    """
    Parse ISO date string to date object.

    Args:
        date_str: ISO date string (YYYY-MM-DD)
        filter_name: Name of filter for error messages

    Returns:
        Tuple of (date_object, error_response) where one is None
    """
    if not date_str:
        return None, None

    try:
        from datetime import datetime

        return datetime.fromisoformat(date_str).date(), None
    except ValueError:
        return None, validation_error_response(f"Invalid {filter_name} format")


def extract_document_date(metadata: Dict[str, Any]) -> Optional[str]:
    """
    Extract best available date from document metadata.

    Priority order:
    1. document_created_at
    2. file_modified_at_disk
    3. uploaded_at

    Args:
        metadata: Document metadata dictionary

    Returns:
        ISO date string or None if no date available
    """
    return (
        metadata.get("document_created_at")
        or metadata.get("file_modified_at_disk")
        or metadata.get("uploaded_at")
    )


def parse_document_date(date_str: str) -> Optional[Any]:
    """
    Parse ISO date string to date object.

    Args:
        date_str: ISO date string

    Returns:
        date object or None if parsing fails
    """
    try:
        from datetime import datetime

        doc_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return doc_date.date()
    except (ValueError, AttributeError):
        return None


def should_include_document(
    doc_date: Any,
    filter_start: Optional[Any],
    filter_end: Optional[Any],
) -> bool:
    """
    Check if document date falls within filter range.

    Args:
        doc_date: Document date object
        filter_start: Start date filter (inclusive)
        filter_end: End date filter (inclusive)

    Returns:
        True if document should be included
    """
    if filter_start and doc_date < filter_start:
        return False
    if filter_end and doc_date > filter_end:
        return False
    return True


def update_date_range(
    doc_date: Any,
    earliest: Optional[Any],
    latest: Optional[Any],
) -> Tuple[Any, Any]:
    """
    Update earliest and latest dates.

    Args:
        doc_date: Current document date
        earliest: Current earliest date
        latest: Current latest date

    Returns:
        Tuple of (new_earliest, new_latest)
    """
    new_earliest = (
        earliest if earliest is not None and earliest < doc_date else doc_date
    )
    new_latest = latest if latest is not None and latest > doc_date else doc_date
    return new_earliest, new_latest


def initialize_year_structure(
    by_year: Dict[str, Dict[str, Any]],
    year: str,
) -> None:
    """
    Initialize year structure in timeline data if not exists.

    Args:
        by_year: Timeline data by year dictionary
        year: Year string (YYYY)
    """
    if year not in by_year:
        by_year[year] = {"count": 0, "months": {}}


def initialize_month_structure(
    year_data: Dict[str, Any],
    month: str,
) -> None:
    """
    Initialize month structure in year data if not exists.

    Args:
        year_data: Year data dictionary
        month: Month string (MM)
    """
    if month not in year_data["months"]:
        year_data["months"][month] = {"count": 0, "documents": []}


def create_document_summary(
    doc: Dict[str, Any],
    metadata: Dict[str, Any],
    doc_date_str: str,
) -> Dict[str, Any]:
    """
    Create document summary for timeline.

    Args:
        doc: Document dictionary
        metadata: Document metadata
        doc_date_str: ISO date string

    Returns:
        Document summary dictionary
    """
    return {
        "id": doc.get("document_id"),
        "title": metadata.get("title", "Untitled"),
        "date": doc_date_str,
        "mime_type": metadata.get("mime_type"),
        "theme": metadata.get("classifications", {}).get("theme"),
    }


def add_document_to_timeline(
    timeline_data: Dict[str, Any],
    year: str,
    month: str,
    doc_summary: Dict[str, Any],
) -> None:
    """
    Add document to timeline data structure.

    Args:
        timeline_data: Timeline data dictionary
        year: Year string (YYYY)
        month: Month string (MM)
        doc_summary: Document summary dictionary
    """
    timeline_data["by_year"][year]["months"][month]["documents"].append(doc_summary)
    timeline_data["by_year"][year]["months"][month]["count"] += 1
    timeline_data["by_year"][year]["count"] += 1
    timeline_data["total_documents"] += 1


def process_timeline_document(
    doc: Dict[str, Any],
    timeline_data: Dict[str, Any],
    filter_start: Optional[Any],
    filter_end: Optional[Any],
    earliest_date: Optional[Any],
    latest_date: Optional[Any],
) -> Tuple[Optional[Any], Optional[Any], bool]:
    """
    Process single document for timeline data.

    Args:
        doc: Document dictionary
        timeline_data: Timeline data to update
        filter_start: Start date filter
        filter_end: End date filter
        earliest_date: Current earliest date
        latest_date: Current latest date

    Returns:
        Tuple of (new_earliest, new_latest, was_processed)
    """
    from datetime import datetime

    metadata = doc.get("metadata", {})
    doc_date_str = extract_document_date(metadata)

    if not doc_date_str:
        timeline_data["documents_without_dates"] += 1
        return earliest_date, latest_date, False

    doc_date_only = parse_document_date(doc_date_str)
    if not doc_date_only:
        return earliest_date, latest_date, False

    if not should_include_document(doc_date_only, filter_start, filter_end):
        return earliest_date, latest_date, False

    earliest_date, latest_date = update_date_range(
        doc_date_only, earliest_date, latest_date
    )

    doc_date = datetime.fromisoformat(doc_date_str.replace("Z", "+00:00"))
    year = str(doc_date.year)
    month = f"{doc_date.month:02d}"

    initialize_year_structure(timeline_data["by_year"], year)
    initialize_month_structure(timeline_data["by_year"][year], month)

    doc_summary = create_document_summary(doc, metadata, doc_date_str)
    add_document_to_timeline(timeline_data, year, month, doc_summary)

    return earliest_date, latest_date, True


def extract_document_date_for_summary(
    metadata: Dict[str, Any],
    data_quality: Dict[str, int],
) -> Optional[str]:
    """
    Extract document date and track data quality metrics.

    Args:
        metadata: Document metadata dictionary
        data_quality: Data quality tracking dictionary to update

    Returns:
        ISO date string or None if no date available
    """
    doc_date_str = metadata.get("document_created_at")
    if doc_date_str:
        data_quality["with_document_created_at"] += 1
        return str(doc_date_str)

    doc_date_str = metadata.get("file_modified_at_disk")
    if doc_date_str:
        data_quality["fallback_to_disk"] += 1
        return str(doc_date_str)

    data_quality["no_dates"] += 1
    return None


def process_summary_document(
    doc: Dict[str, Any],
    summary: Dict[str, Any],
    earliest_date: Optional[Any],
    latest_date: Optional[Any],
) -> Tuple[Optional[Any], Optional[Any]]:
    """
    Process single document for timeline summary.

    Args:
        doc: Document dictionary
        summary: Summary data to update
        earliest_date: Current earliest date
        latest_date: Current latest date

    Returns:
        Tuple of (new_earliest, new_latest)
    """
    from datetime import datetime

    metadata = doc.get("metadata", {})
    doc_date_str = extract_document_date_for_summary(metadata, summary["data_quality"])

    if not doc_date_str:
        return earliest_date, latest_date

    try:
        doc_date = datetime.fromisoformat(doc_date_str.replace("Z", "+00:00"))
        doc_date_only = doc_date.date()

        earliest_date, latest_date = update_date_range(
            doc_date_only, earliest_date, latest_date
        )

        year = str(doc_date.year)
        summary["by_year"][year] = summary["by_year"].get(year, 0) + 1

        return earliest_date, latest_date
    except (ValueError, AttributeError):
        return earliest_date, latest_date
