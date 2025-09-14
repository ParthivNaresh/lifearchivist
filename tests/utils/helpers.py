"""
Helper utilities for Life Archivist testing.

This module provides common helper functions that are used across
different test scenarios to reduce code duplication.
"""

import asyncio
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Union
from unittest.mock import patch

from tests.factories.file.file_factory import TestFile
from tests.factories.file.temp_file_manager import TempFileManager


def create_test_files(
    test_files: List[TestFile],
    cleanup_paths: Optional[List[Path]] = None
) -> List[Path]:
    """
    Create actual temporary files from TestFile objects.
    
    Args:
        test_files: List of TestFile objects to create
        cleanup_paths: Optional list to append created paths to for cleanup
    
    Returns:
        List of created file paths
    """
    created_paths = []
    
    for test_file in test_files:
        temp_path = TempFileManager.create_temp_file(test_file)
        created_paths.append(temp_path)
        
        if cleanup_paths is not None:
            cleanup_paths.append(temp_path)
    
    return created_paths


def cleanup_test_files(file_paths: List[Path]) -> None:
    """
    Clean up temporary test files.
    
    Args:
        file_paths: List of file paths to clean up
    """
    for file_path in file_paths:
        try:
            if file_path.exists():
                if file_path.is_file():
                    file_path.unlink()
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
        except Exception:
            # Ignore cleanup errors in tests
            pass


async def wait_for_condition(
    condition: Callable[[], Union[bool, Any]],
    timeout: float = 5.0,
    interval: float = 0.1,
    error_message: str = "Condition not met within timeout"
) -> Any:
    """
    Wait for a condition to be true within a timeout.
    
    Args:
        condition: Function (sync or async) that returns truthy value when condition is met
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds
        error_message: Error message if timeout is reached
    
    Returns:
        The truthy result from the condition function
        
    Raises:
        TimeoutError: If condition is not met within timeout
    """
    import inspect
    start_time = asyncio.get_event_loop().time()
    
    while True:
        # Handle both sync and async callables
        if inspect.iscoroutinefunction(condition):
            result = await condition()
        else:
            result = condition()
            
        if result:
            return result
        
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > timeout:
            raise TimeoutError(error_message)
        
        await asyncio.sleep(interval)


def compare_responses(
    actual: Dict[str, Any],
    expected: Dict[str, Any],
    ignore_fields: Optional[List[str]] = None,
    approximate_fields: Optional[Dict[str, float]] = None
) -> List[str]:
    """
    Compare two response dictionaries and return list of differences.
    
    Args:
        actual: Actual response data
        expected: Expected response data
        ignore_fields: Fields to ignore in comparison
        approximate_fields: Fields to compare approximately {field: tolerance}
    
    Returns:
        List of difference descriptions (empty if responses match)
    """
    ignore_fields = ignore_fields or []
    approximate_fields = approximate_fields or {}
    differences = []
    
    # Check for missing fields in actual
    for field in expected:
        if field in ignore_fields:
            continue
        
        if field not in actual:
            differences.append(f"Missing field '{field}' in actual response")
            continue
        
        expected_value = expected[field]
        actual_value = actual[field]
        
        # Handle approximate comparisons
        if field in approximate_fields:
            tolerance = approximate_fields[field]
            if isinstance(expected_value, (int, float)) and isinstance(actual_value, (int, float)):
                if abs(actual_value - expected_value) > tolerance:
                    differences.append(
                        f"Field '{field}': expected ~{expected_value} (±{tolerance}), got {actual_value}"
                    )
            else:
                differences.append(
                    f"Field '{field}': cannot do approximate comparison on non-numeric values"
                )
            continue
        
        # Exact comparison
        if actual_value != expected_value:
            differences.append(
                f"Field '{field}': expected {expected_value}, got {actual_value}"
            )
    
    # Check for extra fields in actual
    for field in actual:
        if field not in expected and field not in ignore_fields:
            differences.append(f"Unexpected field '{field}' in actual response")
    
    return differences


def extract_file_id(response_data: Dict[str, Any], field_name: str = "file_id") -> Optional[str]:
    """
    Extract file ID from response data with validation.
    
    Args:
        response_data: Response dictionary
        field_name: Name of the field containing the file ID
    
    Returns:
        File ID string or None if not found/invalid
    """
    file_id = response_data.get(field_name)
    
    if not file_id:
        return None
    
    if not isinstance(file_id, str) or len(file_id) == 0:
        return None
    
    return file_id


def extract_document_ids(response_data: Dict[str, Any], results_field: str = "results") -> List[str]:
    """
    Extract document IDs from search results or document lists.
    
    Args:
        response_data: Response dictionary containing results
        results_field: Field name containing the results list
    
    Returns:
        List of document IDs
    """
    results = response_data.get(results_field, [])
    document_ids = []
    
    for result in results:
        if isinstance(result, dict):
            doc_id = result.get("document_id") or result.get("doc_id")
            if doc_id:
                document_ids.append(doc_id)
    
    return document_ids


def mock_successful_tool_execution(tool_result: Dict[str, Any]):
    """
    Context manager to mock successful tool execution.
    
    Args:
        tool_result: The result to return from tool execution
    """
    return patch(
        'lifearchivist.server.mcp_server.MCPServer.execute_tool',
        return_value={"success": True, "result": tool_result}
    )


def mock_failed_tool_execution(error_message: str = "Tool execution failed"):
    """
    Context manager to mock failed tool execution.
    
    Args:
        error_message: Error message to return
    """
    return patch(
        'lifearchivist.server.mcp_server.MCPServer.execute_tool',
        return_value={"success": False, "error": error_message}
    )


def assert_valid_file_id(file_id: str, prefix: str = "") -> None:
    """
    Assert that a file ID has valid format.
    
    Args:
        file_id: File ID to validate
        prefix: Expected prefix for the file ID
    """
    assert isinstance(file_id, str), f"File ID should be string, got {type(file_id)}"
    assert len(file_id) > 0, "File ID should not be empty"
    
    if prefix:
        assert file_id.startswith(prefix), f"File ID should start with '{prefix}', got '{file_id}'"


def assert_valid_hash(hash_value: str, expected_length: int = 64) -> None:
    """
    Assert that a hash value has valid format.
    
    Args:
        hash_value: Hash value to validate
        expected_length: Expected hash length (default: SHA256 = 64)
    """
    assert isinstance(hash_value, str), f"Hash should be string, got {type(hash_value)}"
    assert len(hash_value) == expected_length, f"Hash should be {expected_length} chars, got {len(hash_value)}"
    assert hash_value.isalnum(), f"Hash should be alphanumeric, got '{hash_value}'"


def assert_valid_timestamp(timestamp: str) -> None:
    """
    Assert that a timestamp has valid ISO format.
    
    Args:
        timestamp: Timestamp string to validate
    """
    assert isinstance(timestamp, str), f"Timestamp should be string, got {type(timestamp)}"
    
    # Try to parse as ISO format
    from datetime import datetime
    try:
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except ValueError as e:
        assert False, f"Invalid timestamp format '{timestamp}': {e}"


def create_pagination_test_cases() -> List[Dict[str, Any]]:
    """
    Create common pagination test cases.
    
    Returns:
        List of test case parameters for pagination testing
    """
    return [
        {"limit": 10, "offset": 0, "description": "First page"},
        {"limit": 5, "offset": 10, "description": "Second page with smaller limit"},
        {"limit": 100, "offset": 0, "description": "Maximum limit"},
        {"limit": 1, "offset": 0, "description": "Single item"},
        {"limit": 20, "offset": 100, "description": "High offset"},
    ]


def create_error_test_cases() -> List[Dict[str, Any]]:
    """
    Create common error test cases for parameter validation.
    
    Returns:
        List of error test case parameters
    """
    return [
        {
            "params": {"limit": -1},
            "expected_status": 400,
            "description": "Negative limit"
        },
        {
            "params": {"limit": 1001},
            "expected_status": 400,
            "description": "Excessive limit"
        },
        {
            "params": {"offset": -1},
            "expected_status": 400,
            "description": "Negative offset"
        },
        {
            "params": {"mode": "invalid_mode"},
            "expected_status": 400,
            "description": "Invalid search mode"
        },
    ]


class ResponseValidator:
    """Helper class for validating API responses with common patterns."""
    
    @staticmethod
    def validate_pagination_response(data: Dict[str, Any], items_field: str = "results") -> None:
        """Validate pagination response structure."""
        required_fields = [items_field, "total", "limit", "offset"]
        for field in required_fields:
            assert field in data, f"Missing pagination field: {field}"
        
        assert isinstance(data[items_field], list), f"{items_field} should be a list"
        assert isinstance(data["total"], int) and data["total"] >= 0, "total should be non-negative integer"
        assert isinstance(data["limit"], int) and data["limit"] > 0, "limit should be positive integer"
        assert isinstance(data["offset"], int) and data["offset"] >= 0, "offset should be non-negative integer"
        
        # Results count should not exceed limit
        assert len(data[items_field]) <= data["limit"], "Results count exceeds limit"
    
    @staticmethod
    def validate_search_response(data: Dict[str, Any]) -> None:
        """Validate search response structure."""
        required_fields = ["results", "total", "query_time_ms", "mode"]
        for field in required_fields:
            assert field in data, f"Missing search field: {field}"
        
        assert isinstance(data["results"], list), "results should be a list"
        assert isinstance(data["query_time_ms"], (int, float)), "query_time_ms should be numeric"
        assert data["query_time_ms"] >= 0, "query_time_ms should be non-negative"
        
        # Validate search results
        for i, result in enumerate(data["results"]):
            assert "document_id" in result, f"Result {i} missing document_id"
            assert "score" in result, f"Result {i} missing score"
            assert 0 <= result["score"] <= 1, f"Result {i} score out of range: {result['score']}"