"""
Conversation service for managing Q&A conversations.

Provides CRUD operations for conversations with:
- Create/read/update/archive conversations
- List conversations with pagination
- Search conversations
- Context document management
- Result type error handling
"""

import logging
from typing import Any, Dict, List, Optional

import asyncpg

from ...config import get_settings
from ...utils.logx import log_event, track
from ...utils.result import (
    FailurePayload,
    Result,
    Success,
    fail,
)
from .utils import (
    build_conversation_updates,
    build_insert_query,
    build_update_query,
    parse_uuid,
    record_to_dict,
    records_to_list,
    validate_max_tokens,
    validate_temperature,
)


class ConversationService:
    """
    Service for managing conversations.

    Handles all conversation-level operations including:
    - CRUD operations
    - Pagination and filtering
    - Context management
    - Search

    All methods return Result types for consistent error handling.
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize conversation service.

        Args:
            db_pool: PostgreSQL connection pool
        """
        self.db_pool = db_pool

    async def _get_user_preferences(self, user_id: str) -> tuple[float, int]:
        """
        Get or create user preferences for temperature and max_tokens.

        Args:
            user_id: User identifier

        Returns:
            Tuple of (temperature, max_output_tokens)
        """
        async with self.db_pool.acquire() as conn:
            prefs = await conn.fetchrow(
                """
                INSERT INTO user_preferences (user_id)
                VALUES ($1)
                ON CONFLICT (user_id) DO UPDATE SET user_id = EXCLUDED.user_id
                RETURNING temperature, max_output_tokens
                """,
                user_id,
            )
            return prefs["temperature"], prefs["max_output_tokens"]

    def _validate_conversation_params(
        self, temperature: float, max_tokens: int
    ) -> Optional[Result[Dict[str, Any], FailurePayload]]:
        """
        Validate temperature and max_tokens parameters.

        Args:
            temperature: Temperature value
            max_tokens: Max tokens value

        Returns:
            Validation error Result if invalid, None if valid
        """
        temp_error = validate_temperature(temperature)
        if temp_error:
            return fail(
                FailurePayload(
                    message=temp_error,
                    error_type="ValidationError",
                    status_code=400,
                    recoverable=True,
                    details={"temperature": temperature},
                )
            )

        tokens_error = validate_max_tokens(max_tokens)
        if tokens_error:
            return fail(
                FailurePayload(
                    message=tokens_error,
                    error_type="ValidationError",
                    status_code=400,
                    recoverable=True,
                    details={"max_tokens": max_tokens},
                )
            )

        return None

    def _build_conversation_data(
        self,
        user_id: str,
        model: str,
        temperature: float,
        max_tokens: int,
        title: Optional[str],
        provider_id: Optional[str],
        context_documents: Optional[List[str]],
        system_prompt: Optional[str],
        metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Build conversation data dictionary for insertion.

        Args:
            user_id: User identifier
            model: LLM model
            temperature: Temperature value
            max_tokens: Max tokens value
            title: Optional title
            provider_id: Optional provider ID
            context_documents: Optional context documents
            system_prompt: Optional system prompt
            metadata: Optional metadata

        Returns:
            Dictionary of conversation data
        """
        data: Dict[str, Any] = {
            "user_id": user_id,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if title:
            data["title"] = title
        if provider_id:
            data["provider_id"] = provider_id
        if context_documents:
            data["context_documents"] = context_documents
        if system_prompt:
            data["system_prompt"] = system_prompt
        if metadata:
            data["metadata"] = metadata

        return data

    @track(operation="conversation_create")
    async def create_conversation(
        self,
        user_id: str = "default",
        title: Optional[str] = None,
        model: Optional[str] = None,
        provider_id: Optional[str] = None,
        context_documents: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Result[Dict[str, Any], FailurePayload]:
        """
        Create a new conversation.

        Args:
            user_id: User identifier (default: "default")
            title: Conversation title (auto-generated if None)
            model: LLM model to use (defaults to current settings)
            provider_id: LLM provider ID (e.g., "my-openai"). NULL = use default
            context_documents: List of document IDs for context
            system_prompt: Custom system prompt
            temperature: LLM temperature (0-2, uses user preferences if None)
            max_tokens: Maximum tokens per response (uses user preferences if None)
            metadata: Additional metadata

        Returns:
            Success with conversation dict, or Failure with error
        """
        try:
            if temperature is None or max_tokens is None:
                pref_temp, pref_tokens = await self._get_user_preferences(user_id)
                temperature = temperature if temperature is not None else pref_temp
                max_tokens = max_tokens if max_tokens is not None else pref_tokens

            if model is None:
                model = get_settings().llm_model

            validation_error_result = self._validate_conversation_params(
                temperature, max_tokens
            )
            if validation_error_result:
                return validation_error_result

            data = self._build_conversation_data(
                user_id,
                model,
                temperature,
                max_tokens,
                title,
                provider_id,
                context_documents,
                system_prompt,
                metadata,
            )

            query, values = build_insert_query("conversations", data)

            async with self.db_pool.acquire() as conn:
                record = await conn.fetchrow(query, *values)

            if not record:
                return fail(
                    FailurePayload(
                        message="Failed to create conversation",
                        error_type="InternalError",
                        status_code=500,
                        recoverable=False,
                        details={"user_id": user_id},
                    )
                )

            conversation = record_to_dict(record)

            log_event(
                "conversation_created",
                {
                    "conversation_id": str(conversation["id"]),
                    "user_id": user_id,
                    "model": model,
                },
            )

            return Success(conversation)

        except asyncpg.UniqueViolationError as e:
            return fail(
                FailurePayload(
                    message=f"Duplicate conversation: {str(e)}",
                    error_type="InternalError",
                    status_code=500,
                    recoverable=False,
                    details={"user_id": user_id},
                )
            )
        except Exception as e:
            log_event(
                "conversation_create_error",
                {"error": str(e), "error_type": type(e).__name__},
                level=logging.ERROR,
            )
            return fail(
                FailurePayload(
                    message=f"Failed to create conversation: {str(e)}",
                    error_type="InternalError",
                    status_code=500,
                    recoverable=False,
                    details={"user_id": user_id, "error_type": type(e).__name__},
                )
            )

    # @track(operation="conversation_get")
    async def get_conversation(
        self, conversation_id: str
    ) -> Result[Dict[str, Any], FailurePayload]:
        """
        Get conversation by ID.

        Args:
            conversation_id: Conversation UUID

        Returns:
            Success with conversation dict, or Failure with error
        """
        try:
            # Parse UUID
            conv_uuid = parse_uuid(conversation_id)

            query = """
                SELECT * FROM conversations
                WHERE id = $1 AND archived_at IS NULL
            """

            async with self.db_pool.acquire() as conn:
                record = await conn.fetchrow(query, conv_uuid)

            if not record:
                return fail(
                    FailurePayload(
                        message=f"Conversation '{conversation_id}' not found",
                        error_type="NotFoundError",
                        status_code=404,
                        recoverable=False,
                        details={"conversation_id": conversation_id},
                    )
                )

            return Success(record_to_dict(record))

        except ValueError as e:
            return fail(
                FailurePayload(
                    message=str(e),
                    error_type="ValidationError",
                    status_code=400,
                    recoverable=True,
                    details={"conversation_id": conversation_id},
                )
            )
        except Exception as e:
            log_event(
                "conversation_get_error",
                {"conversation_id": conversation_id, "error": str(e)},
                level=logging.ERROR,
            )
            return fail(
                FailurePayload(
                    message=f"Failed to get conversation: {str(e)}",
                    error_type="InternalError",
                    status_code=500,
                    recoverable=False,
                    details={"conversation_id": conversation_id},
                )
            )

    @track(operation="conversation_list")
    async def list_conversations(
        self,
        user_id: str = "default",
        limit: int = 50,
        offset: int = 0,
        include_archived: bool = False,
    ) -> Result[Dict[str, Any], FailurePayload]:
        """
        List conversations for a user.

        Args:
            user_id: User identifier
            limit: Maximum conversations to return
            offset: Pagination offset
            include_archived: Include archived conversations

        Returns:
            Success with dict containing conversations and pagination info
        """
        try:
            # Validate pagination
            if limit < 1 or limit > 100:
                return fail(
                    FailurePayload(
                        message="Limit must be between 1 and 100",
                        error_type="ValidationError",
                        status_code=400,
                        recoverable=True,
                        details={"limit": limit},
                    )
                )

            if offset < 0:
                return fail(
                    FailurePayload(
                        message="Offset must be non-negative",
                        error_type="ValidationError",
                        status_code=400,
                        recoverable=True,
                        details={"offset": offset},
                    )
                )

            # Build query
            where_clause = "user_id = $1"
            params = [user_id]

            if not include_archived:
                where_clause += " AND archived_at IS NULL"

            query = f"""
                SELECT * FROM conversations
                WHERE {where_clause}
                ORDER BY last_message_at DESC NULLS LAST, created_at DESC
                LIMIT $2 OFFSET $3
            """

            count_query = f"""
                SELECT COUNT(*) FROM conversations
                WHERE {where_clause}
            """

            async with self.db_pool.acquire() as conn:
                # Get conversations
                records = await conn.fetch(query, *params, limit, offset)
                conversations = records_to_list(records)

                # Get total count
                total = await conn.fetchval(count_query, *params)

            return Success(
                {
                    "conversations": conversations,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(conversations) < total,
                }
            )

        except Exception as e:
            log_event(
                "conversation_list_error",
                {"user_id": user_id, "error": str(e)},
                level=logging.ERROR,
            )
            return fail(
                FailurePayload(
                    message=f"Failed to list conversations: {str(e)}",
                    error_type="InternalError",
                    status_code=500,
                    recoverable=False,
                    details={"user_id": user_id},
                )
            )

    @track(operation="conversation_update")
    async def update_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        model: Optional[str] = None,
        provider_id: Optional[str] = None,
        context_documents: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Result[Dict[str, Any], FailurePayload]:
        """
        Update conversation fields.

        Args:
            conversation_id: Conversation UUID
            title: New title
            model: New model
            provider_id: New provider ID
            context_documents: New context documents
            system_prompt: New system prompt
            temperature: New temperature
            max_tokens: New max tokens
            metadata: New metadata (merged with existing)

        Returns:
            Success with updated conversation dict, or Failure with error
        """
        try:
            conv_uuid = parse_uuid(conversation_id)

            if temperature is not None:
                error_msg = validate_temperature(temperature)
                if error_msg:
                    return fail(
                        FailurePayload(
                            message=error_msg,
                            error_type="ValidationError",
                            status_code=400,
                            recoverable=True,
                            details={"temperature": temperature},
                        )
                    )

            if max_tokens is not None:
                error_msg = validate_max_tokens(max_tokens)
                if error_msg:
                    return fail(
                        FailurePayload(
                            message=error_msg,
                            error_type="ValidationError",
                            status_code=400,
                            recoverable=True,
                            details={"max_tokens": max_tokens},
                        )
                    )

            updates = build_conversation_updates(
                title,
                model,
                provider_id,
                context_documents,
                system_prompt,
                temperature,
                max_tokens,
                metadata,
            )

            if not updates:
                return fail(
                    FailurePayload(
                        message="No updates provided",
                        error_type="ValidationError",
                        status_code=400,
                        recoverable=True,
                        details={"conversation_id": conversation_id},
                    )
                )

            query, values = build_update_query(
                "conversations", updates, f"id = ${len(updates) + 1}"
            )
            values.append(conv_uuid)

            async with self.db_pool.acquire() as conn:
                record = await conn.fetchrow(query, *values)

            if not record:
                return fail(
                    FailurePayload(
                        message=f"Conversation '{conversation_id}' not found",
                        error_type="NotFoundError",
                        status_code=404,
                        recoverable=False,
                        details={"conversation_id": conversation_id},
                    )
                )

            log_event(
                "conversation_updated",
                {
                    "conversation_id": conversation_id,
                    "updated_fields": list(updates.keys()),
                },
            )

            return Success(record_to_dict(record))

        except ValueError as e:
            return fail(
                FailurePayload(
                    message=str(e),
                    error_type="ValidationError",
                    status_code=400,
                    recoverable=True,
                    details={"conversation_id": conversation_id},
                )
            )
        except Exception as e:
            log_event(
                "conversation_update_error",
                {"conversation_id": conversation_id, "error": str(e)},
                level=logging.ERROR,
            )
            return fail(
                FailurePayload(
                    message=f"Failed to update conversation: {str(e)}",
                    error_type="InternalError",
                    status_code=500,
                    recoverable=False,
                    details={"conversation_id": conversation_id},
                )
            )

    @track(operation="conversation_archive")
    async def archive_conversation(
        self, conversation_id: str
    ) -> Result[Dict[str, Any], FailurePayload]:
        """
        Archive (soft delete) a conversation.

        Args:
            conversation_id: Conversation UUID

        Returns:
            Success with archived conversation dict, or Failure with error
        """
        try:
            # Parse UUID
            conv_uuid = parse_uuid(conversation_id)

            query = """
                UPDATE conversations
                SET archived_at = NOW()
                WHERE id = $1 AND archived_at IS NULL
                RETURNING *
            """

            async with self.db_pool.acquire() as conn:
                record = await conn.fetchrow(query, conv_uuid)

            if not record:
                return fail(
                    FailurePayload(
                        message=f"Conversation '{conversation_id}' not found or already archived",
                        error_type="NotFoundError",
                        status_code=404,
                        recoverable=False,
                        details={"conversation_id": conversation_id},
                    )
                )

            log_event(
                "conversation_archived",
                {"conversation_id": conversation_id},
            )

            return Success(record_to_dict(record))

        except ValueError as e:
            return fail(
                FailurePayload(
                    message=str(e),
                    error_type="ValidationError",
                    status_code=400,
                    recoverable=True,
                    details={"conversation_id": conversation_id},
                )
            )
        except Exception as e:
            log_event(
                "conversation_archive_error",
                {"conversation_id": conversation_id, "error": str(e)},
                level=logging.ERROR,
            )
            return fail(
                FailurePayload(
                    message=f"Failed to archive conversation: {str(e)}",
                    error_type="InternalError",
                    status_code=500,
                    recoverable=False,
                    details={"conversation_id": conversation_id},
                )
            )

    @track(operation="conversation_delete")
    async def delete_conversation(
        self, conversation_id: str
    ) -> Result[Dict[str, Any], FailurePayload]:
        """
        Permanently delete a conversation and all its messages.

        Args:
            conversation_id: Conversation UUID

        Returns:
            Success with deletion info, or Failure with error

        Note: This is a hard delete. Use archive_conversation for soft delete.
        """
        try:
            # Parse UUID
            conv_uuid = parse_uuid(conversation_id)

            query = """
                DELETE FROM conversations
                WHERE id = $1
                RETURNING id
            """

            async with self.db_pool.acquire() as conn:
                record = await conn.fetchrow(query, conv_uuid)

            if not record:
                return fail(
                    FailurePayload(
                        message=f"Conversation '{conversation_id}' not found",
                        error_type="NotFoundError",
                        status_code=404,
                        recoverable=False,
                        details={"conversation_id": conversation_id},
                    )
                )

            log_event(
                "conversation_deleted",
                {"conversation_id": conversation_id},
                level=logging.WARNING,
            )

            return Success(
                {
                    "conversation_id": conversation_id,
                    "deleted": True,
                }
            )

        except ValueError as e:
            return fail(
                FailurePayload(
                    message=str(e),
                    error_type="ValidationError",
                    status_code=400,
                    recoverable=True,
                    details={"conversation_id": conversation_id},
                )
            )
        except Exception as e:
            log_event(
                "conversation_delete_error",
                {"conversation_id": conversation_id, "error": str(e)},
                level=logging.ERROR,
            )
            return fail(
                FailurePayload(
                    message=f"Failed to delete conversation: {str(e)}",
                    error_type="InternalError",
                    status_code=500,
                    recoverable=False,
                    details={"conversation_id": conversation_id},
                )
            )
