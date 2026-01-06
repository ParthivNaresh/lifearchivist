from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]

    @classmethod
    def success(cls, warnings: Optional[List[str]] = None) -> "ValidationResult":
        return cls(is_valid=True, errors=[], warnings=warnings or [])

    @classmethod
    def failure(cls, errors: List[str]) -> "ValidationResult":
        return cls(is_valid=False, errors=errors, warnings=[])
