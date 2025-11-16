import json
from typing import TYPE_CHECKING

from ...llm import LLMMessage
from .models.query import ComplexityClassification, QueryComplexity

if TYPE_CHECKING:
    from llm import LLMProviderManager

    from .utils.prompt_builder import PromptBuilder


class ComplexityClassifier:

    def __init__(
        self,
        llm_provider_manager: "LLMProviderManager",
        prompt_builder: "PromptBuilder",
        model: str = "gpt-4o-mini",
    ):
        self.llm = llm_provider_manager
        self.prompt_builder = prompt_builder
        self.model = model

    async def classify(
        self, query: str, context: any = None
    ) -> ComplexityClassification:
        prompt = self.prompt_builder.build_complexity_classification_prompt(
            query=query, context=context
        )

        result = await self.llm.generate(
            messages=[LLMMessage(role="user", content=prompt)],
            model=self.model,
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
