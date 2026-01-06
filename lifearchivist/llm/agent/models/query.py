from dataclasses import dataclass
from enum import Enum


class QueryComplexity(Enum):
    SIMPLE = "simple"
    COMPLEX = "complex"


@dataclass
class ComplexityClassification:
    complexity: QueryComplexity
    confidence: float
    reasoning: str
    estimated_steps: int
