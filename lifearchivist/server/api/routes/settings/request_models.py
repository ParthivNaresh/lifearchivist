from typing import Optional

from pydantic import BaseModel, Field

from .constants import (
    MAX_CONTEXT_WINDOW_SIZE,
    MAX_MAX_FILE_SIZE_MB,
    MAX_MAX_OUTPUT_TOKENS,
    MAX_RESPONSE_TIMEOUT,
    MAX_SEARCH_RESULTS_LIMIT,
    MAX_TEMPERATURE,
    MIN_CONTEXT_WINDOW_SIZE,
    MIN_MAX_FILE_SIZE_MB,
    MIN_MAX_OUTPUT_TOKENS,
    MIN_RESPONSE_TIMEOUT,
    MIN_SEARCH_RESULTS_LIMIT,
    MIN_TEMPERATURE,
)


class SettingsUpdateRequest(BaseModel):
    """Request model for updating settings."""

    auto_extract_dates: Optional[bool] = None
    generate_text_previews: Optional[bool] = None
    max_file_size_mb: Optional[int] = Field(
        None, ge=MIN_MAX_FILE_SIZE_MB, le=MAX_MAX_FILE_SIZE_MB
    )

    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    search_results_limit: Optional[int] = Field(
        None, ge=MIN_SEARCH_RESULTS_LIMIT, le=MAX_SEARCH_RESULTS_LIMIT
    )

    temperature: Optional[float] = Field(None, ge=MIN_TEMPERATURE, le=MAX_TEMPERATURE)
    max_output_tokens: Optional[int] = Field(
        None, ge=MIN_MAX_OUTPUT_TOKENS, le=MAX_MAX_OUTPUT_TOKENS
    )
    response_format: Optional[str] = Field(None, pattern="^(concise|verbose)$")
    context_window_size: Optional[int] = Field(
        None, ge=MIN_CONTEXT_WINDOW_SIZE, le=MAX_CONTEXT_WINDOW_SIZE
    )
    response_timeout: Optional[int] = Field(
        None, ge=MIN_RESPONSE_TIMEOUT, le=MAX_RESPONSE_TIMEOUT
    )

    auto_organize_by_date: Optional[bool] = None
    duplicate_detection: Optional[bool] = None
    default_import_location: Optional[str] = None

    theme: Optional[str] = Field(None, pattern="^(light|dark|system)$")
    interface_density: Optional[str] = Field(
        None, pattern="^(compact|comfortable|spacious)$"
    )
