from typing import Any, Optional

from .base import BasePromptBuilder


class ClassificationPromptBuilder(BasePromptBuilder):

    @staticmethod
    def build(query: str, context: Optional[Any] = None) -> str:
        return f"""You are a classifier that decides whether a user query requires a single-step response (simple)
or multi-step reasoning or tool usage (complex).

Definitions:
- "simple" → can be answered directly with text or a single retrieval of facts.
- "complex" → needs planning, multiple steps, API/tool calls, or reasoning beyond retrieval (e.g., data analysis, code, long reasoning chains).

Return ONLY strict JSON with:
{{
  "complexity": "simple" | "complex",
  "confidence": float (0–1),
  "reasoning": short string (max 20 words),
  "estimated_steps": integer >= 1
}}

Examples:
1. Query: "Who is the CEO of Apple?"
   → {{ "complexity": "simple", "confidence": 0.95, "reasoning": "single fact lookup", "estimated_steps": 1 }}

2. Query: "Summarize these three documents and generate a recommendation."
   → {{ "complexity": "complex", "confidence": 0.93, "reasoning": "multi-doc analysis and synthesis", "estimated_steps": 3 }}

3. Query: "Write Python code that plots sales by region."
   → {{ "complexity": "complex", "confidence": 0.9, "reasoning": "requires code generation", "estimated_steps": 2 }}

4. Query: "What time is it in Tokyo?"
   → {{ "complexity": "simple", "confidence": 0.9, "reasoning": "single lookup", "estimated_steps": 1 }}

USER QUERY:
{query}

Output only the JSON object, nothing else.
"""
