import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib

from lifearchivist.tools.file_import.file_import_tool import FileImportTool
from lifearchivist.tools.file_import.file_import_utils import (
    is_text_extraction_supported,
    should_extract_dates,
    should_extract_embeddings,
    create_document_metadata,
    create_provenance_entry,
    create_duplicate_response,
    create_success_response,
    create_error_response,
    calculate_file_hash,
)
from lifearchivist.server.progress_manager import ProcessingStage
from tests.factories.file.file_factory import FileFactory


class TestFileImportToolMetadata:
    
    def test_metadata_structure(self):
        tool = FileImportTool()
        metadata = tool._get_metadata()
        
        assert metadata.name == "file.import"
        assert metadata.async_tool is True
        assert metadata.idempotent is True
        assert "path" in metadata.input_schema["required"]
        assert "mime_hint" in metadata.input_schema["properties"]
        assert "tags" in metadata.input_schema["properties"]
        assert "metadata" in metadata.input_schema["properties"]
        assert "session_id" in metadata.input_schema["properties"]


class TestFileImportToolExecute:
    
    @pytest.fixture
    def mock_vault(self):
        vault = MagicMock()
        vault.store_file = AsyncMock(return_value={"existed": False, "path": "/vault/path"})
        return vault
    
    @pytest.fixture
    def mock_llamaindex_service(self):
        service = MagicMock()
        service.query_documents_by_metadata = AsyncMock(return_value=[])
        service.add_document = AsyncMock(return_value=True)
        service.update_document_metadata = AsyncMock(return_value=True)
        return service
    
    @pytest.fixture
    def mock_progress_manager(self):
        manager = MagicMock()
        manager.start_progress = AsyncMock()
        manager.complete_progress = AsyncMock()
        manager.error_progress = AsyncMock()
        manager.cleanup_progress = AsyncMock()
        return manager
    
    @pytest.fixture
    def file_import_tool(self, mock_vault, mock_llamaindex_service, mock_progress_manager):
        return FileImportTool(
            vault=mock_vault,
            llamaindex_service=mock_llamaindex_service,
            progress_manager=mock_progress_manager
        )
    
    @pytest.fixture
    def temp_test_file(self, tmp_path):
        test_file = FileFactory.create_text_file(content="Test content for import")
        file_path = tmp_path / test_file.filename
        file_path.write_bytes(test_file.content)
        return file_path, test_file
    
    @pytest.mark.asyncio
    async def test_execute_missing_path(self, file_import_tool):
        with pytest.raises(ValueError, match="File path is required"):
            await file_import_tool.execute()
    
    @pytest.mark.asyncio
    async def test_execute_file_not_found(self, file_import_tool):
        with pytest.raises(FileNotFoundError, match="File not found"):
            await file_import_tool.execute(path="/nonexistent/file.txt")
    
    @pytest.mark.asyncio
    async def test_execute_missing_dependencies(self, temp_test_file):
        file_path, _ = temp_test_file
        tool = FileImportTool()
        
        with pytest.raises(RuntimeError, match="Vault and LlamaIndex service dependencies not provided"):
            await tool.execute(path=str(file_path))
    
    @pytest.mark.asyncio
    async def test_execute_successful_import(
        self, file_import_tool, temp_test_file, mock_vault, mock_llamaindex_service
    ):
        file_path, test_file = temp_test_file
        
        with patch('lifearchivist.tools.file_import.file_import_tool.magic') as mock_magic:
            mock_magic.from_file.return_value = "text/plain"
            
            result = await file_import_tool.execute(
                path=str(file_path),
                tags=["test", "import"],
                metadata={"custom_field": "value"}
            )
        
        assert result["success"] is True
        assert result["status"] == "ready"
        assert result["mime_type"] == "text/plain"
        assert result["size"] == len(test_file.content)
        assert "file_id" in result
        assert "hash" in result
        
        mock_vault.store_file.assert_called_once()
        mock_llamaindex_service.add_document.assert_called_once()
        mock_llamaindex_service.update_document_metadata.assert_called()
    
    @pytest.mark.asyncio
    async def test_execute_with_mime_hint(
        self, file_import_tool, temp_test_file, mock_vault
    ):
        file_path, _ = temp_test_file
        
        result = await file_import_tool.execute(
            path=str(file_path),
            mime_hint="application/custom"
        )
        
        assert result["mime_type"] == "application/custom"
    
    @pytest.mark.asyncio
    async def test_execute_with_session_id(
        self, file_import_tool, temp_test_file, mock_progress_manager
    ):
        file_path, _ = temp_test_file
        session_id = "test-session-123"
        
        result = await file_import_tool.execute(
            path=str(file_path),
            session_id=session_id
        )
        
        assert result["success"] is True
        mock_progress_manager.start_progress.assert_called_once()
        mock_progress_manager.complete_progress.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_duplicate_detection(
        self, file_import_tool, temp_test_file, mock_vault, mock_llamaindex_service
    ):
        file_path, test_file = temp_test_file
        
        mock_vault.store_file.return_value = {"existed": True, "path": "/vault/existing"}
        mock_llamaindex_service.query_documents_by_metadata.return_value = [{
            "document_id": "existing-doc-id",
            "metadata": {"original_path": "existing.txt"}
        }]
        
        result = await file_import_tool.execute(path=str(file_path))
        
        assert result["status"] == "duplicate"
        assert result["deduped"] is True
        assert "existing.txt" in result["message"]
        mock_llamaindex_service.add_document.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_with_original_filename(
        self, file_import_tool, temp_test_file
    ):
        file_path, _ = temp_test_file
        original_filename = "user_uploaded_file.txt"
        
        result = await file_import_tool.execute(
            path=str(file_path),
            metadata={"original_filename": original_filename}
        )
        
        assert result["success"] is True
        assert result["original_path"] == original_filename
    
    @pytest.mark.asyncio
    async def test_execute_error_handling(
        self, file_import_tool, temp_test_file, mock_vault
    ):
        file_path, _ = temp_test_file
        mock_vault.store_file.side_effect = RuntimeError("Vault storage failed")
        
        result = await file_import_tool.execute(path=str(file_path))
        
        assert result["success"] is False
        assert "Vault storage failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_llamaindex_add_failure(
        self, file_import_tool, temp_test_file, mock_llamaindex_service
    ):
        file_path, _ = temp_test_file
        mock_llamaindex_service.add_document.return_value = False
        
        result = await file_import_tool.execute(path=str(file_path))
        
        assert result["success"] is False
        assert "Failed to create document" in result["error"]


class TestFileAnalysis:
    
    @pytest.fixture
    def file_import_tool(self):
        return FileImportTool()
    
    @pytest.mark.asyncio
    async def test_analyze_file(self, file_import_tool, tmp_path):
        test_content = b"Test file content"
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(test_content)
        
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        result = await file_import_tool._analyze_file(test_file, "test.txt")
        
        assert result == expected_hash


class TestDuplicateDetection:
    
    @pytest.fixture
    def mock_llamaindex_service(self):
        service = MagicMock()
        service.query_documents_by_metadata = AsyncMock()
        return service
    
    @pytest.fixture
    def file_import_tool(self, mock_llamaindex_service):
        return FileImportTool(llamaindex_service=mock_llamaindex_service)
    
    @pytest.mark.asyncio
    async def test_check_for_duplicate_found(
        self, file_import_tool, mock_llamaindex_service
    ):
        existing_doc = {
            "document_id": "existing-id",
            "metadata": {"original_path": "existing.txt"}
        }
        mock_llamaindex_service.query_documents_by_metadata.return_value = [existing_doc]
        
        result = await file_import_tool._check_for_duplicate("file-id", "hash123")
        
        assert result == existing_doc
        mock_llamaindex_service.query_documents_by_metadata.assert_called_once_with(
            filters={"file_hash": "hash123"},
            limit=1
        )
    
    @pytest.mark.asyncio
    async def test_check_for_duplicate_not_found(
        self, file_import_tool, mock_llamaindex_service
    ):
        mock_llamaindex_service.query_documents_by_metadata.return_value = []
        
        result = await file_import_tool._check_for_duplicate("file-id", "hash123")
        
        assert result is None


class TestDocumentCreation:
    
    @pytest.fixture
    def mock_llamaindex_service(self):
        service = MagicMock()
        service.add_document = AsyncMock()
        return service
    
    @pytest.fixture
    def file_import_tool(self, mock_llamaindex_service):
        return FileImportTool(llamaindex_service=mock_llamaindex_service)
    
    @pytest.mark.asyncio
    async def test_create_document_success(
        self, file_import_tool, mock_llamaindex_service
    ):
        mock_llamaindex_service.add_document.return_value = True
        
        await file_import_tool._create_document(
            "file-id",
            "extracted text",
            {"metadata": "value"}
        )
        
        mock_llamaindex_service.add_document.assert_called_once_with(
            document_id="file-id",
            content="extracted text",
            metadata={"metadata": "value"}
        )
    
    @pytest.mark.asyncio
    async def test_create_document_failure(
        self, file_import_tool, mock_llamaindex_service
    ):
        mock_llamaindex_service.add_document.return_value = False
        
        with pytest.raises(RuntimeError, match="Failed to create document"):
            await file_import_tool._create_document(
                "file-id",
                "extracted text",
                {"metadata": "value"}
            )


class TestDocumentFinalization:
    
    @pytest.fixture
    def mock_llamaindex_service(self):
        service = MagicMock()
        service.update_document_metadata = AsyncMock()
        return service
    
    @pytest.fixture
    def file_import_tool(self, mock_llamaindex_service):
        return FileImportTool(llamaindex_service=mock_llamaindex_service)
    
    @pytest.mark.asyncio
    async def test_finalize_document(
        self, file_import_tool, mock_llamaindex_service, tmp_path
    ):
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        vault_result = {"path": "/vault/path", "existed": False}
        
        await file_import_tool._finalize_document("file-id", test_file, vault_result)
        
        calls = mock_llamaindex_service.update_document_metadata.call_args_list
        assert len(calls) == 2
        
        assert calls[0][0][0] == "file-id"
        assert calls[0][0][1]["status"] == "ready"
        
        assert calls[1][0][0] == "file-id"
        assert "provenance" in calls[1][0][1]


class TestErrorHandling:
    
    @pytest.fixture
    def mock_llamaindex_service(self):
        service = MagicMock()
        service.update_document_metadata = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_progress_manager(self):
        manager = MagicMock()
        manager.error_progress = AsyncMock()
        return manager
    
    @pytest.fixture
    def file_import_tool(self, mock_llamaindex_service, mock_progress_manager):
        return FileImportTool(
            llamaindex_service=mock_llamaindex_service,
            progress_manager=mock_progress_manager
        )
    
    @pytest.mark.asyncio
    async def test_handle_import_error(
        self, file_import_tool, mock_progress_manager, mock_llamaindex_service
    ):
        error = RuntimeError("Test error")
        
        await file_import_tool._handle_import_error(
            error, "file-id", "test.txt", "session-id"
        )
        
        mock_progress_manager.error_progress.assert_called_once_with(
            "file-id", "Test error", ProcessingStage.UPLOAD
        )
        
        mock_llamaindex_service.update_document_metadata.assert_called_once_with(
            "file-id",
            {"status": "failed", "error_message": "Test error"},
            merge_mode="update"
        )
    
    @pytest.mark.asyncio
    async def test_handle_import_error_with_cleanup_failure(
        self, file_import_tool, mock_progress_manager
    ):
        error = RuntimeError("Test error")
        mock_progress_manager.error_progress.side_effect = Exception("Cleanup failed")
        
        await file_import_tool._handle_import_error(
            error, "file-id", "test.txt", "session-id"
        )


class TestTextExtraction:
    
    @pytest.fixture
    def mock_vault(self):
        return MagicMock()
    
    @pytest.fixture
    def file_import_tool(self, mock_vault):
        return FileImportTool(vault=mock_vault)
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("mime_type,should_extract", [
        ("text/plain", True),
        ("text/html", True),
        ("application/pdf", True),
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", True),
        ("image/jpeg", False),
        ("video/mp4", False),
        ("application/octet-stream", False),
    ])
    async def test_try_extract_text_mime_types(
        self, file_import_tool, tmp_path, mime_type, should_extract
    ):
        test_file = tmp_path / "test.file"
        test_file.write_text("content")
        
        with patch('lifearchivist.tools.extract.extract_tool.ExtractTextTool') as MockExtractTool:
            mock_instance = MockExtractTool.return_value
            mock_instance.execute = AsyncMock(return_value={"text": "extracted text"})
            
            result = await file_import_tool._try_extract_text(
                "file-id", test_file, mime_type, "hash123"
            )
            
            if should_extract:
                assert result == "extracted text"
                MockExtractTool.assert_called_once()
            else:
                assert result == ""
                MockExtractTool.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_try_extract_text_empty_result(
        self, file_import_tool, tmp_path
    ):
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        with patch('lifearchivist.tools.extract.extract_tool.ExtractTextTool') as MockExtractTool:
            mock_instance = MockExtractTool.return_value
            mock_instance.execute = AsyncMock(return_value={"text": ""})
            
            with patch('lifearchivist.tools.file_import.file_import_tool.log_event') as mock_log:
                result = await file_import_tool._try_extract_text(
                    "file-id", test_file, "text/plain", "hash123"
                )
                
                assert result == ""
                warning_logged = any(
                    call[0][0] == "text_extraction_empty"
                    for call in mock_log.call_args_list
                )
                assert warning_logged
    
    def test_get_extraction_method(self, file_import_tool):
        assert file_import_tool._get_extraction_method("text/plain") == "text_file"
        assert file_import_tool._get_extraction_method("application/pdf") == "pypdf"
        assert file_import_tool._get_extraction_method(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ) == "python_docx"
        assert file_import_tool._get_extraction_method("image/jpeg") == "unknown"


class TestContentDateExtraction:
    
    @pytest.fixture
    def mock_llamaindex_service(self):
        return MagicMock()
    
    @pytest.fixture
    def file_import_tool(self, mock_llamaindex_service):
        return FileImportTool(llamaindex_service=mock_llamaindex_service)
    
    @pytest.mark.asyncio
    async def test_try_extract_content_dates_sufficient_text(
        self, file_import_tool
    ):
        text = "This document was created on January 15, 2024. " * 5
        
        with patch('lifearchivist.tools.date_extract.date_extraction_tool.ContentDateExtractionTool') as MockDateTool:
            mock_instance = MockDateTool.return_value
            mock_instance.execute = AsyncMock(return_value={"dates": ["2024-01-15"]})
            
            result = await file_import_tool._try_extract_content_dates("file-id", text)
            
            assert result == {"dates": ["2024-01-15"]}
            MockDateTool.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_try_extract_content_dates_insufficient_text(
        self, file_import_tool
    ):
        text = "Short"
        
        with patch('lifearchivist.tools.date_extract.date_extraction_tool.ContentDateExtractionTool') as MockDateTool:
            result = await file_import_tool._try_extract_content_dates("file-id", text)
            
            assert result is None
            MockDateTool.assert_not_called()


class TestFileImportUtils:
    
    def test_is_text_extraction_supported(self):
        assert is_text_extraction_supported("text/plain") is True
        assert is_text_extraction_supported("text/html") is True
        assert is_text_extraction_supported("application/pdf") is True
        assert is_text_extraction_supported("image/jpeg") is False
        assert is_text_extraction_supported("video/mp4") is False
    
    def test_should_extract_embeddings(self):
        assert should_extract_embeddings("a" * 100) is True
        assert should_extract_embeddings("a" * 99) is False
        assert should_extract_embeddings("") is False
        assert should_extract_embeddings("   ") is False
    
    def test_should_extract_dates(self):
        assert should_extract_dates("a" * 50) is True
        assert should_extract_dates("a" * 49) is False
        assert should_extract_dates("") is False
    
    @pytest.mark.asyncio
    async def test_calculate_file_hash(self, tmp_path):
        test_content = b"Test content for hashing"
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(test_content)
        
        expected_hash = hashlib.sha256(test_content).hexdigest()
        result = await calculate_file_hash(test_file)
        
        assert result == expected_hash
    
    def test_create_document_metadata(self):
        stat = MagicMock()
        stat.st_size = 1024
        stat.st_ctime = 1704067200
        stat.st_mtime = 1704067200
        
        metadata = create_document_metadata(
            file_id="file-123",
            file_hash="hash123",
            original_path="/path/to/file.txt",
            mime_type="text/plain",
            stat=stat,
            text="Sample text",
            custom_metadata={"custom": "value"}
        )
        
        assert metadata["document_id"] == "file-123"
        assert metadata["file_hash"] == "hash123"
        assert metadata["title"] == "file.txt"
        assert metadata["mime_type"] == "text/plain"
        assert metadata["size_bytes"] == 1024
        assert metadata["word_count"] == 2
        assert metadata["has_content"] is True
        assert metadata["custom"] == "value"
        assert "provenance" in metadata
    
    def test_create_provenance_entry(self):
        entry = create_provenance_entry(
            action="import",
            agent="test_agent",
            tool="test.tool",
            params={"param": "value"},
            result={"result": "value"}
        )
        
        assert entry["action"] == "import"
        assert entry["agent"] == "test_agent"
        assert entry["tool"] == "test.tool"
        assert entry["params"] == {"param": "value"}
        assert entry["result"] == {"result": "value"}
        assert "timestamp" in entry
    
    def test_create_duplicate_response(self):
        existing_doc = {
            "document_id": "existing-id",
            "metadata": {"original_path": "existing.txt"}
        }
        stat = MagicMock()
        stat.st_size = 1024
        
        response = create_duplicate_response(
            existing_doc, "hash123", stat, "text/plain", "new.txt"
        )
        
        assert response["success"] is True
        assert response["status"] == "duplicate"
        assert response["deduped"] is True
        assert response["file_id"] == "existing-id"
        assert "existing.txt" in response["message"]
    
    def test_create_success_response(self):
        stat = MagicMock()
        stat.st_size = 1024
        stat.st_ctime = 1704067200
        stat.st_mtime = 1704067200
        vault_result = {"path": "/vault/path", "existed": False}
        
        response = create_success_response(
            "file-id", "hash123", stat, "text/plain", "file.txt", vault_result
        )
        
        assert response["success"] is True
        assert response["status"] == "ready"
        assert response["file_id"] == "file-id"
        assert response["vault_path"] == "/vault/path"
        assert response["deduped"] is False
    
    def test_create_error_response(self):
        error = RuntimeError("Test error")
        
        response = create_error_response(error, "file.txt")
        
        assert response["success"] is False
        assert response["error"] == "Test error"
        assert response["original_path"] == "file.txt"


class TestIntegrationScenarios:
    
    @pytest.fixture
    def full_mock_setup(self):
        vault = MagicMock()
        vault.store_file = AsyncMock(return_value={"existed": False, "path": "/vault/path"})
        
        llamaindex = MagicMock()
        llamaindex.query_documents_by_metadata = AsyncMock(return_value=[])
        llamaindex.add_document = AsyncMock(return_value=True)
        llamaindex.update_document_metadata = AsyncMock(return_value=True)
        
        progress = MagicMock()
        progress.start_progress = AsyncMock()
        progress.complete_progress = AsyncMock()
        progress.error_progress = AsyncMock()
        progress.cleanup_progress = AsyncMock()
        
        return vault, llamaindex, progress
    
    @pytest.mark.asyncio
    async def test_full_import_pipeline_with_text_extraction(
        self, full_mock_setup, tmp_path
    ):
        vault, llamaindex, progress = full_mock_setup
        tool = FileImportTool(vault=vault, llamaindex_service=llamaindex, progress_manager=progress)
        
        test_file = tmp_path / "document.txt"
        test_file.write_text("This is a test document created on January 15, 2024.")
        
        with patch('lifearchivist.tools.extract.extract_tool.ExtractTextTool') as MockExtract:
            mock_extract = MockExtract.return_value
            mock_extract.execute = AsyncMock(return_value={"text": test_file.read_text()})
            
            with patch('lifearchivist.tools.date_extract.date_extraction_tool.ContentDateExtractionTool') as MockDate:
                mock_date = MockDate.return_value
                mock_date.execute = AsyncMock(return_value={"dates": ["2024-01-15"]})
                
                result = await tool.execute(
                    path=str(test_file),
                    tags=["test", "document"],
                    session_id="session-123"
                )
        
        assert result["success"] is True
        assert result["status"] == "ready"
        
        vault.store_file.assert_called_once()
        llamaindex.add_document.assert_called_once()
        progress.start_progress.assert_called_once()
        progress.complete_progress.assert_called_once()
        MockExtract.assert_called_once()
        MockDate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_import_with_duplicate_handling(
        self, full_mock_setup, tmp_path
    ):
        vault, llamaindex, progress = full_mock_setup
        vault.store_file.return_value = {"existed": True, "path": "/vault/existing"}
        llamaindex.query_documents_by_metadata.return_value = [{
            "document_id": "existing-id",
            "metadata": {"original_path": "original.txt"}
        }]
        
        tool = FileImportTool(vault=vault, llamaindex_service=llamaindex, progress_manager=progress)
        
        test_file = tmp_path / "duplicate.txt"
        test_file.write_text("Duplicate content")
        
        result = await tool.execute(
            path=str(test_file),
            session_id="session-123"
        )
        
        assert result["status"] == "duplicate"
        assert result["deduped"] is True
        
        llamaindex.add_document.assert_not_called()
        progress.cleanup_progress.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_import_pdf_file(
        self, full_mock_setup, tmp_path
    ):
        vault, llamaindex, progress = full_mock_setup
        tool = FileImportTool(vault=vault, llamaindex_service=llamaindex)
        
        pdf_file = FileFactory.create_pdf_file(content="PDF content for testing")
        file_path = tmp_path / pdf_file.filename
        file_path.write_bytes(pdf_file.content)
        
        with patch('lifearchivist.tools.file_import.file_import_tool.magic') as mock_magic:
            mock_magic.from_file.return_value = "application/pdf"
            
            with patch('lifearchivist.tools.extract.extract_tool.ExtractTextTool') as MockExtract:
                mock_extract = MockExtract.return_value
                mock_extract.execute = AsyncMock(return_value={"text": "Extracted PDF text"})
                
                result = await tool.execute(path=str(file_path))
        
        assert result["success"] is True
        assert result["mime_type"] == "application/pdf"
        MockExtract.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_import_unsupported_file_type(
        self, full_mock_setup, tmp_path
    ):
        vault, llamaindex, progress = full_mock_setup
        tool = FileImportTool(vault=vault, llamaindex_service=llamaindex)
        
        image_file = tmp_path / "image.jpg"
        image_file.write_bytes(b"\xFF\xD8\xFF\xE0")
        
        with patch('lifearchivist.tools.file_import.file_import_tool.magic') as mock_magic:
            mock_magic.from_file.return_value = "image/jpeg"
            
            with patch('lifearchivist.tools.extract.extract_tool.ExtractTextTool') as MockExtract:
                result = await tool.execute(path=str(image_file))
        
        assert result["success"] is True
        assert result["mime_type"] == "image/jpeg"
        MockExtract.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_import_with_custom_file_id(
        self, full_mock_setup, tmp_path
    ):
        vault, llamaindex, progress = full_mock_setup
        tool = FileImportTool(vault=vault, llamaindex_service=llamaindex)
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        custom_file_id = "custom-file-id-123"
        
        result = await tool.execute(
            path=str(test_file),
            metadata={"file_id": custom_file_id}
        )
        
        assert result["file_id"] == custom_file_id
        
        llamaindex.add_document.assert_called_once()
        call_args = llamaindex.add_document.call_args
        assert call_args[1]["document_id"] == custom_file_id