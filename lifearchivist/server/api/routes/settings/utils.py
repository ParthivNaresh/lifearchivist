from typing import Any, List, Tuple


def update_settings_in_memory(
    settings: Any,
    request: Any,
) -> List[str]:
    """
    Update settings in memory and return list of updated fields.

    Args:
        settings: Settings instance to update
        request: Settings update request

    Returns:
        List of field names that were updated
    """
    updated_fields = []

    if request.max_file_size_mb is not None:
        settings.max_file_size_mb = request.max_file_size_mb
        updated_fields.append("max_file_size_mb")

    if request.llm_model is not None:
        settings.llm_model = request.llm_model
        updated_fields.append("llm_model")

    if request.embedding_model is not None:
        settings.embedding_model = request.embedding_model
        updated_fields.append("embedding_model")

    if request.theme is not None:
        settings.theme = request.theme
        updated_fields.append("theme")

    return updated_fields


def track_non_persisted_fields(request: Any) -> List[str]:
    """
    Track fields that are not yet persisted to settings object.

    Args:
        request: Settings update request

    Returns:
        List of field names that were provided but not persisted
    """
    tracked_fields = []

    if request.auto_extract_dates is not None:
        tracked_fields.append("auto_extract_dates")
    if request.generate_text_previews is not None:
        tracked_fields.append("generate_text_previews")
    if request.search_results_limit is not None:
        tracked_fields.append("search_results_limit")
    if request.auto_organize_by_date is not None:
        tracked_fields.append("auto_organize_by_date")
    if request.duplicate_detection is not None:
        tracked_fields.append("duplicate_detection")
    if request.default_import_location is not None:
        tracked_fields.append("default_import_location")
    if request.interface_density is not None:
        tracked_fields.append("interface_density")

    return tracked_fields


def build_user_preferences_update_query(
    request: Any,
) -> Tuple[List[str], List[Any], List[str]]:
    """
    Build dynamic SQL update query for user preferences.

    Args:
        request: Settings update request

    Returns:
        Tuple of (update_clauses, values, updated_field_names)
    """
    from typing import Union

    updates = []
    values: List[Union[float, int, str]] = []
    updated_fields = []
    param_count = 1

    if request.temperature is not None:
        updates.append(f"temperature = ${param_count}")
        values.append(request.temperature)
        updated_fields.append("temperature")
        param_count += 1

    if request.max_output_tokens is not None:
        updates.append(f"max_output_tokens = ${param_count}")
        values.append(request.max_output_tokens)
        updated_fields.append("max_output_tokens")
        param_count += 1

    if request.response_format is not None:
        updates.append(f"response_format = ${param_count}")
        values.append(request.response_format)
        updated_fields.append("response_format")
        param_count += 1

    if request.context_window_size is not None:
        updates.append(f"context_window_size = ${param_count}")
        values.append(request.context_window_size)
        updated_fields.append("context_window_size")
        param_count += 1

    if request.response_timeout is not None:
        updates.append(f"response_timeout = ${param_count}")
        values.append(request.response_timeout)
        updated_fields.append("response_timeout")
        param_count += 1

    return updates, values, updated_fields


async def update_existing_conversations(
    conn: Any,
    request: Any,
) -> None:
    """
    Update existing conversations with new default values.

    Args:
        conn: Database connection
        request: Settings update request
    """
    if request.temperature is not None:
        await conn.execute(
            """
            UPDATE conversations 
            SET temperature = $1, updated_at = NOW()
            WHERE temperature = 0.7 AND archived_at IS NULL
            """,
            request.temperature,
        )

    if request.max_output_tokens is not None:
        await conn.execute(
            """
            UPDATE conversations 
            SET max_tokens = $1, updated_at = NOW()
            WHERE max_tokens = 2000 AND archived_at IS NULL
            """,
            request.max_output_tokens,
        )


async def update_conversation_defaults_in_db(
    db_pool: Any,
    request: Any,
) -> List[str]:
    """
    Update conversation default settings in database.

    Args:
        db_pool: Database connection pool
        request: Settings update request

    Returns:
        List of field names that were updated
    """
    async with db_pool.acquire() as conn:
        updates, values, updated_fields = build_user_preferences_update_query(request)

        if updates:
            updates.append("updated_at = NOW()")
            query = f"""
                UPDATE user_preferences 
                SET {', '.join(updates)}
                WHERE user_id = 'default'
            """
            await conn.execute(query, *values)

            await update_existing_conversations(conn, request)

        return updated_fields


def has_conversation_defaults_update(request: Any) -> bool:
    """
    Check if request contains conversation default updates.

    Args:
        request: Settings update request

    Returns:
        True if any conversation defaults are being updated
    """
    return any(
        [
            request.temperature is not None,
            request.max_output_tokens is not None,
            request.response_format is not None,
            request.context_window_size is not None,
            request.response_timeout is not None,
        ]
    )
