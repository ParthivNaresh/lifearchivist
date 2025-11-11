"""
Database utility functions for common operations.

Provides reusable helpers for:
- Query building
- Result mapping
- Error handling
- Transaction management
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

import asyncpg


class DatabaseError(Exception):
    """Base exception for database errors."""

    pass


class RecordNotFoundError(DatabaseError):
    """Raised when a record is not found."""

    pass


class DuplicateRecordError(DatabaseError):
    """Raised when attempting to create a duplicate record."""

    pass


def record_to_dict(record: asyncpg.Record) -> Dict[str, Any]:
    """
    Convert asyncpg Record to dictionary with proper JSONB parsing.

    Args:
        record: Database record

    Returns:
        Dictionary with column names as keys and JSONB fields parsed
    """
    import json

    result = dict(record)

    for key, value in result.items():
        if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
            try:
                result[key] = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                pass

    return result


def records_to_list(records: List[asyncpg.Record]) -> List[Dict[str, Any]]:
    """
    Convert list of asyncpg Records to list of dictionaries.

    Args:
        records: List of database records

    Returns:
        List of dictionaries
    """
    return [record_to_dict(record) for record in records]


def build_update_query(
    table: str,
    updates: Dict[str, Any],
    where_clause: str,
    returning: str = "*",
) -> tuple[str, List[Any]]:
    """
    Build UPDATE query with parameterized values.

    Args:
        table: Table name
        updates: Dictionary of column: value pairs
        where_clause: WHERE clause (e.g., "id = $1")
        returning: RETURNING clause (default: "*")

    Returns:
        Tuple of (query, values)

    Example:
        query, values = build_update_query(
            "conversations",
            {"title": "New Title", "updated_at": datetime.now()},
            "id = $1"
        )
    """
    if not updates:
        raise ValueError("No updates provided")

    set_clauses = []
    values = []
    param_num = 1

    for column, value in updates.items():
        set_clauses.append(f"{column} = ${param_num}")
        values.append(value)
        param_num += 1

    query = f"""
        UPDATE {table}
        SET {', '.join(set_clauses)}
        WHERE {where_clause}
        RETURNING {returning}
    """

    return query, values


def build_insert_query(
    table: str,
    data: Dict[str, Any],
    returning: str = "*",
) -> tuple[str, List[Any]]:
    """
    Build INSERT query with parameterized values.

    Args:
        table: Table name
        data: Dictionary of column: value pairs
        returning: RETURNING clause (default: "*")

    Returns:
        Tuple of (query, values)

    Example:
        query, values = build_insert_query(
            "conversations",
            {"user_id": "default", "title": "New Chat", "model": "llama3.2"}
        )
    """
    if not data:
        raise ValueError("No data provided")

    columns = list(data.keys())
    values = list(data.values())
    placeholders = [f"${i+1}" for i in range(len(values))]

    query = f"""
        INSERT INTO {table} ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        RETURNING {returning}
    """

    return query, values


def parse_uuid(value: Any) -> Optional[UUID]:
    """
    Safely parse UUID from various input types.

    Args:
        value: UUID string, UUID object, or None

    Returns:
        UUID object or None

    Raises:
        ValueError: If value is not a valid UUID
    """
    if value is None:
        return None

    if isinstance(value, UUID):
        return value

    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            raise ValueError(f"Invalid UUID: {value}") from None

    raise ValueError(f"Cannot parse UUID from type {type(value)}")


async def execute_in_transaction(
    pool: asyncpg.Pool,
    operations: List[tuple[str, List[Any]]],
) -> List[Any]:
    """
    Execute multiple operations in a single transaction.

    Args:
        pool: Database connection pool
        operations: List of (query, values) tuples

    Returns:
        List of results from each operation

    Raises:
        DatabaseError: If transaction fails

    Example:
        results = await execute_in_transaction(pool, [
            ("INSERT INTO conversations ...", [values]),
            ("INSERT INTO messages ...", [values]),
        ])
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            results = []
            for query, values in operations:
                result = await conn.fetch(query, *values)
                results.append(result)
            return results


def format_timestamp(dt: Any) -> Optional[str]:
    """
    Format datetime to ISO 8601 string.

    Args:
        dt: Datetime object or None

    Returns:
        ISO 8601 string or None
    """
    if dt is None:
        return None

    if hasattr(dt, "isoformat"):
        # Explicit cast: isoformat() returns str
        iso_str: str = dt.isoformat()
        return iso_str

    # Fallback for non-datetime objects - convert to string
    # Explicit cast to satisfy type checker
    result: str = str(dt)
    return result if result else None


def validate_temperature(temperature: float) -> Optional[str]:
    """
    Validate temperature parameter.

    Args:
        temperature: Temperature value to validate

    Returns:
        Error message if invalid, None if valid
    """
    if temperature < 0 or temperature > 2:
        return "Temperature must be between 0 and 2"
    return None


def validate_max_tokens(max_tokens: int) -> Optional[str]:
    """
    Validate max_tokens parameter.

    Args:
        max_tokens: Max tokens value to validate

    Returns:
        Error message if invalid, None if valid
    """
    if max_tokens < 1 or max_tokens > 100000:
        return "Max tokens must be between 1 and 100000"
    return None


def build_conversation_updates(
    title: Optional[str],
    model: Optional[str],
    provider_id: Optional[str],
    context_documents: Optional[List[str]],
    system_prompt: Optional[str],
    temperature: Optional[float],
    max_tokens: Optional[int],
    metadata: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build updates dictionary for conversation update.

    Args:
        title: New title
        model: New model
        provider_id: New provider ID
        context_documents: New context documents
        system_prompt: New system prompt
        temperature: New temperature
        max_tokens: New max tokens
        metadata: New metadata

    Returns:
        Dictionary of updates to apply
    """
    updates: Dict[str, Any] = {}

    if title is not None:
        updates["title"] = title

    if model is not None:
        updates["model"] = model

    if provider_id is not None:
        updates["provider_id"] = provider_id

    if context_documents is not None:
        updates["context_documents"] = context_documents

    if system_prompt is not None:
        updates["system_prompt"] = system_prompt

    if temperature is not None:
        updates["temperature"] = temperature

    if max_tokens is not None:
        updates["max_tokens"] = max_tokens

    if metadata is not None:
        updates["metadata"] = metadata

    return updates


def validate_message_role(role: str) -> Optional[str]:
    """
    Validate message role.

    Args:
        role: Role to validate

    Returns:
        Error message if invalid, None if valid
    """
    if role not in ("user", "assistant", "system"):
        return f"Invalid role: {role}. Must be 'user', 'assistant', or 'system'"
    return None


def validate_message_content(content: str) -> Optional[str]:
    """
    Validate message content.

    Args:
        content: Content to validate

    Returns:
        Error message if invalid, None if valid
    """
    if not content or not content.strip():
        return "Message content cannot be empty"
    return None


def validate_confidence(confidence: float) -> Optional[str]:
    """
    Validate confidence score.

    Args:
        confidence: Confidence value to validate

    Returns:
        Error message if invalid, None if valid
    """
    if confidence < 0 or confidence > 1:
        return "Confidence must be between 0 and 1"
    return None


def build_message_data(
    conv_uuid: Any,
    role: str,
    content: str,
    sequence_number: int,
    model: Optional[str],
    confidence: Optional[float],
    method: Optional[str],
    tokens_used: Optional[int],
    latency_ms: Optional[int],
    parent_uuid: Optional[Any],
    metadata: Optional[Any],
) -> Dict[str, Any]:
    """
    Build message data dictionary for insertion.

    Args:
        conv_uuid: Conversation UUID
        role: Message role
        content: Message content
        sequence_number: Sequence number
        model: Model used
        confidence: Confidence score
        method: Method used
        tokens_used: Token count
        latency_ms: Latency in milliseconds
        parent_uuid: Parent message UUID
        metadata: Additional metadata

    Returns:
        Dictionary of message data
    """
    import json

    data: Dict[str, Any] = {
        "conversation_id": conv_uuid,
        "role": role,
        "content": content.strip(),
        "sequence_number": sequence_number,
    }

    if model:
        data["model"] = model
    if confidence is not None:
        data["confidence"] = confidence
    if method:
        data["method"] = method
    if tokens_used is not None:
        data["tokens_used"] = tokens_used
    if latency_ms is not None:
        data["latency_ms"] = latency_ms
    if parent_uuid:
        data["parent_message_id"] = parent_uuid
    if metadata:
        data["metadata"] = (
            json.dumps(metadata) if isinstance(metadata, dict) else metadata
        )

    return data


def validate_citation_score(score: float) -> Optional[str]:
    """
    Validate citation score.

    Args:
        score: Score value to validate

    Returns:
        Error message if invalid, None if valid
    """
    if score < 0 or score > 1:
        return "Citation score must be between 0 and 1"
    return None


def validate_single_citation(
    citation: Dict[str, Any],
    index: int,
) -> Optional[str]:
    """
    Validate a single citation.

    Args:
        citation: Citation dictionary to validate
        index: Citation index for error messages

    Returns:
        Error message if invalid, None if valid
    """
    if "document_id" not in citation:
        return f"Citation {index} missing document_id"

    score = citation.get("score")
    if score is not None:
        error_msg = validate_citation_score(score)
        if error_msg:
            return f"Citation {index} score must be between 0 and 1"

    return None


def build_citation_data(
    msg_uuid: Any,
    citation: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build citation data dictionary for insertion.

    Args:
        msg_uuid: Message UUID
        citation: Citation dictionary

    Returns:
        Dictionary of citation data
    """
    data: Dict[str, Any] = {
        "message_id": msg_uuid,
        "document_id": citation["document_id"],
    }

    if "chunk_id" in citation:
        data["chunk_id"] = citation["chunk_id"]
    if "score" in citation:
        data["score"] = citation["score"]
    if "snippet" in citation:
        data["snippet"] = citation["snippet"]
    if "position" in citation:
        data["position"] = citation["position"]

    return data
