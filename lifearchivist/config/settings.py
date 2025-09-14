"""
Application settings and configuration.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Core Settings
    lifearch_home: Path = Field(
        default_factory=lambda: Path.home() / ".lifearchivist",
        description="Base directory for Life Archivist data",
    )
    vault_path: Optional[Path] = Field(default=None, description="Document vault path")
    database_url: Optional[str] = Field(default=None, description="Database URL")

    # Models
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2", description="Embedding model"
    )
    llm_model: str = Field(default="llama3.2:1b", description="LLM model for Ollama")
    whisper_model: str = Field(default="base.en", description="Whisper model for audio")
    ocr_lang: str = Field(default="eng", description="OCR language")

    # Services
    qdrant_url: str = Field(default="http://localhost:6333", description="Qdrant URL")
    redis_url: str = Field(default="redis://localhost:6379", description="Redis URL")
    ollama_url: str = Field(default="http://localhost:11434", description="Ollama URL")

    # Performance
    max_workers: int = Field(default=4, description="Maximum worker processes")
    chunk_size: int = Field(default=512, description="Text chunk size")
    chunk_overlap: int = Field(default=64, description="Text chunk overlap")
    embedding_batch_size: int = Field(default=32, description="Embedding batch size")

    # Privacy
    local_only: bool = Field(default=True, description="Local-only mode")
    enable_telemetry: bool = Field(default=False, description="Enable telemetry")
    enable_cloud_models: bool = Field(
        default=False, description="Enable cloud model APIs"
    )

    # Storage Limits
    max_file_size_mb: int = Field(default=100, description="Maximum file size in MB")
    max_vault_size_gb: int = Field(default=100, description="Maximum vault size in GB")
    thumbnail_size: int = Field(default=256, description="Thumbnail size in pixels")

    # UI Settings
    theme: str = Field(default="dark", description="UI theme")
    language: str = Field(default="en", description="Interface language")

    # Server
    host: str = Field(default="localhost", description="Server host")
    port: int = Field(default=8000, description="Server port")

    # Feature Flags
    enable_ui: bool = Field(default=True, description="Enable UI and desktop app")
    enable_agents: bool = Field(
        default=False, description="Enable MCP agents and complex processing"
    )
    enable_websockets: bool = Field(
        default=True, description="Enable WebSocket support"
    )
    api_only_mode: bool = Field(
        default=False, description="API-only mode for debugging"
    )

    class Config:
        env_prefix = "LIFEARCH_"
        env_file = ".env"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Set derived paths if not provided
        if self.vault_path is None:
            self.vault_path = self.lifearch_home / "vault"

        if self.database_url is None:
            self.database_url = f"sqlite:///{self.lifearch_home}/data/lifearch.db"

        # Ensure directories exist
        self.lifearch_home.mkdir(parents=True, exist_ok=True)
        self.vault_path.mkdir(parents=True, exist_ok=True)
        (self.lifearch_home / "data").mkdir(parents=True, exist_ok=True)


def configure_logging(level: str = "INFO") -> None:
    """
    Configure logging with development-friendly structured output.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = getattr(logging, level.upper())

    # Import development formatter
    try:
        from ..utils.logging.structured import create_development_formatter

        formatter = create_development_formatter()
    except ImportError:
        # Fallback to basic formatter if structured logging not available
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

    # Configure only our application logger (lifearchivist.*)
    app_logger = logging.getLogger("lifearchivist")
    app_logger.setLevel(log_level)

    # Remove existing handlers from our app logger
    for handler in app_logger.handlers[:]:
        app_logger.removeHandler(handler)

    # Add console handler to our app logger
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    app_logger.addHandler(console_handler)

    # Prevent propagation to root logger to avoid duplication
    app_logger.propagate = False

    # Set root logger to INFO so uvicorn logs still work
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
