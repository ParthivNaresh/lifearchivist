import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path

from lifearchivist.tools.extract.extract_tool import ExtractTextTool
from lifearchivist.tools.extract.extract_utils import (
    _get_extraction_method,
    _extract_text_by_type,
    extract_table_text,
    extract_paragraph_text,
)


class TestExtractToolMetadata:
    
    def test_metadata_structure(self):
        vault = MagicMock()
        tool = ExtractTextTool(vault)
        metadata = tool._get_metadata()
        
        assert metadata.name == "extract.text"
        assert metadata.async_tool is True
        assert metadata.idempotent is True
        assert "file_id" in metadata.input_schema["required"]
        assert "file_path" in metadata.input_schema["properties"]
        assert "mime_type" in metadata.input_schema["properties"]
        assert "file_hash" in metadata.input_schema["properties"]
        assert "text" in metadata.output_schema["properties"]
        assert "metadata" in metadata.output_schema["properties"]


class TestResolveFileInfo:
    
    @pytest.fixture
    def extract_tool(self):
        vault = MagicMock()
        vault.get_file_path = AsyncMock()
        return ExtractTextTool(vault)
    
    @pytest.mark.asyncio
    async def test_resolve_with_file_path_and_mime_type(self, extract_tool, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        file_path, mime_type = await extract_tool._resolve_file_info(
            file_id="test_id",
            file_path=str(test_file),
            mime_type="text/plain",
            file_hash=""
        )
        
        assert file_path == test_file
        assert mime_type == "text/plain"
    
    @pytest.mark.asyncio
    async def test_resolve_with_file_path_detect_mime_type(self, extract_tool, tmp_path):
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf")
        
        file_path, mime_type = await extract_tool._resolve_file_info(
            file_id="test_id",
            file_path=str(test_file),
            mime_type="",
            file_hash=""
        )
        
        assert file_path == test_file
        assert mime_type == "application/pdf"
    
    @pytest.mark.asyncio
    async def test_resolve_with_file_path_unknown_extension(self, extract_tool, tmp_path):
        test_file = tmp_path / "test.unknownext"
        test_file.write_text("content")
        
        with pytest.raises(ValueError, match="Could not detect MIME type"):
            await extract_tool._resolve_file_info(
                file_id="test_id",
                file_path=str(test_file),
                mime_type="",
                file_hash=""
            )
    
    @pytest.mark.asyncio
    async def test_resolve_with_hash_and_mime_type(self, extract_tool, tmp_path):
        test_file = tmp_path / "abc123.txt"
        test_file.write_text("content")
        extract_tool.vault.get_file_path.return_value = test_file
        
        file_path, mime_type = await extract_tool._resolve_file_info(
            file_id="test_id",
            file_path="",
            mime_type="text/plain",
            file_hash="abc123"
        )
        
        assert file_path == test_file
        assert mime_type == "text/plain"
        extract_tool.vault.get_file_path.assert_called_once_with("abc123", "txt")
    
    @pytest.mark.asyncio
    async def test_resolve_missing_required_params(self, extract_tool):
        with pytest.raises(ValueError, match="Either file_path or both file_hash and mime_type"):
            await extract_tool._resolve_file_info(
                file_id="test_id",
                file_path="",
                mime_type="",
                file_hash="abc123"
            )
    
    @pytest.mark.asyncio
    async def test_resolve_file_not_found(self, extract_tool):
        extract_tool.vault.get_file_path.return_value = None
        
        with pytest.raises(ValueError, match="File not found"):
            await extract_tool._resolve_file_info(
                file_id="test_id",
                file_path="",
                mime_type="text/plain",
                file_hash="abc123"
            )
    
    @pytest.mark.asyncio
    async def test_resolve_unknown_mime_type_extension(self, extract_tool):
        with pytest.raises(ValueError, match="Could not determine extension"):
            await extract_tool._resolve_file_info(
                file_id="test_id",
                file_path="",
                mime_type="application/unknown",
                file_hash="abc123"
            )


class TestExtractToolExecute:
    
    @pytest.fixture
    def extract_tool(self):
        vault = MagicMock()
        vault.get_file_path = AsyncMock()
        return ExtractTextTool(vault)
    
    @pytest.mark.asyncio
    async def test_execute_missing_file_id(self, extract_tool):
        with pytest.raises(ValueError, match="File ID is required"):
            await extract_tool.execute()
    
    @pytest.mark.asyncio
    async def test_execute_text_file_success(self, extract_tool, tmp_path):
        test_file = tmp_path / "test.txt"
        test_content = "This is test content\nWith multiple lines"
        test_file.write_text(test_content)
        
        with patch('lifearchivist.tools.extract.extract_tool._extract_text_by_type', 
                   AsyncMock(return_value=test_content)):
            result = await extract_tool.execute(
                file_id="test_id",
                file_path=str(test_file),
                mime_type="text/plain"
            )
        
        assert result["text"] == test_content
        assert result["metadata"]["word_count"] == 7
        assert result["metadata"]["char_count"] == len(test_content)
        assert result["metadata"]["extraction_method"] == "text_file"
        assert result["metadata"]["mime_type"] == "text/plain"
    
    @pytest.mark.asyncio
    async def test_execute_pdf_file_success(self, extract_tool, tmp_path):
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf")
        test_content = "Extracted PDF content"
        
        with patch('lifearchivist.tools.extract.extract_tool._extract_text_by_type',
                   AsyncMock(return_value=test_content)):
            result = await extract_tool.execute(
                file_id="test_id",
                file_path=str(test_file),
                mime_type="application/pdf"
            )
        
        assert result["text"] == test_content
        assert result["metadata"]["extraction_method"] == "pypdf"
    
    @pytest.mark.asyncio
    async def test_execute_docx_file_success(self, extract_tool, tmp_path):
        test_file = tmp_path / "test.docx"
        test_file.write_bytes(b"fake docx")
        test_content = "Extracted Word content"
        
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        with patch('lifearchivist.tools.extract.extract_tool._extract_text_by_type',
                   AsyncMock(return_value=test_content)):
            result = await extract_tool.execute(
                file_id="test_id",
                file_path=str(test_file),
                mime_type=mime_type
            )
        
        assert result["text"] == test_content
        assert result["metadata"]["extraction_method"] == "python_docx"
    
    @pytest.mark.asyncio
    async def test_execute_unsupported_mime_type(self, extract_tool, tmp_path):
        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"fake video")
        
        with pytest.raises(ValueError, match="Text extraction not supported"):
            await extract_tool.execute(
                file_id="test_id",
                file_path=str(test_file),
                mime_type="video/mp4"
            )
    
    @pytest.mark.asyncio
    async def test_execute_empty_text_extraction(self, extract_tool, tmp_path):
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")
        
        with patch('lifearchivist.tools.extract.extract_tool._extract_text_by_type',
                   AsyncMock(return_value="")):
            result = await extract_tool.execute(
                file_id="test_id",
                file_path=str(test_file),
                mime_type="text/plain"
            )
        
        assert result["text"] == ""
        assert result["metadata"]["word_count"] == 0
        assert result["metadata"]["char_count"] == 0
    
    @pytest.mark.asyncio
    async def test_execute_extraction_error(self, extract_tool, tmp_path):
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf")
        
        with patch('lifearchivist.tools.extract.extract_tool._extract_text_by_type',
                   AsyncMock(side_effect=ValueError("Extraction failed"))):
            with pytest.raises(ValueError, match="Extraction failed"):
                await extract_tool.execute(
                    file_id="test_id",
                    file_path=str(test_file),
                    mime_type="application/pdf"
                )


class TestExtractionMethods:
    
    @pytest.mark.parametrize("mime_type,expected_method", [
        ("text/plain", "text_file"),
        ("text/html", "text_file"),
        ("text/csv", "text_file"),
        ("application/pdf", "pypdf"),
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "python_docx"),
    ])
    def test_get_extraction_method_supported(self, mime_type, expected_method):
        method = _get_extraction_method(mime_type)
        assert method == expected_method
    
    @pytest.mark.parametrize("mime_type", [
        "image/jpeg",
        "video/mp4",
        "audio/mpeg",
        "application/octet-stream",
    ])
    def test_get_extraction_method_unsupported(self, mime_type):
        with pytest.raises(ValueError, match="Mime type not supported"):
            _get_extraction_method(mime_type)


class TestTextFileExtraction:
    
    @pytest.mark.asyncio
    async def test_extract_text_file_utf8(self, tmp_path):
        test_file = tmp_path / "test.txt"
        content = "UTF-8 content with émojis 🎉"
        test_file.write_text(content, encoding="utf-8")
        
        from lifearchivist.tools.extract.extract_utils import _extract_text_file
        result = await _extract_text_file(test_file)
        assert result == content
    
    @pytest.mark.asyncio
    async def test_extract_text_file_with_errors(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"Valid text \x80\x81 invalid bytes")
        
        from lifearchivist.tools.extract.extract_utils import _extract_text_file
        result = await _extract_text_file(test_file)
        assert "Valid text" in result


class TestPDFExtraction:
    
    @pytest.mark.asyncio
    async def test_extract_pdf_success(self):
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content"
        
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2]
        
        with patch('lifearchivist.tools.extract.extract_utils.PdfReader', return_value=mock_reader):
            with patch('builtins.open', mock_open()):
                from lifearchivist.tools.extract.extract_utils import _extract_pdf_text
                result = await _extract_pdf_text(Path("test.pdf"))
        
        assert result == "Page 1 content\nPage 2 content"
    
    @pytest.mark.asyncio
    async def test_extract_pdf_error(self):
        with patch('lifearchivist.tools.extract.extract_utils.PdfReader', 
                   side_effect=Exception("PDF error")):
            with patch('builtins.open', mock_open()):
                from lifearchivist.tools.extract.extract_utils import _extract_pdf_text
                with pytest.raises(ValueError, match="Error extracting PDF text"):
                    await _extract_pdf_text(Path("test.pdf"))


class TestDocxExtraction:
    
    def test_extract_paragraph_text_plain(self):
        paragraph = MagicMock()
        paragraph.text = "  Plain paragraph text  "
        paragraph.style = None
        
        result = extract_paragraph_text(paragraph)
        assert result == "Plain paragraph text"
    
    def test_extract_paragraph_text_heading(self):
        paragraph = MagicMock()
        paragraph.text = "Important Heading"
        paragraph.style = MagicMock()
        paragraph.style.name = "Heading 1"
        
        result = extract_paragraph_text(paragraph)
        assert result == "[HEADING] Important Heading"
    
    def test_extract_paragraph_text_title(self):
        paragraph = MagicMock()
        paragraph.text = "Document Title"
        paragraph.style = MagicMock()
        paragraph.style.name = "Title"
        
        result = extract_paragraph_text(paragraph)
        assert result == "[TITLE] Document Title"
    
    def test_extract_paragraph_text_empty(self):
        paragraph = MagicMock()
        paragraph.text = "   "
        
        result = extract_paragraph_text(paragraph)
        assert result == ""
    
    def test_extract_table_text(self):
        cell1 = MagicMock()
        cell1.text = "Header 1"
        cell2 = MagicMock()
        cell2.text = "Header 2"
        cell3 = MagicMock()
        cell3.text = "Data 1"
        cell4 = MagicMock()
        cell4.text = "Data 2"
        
        row1 = MagicMock()
        row1.cells = [cell1, cell2]
        row2 = MagicMock()
        row2.cells = [cell3, cell4]
        
        table = MagicMock()
        table.rows = [row1, row2]
        
        result = extract_table_text(table)
        assert result == "Header 1 | Header 2\nData 1 | Data 2"
    
    def test_extract_table_text_empty_cells(self):
        cell1 = MagicMock()
        cell1.text = "Data"
        cell2 = MagicMock()
        cell2.text = "  "
        
        row = MagicMock()
        row.cells = [cell1, cell2]
        
        table = MagicMock()
        table.rows = [row]
        
        result = extract_table_text(table)
        assert result == "Data"
    
    @pytest.mark.asyncio
    async def test_extract_docx_comprehensive(self):
        from docx.oxml.text.paragraph import CT_P
        from docx.oxml.table import CT_Tbl
        
        mock_p1 = MagicMock(spec=CT_P)
        mock_p2 = MagicMock(spec=CT_P)
        mock_tbl = MagicMock(spec=CT_Tbl)
        
        mock_doc = MagicMock()
        mock_doc.element.body = [mock_p1, mock_tbl, mock_p2]
        
        para1 = MagicMock()
        para1.text = "First paragraph"
        para1.style = None
        
        para2 = MagicMock()
        para2.text = "Second paragraph"
        para2.style = None
        
        table_cell = MagicMock()
        table_cell.text = "Table data"
        table_row = MagicMock()
        table_row.cells = [table_cell]
        table = MagicMock()
        table.rows = [table_row]
        
        header_para = MagicMock()
        header_para.text = "Header text"
        header_para.style = None
        
        footer_para = MagicMock()
        footer_para.text = "Footer text"
        footer_para.style = None
        
        section = MagicMock()
        section.header.paragraphs = [header_para]
        section.footer.paragraphs = [footer_para]
        mock_doc.sections = [section]
        
        with patch('lifearchivist.tools.extract.extract_utils.Document', return_value=mock_doc):
            with patch('lifearchivist.tools.extract.extract_utils.Paragraph') as mock_para_class:
                with patch('lifearchivist.tools.extract.extract_utils.Table') as mock_table_class:
                    mock_para_class.side_effect = [para1, para2]
                    mock_table_class.return_value = table
                    
                    from lifearchivist.tools.extract.extract_utils import _extract_docx_text
                    result = await _extract_docx_text(Path("test.docx"))
        
        assert "[HEADER] Header text" in result
        assert "First paragraph" in result
        assert "[TABLE]" in result
        assert "Table data" in result
        assert "Second paragraph" in result
        assert "[FOOTER] Footer text" in result
    
    @pytest.mark.asyncio
    async def test_extract_docx_error(self):
        with patch('lifearchivist.tools.extract.extract_utils.Document',
                   side_effect=Exception("DOCX error")):
            from lifearchivist.tools.extract.extract_utils import _extract_docx_text
            with pytest.raises(ValueError, match="Error extracting Word document"):
                await _extract_docx_text(Path("test.docx"))


class TestExtractTextByType:
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("mime_type,mock_func,expected_result", [
        ("text/plain", "_extract_text_file", "Plain text content"),
        ("text/html", "_extract_text_file", "HTML content"),
        ("application/pdf", "_extract_pdf_text", "PDF content"),
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
         "_extract_docx_text", "DOCX content"),
    ])
    async def test_extract_by_type_routing(self, mime_type, mock_func, expected_result):
        with patch(f'lifearchivist.tools.extract.extract_utils.{mock_func}',
                   AsyncMock(return_value=expected_result)):
            result = await _extract_text_by_type(Path("test"), mime_type)
            assert result == expected_result
    
    @pytest.mark.asyncio
    async def test_extract_by_type_unsupported(self):
        result = await _extract_text_by_type(Path("test"), "image/jpeg")
        assert result == ""
    
    @pytest.mark.asyncio
    async def test_extract_by_type_error_handling(self):
        with patch('lifearchivist.tools.extract.extract_utils._extract_text_file',
                   AsyncMock(side_effect=Exception("Read error"))):
            with pytest.raises(ValueError, match="Error extracting text"):
                await _extract_text_by_type(Path("test"), "text/plain")


class TestIntegrationScenarios:
    
    @pytest.fixture
    def extract_tool_with_vault(self, tmp_path):
        vault = MagicMock()
        vault.get_file_path = AsyncMock()
        
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        
        def mock_get_file_path(file_hash, extension):
            file_path = content_dir / f"{file_hash}.{extension}"
            if file_path.exists():
                return file_path
            return None
        
        vault.get_file_path.side_effect = mock_get_file_path
        return ExtractTextTool(vault), content_dir
    
    @pytest.mark.asyncio
    async def test_full_pipeline_text_file(self, extract_tool_with_vault):
        tool, content_dir = extract_tool_with_vault
        
        test_file = content_dir / "abc123.txt"
        test_content = "Complete pipeline test content"
        test_file.write_text(test_content)
        
        with patch('lifearchivist.tools.extract.extract_tool._extract_text_by_type',
                   AsyncMock(return_value=test_content)):
            result = await tool.execute(
                file_id="test_id",
                file_hash="abc123",
                mime_type="text/plain"
            )
        
        assert result["text"] == test_content
        assert result["metadata"]["word_count"] == 4
        assert result["metadata"]["extraction_method"] == "text_file"
    
    @pytest.mark.asyncio
    async def test_full_pipeline_with_file_path_detection(self, tmp_path):
        vault = MagicMock()
        tool = ExtractTextTool(vault)
        
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"fake pdf")
        test_content = "Extracted PDF text"
        
        with patch('lifearchivist.tools.extract.extract_tool._extract_text_by_type',
                   AsyncMock(return_value=test_content)):
            result = await tool.execute(
                file_id="test_id",
                file_path=str(test_file)
            )
        
        assert result["text"] == test_content
        assert result["metadata"]["mime_type"] == "application/pdf"
        assert result["metadata"]["extraction_method"] == "pypdf"