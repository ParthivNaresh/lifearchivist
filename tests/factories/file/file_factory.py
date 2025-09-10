"""
Enhanced File Factory for Life Archivist Testing

This factory provides comprehensive test file creation capabilities that align with
the project's file-centric architecture, supporting various test scenarios across
unit, integration, and e2e tests.
"""

import hashlib
import math
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

from factories.file.content_generator import ContentGenerator
from factories.file.file_schemas import FileCategory, TestScenario, ContentComplexity


@dataclass
class TestFile:
    """
    Enhanced test file representation with comprehensive metadata.
    Supports all aspects of the Life Archivist file lifecycle.
    """
    filename: str
    content: bytes
    mime_type: str

    size: int = field(init=False)
    hash: str = field(init=False)
    
    category: FileCategory = FileCategory.GENERAL
    complexity: ContentComplexity = ContentComplexity.MODERATE
    scenario: TestScenario = TestScenario.UPLOAD
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Expected processing results (for validation)
    expected_chunks: int = 0
    expected_extraction: Optional[str] = None
    expected_dates: List[str] = field(default_factory=list)
    expected_tags: List[str] = field(default_factory=list)
    
    # Temporary file path
    temp_path: Optional[Path] = None
    test_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def __post_init__(self):
        """Calculate derived fields after initialization."""
        self.size = len(self.content)
        self.hash = hashlib.sha256(self.content).hexdigest()

        if self.expected_chunks == 0 and self.size > 0:
            # Compute expected chunks based on text length and configured chunk size
            # Default to 800 to match current LlamaIndexService configuration
            default_chunk_size = 800
            # Allow override via env var for testing consistency
            try:
                chunk_size = int(os.getenv("TEST_CHUNK_SIZE", default_chunk_size))
            except (TypeError, ValueError):
                chunk_size = default_chunk_size

            # Prefer text length if extraction is possible; fallback to byte length
            if self.expected_extraction is not None:
                text_length = len(self.expected_extraction)
            elif self.mime_type.startswith("text/"):
                try:
                    text_length = len(self.content.decode("utf-8", errors="ignore"))
                except Exception:
                    text_length = self.size
            else:
                text_length = self.size

            self.expected_chunks = max(1, math.ceil(text_length / max(1, chunk_size)))
    
    def to_upload_format(self) -> Tuple[str, bytes, str]:
        """Convert to format needed for file upload in tests."""
        return (self.filename, self.content, self.mime_type)
    
    def to_vault_format(self) -> Dict[str, Any]:
        """Convert to format expected by vault storage."""
        return {
            "file_hash": self.hash,
            "content": self.content,
            "mime_type": self.mime_type,
            "size": self.size,
            "original_path": self.filename
        }
    
    def to_llamaindex_format(self) -> Dict[str, Any]:
        """Convert to format expected by LlamaIndex service."""
        return {
            "document_id": self.test_id,
            "content": self.content.decode('utf-8', errors='ignore'),
            "metadata": {
                **self.metadata,
                "file_hash": self.hash,
                "mime_type": self.mime_type,
                "original_path": self.filename,
                "size_bytes": self.size,
                "category": self.category.value,
                "test_scenario": self.scenario.value
            }
        }


class FileFactory:
    """
    Enhanced factory for creating test files with comprehensive features
    supporting all Life Archivist test scenarios.
    """
    
    @classmethod
    def create_test_file(
        cls,
        filename: Optional[str] = None,
        content: Optional[str] = None,
        mime_type: str = "text/plain",
        category: FileCategory = FileCategory.GENERAL,
        complexity: ContentComplexity = ContentComplexity.MODERATE,
        scenario: TestScenario = TestScenario.UPLOAD,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        word_count: int = 200
    ) -> TestFile:
        """
        Create a comprehensive test file for any scenario.
        
        Args:
            filename: Name of the file (auto-generated if not provided)
            content: File content (auto-generated based on category if not provided)
            mime_type: MIME type of the file
            category: Category for domain-specific content
            complexity: Complexity level of content
            scenario: Test scenario this file is designed for
            metadata: Additional metadata to include
            tags: Tags to associate with the file
            word_count: Target word count for generated content
        
        Returns:
            TestFile object ready for testing
        """
        # Auto-generate filename if not provided
        if filename is None:
            extension = cls._get_extension_for_mime(mime_type)
            filename = f"{category.value}_{scenario.value}_{uuid.uuid4().hex[:8]}.{extension}"
        
        # Auto-generate content if not provided
        if content is None:
            content = ContentGenerator.generate_content(category, complexity, word_count)
        
        # Prepare content bytes
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content
        
        # Build metadata
        file_metadata = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "test_category": category.value,
            "test_scenario": scenario.value,
            "complexity": complexity.value,
            **(metadata or {})
        }
        
        # Auto-generate tags if not provided
        if tags is None:
            tags = cls._generate_tags_for_category(category)
        
        # Calculate expected results
        expected_extraction = content if mime_type.startswith("text/") else None
        expected_dates = cls._extract_dates_from_content(content if isinstance(content, str) else "")
        
        return TestFile(
            filename=filename,
            content=content_bytes,
            mime_type=mime_type,
            category=category,
            complexity=complexity,
            scenario=scenario,
            metadata=file_metadata,
            expected_extraction=expected_extraction,
            expected_dates=expected_dates,
            expected_tags=tags
        )
    
    @classmethod
    def create_text_file(cls, **kwargs) -> TestFile:
        """Create a text file with sensible defaults."""
        kwargs.setdefault('mime_type', 'text/plain')
        kwargs.setdefault('filename', f"test_{uuid.uuid4().hex[:8]}.txt")
        return cls.create_test_file(**kwargs)
    
    @classmethod
    def create_pdf_file(cls, **kwargs) -> TestFile:
        """Create a PDF file for testing (valid minimal PDF)."""
        kwargs.setdefault('mime_type', 'application/pdf')
        kwargs.setdefault('filename', f"test_{uuid.uuid4().hex[:8]}.pdf")

        # Generate a valid minimal PDF with embedded text when content is not provided
        if 'content' not in kwargs:
            text_content = ContentGenerator.generate_content(
                kwargs.get('category', FileCategory.GENERAL),
                kwargs.get('complexity', ContentComplexity.MODERATE),
                kwargs.get('word_count', 200)
            )
            kwargs['content'] = cls._create_minimal_pdf(text_content)
        else:
            # If a string is provided, embed it into a valid PDF; otherwise ensure bytes
            if isinstance(kwargs['content'], str):
                kwargs['content'] = cls._create_minimal_pdf(kwargs['content'])
            elif not isinstance(kwargs['content'], (bytes, bytearray)):
                kwargs['content'] = bytes(kwargs['content'])

        return cls.create_test_file(**kwargs)
    
    @classmethod
    def create_duplicate_pair(cls, **kwargs) -> Tuple[TestFile, TestFile]:
        """Create two files with identical content for duplicate testing."""
        kwargs['scenario'] = TestScenario.DUPLICATE
        
        # Create first file
        file1 = cls.create_test_file(**kwargs)
        
        # Create second file with same content but different name
        file2_kwargs = kwargs.copy()
        file2_kwargs['filename'] = f"duplicate_{file1.filename}"
        file2_kwargs['content'] = file1.content
        file2 = cls.create_test_file(**file2_kwargs)
        
        return file1, file2
    
    @classmethod
    def create_search_test_set(cls) -> List[TestFile]:
        """Create a set of files optimized for search testing."""
        return [
            cls.create_test_file(
                content="The patient showed improvement after treatment with the new medication protocol.",
                category=FileCategory.MEDICAL,
                scenario=TestScenario.SEARCH,
                tags=["medical", "treatment", "patient"]
            ),
            cls.create_test_file(
                content="Bank of America reported strong quarterly earnings exceeding analyst expectations.",
                category=FileCategory.FINANCIAL,
                scenario=TestScenario.SEARCH,
                tags=["finance", "earnings", "banking"]
            ),
            cls.create_test_file(
                content="The software architecture uses microservices for improved scalability.",
                category=FileCategory.TECHNICAL,
                scenario=TestScenario.SEARCH,
                tags=["technical", "software", "architecture"]
            ),
            cls.create_test_file(
                content="Legal review of the contract identified several areas requiring clarification.",
                category=FileCategory.LEGAL,
                scenario=TestScenario.SEARCH,
                tags=["legal", "contract", "review"]
            ),
        ]
    
    @classmethod
    def create_performance_test_file(
        cls,
        size_mb: float = 1.0,
        **kwargs
    ) -> TestFile:
        """Create a large file for performance testing."""
        kwargs['scenario'] = TestScenario.PERFORMANCE
        
        # Calculate word count for target size
        # Rough estimate: 1 word ≈ 5 bytes
        word_count = int((size_mb * 1024 * 1024) / 5)
        kwargs['word_count'] = word_count
        kwargs['complexity'] = ContentComplexity.COMPLEX
        
        return cls.create_test_file(**kwargs)
    
    @classmethod
    def create_error_test_files(cls) -> List[TestFile]:
        """Create files designed to trigger various error conditions."""
        return [
            # Empty file
            cls.create_test_file(
                filename="empty.txt",
                content="",
                complexity=ContentComplexity.EMPTY,
                scenario=TestScenario.ERROR
            ),
            # File with invalid characters
            cls.create_test_file(
                filename="invalid_chars.txt",
                content="\x00\x01\x02\x03\x04",
                scenario=TestScenario.ERROR
            ),
            # Very large filename
            cls.create_test_file(
                filename="x" * 255 + ".txt",
                scenario=TestScenario.ERROR
            ),
            # File with misleading extension
            cls.create_test_file(
                filename="not_really_pdf.pdf",
                content="This is plain text, not a PDF",
                mime_type="text/plain",
                scenario=TestScenario.ERROR
            ),
        ]
    
    @staticmethod
    def _escape_pdf_text(text: str) -> str:
        """Escape characters for PDF text literals."""
        return (
            text.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )

    @classmethod
    def _create_minimal_pdf(cls, text: str) -> bytes:
        """Create a minimal, valid single-page PDF containing the given text.

        The output includes a proper header, objects, xref table, and trailer so
        PDF parsers like PyPDF can open and extract text.
        """
        def to_bytes(s: str) -> bytes:
            # Latin-1 is sufficient for our ASCII content; replace unknowns
            return s.encode("latin-1", errors="replace")

        # Prepare text lines (wrap long lines ~80 chars)
        raw_lines: list[str] = []
        for para in str(text).splitlines() or [""]:
            if not para:
                raw_lines.append("")
                continue
            s = para
            width = 80
            for i in range(0, len(s), width):
                raw_lines.append(s[i : i + width])

        content_ops: list[str] = [
            "BT",
            "/F1 12 Tf",      # Font and size
            "72 720 Td",       # Start near top-left
            "14 TL",           # Line height
        ]
        first = True
        for line in raw_lines:
            esc = cls._escape_pdf_text(line)
            if first:
                content_ops.append(f"({esc}) Tj")
                first = False
            else:
                content_ops.append("T*")  # move to next line
                content_ops.append(f"({esc}) Tj")
        content_ops.append("ET")
        content_stream_str = "\n".join(content_ops) + "\n"
        content_stream = to_bytes(content_stream_str)

        parts: list[bytes] = []

        def current_offset() -> int:
            return sum(len(p) for p in parts)

        # Header (binary comment line improves parser compatibility)
        parts.append(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        offsets: list[int] = [0]  # index 0 is the free object

        # 1: Catalog
        offsets.append(current_offset())
        parts.append(to_bytes("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"))

        # 2: Pages
        offsets.append(current_offset())
        parts.append(to_bytes("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"))

        # 3: Page
        page_obj = (
            "3 0 obj\n"
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
            "   /Resources << /Font << /F1 4 0 R >> >>\n"
            "   /Contents 5 0 R >>\n"
            "endobj\n"
        )
        offsets.append(current_offset())
        parts.append(to_bytes(page_obj))

        # 4: Font
        offsets.append(current_offset())
        parts.append(to_bytes("4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"))

        # 5: Contents (stream)
        contents_header = to_bytes(f"5 0 obj\n<< /Length {len(content_stream)} >>\nstream\n")
        contents_footer = b"endstream\nendobj\n"
        offsets.append(current_offset())
        parts.append(contents_header)
        parts.append(content_stream)
        parts.append(contents_footer)

        # xref table
        xref_offset = current_offset()
        parts.append(b"xref\n")
        # We have objects 0..5 => size 6
        parts.append(to_bytes("0 6\n"))
        parts.append(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            parts.append(to_bytes(f"{off:010d} 00000 n \n"))

        # trailer and EOF
        trailer = (
            "trailer\n"
            "<< /Size 6 /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n"
            "%%EOF\n"
        )
        parts.append(to_bytes(trailer))

        return b"".join(parts)

    @classmethod
    def _get_extension_for_mime(cls, mime_type: str) -> str:
        """Get file extension for MIME type."""
        extensions = {
            "text/plain": "txt",
            "application/pdf": "pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "application/json": "json",
            "text/csv": "csv",
            "image/jpeg": "jpg",
            "image/png": "png",
        }
        return extensions.get(mime_type, "bin")
    
    @classmethod
    def _generate_tags_for_category(cls, category: FileCategory) -> List[str]:
        """Generate relevant tags for a category."""
        tag_map = {
            FileCategory.MEDICAL: ["healthcare", "medical", "patient", "treatment"],
            FileCategory.FINANCIAL: ["finance", "money", "investment", "banking"],
            FileCategory.LEGAL: ["legal", "law", "contract", "compliance"],
            FileCategory.TECHNICAL: ["technology", "software", "development", "engineering"],
            FileCategory.PERSONAL: ["personal", "private", "diary", "notes"],
            FileCategory.RESEARCH: ["research", "study", "analysis", "academic"],
            FileCategory.GENERAL: ["document", "general", "misc", "other"],
        }
        return tag_map.get(category, ["general"])
    
    @classmethod
    def _extract_dates_from_content(cls, content: str) -> List[str]:
        """Extract date patterns from content for validation."""
        import re
        
        # Simple date pattern matching (can be enhanced)
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{1,2}/\d{1,2}/\d{4}',  # MM/DD/YYYY
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, content)
            dates.extend(matches)
        
        return dates
