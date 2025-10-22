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
from ...utils.logging import log_event, track
from ...utils.result import (
    Result,
    Success,
    internal_error,
    not_found_error,
    validation_error,
)
from .utils import (
    build_insert_query,
    build_update_query,
    parse_uuid,
    record_to_dict,
    records_to_list,
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

    @track(
        operation="conversation_create",
        include_args=["user_id", "model"],
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
    )
    async def create_conversation(
        self,
        user_id: str = "default",
        title: Optional[str] = None,
        model: Optional[str] = None,
        context_documents: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Result[Dict[str, Any], str]:
        """
        Create a new conversation.

        Args:
            user_id: User identifier (default: "default")
            title: Conversation title (auto-generated if None)
            model: LLM model to use (defaults to current settings)
            context_documents: List of document IDs for context
            system_prompt: Custom system prompt
            temperature: LLM temperature (0-2)
            max_tokens: Maximum tokens per response
            metadata: Additional metadata

        Returns:
            Success with conversation dict, or Failure with error
        """
        try:
            # Use current settings if model not specified
            if model is None:
                settings = get_settings()
                model = settings.llm_model

            # Validate inputs
            if temperature < 0 or temperature > 2:
                return validation_error(
                    "Temperature must be between 0 and 2",
                    context={"temperature": temperature},
                )

            if max_tokens < 1 or max_tokens > 100000:
                return validation_error(
                    "Max tokens must be between 1 and 100000",
                    context={"max_tokens": max_tokens},
                )

            # Prepare data
            data = {
                "user_id": user_id,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if title:
                data["title"] = title

            if context_documents:
                data["context_documents"] = context_documents

            if system_prompt:
                data["system_prompt"] = system_prompt

            if metadata:
                data["metadata"] = metadata

            # Insert conversation
            query, values = build_insert_query("conversations", data)

            async with self.db_pool.acquire() as conn:
                record = await conn.fetchrow(query, *values)

            if not record:
                return internal_error(
                    "Failed to create conversation",
                    context={"user_id": user_id},
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
            return internal_error(
                f"Duplicate conversation: {str(e)}",
                context={"user_id": user_id},
            )
        except Exception as e:
            log_event(
                "conversation_create_error",
                {"error": str(e), "error_type": type(e).__name__},
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to create conversation: {str(e)}",
                context={"user_id": user_id, "error_type": type(e).__name__},
            )

    @track(
        operation="conversation_get",
        include_args=["conversation_id"],
        track_performance=True,
        frequency="high_frequency",
    )
    async def get_conversation(
        self, conversation_id: str
    ) -> Result[Dict[str, Any], str]:
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
                return not_found_error(
                    f"Conversation '{conversation_id}' not found",
                    context={"conversation_id": conversation_id},
                )

            return Success(record_to_dict(record))

        except ValueError as e:
            return validation_error(
                str(e), context={"conversation_id": conversation_id}
            )
        except Exception as e:
            log_event(
                "conversation_get_error",
                {"conversation_id": conversation_id, "error": str(e)},
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to get conversation: {str(e)}",
                context={"conversation_id": conversation_id},
            )

    @track(
        operation="conversation_list",
        include_args=["user_id", "limit", "offset"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def list_conversations(
        self,
        user_id: str = "default",
        limit: int = 50,
        offset: int = 0,
        include_archived: bool = False,
    ) -> Result[Dict[str, Any], str]:
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
                return validation_error(
                    "Limit must be between 1 and 100",
                    context={"limit": limit},
                )

            if offset < 0:
                return validation_error(
                    "Offset must be non-negative",
                    context={"offset": offset},
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
            return internal_error(
                f"Failed to list conversations: {str(e)}",
                context={"user_id": user_id},
            )

    @track(
        operation="conversation_update",
        include_args=["conversation_id"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def update_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        context_documents: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Result[Dict[str, Any], str]:
        """
        Update conversation fields.

        Args:
            conversation_id: Conversation UUID
            title: New title
            context_documents: New context documents
            system_prompt: New system prompt
            temperature: New temperature
            max_tokens: New max tokens
            metadata: New metadata (merged with existing)

        Returns:
            Success with updated conversation dict, or Failure with error
        """
        try:
            # Parse UUID
            conv_uuid = parse_uuid(conversation_id)

            # Build updates - dict can contain various types
            updates: Dict[str, Any] = {}

            if title is not None:
                updates["title"] = title

            if context_documents is not None:
                updates["context_documents"] = context_documents

            if system_prompt is not None:
                updates["system_prompt"] = system_prompt

            if temperature is not None:
                if temperature < 0 or temperature > 2:
                    return validation_error(
                        "Temperature must be between 0 and 2",
                        context={"temperature": temperature},
                    )
                updates["temperature"] = temperature

            if max_tokens is not None:
                if max_tokens < 1 or max_tokens > 100000:
                    return validation_error(
                        "Max tokens must be between 1 and 100000",
                        context={"max_tokens": max_tokens},
                    )
                updates["max_tokens"] = max_tokens

            if metadata is not None:
                updates["metadata"] = metadata

            if not updates:
                return validation_error(
                    "No updates provided",
                    context={"conversation_id": conversation_id},
                )

            # Build and execute query
            query, values = build_update_query(
                "conversations", updates, f"id = ${len(updates) + 1}"
            )
            values.append(conv_uuid)

            async with self.db_pool.acquire() as conn:
                record = await conn.fetchrow(query, *values)

            if not record:
                return not_found_error(
                    f"Conversation '{conversation_id}' not found",
                    context={"conversation_id": conversation_id},
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
            return validation_error(
                str(e), context={"conversation_id": conversation_id}
            )
        except Exception as e:
            log_event(
                "conversation_update_error",
                {"conversation_id": conversation_id, "error": str(e)},
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to update conversation: {str(e)}",
                context={"conversation_id": conversation_id},
            )

    @track(
        operation="conversation_archive",
        include_args=["conversation_id"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def archive_conversation(
        self, conversation_id: str
    ) -> Result[Dict[str, Any], str]:
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
                return not_found_error(
                    f"Conversation '{conversation_id}' not found or already archived",
                    context={"conversation_id": conversation_id},
                )

            log_event(
                "conversation_archived",
                {"conversation_id": conversation_id},
            )

            return Success(record_to_dict(record))

        except ValueError as e:
            return validation_error(
                str(e), context={"conversation_id": conversation_id}
            )
        except Exception as e:
            log_event(
                "conversation_archive_error",
                {"conversation_id": conversation_id, "error": str(e)},
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to archive conversation: {str(e)}",
                context={"conversation_id": conversation_id},
            )

    async def delete_conversation(
        self, conversation_id: str
    ) -> Result[Dict[str, Any], str]:
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
                return not_found_error(
                    f"Conversation '{conversation_id}' not found",
                    context={"conversation_id": conversation_id},
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
            return validation_error(
                str(e), context={"conversation_id": conversation_id}
            )
        except Exception as e:
            log_event(
                "conversation_delete_error",
                {"conversation_id": conversation_id, "error": str(e)},
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to delete conversation: {str(e)}",
                context={"conversation_id": conversation_id},
            )
