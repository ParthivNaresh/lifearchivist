import json
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict

from ..llm.base_provider import LLMMessage
from .complexity_classifier import ComplexityClassifier
from .exceptions import PlanningError
from .executor import TaskExecutor
from .models.context import ConversationContext
from .models.events import AgentEvent, AgentEventType
from .models.query import QueryComplexity
from .models.task import AgentTask, ExecutionPlan
from .plan_validator import PlanValidator
from .tool_registry import AgentToolRegistry
from .utils.prompt_builder import PromptBuilder

if TYPE_CHECKING:
    from ..llm import LLMProviderManager


class AgentOrchestrator:

    def __init__(
        self,
        llm_provider_manager: "LLMProviderManager",
        tool_registry: AgentToolRegistry,
        complexity_classifier: ComplexityClassifier,
        executor: TaskExecutor,
        prompt_builder: PromptBuilder,
        plan_validator: PlanValidator,
    ):
        self.llm = llm_provider_manager
        self.tools = tool_registry
        self.classifier = complexity_classifier
        self.executor = executor
        self.prompt_builder = prompt_builder
        self.validator = plan_validator

    async def process_query(
        self, query: str, context: ConversationContext
    ) -> AsyncGenerator[AgentEvent, None]:
        classification = await self.classifier.classify(query, context)
        yield AgentEvent.complexity_classified(classification)

        if classification.complexity == QueryComplexity.SIMPLE:
            yield AgentEvent.error("Simple queries should be routed to RAG, not agent")
            return

        plan = await self._create_execution_plan(query, context)
        yield AgentEvent.plan_created(plan)

        task_results: Dict[str, Any] = {}
        async for task_event in self.executor.execute_plan(plan, context):
            yield task_event

            if task_event.type == AgentEventType.TASK_COMPLETED:
                if task_event.task_id:
                    task_results[task_event.task_id] = task_event.data

        yield AgentEvent.synthesis_started()
        async for chunk in self._synthesize_response(query, plan, task_results):
            yield AgentEvent.response_chunk(chunk)

        yield AgentEvent.complete()

    async def _create_execution_plan(
        self, query: str, context: ConversationContext
    ) -> ExecutionPlan:
        prompt = self.prompt_builder.build_planning_prompt(
            query=query, context=context, available_tools=self.tools.list_tools()
        )

        result = await self.llm.generate(
            messages=[LLMMessage(role="user", content=prompt)],
            model="gpt-4o",
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        if result.is_failure():
            raise PlanningError(result.error)

        response = result.unwrap()
        plan_data = json.loads(response.content)

        plan = ExecutionPlan(
            tasks=[AgentTask(**task) for task in plan_data["tasks"]],
            estimated_time_seconds=plan_data["estimated_time_seconds"],
            estimated_cost_usd=plan_data["estimated_cost_usd"],
            reasoning=plan_data["reasoning"],
        )

        self.validator.validate(plan)

        return plan

    async def _synthesize_response(
        self, query: str, plan: ExecutionPlan, task_results: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        prompt = self.prompt_builder.build_synthesis_prompt(
            query=query, plan=plan, results=task_results
        )

        async for chunk in self.llm.generate_stream(
            messages=[LLMMessage(role="user", content=prompt)],
            model="gpt-4o",
            temperature=0.7,
        ):
            yield chunk.content
