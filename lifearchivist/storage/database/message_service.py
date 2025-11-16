"""
Message service for managing conversation messages.

Provides operations for:
- Adding messages (questions and answers)
- Retrieving message history
- Managing citations
- Message metadata
"""

import logging
from typing import Any, Dict, List, Optional

import asyncpg

from ...utils.logx import log_event, track
from ...utils.result import (
    Result,
    Success,
    internal_error,
    not_found_error,
    validation_error,
)
from .utils import (
    build_citation_data,
    build_insert_query,
    build_message_data,
    build_update_query,
    parse_uuid,
    record_to_dict,
    records_to_list,
    validate_confidence,
    validate_message_content,
    validate_message_role,
    validate_message_status,
    validate_single_citation,
)


class MessageService:
    """
    Service for managing conversation messages.

    Handles message operations including:
    - Creating user questions and AI responses
    - Retrieving message history with pagination
    - Managing citations and sources
    - Message metadata tracking

    All methods return Result types for consistent error handling.
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize message service.

        Args:
            db_pool: PostgreSQL connection pool
        """
        self.db_pool = db_pool

    @track(
        operation="message_add",
        include_args=["conversation_id", "role"],
        include_result=True,
        track_performance=True,
        frequency="high_frequency",
    )
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model: Optional[str] = None,
        confidence: Optional[float] = None,
        method: Optional[str] = None,
        tokens_used: Optional[int] = None,
        latency_ms: Optional[int] = None,
        parent_message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "completed",
    ) -> Result[Dict[str, Any], str]:
        """
        Add a message to a conversation.

        Args:
            conversation_id: Conversation UUID
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            model: Model used (for assistant messages)
            confidence: Answer confidence 0-1 (for assistant messages)
            method: Method used ('rag', 'direct', 'hybrid')
            tokens_used: Token count for cost tracking
            latency_ms: Response time in milliseconds
            parent_message_id: Parent message for branching
            metadata: Additional metadata
            status: Message status (default: 'completed')

        Returns:
            Success with message dict, or Failure with error
        """
        try:
            error_msg = validate_message_role(role)
            if error_msg:
                return validation_error(error_msg, context={"role": role})

            if status != "processing":
                error_msg = validate_message_content(content)
                if error_msg:
                    return validation_error(
                        error_msg, context={"conversation_id": conversation_id}
                    )

            error_msg = validate_message_status(status)
            if error_msg:
                return validation_error(error_msg, context={"status": status})

            if confidence is not None:
                error_msg = validate_confidence(confidence)
                if error_msg:
                    return validation_error(
                        error_msg, context={"confidence": confidence}
                    )

            conv_uuid = parse_uuid(conversation_id)
            parent_uuid = parse_uuid(parent_message_id) if parent_message_id else None

            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    sequence_number = await conn.fetchval(
                        """
                        SELECT COALESCE(MAX(sequence_number), -1) + 1
                        FROM messages
                        WHERE conversation_id = $1
                        """,
                        conv_uuid,
                    )

                    data = build_message_data(
                        conv_uuid,
                        role,
                        content,
                        sequence_number,
                        model,
                        confidence,
                        method,
                        tokens_used,
                        latency_ms,
                        parent_uuid,
                        metadata,
                        status,
                    )

                    query, values = build_insert_query("messages", data)
                    record = await conn.fetchrow(query, *values)

                    if not record:
                        return internal_error(
                            "Failed to create message",
                            context={"conversation_id": conversation_id},
                        )

            message = record_to_dict(record)

            log_event(
                "message_added",
                {
                    "message_id": str(message["id"]),
                    "conversation_id": conversation_id,
                    "role": role,
                    "status": status,
                    "sequence": sequence_number,
                },
            )

            return Success(message)

        except ValueError as e:
            return validation_error(
                str(e), context={"conversation_id": conversation_id}
            )
        except asyncpg.ForeignKeyViolationError:
            return not_found_error(
                f"Conversation '{conversation_id}' not found",
                context={"conversation_id": conversation_id},
            )
        except Exception as e:
            log_event(
                "message_add_error",
                {"conversation_id": conversation_id, "error": str(e)},
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to add message: {str(e)}",
                context={"conversation_id": conversation_id},
            )

    @track(
        operation="message_status_update",
        include_args=["message_id", "status"],
        track_performance=True,
        frequency="high_frequency",
    )
    async def update_message_status(
        self,
        message_id: str,
        status: str,
        content: Optional[str] = None,
    ) -> Result[Dict[str, Any], str]:
        """
        Update message status and optionally content.

        Args:
            message_id: Message UUID
            status: New status ('processing', 'completed', 'failed', 'cancelled')
            content: Optional new content (for updating during completion)

        Returns:
            Success with updated message dict, or Failure with error
        """
        try:
            error_msg = validate_message_status(status)
            if error_msg:
                return validation_error(error_msg, context={"status": status})

            msg_uuid = parse_uuid(message_id)

            updates: Dict[str, Any] = {"status": status}
            if content is not None:
                updates["content"] = content.strip()

            query, values = build_update_query(
                "messages", updates, f"id = ${len(updates) + 1}"
            )
            values.append(msg_uuid)

            async with self.db_pool.acquire() as conn:
                record = await conn.fetchrow(query, *values)

            if not record:
                return not_found_error(
                    f"Message '{message_id}' not found",
                    context={"message_id": message_id},
                )

            message = record_to_dict(record)

            log_event(
                "message_status_updated",
                {
                    "message_id": message_id,
                    "status": status,
                    "content_updated": content is not None,
                },
            )

            return Success(message)

        except ValueError as e:
            return validation_error(str(e), context={"message_id": message_id})
        except Exception as e:
            log_event(
                "message_status_update_error",
                {"message_id": message_id, "error": str(e)},
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to update message status: {str(e)}",
                context={"message_id": message_id},
            )

    @track(
        operation="messages_get",
        include_args=["conversation_id", "limit"],
        track_performance=True,
        frequency="high_frequency",
    )
    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
        include_citations: bool = False,
    ) -> Result[Dict[str, Any], str]:
        """
        Get messages for a conversation.

        Args:
            conversation_id: Conversation UUID
            limit: Maximum messages to return
            offset: Pagination offset
            include_citations: Include citation data

        Returns:
            Success with dict containing messages and pagination info
        """
        try:
            # Validate pagination
            if limit < 1 or limit > 200:
                return validation_error(
                    "Limit must be between 1 and 200",
                    context={"limit": limit},
                )

            if offset < 0:
                return validation_error(
                    "Offset must be non-negative",
                    context={"offset": offset},
                )

            # Parse UUID
            conv_uuid = parse_uuid(conversation_id)

            async with self.db_pool.acquire() as conn:
                # Get messages
                messages_query = """
                    SELECT * FROM messages
                    WHERE conversation_id = $1
                    ORDER BY sequence_number ASC
                    LIMIT $2 OFFSET $3
                """
                records = await conn.fetch(messages_query, conv_uuid, limit, offset)
                messages = records_to_list(records)

                # Get total count
                total = await conn.fetchval(
                    "SELECT COUNT(*) FROM messages WHERE conversation_id = $1",
                    conv_uuid,
                )

                # Optionally include citations
                if include_citations and messages:
                    message_ids = [msg["id"] for msg in messages]
                    citations_query = """
                        SELECT * FROM message_citations
                        WHERE message_id = ANY($1)
                        ORDER BY message_id, position
                    """
                    citation_records = await conn.fetch(citations_query, message_ids)
                    citations_by_message: Dict[Any, List[Dict[str, Any]]] = {}
                    for citation in citation_records:
                        msg_id = citation["message_id"]
                        if msg_id not in citations_by_message:
                            citations_by_message[msg_id] = []
                        citations_by_message[msg_id].append(record_to_dict(citation))

                    # Attach citations to messages
                    for message in messages:
                        message["citations"] = citations_by_message.get(
                            message["id"], []
                        )

            return Success(
                {
                    "messages": messages,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(messages) < total,
                }
            )

        except ValueError as e:
            return validation_error(
                str(e), context={"conversation_id": conversation_id}
            )
        except Exception as e:
            log_event(
                "messages_get_error",
                {"conversation_id": conversation_id, "error": str(e)},
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to get messages: {str(e)}",
                context={"conversation_id": conversation_id},
            )

    @track(
        operation="citation_add",
        include_args=["message_id"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def add_citations(
        self,
        message_id: str,
        citations: List[Dict[str, Any]],
    ) -> Result[List[Dict[str, Any]], str]:
        """
        Add citations to a message.

        Args:
            message_id: Message UUID
            citations: List of citation dicts with:
                - document_id: Document ID
                - chunk_id: Optional chunk ID
                - score: Relevance score (0-1)
                - snippet: Text snippet
                - position: Order in citation list

        Returns:
            Success with list of created citations, or Failure with error
        """
        try:
            if not citations:
                return validation_error(
                    "No citations provided",
                    context={"message_id": message_id},
                )

            msg_uuid = parse_uuid(message_id)

            for i, citation in enumerate(citations):
                error_msg = validate_single_citation(citation, i)
                if error_msg:
                    return validation_error(
                        error_msg, context={"message_id": message_id}
                    )

            created_citations = []
            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    for citation in citations:
                        data = build_citation_data(msg_uuid, citation)
                        query, values = build_insert_query("message_citations", data)
                        record = await conn.fetchrow(query, *values)
                        created_citations.append(record_to_dict(record))

            log_event(
                "citations_added",
                {
                    "message_id": message_id,
                    "citation_count": len(created_citations),
                },
            )

            return Success(created_citations)

        except ValueError as e:
            return validation_error(str(e), context={"message_id": message_id})
        except asyncpg.ForeignKeyViolationError:
            return not_found_error(
                f"Message '{message_id}' not found",
                context={"message_id": message_id},
            )
        except Exception as e:
            log_event(
                "citations_add_error",
                {"message_id": message_id, "error": str(e)},
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to add citations: {str(e)}",
                context={"message_id": message_id},
            )

    async def get_message_with_citations(
        self, message_id: str
    ) -> Result[Dict[str, Any], str]:
        """
        Get a single message with its citations.

        Args:
            message_id: Message UUID

        Returns:
            Success with message dict including citations, or Failure with error
        """
        try:
            # Parse UUID
            msg_uuid = parse_uuid(message_id)

            async with self.db_pool.acquire() as conn:
                # Get message
                message_record = await conn.fetchrow(
                    "SELECT * FROM messages WHERE id = $1", msg_uuid
                )

                if not message_record:
                    return not_found_error(
                        f"Message '{message_id}' not found",
                        context={"message_id": message_id},
                    )

                message = record_to_dict(message_record)

                # Get citations
                citation_records = await conn.fetch(
                    """
                    SELECT * FROM message_citations
                    WHERE message_id = $1
                    ORDER BY position
                    """,
                    msg_uuid,
                )
                message["citations"] = records_to_list(citation_records)

            return Success(message)

        except ValueError as e:
            return validation_error(str(e), context={"message_id": message_id})
        except Exception as e:
            log_event(
                "message_get_error",
                {"message_id": message_id, "error": str(e)},
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to get message: {str(e)}",
                context={"message_id": message_id},
            )

    async def delete_message(self, message_id: str) -> Result[Dict[str, Any], str]:
        """
        Delete a message and its citations.

        Args:
            message_id: Message UUID

        Returns:
            Success with deletion info, or Failure with error

        Note: This is a hard delete. Citations are cascade deleted.
        """
        try:
            # Parse UUID
            msg_uuid = parse_uuid(message_id)

            query = """
                DELETE FROM messages
                WHERE id = $1
                RETURNING id, conversation_id
            """

            async with self.db_pool.acquire() as conn:
                record = await conn.fetchrow(query, msg_uuid)

            if not record:
                return not_found_error(
                    f"Message '{message_id}' not found",
                    context={"message_id": message_id},
                )

            log_event(
                "message_deleted",
                {
                    "message_id": message_id,
                    "conversation_id": str(record["conversation_id"]),
                },
                level=logging.WARNING,
            )

            return Success(
                {
                    "message_id": message_id,
                    "conversation_id": str(record["conversation_id"]),
                    "deleted": True,
                }
            )

        except ValueError as e:
            return validation_error(str(e), context={"message_id": message_id})
        except Exception as e:
            log_event(
                "message_delete_error",
                {"message_id": message_id, "error": str(e)},
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to delete message: {str(e)}",
                context={"message_id": message_id},
            )
