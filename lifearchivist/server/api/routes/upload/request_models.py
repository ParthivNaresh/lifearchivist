from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """Document ingestion request."""

    path: str = Field(description="File path to ingest")
    mime_hint: Optional[str] = Field(default=None, description="MIME type hint")
    tags: Optional[List[str]] = Field(default=None, description="Initial tags")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Custom metadata"
    )
    session_id: Optional[str] = Field(
        default=None, description="WebSocket session ID for progress tracking"
    )


class BulkIngestRequest(BaseModel):
    file_paths: List[str]
    folder_path: str = ""
