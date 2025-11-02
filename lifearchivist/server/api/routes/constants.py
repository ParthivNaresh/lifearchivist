"""
Constants for API routes.

Centralizes HTTP status codes, error messages, and configuration values
used across API endpoints.
"""

from typing import Final


class HTTPStatus:
    """HTTP status codes used in API responses."""

    OK: Final[int] = 200
    CREATED: Final[int] = 201
    BAD_REQUEST: Final[int] = 400
    FORBIDDEN: Final[int] = 403
    NOT_FOUND: Final[int] = 404
    PAYMENT_REQUIRED: Final[int] = 402
    INTERNAL_SERVER_ERROR: Final[int] = 500
    SERVICE_UNAVAILABLE: Final[int] = 503


class ErrorMessages:
    """Common error messages used across API endpoints."""

    SERVICE_NOT_INITIALIZED: Final[str] = "{service} service not initialized"
    SERVICE_NOT_AVAILABLE: Final[str] = "{service} service not available"
    INVALID_PATH: Final[str] = "Invalid {path_type} path: {error}"
    RESOURCE_NOT_FOUND: Final[str] = "{resource} not found: {identifier}"
    OPERATION_FAILED: Final[str] = "Failed to {operation}: {error}"
    RESOURCE_ADDED_NOT_RETRIEVED: Final[str] = (
        "{resource} was added but could not be retrieved"
    )
    RESOURCE_MUST_BE_ENABLED: Final[str] = "{resource} must be enabled to {action}"
    PATH_NOT_ACCESSIBLE: Final[str] = "{path_type} path no longer accessible: {path}"
    VAULT_NOT_INITIALIZED: Final[str] = "Vault not initialized"


class SuccessMessages:
    """Common success messages used across API endpoints."""

    RESOURCE_REMOVED: Final[str] = "{resource} removed successfully"
    OPERATION_COMPLETED: Final[str] = "{operation} completed successfully"
    SCAN_COMPLETED: Final[str] = (
        "Scanned {resource} and queued {count} files for ingestion"
    )


class PaginationDefaults:
    """Default pagination values used across API endpoints."""

    DEFAULT_LIMIT: Final[int] = 50
    DEFAULT_OFFSET: Final[int] = 0
    MAX_LIMIT: Final[int] = 500
    MIN_LIMIT: Final[int] = 1


class DocumentConstants:
    """Constants specific to document operations."""

    CHUNKS_DEFAULT_LIMIT: Final[int] = 100
    CHUNKS_MAX_LIMIT: Final[int] = 1000
    CHUNKS_MIN_LIMIT: Final[int] = 1
    NEIGHBORS_DEFAULT_TOP_K: Final[int] = 10
    NEIGHBORS_MAX_TOP_K: Final[int] = 100
    NEIGHBORS_MIN_TOP_K: Final[int] = 1
    COUNT_QUERY_LIMIT: Final[int] = 10000
    SINGLE_DOCUMENT_LIMIT: Final[int] = 1
    DEDUPLICATION_CHECK_LIMIT: Final[int] = 2


class SearchConstants:
    """Constants specific to search operations."""

    DEFAULT_LIMIT: Final[int] = 20
    MAX_LIMIT: Final[int] = 100
    MIN_LIMIT: Final[int] = 1
    DEFAULT_OFFSET: Final[int] = 0
    DEFAULT_SIMILARITY_THRESHOLD: Final[float] = 0.3
    DEFAULT_SEMANTIC_WEIGHT: Final[float] = 0.6
    VALID_MODES: Final[tuple[str, ...]] = ("keyword", "semantic", "hybrid")
    DEFAULT_MODE: Final[str] = "semantic"


class QAConstants:
    """Constants specific to Q&A operations."""

    DEFAULT_CONTEXT_LIMIT: Final[int] = 5
    MIN_CONTEXT_LIMIT: Final[int] = 1
    MAX_CONTEXT_LIMIT: Final[int] = 20
    MIN_QUESTION_LENGTH: Final[int] = 3
    DEFAULT_RESPONSE_MODE: Final[str] = "tree_summarize"
    SNIPPET_MAX_LENGTH: Final[int] = 200


class VaultConstants:
    """Constants specific to vault operations."""

    DEFAULT_DIRECTORY: Final[str] = "content"
    DEFAULT_LIMIT: Final[int] = 100
    MAX_LIMIT: Final[int] = 1000
    MIN_LIMIT: Final[int] = 1
    DEFAULT_OFFSET: Final[int] = 0
    HASH_LENGTH: Final[int] = 64
    MIN_HASH_LENGTH: Final[int] = 4
    HASH_DIR1_LENGTH: Final[int] = 2
    HASH_DIR2_START: Final[int] = 2
    HASH_DIR2_LENGTH: Final[int] = 2
    HASH_STEM_START: Final[int] = 4


class ValidationMessages:
    """Validation error messages."""

    LIMIT_RANGE: Final[str] = "Limit must be between {min} and {max}"
    OFFSET_NON_NEGATIVE: Final[str] = "Offset must be non-negative"
    TOP_K_RANGE: Final[str] = "top_k must be between {min} and {max}"
    INVALID_HASH_FORMAT: Final[str] = (
        "Invalid file hash format. Expected SHA256 hash ({length} characters)."
    )
    INVALID_HASH_LENGTH: Final[str] = (
        "Invalid hash length: {actual}. Expected {expected} characters."
    )
    QUESTION_REQUIRED: Final[str] = "Question is required"
    QUESTION_MIN_LENGTH: Final[str] = "Question must be at least {min} characters long"
    CONTEXT_LIMIT_RANGE: Final[str] = "context_limit must be between {min} and {max}"
    CONTEXT_LIMIT_NUMERIC: Final[str] = "context_limit must be a number"
    INVALID_MODE: Final[str] = "Invalid mode '{mode}'. Must be one of: {valid_modes}"


class FolderWatchConstants:
    """Constants specific to folder watching functionality."""

    SUPPORTED_EXTENSIONS: Final[tuple[str, ...]] = (
        ".pdf",
        ".txt",
        ".md",
        ".doc",
        ".docx",
    )
    HIDDEN_FILE_PREFIXES: Final[tuple[str, ...]] = (".", "~")
    DEFAULT_ENABLED: Final[bool] = True
    DEFAULT_ENABLED_ONLY_FILTER: Final[bool] = False


class ServiceNames:
    """Service names used in error messages and logging."""

    FOLDER_WATCHER: Final[str] = "Folder watcher"
    LLAMAINDEX: Final[str] = "LlamaIndex"
    CONVERSATION: Final[str] = "Conversation"
    MESSAGE: Final[str] = "Message"
    CREDENTIAL: Final[str] = "Credential"
    VAULT: Final[str] = "Vault"
    PROGRESS: Final[str] = "Progress"
    SEARCH: Final[str] = "Search"
    QUERY: Final[str] = "Query"


class ResourceNames:
    """Resource names used in error messages."""

    FOLDER: Final[str] = "Folder"
    DOCUMENT: Final[str] = "Document"
    CONVERSATION: Final[str] = "Conversation"
    MESSAGE: Final[str] = "Message"
    PROVIDER: Final[str] = "Provider"
    FILE: Final[str] = "File"
    SETTINGS: Final[str] = "Settings"


class PathParamDescriptions:
    """Descriptions for path parameters used in API endpoints."""

    FOLDER_UUID: Final[str] = "Folder UUID"
    DOCUMENT_ID: Final[str] = "Document ID"
    FILE_HASH: Final[str] = "File hash (SHA256)"
    SESSION_ID: Final[str] = "Session ID for progress tracking"
