"""
Factory for creating test files and file-related objects.
"""

import hashlib
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass


@dataclass
class TestFile:
    """Represents a test file with its metadata."""
    path: Path
    content: bytes
    filename: str
    mime_type: str
    size: int
    hash: str
    metadata: Dict[str, Any]


class FileFactory:
    """Factory for creating test files with various content types."""
    
    SAMPLE_TEXT_CONTENT = """
    This is a sample text document for testing purposes.
    It contains multiple lines and various formatting.
    
    Key topics covered:
    - Document processing
    - Text extraction
    - Search functionality
    - Natural language queries
    
    This content should be sufficient for testing search and Q&A functionality.
    The document was created on January 1, 2024 by the testing system.
    """
    
    SAMPLE_PDF_METADATA = {
        "title": "Sample Test Document", 
        "author": "Test System",
        "subject": "Testing",
        "creator": "Test Factory",
    }
    
    @classmethod
    def create_text_file(
        self,
        content: Optional[str] = None,
        filename: str = "test_document.txt",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TestFile:
        """Create a text file for testing."""
        if content is None:
            content = self.SAMPLE_TEXT_CONTENT.strip()
        
        content_bytes = content.encode('utf-8')
        file_hash = hashlib.sha256(content_bytes).hexdigest()
        
        return TestFile(
            path=Path(filename),  # Will be converted to actual path when needed
            content=content_bytes,
            filename=filename,
            mime_type="text/plain",
            size=len(content_bytes),
            hash=file_hash,
            metadata=metadata or {},
        )
    
    @classmethod
    def create_pdf_like_file(
        self,
        filename: str = "test_document.pdf",
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TestFile:
        """Create a PDF-like file for testing (simulated PDF content)."""
        if content is None:
            content = self.SAMPLE_TEXT_CONTENT.strip()
        
        # Simulate PDF binary structure with text content
        pdf_content = f"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length {len(content)} >>\nstream\n{content}\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000174 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{200 + len(content)}\n%%EOF"
        
        content_bytes = pdf_content.encode('utf-8')
        file_hash = hashlib.sha256(content_bytes).hexdigest()
        
        merged_metadata = {**self.SAMPLE_PDF_METADATA, **(metadata or {})}
        
        return TestFile(
            path=Path(filename),
            content=content_bytes,
            filename=filename,
            mime_type="application/pdf",
            size=len(content_bytes),
            hash=file_hash,
            metadata=merged_metadata,
        )
    
    @classmethod
    def create_docx_like_file(
        self,
        filename: str = "test_document.docx",
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TestFile:
        """Create a DOCX-like file for testing (simulated DOCX content)."""
        if content is None:
            content = self.SAMPLE_TEXT_CONTENT.strip()
        
        # Simulate minimal DOCX structure (ZIP-based)
        docx_content = f"""PK{content}PK_DOCX_END"""
        
        content_bytes = docx_content.encode('utf-8')
        file_hash = hashlib.sha256(content_bytes).hexdigest()
        
        return TestFile(
            path=Path(filename),
            content=content_bytes,
            filename=filename,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size=len(content_bytes),
            hash=file_hash,
            metadata=metadata or {},
        )
    
    @classmethod
    def create_binary_file(
        self,
        filename: str = "test_binary.bin",
        size: int = 1024,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TestFile:
        """Create a binary file for testing."""
        content_bytes = b'\x00' * size  # Simple binary content
        file_hash = hashlib.sha256(content_bytes).hexdigest()
        
        return TestFile(
            path=Path(filename),
            content=content_bytes,
            filename=filename,
            mime_type="application/octet-stream",
            size=size,
            hash=file_hash,
            metadata=metadata or {},
        )
    
    @classmethod
    def create_large_text_file(
        self,
        filename: str = "large_test_document.txt",
        size_kb: int = 100,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TestFile:
        """Create a large text file for performance testing."""
        # Create content that repeats to reach the desired size
        base_content = self.SAMPLE_TEXT_CONTENT.strip()
        target_size = size_kb * 1024
        
        content = ""
        while len(content.encode('utf-8')) < target_size:
            content += base_content + f"\n--- Section {len(content) // len(base_content) + 1} ---\n"
        
        # Trim to exact size
        content_bytes = content.encode('utf-8')[:target_size]
        content = content_bytes.decode('utf-8', errors='ignore')
        content_bytes = content.encode('utf-8')
        
        file_hash = hashlib.sha256(content_bytes).hexdigest()
        
        return TestFile(
            path=Path(filename),
            content=content_bytes,
            filename=filename,
            mime_type="text/plain",
            size=len(content_bytes),
            hash=file_hash,
            metadata=metadata or {"size_category": "large"},
        )


class TempFileFactory:
    """Factory for creating actual temporary files on disk."""
    
    @classmethod
    def create_temp_file(self, test_file: TestFile) -> Path:
        """Create an actual temporary file from a TestFile object."""
        # Create temp file with correct suffix
        suffix = Path(test_file.filename).suffix
        with tempfile.NamedTemporaryFile(
            suffix=suffix, 
            delete=False,
            prefix="lifearch_test_"
        ) as temp_file:
            temp_file.write(test_file.content)
            temp_file.flush()
            temp_path = Path(temp_file.name)
        
        return temp_path
    
    @classmethod 
    def create_temp_files(self, test_files: list[TestFile]) -> list[Path]:
        """Create multiple temporary files."""
        return [self.create_temp_file(test_file) for test_file in test_files]
    
    @classmethod
    def create_test_text_file(
        self,
        content: Optional[str] = None,
        filename: str = "test.txt",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> tuple[Path, TestFile]:
        """Create a temporary text file and return both the path and TestFile object."""
        test_file = FileFactory.create_text_file(content, filename, metadata)
        temp_path = self.create_temp_file(test_file)
        return temp_path, test_file
    
    @classmethod
    def create_test_pdf_file(
        self,
        filename: str = "test.pdf", 
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> tuple[Path, TestFile]:
        """Create a temporary PDF-like file and return both the path and TestFile object."""
        test_file = FileFactory.create_pdf_like_file(filename, content, metadata)
        temp_path = self.create_temp_file(test_file)
        return temp_path, test_file


# Convenience functions for common test scenarios
def create_sample_documents() -> list[TestFile]:
    """Create a set of sample documents for testing."""
    return [
        FileFactory.create_text_file(
            content="This is a medical report about patient care and treatment protocols.",
            filename="medical_report.txt",
            metadata={"category": "medical", "patient_id": "12345"}
        ),
        FileFactory.create_pdf_like_file(
            content="Bank of America quarterly earnings report with financial data.",
            filename="earnings_report.pdf", 
            metadata={"category": "financial", "quarter": "Q1", "year": "2024"}
        ),
        FileFactory.create_text_file(
            content="Mortgage rates and home loan information for real estate.",
            filename="mortgage_info.txt",
            metadata={"category": "real_estate", "type": "mortgage"}
        ),
    ]


def create_test_files_for_upload() -> list[TestFile]:
    """Create test files specifically designed for upload testing."""
    return [
        FileFactory.create_text_file(
            content="Simple test document for upload validation.",
            filename="simple_upload.txt",
        ),
        FileFactory.create_pdf_like_file(
            content="PDF document for upload testing with metadata.",
            filename="upload_test.pdf",
            metadata={"upload_test": True}
        ),
        FileFactory.create_large_text_file(
            filename="large_upload.txt",
            size_kb=50,  # 50KB for performance testing
        ),
    ]