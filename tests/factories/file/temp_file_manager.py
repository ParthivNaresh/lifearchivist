import tempfile
from pathlib import Path
from typing import List, Optional

from .file_factory import TestFile


class TempFileManager:
    """
    Manages temporary file creation and cleanup for tests.
    Ensures proper cleanup even if tests fail.
    """

    def __init__(self):
        self.temp_files: List[Path] = []
        self.temp_dir: Optional[Path] = None

    def create_temp_dir(self, prefix: str = "lifearch_test_") -> Path:
        """Create a temporary directory for test files."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        return self.temp_dir

    def create_temp_file(self, test_file: TestFile) -> Path:
        """Create a temporary file from a TestFile object."""
        # Use temp_dir if available, otherwise system temp
        parent_dir = self.temp_dir or Path(tempfile.gettempdir())

        # Create file with proper name
        temp_path = parent_dir / test_file.filename
        temp_path.write_bytes(test_file.content)

        # Track for cleanup
        self.temp_files.append(temp_path)
        test_file.temp_path = temp_path

        return temp_path

    def create_temp_files(self, test_files: List[TestFile]) -> List[Path]:
        """Create multiple temporary files."""
        return [self.create_temp_file(tf) for tf in test_files]

    def cleanup(self):
        """Clean up all temporary files and directories."""
        import shutil

        # Clean up individual files
        for file_path in self.temp_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors

        # Clean up temp directory
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

        # Clear tracking
        self.temp_files.clear()
        self.temp_dir = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup."""
        self.cleanup()
