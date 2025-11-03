"""
Get settings endpoint.
"""

from fastapi import APIRouter, HTTPException

from ..shared.dependencies import get_server
from .models import SettingsResponse

router = APIRouter()


@router.get("/", response_model=SettingsResponse)
async def get_settings():
    """
    Get current application settings.

    Returns all configuration including:
    - Document processing preferences
    - AI model selections
    - Conversation defaults
    - File management settings
    - UI appearance
    - System paths (read-only)
    """
    server = get_server()

    try:
        settings = server.settings

        temperature = 0.7
        max_output_tokens = 2000
        response_format = "concise"
        context_window_size = 10
        response_timeout = 30

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
        raise HTTPException(
            status_code=500, detail=f"Settings configuration error: {str(e)}"
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve settings: {str(e)}"
        ) from None
