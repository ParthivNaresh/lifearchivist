# Agent Orchestration Architecture

## Overview

LLM-based agent orchestration system that dynamically creates execution plans and spawns specialized agents to handle complex multi-step queries.

**Core Principle**: Use LLMs for planning and task execution to handle infinite query variations without rule maintenance.

---

## File Hierarchy

```
lifearchivist/agents/
├── __init__.py
├── orchestrator.py          # Main orchestration engine
├── executor.py              # Task execution coordinator
├── agent_spawner.py         # Creates specialized agents for tasks
├── complexity_classifier.py # Determines simple vs complex queries
│
├── models/
│   ├── __init__.py
│   ├── query.py            # QueryComplexity, ParsedQuery
│   ├── task.py             # AgentTask, ExecutionPlan
│   ├── events.py           # AgentEvent types
│   └── context.py          # AgentContext, ConversationContext
│
├── tools/
│   ├── __init__.py
│   ├── base.py             # BaseAgentTool abstract class
│   ├── timeline_tool.py    # Timeline generation
│   ├── extraction_tool.py  # Data extraction with LLM
│   └── aggregation_tool.py # Data aggregation
│
└── utils/
    ├── __init__.py
    ├── prompt_builder.py   # Builds prompts for orchestrator/agents
    └── tool_formatter.py   # Formats tool descriptions for LLM
```

---

## Core Models

### Query Models (`agents/models/query.py`)

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any

class QueryComplexity(Enum):
    SIMPLE = "simple"
    COMPLEX = "complex"

@dataclass
class ComplexityClassification:
    complexity: QueryComplexity
    confidence: float
    reasoning: str
    estimated_steps: int
```

### Task Models (`agents/models/task.py`)

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from uuid import uuid4

@dataclass
class AgentTask:
    task_id: str = field(default_factory=lambda: str(uuid4()))
    tool_name: str
    description: str
    requires_llm: bool
    parameters: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    
    def is_ready(self, completed_tasks: set[str]) -> bool:
        return all(dep in completed_tasks for dep in self.depends_on)

@dataclass
class ExecutionPlan:
    tasks: List[AgentTask]
    estimated_time_seconds: int
    estimated_cost_usd: float
    reasoning: str
    
    def get_executable_tasks(self, completed: set[str]) -> List[AgentTask]:
        return [task for task in self.tasks if task.is_ready(completed)]
```

### Event Models (`agents/models/events.py`)

```python
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
from datetime import datetime

class AgentEventType(Enum):
    COMPLEXITY_CLASSIFIED = "complexity_classified"
    PLAN_CREATED = "plan_created"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    AGENT_SPAWNED = "agent_spawned"
    SYNTHESIS_STARTED = "synthesis_started"
    RESPONSE_CHUNK = "response_chunk"
    COMPLETE = "complete"
    ERROR = "error"

@dataclass
class AgentEvent:
    type: AgentEventType
    data: Any
    timestamp: datetime = field(default_factory=datetime.now)
    task_id: Optional[str] = None
    
    @classmethod
    def complexity_classified(cls, classification: ComplexityClassification):
        return cls(type=AgentEventType.COMPLEXITY_CLASSIFIED, data=classification)
    
    @classmethod
    def plan_created(cls, plan: ExecutionPlan):
        return cls(type=AgentEventType.PLAN_CREATED, data=plan)
    
    @classmethod
    def task_started(cls, task: AgentTask):
        return cls(
            type=AgentEventType.TASK_STARTED,
            data={"task_id": task.task_id, "tool": task.tool_name},
            task_id=task.task_id
        )
```

---

## Orchestrator Pseudocode

### Main Orchestrator (`agents/orchestrator.py`)

```python
class AgentOrchestrator:
    """
    Main orchestration engine for complex queries.
    
    Responsibilities:
    1. Classify query complexity
    2. Create execution plans (LLM)
    3. Coordinate task execution
    4. Synthesize final response (LLM)
    """
    
    def __init__(
        self,
        llm_provider_manager: LLMProviderManager,
        tool_registry: ToolRegistry,
        complexity_classifier: ComplexityClassifier,
        executor: TaskExecutor,
        prompt_builder: PromptBuilder,
    ):
        self.llm = llm_provider_manager
        self.tools = tool_registry
        self.classifier = complexity_classifier
        self.executor = executor
        self.prompt_builder = prompt_builder
    
    async def process_query(
        self,
        query: str,
        context: ConversationContext
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Main entry point for agent processing.
        
        Flow:
        1. Classify complexity (LLM)
        2. If simple → route to RAG
        3. If complex → create plan (LLM) → execute → synthesize (LLM)
        """
        
        # LLM CALL #1: Complexity Classification
        classification = await self.classifier.classify(query, context)
        yield AgentEvent.complexity_classified(classification)
        
        if classification.complexity == QueryComplexity.SIMPLE:
            # Route to existing RAG service
            async for event in self._route_to_rag(query, context):
                yield event
            return
        
        # LLM CALL #2: Create Execution Plan
        plan = await self._create_execution_plan(query, context)
        yield AgentEvent.plan_created(plan)
        
        # Execute tasks (may spawn LLM agents)
        task_results = {}
        async for task_event in self.executor.execute_plan(plan, context):
            yield task_event
            
            if task_event.type == AgentEventType.TASK_COMPLETED:
                task_results[task_event.task_id] = task_event.data
        
        # LLM CALL #3: Synthesize Response
        yield AgentEvent.synthesis_started()
        async for chunk in self._synthesize_response(query, plan, task_results):
            yield AgentEvent.response_chunk(chunk)
        
        yield AgentEvent.complete()
    
    async def _create_execution_plan(
        self,
        query: str,
        context: ConversationContext
    ) -> ExecutionPlan:
        """
        LLM creates dynamic execution plan.
        
        LLM CALL: Uses gpt-4o for reasoning capability
        Cost: ~$0.0015
        Time: 400-600ms
        """
        
        # Build prompt with tool descriptions
        prompt = self.prompt_builder.build_planning_prompt(
            query=query,
            context=context,
            available_tools=self.tools.list_all()
        )
        
        # Call LLM with structured output
        result = await self.llm.generate(
            messages=[LLMMessage(role="user", content=prompt)],
            model="gpt-4o",
            temperature=0.2,  # Low temp for consistent planning
            response_format={"type": "json_object"}
        )
        
        if result.is_failure():
            raise PlanningError(result.error)
        
        response = result.unwrap()
        plan_data = json.loads(response.content)
        
        return ExecutionPlan(
            tasks=[AgentTask(**task) for task in plan_data["tasks"]],
            estimated_time_seconds=plan_data["estimated_time_seconds"],
            estimated_cost_usd=plan_data["estimated_cost_usd"],
            reasoning=plan_data["reasoning"]
        )
    
    async def _synthesize_response(
        self,
        query: str,
        plan: ExecutionPlan,
        task_results: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """
        LLM synthesizes final response from task results.
        
        LLM CALL: Uses gpt-4o for quality, streams response
        Cost: ~$0.006
        Time: 1-2 seconds
        """
        
        prompt = self.prompt_builder.build_synthesis_prompt(
            query=query,
            plan=plan,
            results=task_results
        )
        
        async for chunk in self.llm.generate_stream(
            messages=[LLMMessage(role="user", content=prompt)],
            model="gpt-4o",
            temperature=0.7
        ):
            yield chunk.content
```

### Task Executor (`agents/executor.py`)

```python
class TaskExecutor:
    """
    Executes tasks from execution plan.
    
    Responsibilities:
    1. Manage task dependencies
    2. Execute non-LLM tools directly
    3. Spawn LLM agents for LLM-based tasks
    4. Handle errors and retries
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        agent_spawner: AgentSpawner,
    ):
        self.tools = tool_registry
        self.spawner = agent_spawner
    
    async def execute_plan(
        self,
        plan: ExecutionPlan,
        context: ConversationContext
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Execute all tasks in plan, respecting dependencies.
        """
        
        completed_tasks = set()
        task_results = {}
        
        while len(completed_tasks) < len(plan.tasks):
            # Get tasks ready to execute
            executable = plan.get_executable_tasks(completed_tasks)
            
            if not executable:
                # Deadlock - circular dependency
                raise ExecutionError("Circular task dependency detected")
            
            # Execute tasks (could be parallel in future)
            for task in executable:
                yield AgentEvent.task_started(task)
                
                try:
                    if task.requires_llm:
                        # Spawn LLM agent for this task
                        result = await self.spawner.spawn_and_execute(
                            task, task_results, context
                        )
                    else:
                        # Execute tool directly
                        result = await self._execute_tool(task, task_results)
                    
                    task_results[task.task_id] = result
                    completed_tasks.add(task.task_id)
                    
                    yield AgentEvent.task_completed(task, result)
                    
                except Exception as e:
                    yield AgentEvent.task_failed(task, str(e))
                    raise
    
    async def _execute_tool(
        self,
        task: AgentTask,
        previous_results: Dict[str, Any]
    ) -> Any:
        """
        Execute non-LLM tool directly.
        """
        
        tool = self.tools.get_tool(task.tool_name)
        if not tool:
            raise ToolNotFoundError(f"Tool not found: {task.tool_name}")
        
        # Resolve parameters from previous results
        resolved_params = self._resolve_parameters(
            task.parameters,
            previous_results
        )
        
        return await tool.execute(**resolved_params)
```

### Agent Spawner (`agents/agent_spawner.py`)

```python
class AgentSpawner:
    """
    Creates specialized LLM agents for specific tasks.
    
    Each agent is a focused LLM call with task-specific context.
    """
    
    def __init__(
        self,
        llm_provider_manager: LLMProviderManager,
        tool_registry: ToolRegistry,
        prompt_builder: PromptBuilder,
    ):
        self.llm = llm_provider_manager
        self.tools = tool_registry
        self.prompt_builder = prompt_builder
    
    async def spawn_and_execute(
        self,
        task: AgentTask,
        previous_results: Dict[str, Any],
        context: ConversationContext
    ) -> Any:
        """
        Spawn an LLM agent to execute this task.
        
        LLM CALL: Uses gpt-4o-mini for cost efficiency
        Cost: ~$0.0003-0.001 per task
        Time: 500-1500ms
        """
        
        # Get tool
        tool = self.tools.get_tool(task.tool_name)
        if not tool:
            raise ToolNotFoundError(f"Tool not found: {task.tool_name}")
        
        # Build task-specific context
        task_context = self._build_task_context(task, previous_results, context)
        
        # Build agent prompt
        prompt = self.prompt_builder.build_agent_prompt(
            task=task,
            tool=tool,
            context=task_context
        )
        
        # Execute tool with LLM guidance
        result = await tool.execute_with_llm(
            llm_provider=self.llm,
            prompt=prompt,
            parameters=task.parameters,
            context=task_context
        )
        
        return result
    
    def _build_task_context(
        self,
        task: AgentTask,
        previous_results: Dict[str, Any],
        context: ConversationContext
    ) -> Dict[str, Any]:
        """
        Build context for this specific task.
        """
        
        # Get results from dependent tasks
        dependent_results = {
            dep_id: previous_results[dep_id]
            for dep_id in task.depends_on
            if dep_id in previous_results
        }
        
        return {
            "task_description": task.description,
            "dependent_results": dependent_results,
            "conversation_history": context.recent_messages,
            "user_preferences": context.user_preferences,
        }
```

---

## Tool Example: DataExtractionTool

### Tool Implementation (`agents/tools/extraction_tool.py`)

```python
class DataExtractionTool(BaseAgentTool):
    """
    Extracts structured data from documents using LLM.
    
    Example use cases:
    - Extract cholesterol values from health documents
    - Extract income figures from financial documents
    - Extract dates from immigration documents
    """
    
    def __init__(
        self,
        llamaindex_service: LlamaIndexService,
        document_service: DocumentService,
    ):
        self.llamaindex = llamaindex_service
        self.documents = document_service
    
    @property
    def name(self) -> str:
        return "DataExtractionTool"
    
    @property
    def description(self) -> str:
        return """Extract structured data from documents using LLM.
        
        Capabilities:
        - Extract specific fields (dates, amounts, names, etc.)
        - Handle multiple documents in batch
        - Return structured JSON output
        - Validate extracted data against schema
        
        Parameters:
        - document_ids: List of document IDs to process
        - fields: List of field names to extract
        - schema: Optional JSON schema for validation
        """
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "document_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Document IDs to extract from"
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Field names to extract"
                },
                "schema": {
                    "type": "object",
                    "description": "Optional JSON schema for validation"
                }
            },
            "required": ["document_ids", "fields"]
        }
    
    async def execute_with_llm(
        self,
        llm_provider: LLMProviderManager,
        prompt: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute extraction with LLM guidance.
        
        LLM CALL: Uses gpt-4o-mini, batches documents
        Cost: ~$0.0005-0.002 per batch
        Time: 1-3 seconds
        """
        
        document_ids = parameters["document_ids"]
        fields = parameters["fields"]
        schema = parameters.get("schema")
        
        # Fetch documents
        documents = await self.documents.get_documents_batch(document_ids)
        
        # Batch documents (3-5 per LLM call for efficiency)
        batches = self._create_batches(documents, batch_size=3)
        
        # Process batches in parallel
        extraction_tasks = [
            self._extract_batch(
                batch, fields, schema, llm_provider, prompt
            )
            for batch in batches
        ]
        
        batch_results = await asyncio.gather(*extraction_tasks)
        
        # Flatten results
        all_extractions = []
        for batch_result in batch_results:
            all_extractions.extend(batch_result)
        
        return {
            "extractions": all_extractions,
            "document_count": len(documents),
            "field_count": len(fields),
            "success_rate": self._calculate_success_rate(all_extractions)
        }
    
    async def _extract_batch(
        self,
        documents: List[Dict],
        fields: List[str],
        schema: Optional[Dict],
        llm_provider: LLMProviderManager,
        agent_prompt: str
    ) -> List[Dict]:
        """
        Extract data from batch of documents.
        
        This is where the LLM agent does its work.
        """
        
        # Format documents for LLM
        docs_text = "\n\n---\n\n".join([
            f"Document {i+1} (ID: {doc['id']}):\n{doc['text'][:2000]}"
            for i, doc in enumerate(documents)
        ])
        
        # Build extraction prompt
        extraction_prompt = f"""{agent_prompt}

Documents to process:
{docs_text}

Fields to extract: {', '.join(fields)}

{f"Validation schema: {json.dumps(schema, indent=2)}" if schema else ""}

Extract the specified fields from each document. Return JSON array:
[
  {{
    "document_id": "doc_id",
    "extractions": {{
      "field_name": "extracted_value",
      ...
    }},
    "confidence": 0.0-1.0
  }},
  ...
]

Rules:
1. Only extract if clearly stated in document
2. Follow schema types if provided
3. Include confidence score
4. Return empty extractions if field not found"""

        # Call LLM
        result = await llm_provider.generate(
            messages=[LLMMessage(role="user", content=extraction_prompt)],
            model="gpt-4o-mini",
            temperature=0.0,  # Deterministic for extraction
            response_format={"type": "json_object"}
        )
        
        if result.is_failure():
            raise ExtractionError(result.error)
        
        response = result.unwrap()
        return json.loads(response.content)
```

---

## LLM Call Summary

### Where LLMs Are Called

| Component | LLM Call | Model | Purpose | Cost | Time |
|-----------|----------|-------|---------|------|------|
| **ComplexityClassifier** | Required | gpt-4o-mini | Classify simple vs complex | $0.0001 | 200ms |
| **Orchestrator** | Required | gpt-4o | Create execution plan | $0.0015 | 500ms |
| **AgentSpawner** | Per LLM task | gpt-4o-mini | Execute LLM-based tool | $0.0005 | 1000ms |
| **Orchestrator** | Required | gpt-4o | Synthesize final response | $0.006 | 1500ms |

**Total for complex query**: 3-6 LLM calls, $0.008-0.015, 3-8 seconds

### How to Call LLMs

**Use existing `LLMProviderManager`** - it provides:
- ✅ Provider routing
- ✅ Cost tracking
- ✅ Health monitoring
- ✅ Streaming support
- ✅ Error handling

```python
# Example: Orchestrator calling LLM
result = await self.llm_provider_manager.generate(
    messages=[LLMMessage(role="user", content=prompt)],
    model="gpt-4o",
    temperature=0.2,
    response_format={"type": "json_object"}
)

# Example: Streaming synthesis
async for chunk in self.llm_provider_manager.generate_stream(
    messages=[LLMMessage(role="user", content=prompt)],
    model="gpt-4o",
    temperature=0.7
):
    yield chunk.content
```

---

## Deliverables

### Phase 1: Core Infrastructure (Week 1)
- [ ] `agents/models/` - All data models
- [ ] `agents/complexity_classifier.py` - Simple vs complex classification
- [ ] `agents/orchestrator.py` - Main orchestration engine
- [ ] `agents/executor.py` - Task execution coordinator
- [ ] `agents/agent_spawner.py` - Agent creation
- [ ] `agents/utils/prompt_builder.py` - Prompt templates
- [ ] Integration with existing `LLMProviderManager`

### Phase 2: Initial Tools (Week 2)
- [ ] `agents/tools/base.py` - Base tool interface
- [ ] `agents/tools/extraction_tool.py` - Data extraction
- [ ] `agents/tools/timeline_tool.py` - Timeline generation
- [ ] `agents/tools/aggregation_tool.py` - Data aggregation
- [ ] Tool registry integration

### Phase 3: Integration (Week 3)
- [ ] Integrate with `RAGService` for routing
- [ ] Add to `ServiceContainer` initialization
- [ ] Update streaming endpoints
- [ ] Add agent event types to SSE
- [ ] Error handling and recovery

### Phase 4: Testing & Optimization (Week 4)
- [ ] End-to-end testing with real queries
- [ ] Cost monitoring and optimization
- [ ] Performance profiling
- [ ] Documentation
- [ ] Feature flag for gradual rollout

---

## Integration Points

### ServiceContainer

```python
# lifearchivist/server/service_container.py

async def _init_agent_orchestrator(self) -> None:
    from ..agents import AgentOrchestrator, ComplexityClassifier, TaskExecutor, AgentSpawner
    from ..agents.utils import PromptBuilder
    
    prompt_builder = PromptBuilder()
    
    complexity_classifier = ComplexityClassifier(
        llm_provider_manager=self.llm_provider_manager,
        prompt_builder=prompt_builder
    )
    
    agent_spawner = AgentSpawner(
        llm_provider_manager=self.llm_provider_manager,
        tool_registry=self.tool_registry,
        prompt_builder=prompt_builder
    )
    
    executor = TaskExecutor(
        tool_registry=self.tool_registry,
        agent_spawner=agent_spawner
    )
    
    self.agent_orchestrator = AgentOrchestrator(
        llm_provider_manager=self.llm_provider_manager,
        tool_registry=self.tool_registry,
        complexity_classifier=complexity_classifier,
        executor=executor,
        prompt_builder=prompt_builder
    )
```

### RAG Service

```python
# lifearchivist/rag/service.py

async def process_message_with_rag(
    self,
    conversation_id: str,
    message_content: str,
    ...
) -> AsyncGenerator[StreamEvent, None]:
    
    # Check if agent orchestrator available
    if self.agent_orchestrator:
        # Let orchestrator decide routing
        async for event in self.agent_orchestrator.process_query(
            query=message_content,
            context=ConversationContext(...)
        ):
            # Convert agent events to stream events
            yield self._convert_agent_event(event)
        return
    
    # Fallback to existing RAG
    async for event in self._process_with_rag(...):
        yield event
```

---

## Cost & Performance Targets

### Cost Targets
- Simple queries (80%): $0.001-0.002 (existing RAG)
- Complex queries (20%): $0.008-0.015 (agent orchestration)
- **Average**: $0.002-0.004 per query

### Performance Targets
- Complexity classification: <300ms
- Plan creation: <600ms
- Tool execution: 200-500ms per tool
- Response synthesis: 1-2 seconds
- **Total**: 3-8 seconds for complex queries

### Quality Targets
- Complexity classification accuracy: >95%
- Plan execution success rate: >90%
- User satisfaction: >4.5/5

---

## Future Enhancements

### Phase 5+
- Parallel task execution
- Tool result caching
- Plan optimization based on historical data
- Custom tool creation via UI
- Multi-agent collaboration
- Long-running workflows with checkpointing
