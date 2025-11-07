from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Citation information."""

    doc_id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    snippet: str = Field(..., description="Text snippet")
    score: float = Field(..., description="Relevance score")
