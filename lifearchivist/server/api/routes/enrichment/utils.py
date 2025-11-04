"""
Utility functions for enrichment endpoints.
"""

from typing import Any, Optional, Tuple

from fastapi.responses import JSONResponse

from ..shared.responses import error_response


def validate_background_tasks(
    server: Any,
) -> Tuple[Optional[Any], Optional[JSONResponse]]:
    """
    Validate background tasks service availability.

    Args:
        server: Server instance

    Returns:
        Tuple of (service, error_response) where one is None
    """
    if not server.background_tasks:
        return None, error_response(
            error="Background enrichment not available",
            error_type="ServiceUnavailable",
            status_code=503,
            enabled=False,
        )

    return server.background_tasks, None


def validate_enrichment_queue(
    server: Any,
) -> Tuple[Optional[Any], Optional[JSONResponse]]:
    """
    Validate enrichment queue availability.

    Args:
        server: Server instance

    Returns:
        Tuple of (service, error_response) where one is None
    """
    if not server.enrichment_queue:
        return None, error_response(
            error="Enrichment queue not initialized",
            error_type="ServiceUnavailable",
            status_code=503,
            status="not_available",
        )

    return server.enrichment_queue, None
