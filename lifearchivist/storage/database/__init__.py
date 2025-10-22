"""
Database module for PostgreSQL-backed conversation storage.

This module provides production-grade conversation management with:
- Conversation history and context
- Message threading and branching
- Citation tracking
- File attachments
- Full-text search
- Performance optimizations

The schema is designed to scale to millions of conversations while
maintaining sub-10ms query performance through proper indexing and
connection pooling.
"""

from .conversation_service import ConversationService
from .message_service import MessageService
from .utils import (
    DatabaseError,
    DuplicateRecordError,
    RecordNotFoundError,
    build_insert_query,
    build_update_query,
    parse_uuid,
    record_to_dict,
    records_to_list,
)

__all__ = [
    "ConversationService",
    "MessageService",
    "DatabaseError",
    "RecordNotFoundError",
    "DuplicateRecordError",
    "build_insert_query",
    "build_update_query",
    "parse_uuid",
    "record_to_dict",
    "records_to_list",
]
