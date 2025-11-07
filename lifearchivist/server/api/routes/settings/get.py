"""
Get settings endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError
from .response_models import SettingsResponse

router = APIRouter()

DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_OUTPUT_TOKENS = 2000
DEFAULT_RESPONSE_FORMAT = "concise"
DEFAULT_CONTEXT_WINDOW_SIZE = 10
DEFAULT_RESPONSE_TIMEOUT = 30


@router.get(
    "/",
    response_model=SettingsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Get settings failed: <error message>"}
                }
            },
        },
    },
)
async def get_settings() -> SettingsResponse:
    """
    Get current application settings and user preferences.

    Returns all configuration including document processing, AI model settings,
    conversation defaults, and system paths.

    ## Response Fields

    - **auto_extract_dates**: Auto-extract dates from documents
    - **generate_text_previews**: Generate text previews
    - **max_file_size_mb**: Maximum file size in MB
    - **llm_model**: LLM model name
    - **embedding_model**: Embedding model name
    - **search_results_limit**: Default search result limit
    - **temperature**: LLM temperature (0.0-2.0)
    - **max_output_tokens**: Maximum output tokens
    - **response_format**: Response format preference
    - **context_window_size**: Conversation context window
    - **response_timeout**: Response timeout in seconds
    - **auto_organize_by_date**: Auto-organize by date
    - **duplicate_detection**: Enable duplicate detection
    - **default_import_location**: Default import path
    - **theme**: UI theme
    - **interface_density**: UI density
    - **vault_path**: Vault storage path (read-only)
    - **lifearch_home**: Application home path (read-only)

    ## Example Response

    ```json
    {
        "auto_extract_dates": true,
        "generate_text_previews": true,
        "max_file_size_mb": 100,
        "llm_model": "gpt-4",
        "embedding_model": "text-embedding-3-small",
        "search_results_limit": 25,
        "temperature": 0.7,
        "max_output_tokens": 2000,
        "response_format": "concise",
        "context_window_size": 10,
        "response_timeout": 30,
        "auto_organize_by_date": false,
        "duplicate_detection": true,
        "default_import_location": "~/Documents",
        "theme": "dark",
        "interface_density": "comfortable",
        "vault_path": "/Users/username/.lifearchivist/vault",
        "lifearch_home": "/Users/username/.lifearchivist"
    }
    ```

    ## Settings Categories

    ### Document Processing
    - auto_extract_dates
    - generate_text_previews
    - max_file_size_mb
    - duplicate_detection

    ### AI Configuration
    - llm_model
    - embedding_model
    - temperature
    - max_output_tokens
    - response_format

    ### Conversation
    - context_window_size
    - response_timeout

    ### Search
    - search_results_limit

    ### File Management
    - auto_organize_by_date
    - default_import_location

    ### UI Preferences
    - theme
    - interface_density

    ### System Paths (Read-Only)
    - vault_path
    - lifearch_home

    ## User Preferences

    Settings are user-specific and stored in database:
    - temperature
    - max_output_tokens
    - response_format
    - context_window_size
    - response_timeout

    ## Use Cases

    - Load settings in UI
    - Display current configuration
    - Verify settings
    - Export configuration
    - Settings management

    ## Performance Notes

    - Fast database query
    - Cached where possible
    - Minimal overhead
    - Safe to call frequently

    ## Notes

    - Returns current snapshot
    - User preferences from database
    - System settings from config
    - Paths are absolute
    - Some fields read-only
    """
    server = get_server()

    try:
        settings = server.settings

        temperature = DEFAULT_TEMPERATURE
        max_output_tokens = DEFAULT_MAX_OUTPUT_TOKENS
        response_format = DEFAULT_RESPONSE_FORMAT
        context_window_size = DEFAULT_CONTEXT_WINDOW_SIZE
        response_timeout = DEFAULT_RESPONSE_TIMEOUT

        if server.service_container and server.service_container.conversation_service:
            db_pool = server.service_container.conversation_service.db_pool

            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO user_preferences (user_id)
                    VALUES ('default')
                    ON CONFLICT (user_id) DO UPDATE SET user_id = EXCLUDED.user_id
                    RETURNING temperature, max_output_tokens, response_format, 
                              context_window_size, response_timeout
                    """
                )

                if row:
                    temperature = row["temperature"]
                    max_output_tokens = row["max_output_tokens"]
                    response_format = row["response_format"]
                    context_window_size = row["context_window_size"]
                    response_timeout = row["response_timeout"]

        return SettingsResponse(
            auto_extract_dates=True,
            generate_text_previews=True,
            max_file_size_mb=settings.max_file_size_mb,
            llm_model=settings.llm_model,
            embedding_model=settings.embedding_model,
            search_results_limit=25,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_format=response_format,
            context_window_size=context_window_size,
            response_timeout=response_timeout,
            auto_organize_by_date=False,
            duplicate_detection=True,
            default_import_location="~/Documents",
            theme=settings.theme,
            interface_density="comfortable",
            vault_path=str(settings.vault_path),
            lifearch_home=str(settings.lifearch_home),
        )

    except AttributeError as e:
        raise InternalServerError(
            "Get settings", RuntimeError(f"Settings configuration error: {str(e)}")
        ) from e
    except Exception as e:
        raise InternalServerError("Get settings", e) from e
