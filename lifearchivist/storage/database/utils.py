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
    Convert asyncpg Record to dictionary.

    Args:
        record: Database record

    Returns:
        Dictionary with column names as keys
    """
    return dict(record)


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
