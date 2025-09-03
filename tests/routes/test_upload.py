"""
Tests for upload routes (/api/upload, /api/ingest, /api/bulk-ingest).

This module demonstrates the testing patterns for upload-related routes
using the testing framework and base classes.
"""
from pathlib import Path

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from ..base import BaseUploadTest, ParameterizedRouteTest
from ..factories.file_factory import FileFactory, TempFileFactory
from ..factories.request_factory import RequestFactory
from ..utils.helpers import extract_file_id, assert_valid_file_id, assert_valid_hash


class TestUploadRoutes(BaseUploadTest):
    """Test upload routes with mocked services."""
    
    @pytest.mark.asyncio
    async def test_upload_simple_text_file(self, async_client: AsyncClient):
        """Test uploading a simple text file."""
        # Create test file content
        test_content = "This is a simple test file for upload testing."
        
        # Perform upload
        response_data = await self.perform_upload(
            async_client,
            file_content=test_content.encode(),
            filename="simple_test.txt",
            content_type="text/plain"
        )
        
        # Validate response structure
        assert "file_id" in response_data
        assert "hash" in response_data
        assert "size" in response_data
        assert "mime_type" in response_data
        assert "status" in response_data
        
        # Validate response values
        assert_valid_file_id(response_data["file_id"])
        assert_valid_hash(response_data["hash"])
        assert response_data["size"] == len(test_content.encode())
        assert response_data["mime_type"] == "text/plain"
        assert response_data["status"] in ["completed", "processing", "ready"]
    
    @pytest.mark.asyncio
    async def test_upload_with_metadata(self, async_client: AsyncClient):
        """Test uploading a file with custom metadata."""
        test_metadata = {
            "category": "test_document",
            "author": "Test User",
            "description": "Test file with metadata"
        }
        
        response_data = await self.perform_upload(
            async_client,
            file_content=b"Test content with metadata",
            filename="metadata_test.txt",
            metadata=test_metadata
        )
        
        # File should be uploaded successfully
        assert_valid_file_id(response_data["file_id"])
        assert response_data["status"] in ["completed", "processing", "ready"]
    
    @pytest.mark.asyncio
    async def test_upload_with_tags(self, async_client: AsyncClient):
        """Test uploading a file with tags."""
        test_tags = ["test", "upload", "tagged"]
        
        response_data = await self.perform_upload(
            async_client,
            file_content=b"Test content with tags",
            filename="tagged_test.txt",
            tags=test_tags
        )
        
        # File should be uploaded successfully
        assert_valid_file_id(response_data["file_id"])
        assert response_data["status"] in ["completed", "processing", "ready"]
    
    @pytest.mark.asyncio
    async def test_upload_pdf_like_file(self, async_client: AsyncClient):
        """Test uploading a PDF-like file."""
        # Create a PDF-like test file
        test_file = FileFactory.create_pdf_like_file(
            filename="test_document.pdf",
            content="This is test PDF content for upload testing."
        )
        
        response_data = await self.perform_upload(
            async_client,
            file_content=test_file.content,
            filename=test_file.filename,
            content_type=test_file.mime_type
        )
        
        # Validate PDF-specific response
        assert response_data["mime_type"] == "application/pdf"
        assert response_data["size"] == len(test_file.content)
        assert_valid_file_id(response_data["file_id"])
    
    @pytest.mark.asyncio
    async def test_upload_empty_file(self, async_client: AsyncClient):
        """Test uploading an empty file."""
        response_data = await self.perform_upload(
            async_client,
            file_content=b"",
            filename="empty.txt"
        )
        
        # Empty file should still be processed
        assert_valid_file_id(response_data["file_id"])
        assert response_data["size"] == 0
    
    @pytest.mark.asyncio
    async def test_upload_large_file(self, async_client: AsyncClient):
        """Test uploading a larger file."""
        # Create a larger test file (10KB)
        test_file = FileFactory.create_large_text_file(
            filename="large_test.txt",
            size_kb=10
        )
        
        response_data = await self.perform_upload(
            async_client,
            file_content=test_file.content,
            filename=test_file.filename
        )
        
        # Large file should be processed successfully
        assert_valid_file_id(response_data["file_id"])
        assert response_data["size"] == len(test_file.content)
        assert response_data["size"] >= 10 * 1024  # At least 10KB
    
    def test_upload_with_sync_client(self, sync_client: TestClient):
        """Test uploading with synchronous client (demonstrates both client types)."""
        import json
        test_content = "Test content for sync client upload."
        
        # Perform direct sync upload since perform_upload is async
        form_data = {
            "tags": json.dumps([]),
            "metadata": json.dumps({}),
        }
        files = {"file": ("sync_test.txt", test_content.encode(), "text/plain")}
        
        response = sync_client.post("/api/upload", data=form_data, files=files)
        
        # Use assertion helper to validate response
        from ..utils.assertions import assert_upload_response
        response_data = assert_upload_response(response)
        
        # Extract and validate file ID using helper
        file_id = extract_file_id(response_data)
        assert file_id is not None
        assert_valid_file_id(file_id)
        assert_valid_hash(response_data["hash"])
    
    @pytest.mark.asyncio
    async def test_upload_and_extract_file_id(self, async_client: AsyncClient):
        """Test upload and demonstrate file ID extraction for workflow testing."""
        response_data = await self.perform_upload(
            async_client,
            file_content=b"Test content for ID extraction",
            filename="id_extract_test.txt",
            tags=["test", "workflow"],
            metadata={"purpose": "demonstrate_id_extraction"}
        )
        
        # Extract file ID for use in subsequent operations
        file_id = extract_file_id(response_data)
        assert file_id is not None
        assert_valid_file_id(file_id)
        
        # File ID should be usable for other operations
        # (In integration tests, this would be passed to search/query operations)
        assert len(file_id) > 0
        assert isinstance(file_id, str)


class TestIngestRoutes(BaseUploadTest):
    """Test ingest routes."""
    
    @pytest.mark.asyncio
    async def test_ingest_from_file_path(self, async_client: AsyncClient):
        """Test ingesting a file from a file path."""
        # Create temporary file
        test_file = FileFactory.create_text_file(
            content="This is a test file for ingest testing.",
            filename="ingest_test.txt"
        )
        temp_path, _ = TempFileFactory.create_test_text_file(
            content="This is a test file for ingest testing.",
            filename="ingest_test.txt"
        )
        
        try:
            response_data = await self.perform_ingest(
                async_client,
                file_path=str(temp_path)
            )
            
            # Validate ingest response
            assert "file_id" in response_data
            assert "status" in response_data
            assert_valid_file_id(response_data["file_id"])
            assert response_data["status"] in ["completed", "processing", "ready"]
        
        finally:
            # Cleanup temp file
            if temp_path.exists():
                temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_ingest_with_metadata(self, async_client: AsyncClient):
        """Test ingesting with custom metadata."""
        # Create temporary file
        temp_path, _ = TempFileFactory.create_test_text_file(
            content="Test file with metadata for ingest.",
            filename="metadata_ingest.txt"
        )
        
        test_metadata = {
            "source": "test_ingest",
            "category": "test_document"
        }
        
        try:
            response_data = await self.perform_ingest(
                async_client,
                file_path=str(temp_path),
                metadata=test_metadata
            )
            
            assert_valid_file_id(response_data["file_id"])
            assert response_data["status"] in ["completed", "processing", "ready"]
        
        finally:
            if temp_path.exists():
                temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_ingest_nonexistent_file(self, async_client: AsyncClient):
        """Test ingesting a nonexistent file should return error."""
        from ..utils.assertions import assert_error_response
        
        payload = RequestFactory.create_ingest_request(
            path="/nonexistent/file/path.txt"
        )
        
        response = await async_client.post("/api/ingest", json=payload)
        
        # Should return error for nonexistent file
        assert_error_response(
            response,
            expected_status=500,  # Tool execution error
            expected_detail_contains="not found"
        )


class TestBulkIngestRoutes(BaseUploadTest):
    """Test bulk ingest routes."""
    
    @pytest.mark.asyncio
    async def test_bulk_ingest_multiple_files(self, async_client: AsyncClient):
        """Test bulk ingesting multiple files."""
        # Create multiple temporary files
        test_files = [
            FileFactory.create_text_file(
                content=f"Content of bulk test file {i+1}",
                filename=f"bulk_test_{i+1}.txt"
            )
            for i in range(3)
        ]
        
        temp_paths = []
        try:
            # Create temporary files
            for test_file in test_files:
                temp_path = TempFileFactory.create_temp_file(test_file)
                temp_paths.append(str(temp_path))
            
            response_data = await self.perform_bulk_ingest(
                async_client,
                file_paths=temp_paths,
                folder_path="/tmp/bulk_test"
            )
            
            # Validate bulk ingest response
            assert response_data["success"] is True
            assert response_data["total_files"] == 3
            assert "successful_count" in response_data
            assert "failed_count" in response_data
            assert "results" in response_data
            assert len(response_data["results"]) == 3
            
            # Check individual results
            for result in response_data["results"]:
                assert "file_path" in result
                assert "success" in result
                if result["success"]:
                    assert "file_id" in result
                    assert_valid_file_id(result["file_id"])
        
        finally:
            # Cleanup temp files
            for temp_path in temp_paths:
                path = Path(temp_path)
                if path.exists():
                    path.unlink()
    
    @pytest.mark.asyncio
    async def test_bulk_ingest_empty_list(self, async_client: AsyncClient):
        """Test bulk ingest with empty file list should return error."""
        from ..utils.assertions import assert_error_response
        
        payload = RequestFactory.create_bulk_ingest_request(file_paths=[])
        
        response = await async_client.post("/api/bulk-ingest", json=payload)
        
        # Should return error for empty file list
        assert_error_response(
            response,
            expected_status=400,
            expected_detail_contains="No file paths provided"
        )


class TestUploadProgress(BaseUploadTest):
    """Test upload progress tracking."""
    
    @pytest.mark.asyncio
    async def test_get_upload_progress_nonexistent(self, async_client: AsyncClient):
        """Test getting progress for nonexistent upload."""
        from ..utils.assertions import assert_error_response
        
        fake_file_id = "nonexistent_file_123"
        response = await async_client.get(f"/api/upload/{fake_file_id}/progress")
        
        # Should return 404 for nonexistent progress
        assert_error_response(
            response,
            expected_status=404,
            expected_detail_contains="Progress not found"
        )


class TestUploadParameterized(ParameterizedRouteTest):
    """Parameterized tests for upload routes."""
    
    @pytest.mark.parametrize("file_size", [0, 1, 1024, 10240])  # 0B, 1B, 1KB, 10KB
    @pytest.mark.asyncio
    async def test_upload_various_sizes(self, async_client: AsyncClient, file_size: int):
        """Test uploading files of various sizes."""
        # Create content of specified size
        content = b"x" * file_size
        
        response = await async_client.post(
            "/api/upload",
            files={"file": ("test.txt", content, "text/plain")},
            data={"tags": "[]", "metadata": "{}"}
        )
        
        data = await self.assert_successful_response(response)
        assert data["size"] == file_size
        assert_valid_file_id(data["file_id"])
    
    @pytest.mark.parametrize("mime_type,extension", [
        ("text/plain", "txt"),
        ("application/pdf", "pdf"),
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
    ])
    @pytest.mark.asyncio
    async def test_upload_various_mime_types(
        self,
        async_client: AsyncClient,
        mime_type: str,
        extension: str
    ):
        """Test uploading files with various MIME types."""
        filename = f"test.{extension}"
        
        # Create proper mock content for each file type
        if extension == "txt":
            content = b"Test content for text file"
        elif extension == "pdf":
            # Create a minimal PDF with proper header
            content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Test PDF content) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000110 00000 n 
0000000181 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
275
%%EOF"""
        elif extension == "docx":
            # Create a minimal DOCX file (ZIP with XML content)
            import zipfile
            import io
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add minimal required DOCX files
                zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')
                
                zip_file.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')
                
                zip_file.writestr('word/document.xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p>
<w:r>
<w:t>Test DOCX content</w:t>
</w:r>
</w:p>
</w:body>
</w:document>''')
                
            content = zip_buffer.getvalue()
        else:
            content = b"Default test content"
        
        response = await async_client.post(
            "/api/upload",
            files={"file": (filename, content, mime_type)},
            data={"tags": "[]", "metadata": "{}"}
        )
        
        data = await self.assert_successful_response(response)
        assert data["mime_type"] == mime_type
        assert_valid_file_id(data["file_id"])