"""
Utility functions for conversation endpoints.
"""

from datetime import datetime
from typing import Any
from uuid import UUID


def serialize_for_json(obj: Any) -> Any:
    """
    Recursively convert objects to JSON-serializable types.

    Handles:
    - UUID -> str
    - datetime -> ISO format str
    - dict -> recursively serialize values
    - list -> recursively serialize items
    """
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    else:
        return obj
