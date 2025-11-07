from typing import Optional

from pydantic import BaseModel, Field


class SettingsUpdateRequest(BaseModel):
    """Request model for updating settings."""

    auto_extract_dates: Optional[bool] = None
    generate_text_previews: Optional[bool] = None
    max_file_size_mb: Optional[int] = Field(None, ge=1, le=1000)

    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    search_results_limit: Optional[int] = Field(None, ge=1, le=1000)

    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_output_tokens: Optional[int] = Field(None, ge=1, le=1000000)
    response_format: Optional[str] = Field(None, pattern="^(concise|verbose)$")
    context_window_size: Optional[int] = Field(None, ge=1, le=50)
    response_timeout: Optional[int] = Field(None, ge=5, le=300)

    auto_organize_by_date: Optional[bool] = None
    duplicate_detection: Optional[bool] = None
    default_import_location: Optional[str] = None

    theme: Optional[str] = Field(None, pattern="^(light|dark|system)$")
    interface_density: Optional[str] = Field(
        None, pattern="^(compact|comfortable|spacious)$"
    )
