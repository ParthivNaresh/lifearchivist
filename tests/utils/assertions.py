"""
Custom assertions for Life Archivist API testing.

This module provides specialized assertion functions for validating
API responses and ensuring consistent testing patterns.
"""

from typing import Dict, Any, List, Optional, Union
from fastapi.testclient import TestClient
from httpx import Response


def assert_successful_response(
    response: Response,
    expected_status: int = 200,
    required_fields: Optional[List[str]] = None,
    forbidden_fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Assert that a response is successful and contains expected fields.
    
    Args:
        response: HTTP response object
        expected_status: Expected HTTP status code
        required_fields: Fields that must be present in response
        forbidden_fields: Fields that must not be present in response
    
    Returns:
        Parsed response JSON
    """
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}. "
        f"Response: {response.text}"
    )
    
    # Ensure response is JSON
    assert response.headers.get("content-type", "").startswith("application/json"), (
        f"Expected JSON response, got {response.headers.get('content-type')}"
    )
    
    data = response.json()
    
    # Check required fields
    if required_fields:
        for field in required_fields:
            assert field in data, f"Required field '{field}' not found in response: {data.keys()}"
    
    # Check forbidden fields
    if forbidden_fields:
        for field in forbidden_fields:
            assert field not in data, f"Forbidden field '{field}' found in response"
    
    return data


def assert_error_response(
    response: Response,
    expected_status: int,
    expected_detail_contains: Optional[str] = None,
    expected_error_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Assert that a response is an error response with expected content.
    
    Args:
        response: HTTP response object
        expected_status: Expected HTTP status code (400-599)
        expected_detail_contains: String that should be contained in error detail
        expected_error_type: Expected error type if present
    
    Returns:
        Parsed response JSON
    """
    assert 400 <= expected_status <= 599, f"Expected error status code, got {expected_status}"
    assert response.status_code == expected_status, (
        f"Expected error status {expected_status}, got {response.status_code}. "
        f"Response: {response.text}"
    )
    
    data = response.json()
    
    # FastAPI error responses should have 'detail' field
    assert "detail" in data, f"Error response missing 'detail' field: {data}"
    
    if expected_detail_contains:
        detail = str(data["detail"])
        assert expected_detail_contains.lower() in detail.lower(), (
            f"Expected '{expected_detail_contains}' in error detail, got: {detail}"
        )
    
    if expected_error_type:
        # Some error responses might include error type
        error_type = data.get("type", data.get("error_type"))
        if error_type:
            assert error_type == expected_error_type, (
                f"Expected error type '{expected_error_type}', got '{error_type}'"
            )
    
    return data


def assert_pagination_response(
    response: Response,
    expected_status: int = 200,
    expected_total: Optional[int] = None,
    expected_limit: Optional[int] = None,
    expected_offset: Optional[int] = None,
    items_field: str = "results",
) -> Dict[str, Any]:
    """
    Assert that a response is a valid paginated response.
    
    Args:
        response: HTTP response object
        expected_status: Expected HTTP status code
        expected_total: Expected total count
        expected_limit: Expected limit value
        expected_offset: Expected offset value
        items_field: Field name containing the items list
    
    Returns:
        Parsed response JSON
    """
    data = assert_successful_response(
        response,
        expected_status,
        required_fields=[items_field, "total", "limit", "offset"]
    )
    
    # Validate pagination fields
    assert isinstance(data[items_field], list), f"'{items_field}' should be a list"
    assert isinstance(data["total"], int), "total should be an integer"
    assert isinstance(data["limit"], int), "limit should be an integer"
    assert isinstance(data["offset"], int), "offset should be an integer"
    
    # Check pagination constraints
    assert data["limit"] > 0, "limit should be positive"
    assert data["offset"] >= 0, "offset should be non-negative"
    assert len(data[items_field]) <= data["limit"], "returned items should not exceed limit"
    
    # Check expected values if provided
    if expected_total is not None:
        assert data["total"] == expected_total, f"Expected total {expected_total}, got {data['total']}"
    
    if expected_limit is not None:
        assert data["limit"] == expected_limit, f"Expected limit {expected_limit}, got {data['limit']}"
    
    if expected_offset is not None:
        assert data["offset"] == expected_offset, f"Expected offset {expected_offset}, got {data['offset']}"
    
    return data


def assert_search_response(
    response: Response,
    expected_status: int = 200,
    min_results: int = 0,
    max_results: Optional[int] = None,
    expected_mode: Optional[str] = None,
    expected_query: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Assert that a response is a valid search response.
    
    Args:
        response: HTTP response object
        expected_status: Expected HTTP status code
        min_results: Minimum number of results expected
        max_results: Maximum number of results expected
        expected_mode: Expected search mode
        expected_query: Expected search query
    
    Returns:
        Parsed response JSON
    """
    data = assert_successful_response(
        response,
        expected_status,
        required_fields=["results", "total", "query_time_ms"]
    )
    
    # Validate search response structure
    assert isinstance(data["results"], list), "results should be a list"
    assert isinstance(data["total"], int), "total should be an integer"
    assert isinstance(data["query_time_ms"], (int, float)), "query_time_ms should be numeric"
    
    # Check results count constraints
    results_count = len(data["results"])
    assert results_count >= min_results, f"Expected at least {min_results} results, got {results_count}"
    
    if max_results is not None:
        assert results_count <= max_results, f"Expected at most {max_results} results, got {results_count}"
    
    # Check expected values (mode is optional since API might not return it)
    if expected_mode and "mode" in data:
        assert data["mode"] == expected_mode, f"Expected mode '{expected_mode}', got '{data['mode']}'"
    
    if expected_query:
        query = data.get("query", "")
        assert expected_query in query, f"Expected query to contain '{expected_query}', got '{query}'"
    
    # Validate individual search results
    for i, result in enumerate(data["results"]):
        assert isinstance(result, dict), f"Result {i} should be a dict"
        assert "document_id" in result, f"Result {i} missing document_id"
        assert "score" in result, f"Result {i} missing score"
        
        # Score should be numeric and reasonable
        score = result["score"]
        assert isinstance(score, (int, float)), f"Result {i} score should be numeric"
        assert 0 <= score <= 1, f"Result {i} score should be between 0 and 1, got {score}"
    
    return data


def assert_document_response(
    response: Response,
    expected_status: int = 200,
    expected_document_id: Optional[str] = None,
    required_fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Assert that a response is a valid document response.
    
    Args:
        response: HTTP response object
        expected_status: Expected HTTP status code
        expected_document_id: Expected document ID
        required_fields: Additional required fields
    
    Returns:
        Parsed response JSON
    """
    default_fields = ["document_id", "title", "status"]
    all_required_fields = default_fields + (required_fields or [])
    
    data = assert_successful_response(
        response,
        expected_status,
        required_fields=all_required_fields
    )
    
    # Validate document fields
    assert isinstance(data["document_id"], str), "document_id should be a string"
    assert len(data["document_id"]) > 0, "document_id should not be empty"
    assert isinstance(data["status"], str), "status should be a string"
    
    if expected_document_id:
        assert data["document_id"] == expected_document_id, (
            f"Expected document_id '{expected_document_id}', got '{data['document_id']}'"
        )
    
    return data


def assert_upload_response(
    response: Response,
    expected_status: int = 200,
    expected_file_size: Optional[int] = None,
    expected_mime_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Assert that a response is a valid upload response.
    
    Args:
        response: HTTP response object
        expected_status: Expected HTTP status code
        expected_file_size: Expected file size
        expected_mime_type: Expected MIME type
    
    Returns:
        Parsed response JSON
    """
    data = assert_successful_response(
        response,
        expected_status,
        required_fields=["file_id", "hash", "size", "mime_type", "status"]
    )
    
    # Validate upload response fields
    assert isinstance(data["file_id"], str), "file_id should be a string"
    assert len(data["file_id"]) > 0, "file_id should not be empty"
    assert isinstance(data["hash"], str), "hash should be a string"
    assert len(data["hash"]) > 0, "hash should not be empty"
    assert isinstance(data["size"], int), "size should be an integer"
    assert isinstance(data["mime_type"], str), "mime_type should be a string"
    assert isinstance(data["status"], str), "status should be a string"
    
    if expected_file_size:
        assert data["size"] == expected_file_size, f"Expected size {expected_file_size}, got {data['size']}"
    
    if expected_mime_type:
        assert data["mime_type"] == expected_mime_type, (
            f"Expected mime_type '{expected_mime_type}', got '{data['mime_type']}'"
        )
    
    return data


def assert_qa_response(
    response: Response,
    expected_status: int = 200,
    min_confidence: float = 0.0,
    max_confidence: float = 1.0,
    min_citations: int = 0,
) -> Dict[str, Any]:
    """
    Assert that a response is a valid Q&A response.
    
    Args:
        response: HTTP response object
        expected_status: Expected HTTP status code
        min_confidence: Minimum expected confidence score
        max_confidence: Maximum expected confidence score
        min_citations: Minimum expected number of citations
    
    Returns:
        Parsed response JSON
    """
    data = assert_successful_response(
        response,
        expected_status,
        required_fields=["answer", "confidence", "citations"]
    )
    
    # Validate Q&A response structure
    assert isinstance(data["answer"], str), "answer should be a string"
    assert len(data["answer"]) > 0, "answer should not be empty"
    assert isinstance(data["confidence"], (int, float)), "confidence should be numeric"
    assert isinstance(data["citations"], list), "citations should be a list"
    
    # Check confidence bounds
    confidence = data["confidence"]
    assert min_confidence <= confidence <= max_confidence, (
        f"Confidence {confidence} not in range [{min_confidence}, {max_confidence}]"
    )
    
    # Check citations count
    citations_count = len(data["citations"])
    assert citations_count >= min_citations, (
        f"Expected at least {min_citations} citations, got {citations_count}"
    )
    
    # Validate individual citations
    for i, citation in enumerate(data["citations"]):
        assert isinstance(citation, dict), f"Citation {i} should be a dict"
        assert "doc_id" in citation, f"Citation {i} missing doc_id"
        assert "snippet" in citation, f"Citation {i} missing snippet"
        assert "score" in citation, f"Citation {i} missing score"
        
        score = citation["score"]
        assert isinstance(score, (int, float)), f"Citation {i} score should be numeric"
        assert 0 <= score <= 1, f"Citation {i} score should be between 0 and 1, got {score}"
    
    return data


def assert_health_response(
    response: Response,
    expected_status: int = 200,
) -> Dict[str, Any]:
    """
    Assert that a response is a valid health check response.
    
    Args:
        response: HTTP response object
        expected_status: Expected HTTP status code
    
    Returns:
        Parsed response JSON
    """
    data = assert_successful_response(
        response,
        expected_status,
        required_fields=["status", "timestamp"]
    )
    
    # Validate health response
    assert data["status"] in ["healthy", "degraded", "unhealthy"], (
        f"Invalid health status: {data['status']}"
    )
    assert isinstance(data["timestamp"], str), "timestamp should be a string"
    
    return data