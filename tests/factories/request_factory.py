"""
Factory for creating API request objects for testing.
"""

import json
import uuid
from typing import Dict, Any, List, Optional, Union
from io import BytesIO


class RequestFactory:
    """Factory for creating API request objects and payloads for testing."""
    
    @classmethod
    def create_ingest_request(
        self,
        path: str = "/tmp/test_file.txt",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create an ingest request payload."""
        return {
            "path": path,
            "tags": tags or [],
            "metadata": metadata or {},
            "session_id": session_id,
        }
    
    @classmethod
    def create_upload_form_data(
        self,
        file_content: bytes = b"Test file content",
        filename: str = "test.txt",
        content_type: str = "text/plain",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create form data for file upload testing."""
        return {
            "file": (filename, BytesIO(file_content), content_type),
            "tags": json.dumps(tags or []),
            "metadata": json.dumps(metadata or {}),
            "session_id": session_id,
        }
    
    @classmethod
    def create_bulk_ingest_request(
        self,
        file_paths: Optional[List[str]] = None,
        folder_path: str = "/tmp/test_folder",
    ) -> Dict[str, Any]:
        """Create a bulk ingest request payload."""
        if file_paths is None:
            file_paths = [
                "/tmp/test_folder/file1.txt",
                "/tmp/test_folder/file2.pdf",
                "/tmp/test_folder/file3.docx",
            ]
        
        return {
            "file_paths": file_paths,
            "folder_path": folder_path,
        }
    
    @classmethod
    def create_search_request(
        self,
        query: str = "test query",
        mode: str = "keyword",
        limit: int = 20,
        offset: int = 0,
        include_content: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a search request payload."""
        return {
            "query": query,
            "mode": mode,
            "limit": limit,
            "offset": offset,
            "include_content": include_content,
            "filters": filters or {},
        }
    
    @classmethod
    def create_search_query_params(
        self,
        q: str = "test query",
        mode: str = "keyword",
        limit: int = 20,
        offset: int = 0,
        include_content: bool = False,
        mime_type: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> Dict[str, Union[str, int, bool]]:
        """Create search query parameters for GET requests."""
        params = {
            "q": q,
            "mode": mode,
            "limit": limit,
            "offset": offset,
            "include_content": include_content,
        }
        
        if mime_type:
            params["mime_type"] = mime_type
        if status:
            params["status"] = status
        if tags:
            params["tags"] = tags
        
        return params
    
    @classmethod
    def create_ask_request(
        self,
        question: str = "What is this document about?",
        context_limit: int = 5,
    ) -> Dict[str, Any]:
        """Create a Q&A request payload."""
        return {
            "question": question,
            "context_limit": context_limit,
        }
    
    @classmethod
    def create_documents_query_params(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Union[str, int]]:
        """Create documents listing query parameters."""
        params = {
            "limit": limit,
            "offset": offset,
        }
        
        if status:
            params["status"] = status
        
        return params
    
    @classmethod
    def create_document_chunks_query_params(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, int]:
        """Create document chunks query parameters."""
        return {
            "limit": limit,
            "offset": offset,
        }
    
    @classmethod
    def create_document_neighbors_query_params(
        self,
        top_k: int = 10,
    ) -> Dict[str, int]:
        """Create document neighbors query parameters."""
        return {
            "top_k": top_k,
        }
    
    @classmethod
    def create_vault_files_query_params(
        self,
        directory: str = "content",
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Union[str, int]]:
        """Create vault files query parameters."""
        return {
            "directory": directory,
            "limit": limit,
            "offset": offset,
        }
    
    @classmethod
    def create_websocket_message(
        self,
        message_type: str = "tool_execute",
        tool: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a WebSocket message for testing."""
        if message_id is None:
            message_id = f"msg_{uuid.uuid4().hex[:12]}"
        
        message = {
            "type": message_type,
            "id": message_id,
        }
        
        if tool:
            message["tool"] = tool
        if params:
            message["params"] = params
        
        return message
    
    @classmethod
    def create_agent_query_message(
        self,
        agent: str = "query_agent",
        query: str = "test query",
        message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create an agent query WebSocket message."""
        if message_id is None:
            message_id = f"agent_msg_{uuid.uuid4().hex[:12]}"
        
        return {
            "type": "agent_query",
            "id": message_id,
            "agent": agent,
            "query": query,
        }


# Convenience functions for common request scenarios
def create_medical_search_requests() -> List[Dict[str, Any]]:
    """Create search requests for medical domain testing."""
    return [
        RequestFactory.create_search_request(
            query="blood pressure medication",
            mode="semantic",
            filters={"category": "medical"}
        ),
        RequestFactory.create_search_request(
            query="patient care guidelines",
            mode="keyword",
            filters={"tags": ["medical", "guidelines"]}
        ),
        RequestFactory.create_search_request(
            query="medical report analysis",
            mode="hybrid",
            filters={"mime_type": "application/pdf"}
        ),
    ]


def create_financial_search_requests() -> List[Dict[str, Any]]:
    """Create search requests for financial domain testing."""
    return [
        RequestFactory.create_search_request(
            query="quarterly earnings bank",
            mode="semantic",
            filters={"category": "financial"}
        ),
        RequestFactory.create_search_request(
            query="mortgage rates interest",
            mode="keyword",
            filters={"tags": ["financial", "mortgage"]}
        ),
    ]


def create_qa_requests() -> List[Dict[str, Any]]:
    """Create Q&A requests for testing."""
    return [
        RequestFactory.create_ask_request(
            question="What are the current mortgage rates?",
            context_limit=3
        ),
        RequestFactory.create_ask_request(
            question="Summarize the patient's blood pressure readings.",
            context_limit=5
        ),
        RequestFactory.create_ask_request(
            question="What were the key findings in the earnings report?",
            context_limit=7
        ),
    ]


def create_invalid_requests() -> Dict[str, Dict[str, Any]]:
    """Create invalid requests for error testing."""
    return {
        "empty_query_search": RequestFactory.create_search_request(query=""),
        "invalid_mode_search": RequestFactory.create_search_request(mode="invalid_mode"),
        "negative_limit_search": RequestFactory.create_search_request(limit=-1),
        "excessive_limit_search": RequestFactory.create_search_request(limit=1000),
        "empty_question_ask": RequestFactory.create_ask_request(question=""),
        "invalid_context_limit": RequestFactory.create_ask_request(context_limit=50),
        "missing_path_ingest": {"tags": [], "metadata": {}},  # Missing required path
    }


def create_edge_case_requests() -> Dict[str, Dict[str, Any]]:
    """Create edge case requests for boundary testing."""
    return {
        "max_limit_search": RequestFactory.create_search_request(limit=100),
        "zero_offset_search": RequestFactory.create_search_request(offset=0),
        "large_offset_search": RequestFactory.create_search_request(offset=1000),
        "min_context_ask": RequestFactory.create_ask_request(context_limit=1),
        "max_context_ask": RequestFactory.create_ask_request(context_limit=20),
        "long_query_search": RequestFactory.create_search_request(
            query="This is a very long search query " * 20
        ),
        "unicode_query_search": RequestFactory.create_search_request(
            query="测试查询 🔍 émojis and ñon-ASCII characters"
        ),
    }