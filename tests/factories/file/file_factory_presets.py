from typing import List

from factories import FileFactory
from .file_factory import TestFile
from .file_schemas import FileCategory, ContentComplexity, TestScenario


class FileFactoryPresets:
    """Pre-configured file sets for common test scenarios."""

    @classmethod
    def for_upload_tests(cls) -> List[TestFile]:
        """Files optimized for upload endpoint testing."""
        return [
            FileFactory.create_text_file(
                category=FileCategory.GENERAL,
                complexity=ContentComplexity.SIMPLE,
                scenario=TestScenario.UPLOAD
            ),
            FileFactory.create_pdf_file(
                category=FileCategory.FINANCIAL,
                complexity=ContentComplexity.MODERATE,
                scenario=TestScenario.UPLOAD
            ),
            FileFactory.create_test_file(
                mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                category=FileCategory.MEDICAL,
                complexity=ContentComplexity.COMPLEX,
                scenario=TestScenario.UPLOAD
            ),
        ]

    @classmethod
    def for_search_tests(cls) -> List[TestFile]:
        """Files with diverse content for search testing."""
        return FileFactory.create_search_test_set()

    @classmethod
    def for_duplicate_tests(cls) -> List[TestFile]:
        """Files for testing duplicate detection."""
        files = []

        # Create duplicate pairs
        pair1, pair2 = FileFactory.create_duplicate_pair(
            category=FileCategory.FINANCIAL,
            content="Quarterly financial report with important metrics."
        )
        files.extend([pair1, pair2])

        # Add unique file
        files.append(FileFactory.create_text_file(
            category=FileCategory.TECHNICAL,
            content="Unique technical documentation."
        ))

        return files

    @classmethod
    def for_performance_tests(cls) -> List[TestFile]:
        """Large files for performance testing."""
        return [
            FileFactory.create_performance_test_file(size_mb=0.5),
            FileFactory.create_performance_test_file(size_mb=1.0),
            FileFactory.create_performance_test_file(size_mb=5.0),
        ]

    @classmethod
    def for_workflow_tests(cls) -> List[TestFile]:
        """Comprehensive file set for end-to-end workflow testing."""
        files = []

        # Add files from each category
        for category in FileCategory:
            files.append(FileFactory.create_test_file(
                category=category,
                complexity=ContentComplexity.MODERATE,
                scenario=TestScenario.WORKFLOW
            ))

        return files

    @classmethod
    def for_error_tests(cls) -> List[TestFile]:
        """Files designed to trigger error conditions."""
        return FileFactory.create_error_test_files()
