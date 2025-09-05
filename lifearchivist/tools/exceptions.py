"""
Custom exceptions for the tools system.
"""


class LifeArchivistError(Exception):
    """Base exception for LifeArchivist errors."""

    pass


class ToolError(LifeArchivistError):
    """Base exception for tool-related errors."""

    pass


class ValidationError(ToolError):
    """Raised when input or output validation fails."""

    pass


class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not found."""

    pass


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""

    pass


class StorageError(LifeArchivistError):
    """Raised when storage operations fail."""

    pass


class IndexingError(LifeArchivistError):
    """Raised when indexing operations fail."""

    pass
