import json
import logging
from typing import TYPE_CHECKING, Any

from ...llm import LLMMessage
from ...utils.logx import log_event, track
from .models.query import ComplexityClassification, QueryComplexity

if TYPE_CHECKING:
    from llm import LLMProviderManager

    from .utils.prompt_builder import PromptBuilder


class ComplexityClassifier:

    def __init__(
        self,
        llm_provider_manager: "LLMProviderManager",
        prompt_builder: "PromptBuilder",
        model: str = "qwen2.5:7b",
    ):
        self.llm = llm_provider_manager
        self.prompt_builder = prompt_builder
        self.model = model

    @track(operation="complexity_classify")
    async def classify(
        self, query: str, context: Any | None = None
    ) -> ComplexityClassification:
        conversation_id = getattr(context, "conversation_id", None) if context else None

        log_event(
            "classifier_classify_started",
            {
                "conversation_id": conversation_id,
                "query_length": len(query),
                "model": self.model,
            },
        )

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
            log_event(
                "classifier_llm_failed",
                {
                    "conversation_id": conversation_id,
                    "error": result.error,
                    "fallback": "simple",
                },
                level=logging.WARNING,
            )
            return ComplexityClassification(
                complexity=QueryComplexity.SIMPLE,
                confidence=0.5,
                reasoning="Failed to classify, defaulting to simple",
                estimated_steps=1,
            )

        response = result.unwrap()
        log_event(
            "classifier_llm_response_received",
            {
                "conversation_id": conversation_id,
                "tokens_used": response.tokens_used,
                "cost_usd": response.cost_usd,
            },
        )

        try:
            data = json.loads(response.content)
            classification = ComplexityClassification(
                complexity=QueryComplexity(data["complexity"]),
                confidence=data["confidence"],
                reasoning=data["reasoning"],
                estimated_steps=data.get("estimated_steps", 1),
            )
            log_event(
                "classifier_classify_success",
                {
                    "conversation_id": conversation_id,
                    "complexity": classification.complexity.value,
                    "confidence": classification.confidence,
                    "estimated_steps": classification.estimated_steps,
                },
            )
            return classification
        except Exception as e:
            log_event(
                "classifier_parse_failed",
                {
                    "conversation_id": conversation_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "content_preview": response.content[:500],
                    "fallback": "simple",
                },
                level=logging.ERROR,
            )
            return ComplexityClassification(
                complexity=QueryComplexity.SIMPLE,
                confidence=0.5,
                reasoning=f"Failed to parse classification: {e}",
                estimated_steps=1,
            )
