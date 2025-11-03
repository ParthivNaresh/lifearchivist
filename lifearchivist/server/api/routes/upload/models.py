"""
Pydantic models for upload endpoints.
"""

from typing import List

from pydantic import BaseModel


class BulkIngestRequest(BaseModel):
    file_paths: List[str]
    folder_path: str = ""
