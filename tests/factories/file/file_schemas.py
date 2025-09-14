from enum import Enum


class FileCategory(Enum):
    """Categories of files for domain-specific testing."""
    MEDICAL = "medical"
    FINANCIAL = "financial"
    LEGAL = "legal"
    TECHNICAL = "technical"
    PERSONAL = "personal"
    RESEARCH = "research"
    GENERAL = "general"


class ContentComplexity(Enum):
    """Content complexity levels for different test scenarios."""
    SIMPLE = "simple"      # Single paragraph, basic text
    MODERATE = "moderate"  # Multiple sections, some structure
    COMPLEX = "complex"    # Rich formatting, multiple topics
    EMPTY = "empty"        # Edge case: empty or minimal content


class TestScenario(Enum):
    """Test scenarios that files are designed for."""
    UPLOAD = "upload"
    SEARCH = "search"
    EXTRACTION = "extraction"
    DUPLICATE = "duplicate"
    PERFORMANCE = "performance"
    ERROR = "error"
    WORKFLOW = "workflow"

