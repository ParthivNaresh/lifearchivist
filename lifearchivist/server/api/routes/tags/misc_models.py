"""
Miscellaneous models for tags endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Tag(BaseModel):
    """Tag model with document count."""

    name: str = Field(..., description="Tag name")
    count: int = Field(..., description="Number of documents with this tag")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional tag metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "AI",
                "count": 42,
                "metadata": {"category": "technology"},
            }
        }


class Topic(BaseModel):
    """Topic model for landscape visualization."""

    id: str = Field(..., description="Topic identifier")
    name: str = Field(..., description="Topic name")
    document_count: int = Field(..., description="Number of documents in this topic")
    subtopics: List[str] = Field(
        default_factory=list, description="List of subtopic names"
    )
    parent_topic: Optional[str] = Field(None, description="Parent topic name")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional topic metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "topic_ai",
                "name": "Artificial Intelligence",
                "document_count": 150,
                "subtopics": ["Machine Learning", "Neural Networks"],
                "parent_topic": None,
                "metadata": {"category": "technology"},
            }
        }
