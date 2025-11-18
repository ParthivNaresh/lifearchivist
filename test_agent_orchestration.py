import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from llm.agent import (
    AgentOrchestrator,
    AgentSpawner,
    AgentToolRegistry,
    ComplexityClassifier,
    ConversationContext,
    TaskExecutor,
    QueryComplexity,
    ComplexityClassification,
)
from llm.agent.plan_validator import PlanValidator
from llm.agent.utils import PromptBuilder
from lifearchivist.config.settings import Settings, configure_logging
from lifearchivist.server.service_container import ServiceConfig, ServiceContainer


class OrchestrationTestLogger:
    def __init__(self):
        self.events: list[Dict[str, Any]] = []
        self.stage_timings: Dict[str, float] = {}
        self.current_stage_start: float = 0.0
        
    def log_stage(self, stage: str, data: Dict[str, Any] | None = None) -> None:
        timestamp = datetime.now()
        elapsed = 0.0
        if self.current_stage_start:
            elapsed = (timestamp.timestamp() - self.current_stage_start) * 1000
            self.stage_timings[stage] = elapsed
        
        event = {
            "timestamp": timestamp.isoformat(),
            "stage": stage,
            "elapsed_ms": round(elapsed, 2),
            "data": data or {}
        }
        self.events.append(event)
        
        print(f"\n{'='*80}")
        print(f"STAGE: {stage}")
        print(f"TIME: {timestamp.strftime('%H:%M:%S.%f')[:-3]}")
        if elapsed:
            print(f"ELAPSED: {elapsed:.2f}ms")
        if data:
            print(f"DATA: {json.dumps(data, indent=2, default=str)}")
        print(f"{'='*80}\n")
        
        self.current_stage_start = timestamp.timestamp()
    
    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        timestamp = datetime.now()
        event = {
            "timestamp": timestamp.isoformat(),
            "type": event_type,
            "data": data
        }
        self.events.append(event)
        
        print(f"  → {event_type}: {json.dumps(data, default=str)}")
    
    def print_summary(self) -> None:
        print(f"\n{'='*80}")
        print("TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Events: {len(self.events)}")
        print(f"\nStage Timings:")
        for stage, timing in self.stage_timings.items():
            print(f"  {stage}: {timing:.2f}ms")
        total_time = sum(self.stage_timings.values())
        print(f"\nTotal Time: {total_time:.2f}ms ({total_time/1000:.2f}s)")
        print(f"{'='*80}\n")


class TestPromptBuilder(PromptBuilder):
    def __init__(self, forced_tool_model: str):
        self.forced_tool_model = forced_tool_model
    def build_planning_prompt(
        self,
        *,
        query: str,
        context: Any,
        available_tools,
        max_tasks: int = 20,
        cost_budget_usd: float = 1.0,
        time_budget_s: int = 300,
    ) -> str:
        base = super().build_planning_prompt(
            query=query,
            context=context,
            available_tools=available_tools,
            max_tasks=max_tasks,
            cost_budget_usd=cost_budget_usd,
            time_budget_s=time_budget_s,
        )
        require = f'\nADDITIONAL REQUIREMENTS:\n- For any LLM-assisted tool, include a "model" parameter set to "{self.forced_tool_model}".\n- Ensure all tool parameters validate against the provided input_schema.\n'
        return base + require


class TestOrchestrator(AgentOrchestrator):
    def __init__(self, *args, tool_default_model: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.tool_default_model = tool_default_model
    async def _create_execution_plan(self, query: str, context: ConversationContext):
        from llm.agent import AgentTask, ExecutionPlan, PlanningError
        from lifearchivist.llm import LLMMessage
        prompt = self.prompt_builder.build_planning_prompt(
            query=query, context=context, available_tools=self.tools.list_tools()
        )
        result = await self.llm.generate(
            messages=[LLMMessage(role="user", content=prompt)],
            model=self.planning_model,
            temperature=self.planning_temperature,
            response_format={"type": "json_object"},
        )
        def make_fallback_plan() -> ExecutionPlan:
            t = AgentTask(
                task_id="extract_health_docs",
                tool_name="data_extraction",
                description="Extract cholesterol levels and related metrics",
                requires_llm=True,
                parameters={
                    "document_ids": ["dummy-doc-1"],
                    "queries": ["cholesterol"],
                    "fields": ["cholesterol"],
                    "model": self.tool_default_model,
                },
                depends_on=[],
            )
            return ExecutionPlan(
                tasks=[t],
                estimated_time_seconds=60,
                estimated_cost_usd=0.01,
                reasoning="Fallback plan for test execution",
            )
        if result.is_failure():
            return make_fallback_plan()
        try:
            response = result.unwrap()
            plan_data = json.loads(response.content)
        except Exception:
            return make_fallback_plan()
        known = set(self.tools.get_tool_names()) if hasattr(self.tools, "get_tool_names") else set([getattr(t, "name", "") for t in self.tools.list_tools()])
        raw_tasks = plan_data.get("tasks", []) if isinstance(plan_data, dict) else []
        tasks = []
        for idx, t in enumerate(raw_tasks, start=1):
            tool_name = t.get("tool_name")
            if not isinstance(tool_name, str) or tool_name not in known:
                continue
            task_id = str(t.get("task_id") or f"task_{idx}")
            requires_llm = bool(t.get("requires_llm", tool_name == "data_extraction"))
            params = dict(t.get("parameters", {})) if isinstance(t.get("parameters", {}), dict) else {}
            if tool_name == "data_extraction":
                if not isinstance(params.get("document_ids"), list) or not params.get("document_ids"):
                    params["document_ids"] = ["dummy-doc-1"]
                if not isinstance(params.get("queries"), list) or not params.get("queries"):
                    params["queries"] = ["cholesterol"]
                if not isinstance(params.get("fields"), list) or not params.get("fields"):
                    params["fields"] = ["cholesterol"]
                requires_llm = True
            if requires_llm and "model" not in params:
                params["model"] = self.tool_default_model
            depends_on = [d for d in (t.get("depends_on") or []) if isinstance(d, str)]
            tasks.append(
                AgentTask(
                    task_id=task_id,
                    tool_name=tool_name,
                    description=str(t.get("description", "")),
                    requires_llm=requires_llm,
                    parameters=params,
                    depends_on=depends_on,
                )
            )
        # prune bad dependencies
        id_set = {t.task_id for t in tasks}
        for t in tasks:
            t.depends_on = [d for d in t.depends_on if d in id_set]
        if not tasks:
            plan = make_fallback_plan()
        else:
            plan = ExecutionPlan(
                tasks=tasks,
                estimated_time_seconds=int(plan_data.get("estimated_time_seconds", 0) or 0),
                estimated_cost_usd=float(plan_data.get("estimated_cost_usd", 0.0) or 0.0),
                reasoning=str(plan_data.get("reasoning", "")),
            )
        try:
            self.validator.validate(plan)
        except PlanningError:
            plan = make_fallback_plan()
            self.validator.validate(plan)
        return plan


class ForcingComplexityClassifier(ComplexityClassifier):
    async def classify(self, query: str, context: Any = None):
        result = await super().classify(query, context)
        if getattr(result, "complexity", None) == QueryComplexity.SIMPLE:
            return ComplexityClassification(
                complexity=QueryComplexity.COMPLEX,
                confidence=0.95,
                reasoning="Forced complex for integration to exercise planning/execution.",
                estimated_steps=max(2, getattr(result, "estimated_steps", 2)),
            )
        return result


async def test_orchestration_pipeline():
    configure_logging("DEBUG")
    logger = OrchestrationTestLogger()
    
    logger.log_stage("INITIALIZATION", {"description": "Setting up services"})
    
    settings = Settings()
    
    config = ServiceConfig(
        redis_url=settings.redis_url,
        qdrant_url=settings.qdrant_url,
        database_url=settings.database_url,
        vault_path=settings.vault_path or Path.home() / ".lifearchivist" / "vault",
        settings=settings,
    )
    
    container = ServiceContainer(config)
    
    try:
        logger.log_stage("SERVICE_CONTAINER_INIT", {"description": "Initializing service container"})
        await container.initialize()
        logger.log_event("services_initialized", {
            "redis": container.redis_client is not None,
            "qdrant": container.qdrant_client is not None,
            "database": container.db_pool is not None,
            "llm_manager": container.llm_provider_manager is not None,
        })
        
        logger.log_stage("LLM_PROVIDER_SETUP", {"description": "Configuring LLM provider"})
        
        if not container.llm_provider_manager:
            raise RuntimeError("LLM provider manager not initialized")
        
        llm_manager = container.llm_provider_manager
        
        providers = llm_manager.registry.list_all()
        logger.log_event("existing_providers", {"count": len(providers), "providers": [p.provider_id for p in providers]})
        
        openai_key = os.getenv("OPENAI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")

        groq_providers = [p for p in providers if getattr(p, "provider_type", None) and getattr(p.provider_type, "value", "") == "groq"]
        use_groq = bool(groq_key) or len(groq_providers) > 0
        
        if groq_key:
            logger.log_event("adding_groq_provider", {"has_key": True})
            from lifearchivist.llm.providers.groq_provider import GroqProvider
            from lifearchivist.llm.provider_config import GroqConfig
            
            groq_config = GroqConfig(api_key=groq_key)
            groq_provider = GroqProvider(
                provider_id="groq_test",
                config=groq_config,
            )
            add_result = await llm_manager.add_provider(groq_provider, set_as_default=True)
            if add_result.is_failure():
                logger.log_event("groq_provider_failed", {"error": add_result.error})
            else:
                logger.log_event("groq_provider_added", {"provider_id": "groq_test"})
        elif len(groq_providers) > 0:
            groq_existing_id = groq_providers[0].provider_id
            set_res = llm_manager.registry.set_default(groq_existing_id)
            if set_res.is_failure():
                logger.log_event("groq_default_set_failed", {"error": set_res.error_or("unknown")})
            else:
                logger.log_event("groq_default_set", {"provider_id": groq_existing_id})
        elif openai_key:
            logger.log_event("adding_openai_provider", {"has_key": True})
            from lifearchivist.llm.providers.openai_provider import OpenAIProvider
            from lifearchivist.llm.provider_config import OpenAIConfig
            
            openai_config = OpenAIConfig(api_key=openai_key)
            openai_provider = OpenAIProvider(
                provider_id="openai_test",
                config=openai_config,
            )
            add_result = await llm_manager.add_provider(openai_provider, set_as_default=True)
            if add_result.is_failure():
                logger.log_event("openai_provider_failed", {"error": add_result.error})
            else:
                logger.log_event("openai_provider_added", {"provider_id": "openai_test"})
        elif anthropic_key:
            logger.log_event("adding_anthropic_provider", {"has_key": True})
            from lifearchivist.llm.providers.anthropic_provider import AnthropicProvider
            from lifearchivist.llm.provider_config import AnthropicConfig
            
            anthropic_config = AnthropicConfig(api_key=anthropic_key)
            anthropic_provider = AnthropicProvider(
                provider_id="anthropic_test",
                config=anthropic_config,
            )
            add_result = await llm_manager.add_provider(anthropic_provider, set_as_default=True)
            if add_result.is_failure():
                logger.log_event("anthropic_provider_failed", {"error": add_result.error})
            else:
                logger.log_event("anthropic_provider_added", {"provider_id": "anthropic_test"})
        else:
            logger.log_event("using_ollama_fallback", {"reason": "No API keys found"})
        
        default_provider = llm_manager.registry.get_default_id()
        logger.log_event("default_provider", {"provider_id": default_provider})
        
        logger.log_stage("TOOL_REGISTRY_SETUP", {"description": "Initializing tool registry"})
        tool_registry = AgentToolRegistry(
            document_service=container.llamaindex_service.document_service if container.llamaindex_service else None
        )
        tool_registry.register_all()
        tool_registry.finalize()
        logger.log_event("tools_registered", {
            "count": tool_registry.count(),
            "tools": tool_registry.get_tool_names()
        })
        
        logger.log_stage("ORCHESTRATOR_SETUP", {"description": "Building orchestrator components"})
        
        if use_groq:
            classification_model = "llama-3.1-8b-instant"
            planning_model = "llama-3.1-8b-instant"
            synthesis_model = "llama-3.1-8b-instant"
        elif openai_key:
            classification_model = "gpt-4o-mini"
            planning_model = "gpt-4o"
            synthesis_model = "gpt-4o"
        elif anthropic_key:
            classification_model = "claude-3-5-sonnet-20241022"
            planning_model = "claude-3-5-sonnet-20241022"
            synthesis_model = "claude-3-5-sonnet-20241022"
        else:
            classification_model = "qwen2.5:7b"
            planning_model = "qwen2.5:7b"
            synthesis_model = "qwen2.5:7b"
        
        logger.log_event("model_selection", {
            "classification": classification_model,
            "planning": planning_model,
            "synthesis": synthesis_model
        })
        
        prompt_builder = TestPromptBuilder(forced_tool_model=planning_model)
        
        complexity_classifier = ForcingComplexityClassifier(
            llm_provider_manager=llm_manager,
            prompt_builder=prompt_builder,
            model=classification_model,
        )
        
        def observer(event: str, fields: dict) -> None:
            logger.log_event(f"orchestrator.{event}", fields)
        
        agent_spawner = AgentSpawner(
            llm_provider_manager=llm_manager,
            tool_registry=tool_registry,
            prompt_builder=prompt_builder,
            task_timeout_s=120.0,
            max_retries=2,
        )
        
        executor = TaskExecutor(
            agent_spawner,
            max_concurrency=8,
            fail_fast=True,
            on_observe=observer,
        )
        
        plan_validator = PlanValidator(
            tool_registry=tool_registry,
            max_tasks=20,
            max_cost_usd=1.0,
            max_time_seconds=300,
        )
        
        orchestrator = TestOrchestrator(
            llm_provider_manager=llm_manager,
            tool_registry=tool_registry,
            complexity_classifier=complexity_classifier,
            executor=executor,
            prompt_builder=prompt_builder,
            plan_validator=plan_validator,
            on_observe=observer,
            planning_model=planning_model,
            planning_temperature=0.2,
            synthesis_model=synthesis_model,
            synthesis_temperature=0.7,
            tool_default_model=planning_model,
        )
        
        logger.log_event("orchestrator_created", {"status": "ready"})
        
        logger.log_stage("TEST_QUERY_EXECUTION", {"description": "Processing test query"})
        
        test_query = "Analyze all my health documents from 2023, extract cholesterol levels, calculate the average, and create a timeline showing the trend over time with recommendations based on the data."
        
        context = ConversationContext(
            conversation_id="test_conv_001",
            user_id="test_user",
            recent_messages=[],
            user_preferences={},
            metadata={"test": True}
        )
        
        logger.log_event("query_submitted", {
            "query": test_query,
            "context": {
                "conversation_id": context.conversation_id,
                "user_id": context.user_id
            }
        })
        
        logger.log_stage("ORCHESTRATION_PIPELINE", {"description": "Streaming events from orchestrator"})
        
        event_count = 0
        response_chunks = []
        
        async for event in orchestrator.process_query(test_query, context):
            event_count += 1
            event_dict = event.to_dict()
            
            logger.log_event(f"agent_event.{event.type.value}", {
                "event_number": event_count,
                "task_id": event.task_id,
                "data_preview": str(event_dict.get("data", ""))[:200]
            })
            
            if event.type.value == "complexity_classified":
                complexity_data = event.data
                if hasattr(complexity_data, "complexity"):
                    complexity_info = {
                        "complexity": complexity_data.complexity.value,
                        "confidence": complexity_data.confidence,
                        "reasoning": complexity_data.reasoning,
                        "estimated_steps": complexity_data.estimated_steps,
                    }
                else:
                    complexity_info = {"raw": str(complexity_data)}
                logger.log_stage("COMPLEXITY_CLASSIFICATION", complexity_info)
            
            elif event.type.value == "plan_created":
                logger.log_stage("PLAN_CREATION", {
                    "tasks": event_dict.get("data", {}).get("tasks", []),
                    "estimated_time": event_dict.get("data", {}).get("estimated_time_seconds"),
                    "estimated_cost": event_dict.get("data", {}).get("estimated_cost_usd"),
                })
            
            elif event.type.value == "task_started":
                logger.log_event("task_execution_started", {
                    "task_id": event.task_id,
                    "tool": event_dict.get("data", {}).get("tool")
                })
            
            elif event.type.value == "task_completed":
                logger.log_event("task_execution_completed", {
                    "task_id": event.task_id,
                    "result_preview": str(event.data)[:200] if event.data else None
                })
            
            elif event.type.value == "task_failed":
                logger.log_event("task_execution_failed", {
                    "task_id": event.task_id,
                    "error": event_dict.get("data", {}).get("error")
                })
            
            elif event.type.value == "plan_completed":
                logger.log_stage("PLAN_EXECUTION_COMPLETE", {
                    "results": event_dict.get("data", {}).get("results", {})
                })
            
            elif event.type.value == "plan_failed":
                logger.log_stage("PLAN_EXECUTION_FAILED", {
                    "error": event_dict.get("data", {}).get("error")
                })
            
            elif event.type.value == "synthesis_started":
                logger.log_stage("RESPONSE_SYNTHESIS", {"description": "Generating final response"})
            
            elif event.type.value == "response_chunk":
                chunk = event.data if isinstance(event.data, str) else str(event.data)
                response_chunks.append(chunk)
                logger.log_event("synthesis_chunk", {"chunk": chunk[:100]})
            
            elif event.type.value == "complete":
                logger.log_stage("ORCHESTRATION_COMPLETE", {
                    "total_events": event_count,
                    "response_length": len("".join(response_chunks))
                })
            
            elif event.type.value == "error":
                logger.log_event("orchestration_error", {
                    "error": event_dict.get("data", {}).get("error")
                })
        
        final_response = "".join(response_chunks)
        
        logger.log_stage("FINAL_RESULTS", {
            "query": test_query,
            "response": final_response,
            "total_events": event_count,
            "response_length": len(final_response)
        })
        
        print("\n" + "="*80)
        print("FINAL RESPONSE")
        print("="*80)
        print(final_response)
        print("="*80 + "\n")
        
        logger.print_summary()
        
        return True
        
    except Exception as e:
        logger.log_stage("ERROR", {
            "error": str(e),
            "error_type": type(e).__name__,
        })
        logging.exception("Test failed with exception")
        return False
        
    finally:
        logger.log_stage("CLEANUP", {"description": "Cleaning up resources"})
        if container.llm_provider_manager:
            await container.llm_provider_manager.shutdown()
        await container.cleanup()
        logger.log_event("cleanup_complete", {"status": "done"})


async def main():
    print("\n" + "="*80)
    print("AGENT ORCHESTRATION PIPELINE TEST")
    print("="*80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    success = await test_orchestration_pipeline()
    
    print("\n" + "="*80)
    print(f"TEST {'PASSED' if success else 'FAILED'}")
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
