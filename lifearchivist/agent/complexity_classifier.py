import json
from typing import TYPE_CHECKING

from ..llm.base_provider import LLMMessage
from .models.query import ComplexityClassification, QueryComplexity

if TYPE_CHECKING:
    from ..llm import LLMProviderManager
    from .utils.prompt_builder import PromptBuilder


class ComplexityClassifier:

    def __init__(
        self,
        llm_provider_manager: "LLMProviderManager",
        prompt_builder: "PromptBuilder",
    ):
        self.llm = llm_provider_manager
        self.prompt_builder = prompt_builder

    async def classify(
        self, query: str, context: any = None
    ) -> ComplexityClassification:
        prompt = self.prompt_builder.build_complexity_classification_prompt(query)

        result = await self.llm.generate(
            messages=[LLMMessage(role="user", content=prompt)],
            model="gpt-4o-mini",
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        if result.is_failure():
            return ComplexityClassification(
                complexity=QueryComplexity.SIMPLE,
                confidence=0.5,
                reasoning="Failed to classify, defaulting to simple",
                estimated_steps=1,
            )

        response = result.unwrap()
        data = json.loads(response.content)

        return ComplexityClassification(
            complexity=QueryComplexity(data["complexity"]),
            confidence=0.9,
            reasoning=data["reasoning"],
            estimated_steps=data.get("estimated_steps", 1),
        )
