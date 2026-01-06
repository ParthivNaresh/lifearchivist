# LifeArchivist Agent Orchestration System

## System Overview

LifeArchivist implements a **hierarchical multi-phase agent orchestration system** with factory-based resource isolation. Complex queries are decomposed into strategic phases, each executed by an isolated tactical planner with independent resources.

---

## Architecture Flow

```
USER QUERY
    ↓
GatewayStreamProcessor (gateway.py)
    ├─ ComplexityClassifier
    ├─ SIMPLE → DirectStreamProcessor (RAG)
    └─ COMPLEX → PhaseCoordinator
                    ↓
            StrategicPlanner (strategic_planner.py)
                    ↓
            Creates StrategicPlan with 3-7 phases
                    ↓
            PhaseCoordinator executes each phase:
                    ↓
            ┌───────┴───────┬───────────┬───────────┐
            ▼               ▼           ▼           ▼
        PHASE 1         PHASE 2     PHASE 3     SYNTHESIS
            ↓               ↓           ↓           ↓
    TacticalPlannerFactory.create() [NEW instance per phase]
            ↓
    TacticalPlanner (tactical_planner.py)
        ├─ create_tactical_plan() → ExecutionPlan (task DAG)
        └─ TaskExecutor.execute_plan()
                ↓
        ┌───────┴───────┬───────────┐
        ▼               ▼           ▼
    TASK 1          TASK 2      TASK 3
        ↓               ↓           ↓
    AgentSpawner (agent_spawner.py)
        ↓
    Tool Execution (via AgentToolRegistry)
        ├─ document_search
        ├─ text_extraction
        └─ structured_extraction
                ↓
        Task Results → Phase Results → Final Synthesis
```

---

## Core Components

### 1. GatewayStreamProcessor
**File:** `lifearchivist/llm/processors/gateway.py`
**Entry Point:** `async def process(context: StreamContext)`

**Flow:**
1. Receives user query
2. Classifies complexity: `ComplexityClassifier.classify()`
3. Routes based on complexity:
   - `simple` → `DirectStreamProcessor` (RAG)
   - `complex/medium` → `PhaseCoordinator.execute_query()`

**Key Code:**
```python
classification = await classifier.classify(query, agent_ctx)
if classification.complexity.value == "simple":
    # RAG path
else:
    coordinator = self.server.service_container.phase_coordinator
    async for ev in coordinator.execute_query(query, agent_ctx):
        # Stream events
```

---

### 2. PhaseCoordinator
**File:** `lifearchivist/llm/agent/phase_coordinator.py`
**Entry Point:** `async def execute_query(query: str, context: ConversationContext)`

**Responsibilities:**
- Orchestrates multi-phase execution
- Creates isolated TacticalPlanner per phase via factory
- Manages phase dependencies
- Aggregates results
- Synthesizes final response

**Flow:**
```python
# 1. Strategic Planning
strategic_plan = await self.strategic_planner.create_strategic_plan(query, context)

# 2. Execute each phase sequentially
for phase in strategic_plan.phases:
    # Check dependencies
    if not phase.is_ready(completed_phases):
        raise error
    
    # Execute phase with NEW tactical planner
    phase_result = await self._execute_phase(phase, ...)
    phase_results[phase.phase_id] = phase_result
    completed_phases.add(phase.phase_id)

# 3. Synthesize final response
synthesis_planner = self.tactical_planner_factory.create()
async for chunk in synthesis_planner._synthesize_response(...):
    yield AgentEvent.response_chunk(chunk)
```

**Key Method:** `_execute_phase()`
```python
async def _execute_phase(phase, ...):
    # Create NEW isolated tactical planner
    tactical_planner = self.tactical_planner_factory.create()
    
    # Build phase-specific query
    phase_query = self._build_phase_query(phase, query, previous_results)
    
    # Filter tools for this phase
    available_tools = self._filter_tools_for_phase(phase, tactical_planner)
    
    # Create tactical plan
    execution_plan = await tactical_planner.create_tactical_plan(
        query=phase_query,
        context=context,
        available_tools=available_tools
    )
    
    # Execute tasks
    async for ev in tactical_planner.executor.execute_plan(execution_plan, context):
        if ev.type == AgentEventType.TASK_COMPLETED:
            phase_task_results[ev.task_id] = ev.data
    
    return phase_task_results
```

---

### 3. StrategicPlanner
**File:** `lifearchivist/llm/agent/strategic_planner.py`
**Entry Point:** `async def create_strategic_plan(query: str, context: ConversationContext)`

**Responsibilities:**
- Decomposes complex queries into 3-7 high-level phases
- Assigns required tools to each phase
- Estimates complexity per phase
- Defines phase dependencies

**Output:** `StrategicPlan`
```python
@dataclass
class StrategicPlan:
    strategy: str                    # Overall strategy description
    phases: List[StrategicPhase]     # 3-7 phases
    estimated_time_seconds: int
    estimated_cost_usd: float

@dataclass
class StrategicPhase:
    phase_id: str                    # Unique identifier
    description: str                 # What this phase does
    required_tools: List[str]        # Tools needed
    depends_on: List[str]            # Phase dependencies
    estimated_complexity: PhaseComplexity  # SIMPLE/MEDIUM/COMPLEX
```

**Example Output:**
```python
StrategicPlan(
    strategy="Multi-phase document discovery and data extraction",
    phases=[
        StrategicPhase(
            phase_id="discover",
            description="Find blood test documents from 2024",
            required_tools=["document_search"],
            depends_on=[],
            estimated_complexity=PhaseComplexity.SIMPLE
        ),
        StrategicPhase(
            phase_id="extract",
            description="Extract cholesterol and glucose levels",
            required_tools=["structured_extraction"],
            depends_on=["discover"],
            estimated_complexity=PhaseComplexity.MEDIUM
        )
    ]
)
```

---

### 4. TacticalPlannerFactory
**File:** `lifearchivist/llm/agent/tactical_planner_factory.py`
**Entry Point:** `def create() -> TacticalPlanner`

**Responsibilities:**
- Creates isolated TacticalPlanner instances
- Each instance has independent resources:
  - `TaskExecutor` (own concurrency limits)
  - `AgentSpawner`
  - `PlanValidator`

**Why Factory Pattern:**
- **Phase Isolation:** No state pollution between phases
- **Resource Control:** Each phase has independent limits
- **Parallel-Ready:** Can add parallel execution later
- **Testable:** Easy to verify isolation

**Configuration:**
```python
TacticalPlannerFactory(
    llm_provider_manager=...,
    tool_registry=...,
    prompt_builder=...,
    complexity_classifier=...,
    max_concurrency=32,                      # Global task limit
    per_tool_limits={"structured_extraction": 8},  # Per-tool limits
    max_tasks=20,                            # Max tasks per plan
    max_cost_usd=1.0,                        # Cost limit
    max_time_seconds=300                     # Time limit
)
```

---

### 5. TacticalPlanner
**File:** `lifearchivist/llm/agent/tactical_planner.py`
**Entry Point:** `async def create_tactical_plan(query, context, available_tools)`

**Responsibilities:**
- Converts goals (phase descriptions) into task DAGs
- Validates plans
- Executes tasks via TaskExecutor
- Synthesizes responses

**Flow:**
```python
# 1. Create tactical plan (task DAG)
execution_plan = await create_tactical_plan(query, context, available_tools)

# 2. Validate plan
validator.validate(execution_plan)

# 3. Execute tasks
async for event in executor.execute_plan(execution_plan, context):
    yield event

# 4. Synthesize response
async for chunk in _synthesize_response(query, plan, task_results):
    yield chunk
```

**Output:** `ExecutionPlan`
```python
@dataclass
class ExecutionPlan:
    tasks: List[AgentTask]           # Task DAG
    estimated_time_seconds: int
    estimated_cost_usd: float
    reasoning: str                   # Plan explanation

@dataclass
class AgentTask:
    task_id: str                     # Unique identifier
    tool_name: str                   # Tool to execute
    description: str                 # Task description
    requires_llm: bool               # Needs LLM?
    parameters: Dict[str, Any]       # Tool parameters
    depends_on: List[str]            # Task dependencies
```

---

### 6. TaskExecutor
**File:** `lifearchivist/llm/agent/executor.py`
**Entry Point:** `async def execute_plan(plan: ExecutionPlan, context: ConversationContext)`

**Responsibilities:**
- Manages task dependencies (DAG execution)
- Concurrent task execution (respects limits)
- Spawns agents for each task
- Streams execution events

**Key Features:**
- Topological sort for dependency resolution
- Semaphore-based concurrency control
- Per-tool concurrency limits
- Fail-fast or continue-on-error modes

**Flow:**
```python
# 1. Resolve dependencies (topological sort)
execution_order = self._topological_sort(plan.tasks)

# 2. Execute tasks concurrently (respecting dependencies)
for task in execution_order:
    # Wait for dependencies
    await wait_for_dependencies(task.depends_on)
    
    # Acquire semaphore (concurrency control)
    async with self.semaphore:
        # Spawn agent and execute
        result = await self.spawner.spawn_and_execute(task, context)
        task_results[task.task_id] = result
        
        yield AgentEvent.task_completed(task.task_id, result)
```

---

### 7. AgentSpawner
**File:** `lifearchivist/llm/agent/agent_spawner.py`
**Entry Point:** `async def spawn_and_execute(task: AgentTask, context: ConversationContext)`

**Responsibilities:**
- Creates agent for each task
- Executes tool with or without LLM
- Handles retries and timeouts
- Returns task results

**Flow:**
```python
# 1. Get tool from registry
tool = self.tool_registry.get_tool(task.tool_name)

# 2. Execute based on LLM requirement
if task.requires_llm:
    result = await tool.execute_with_llm(
        llm_provider=self.llm_provider_manager,
        prompt=task.description,
        params=task.parameters,
        context={"task_description": task.description}
    )
else:
    result = await tool.execute_typed(
        params=task.parameters,
        context={"task_description": task.description}
    )

return result
```

---

### 8. AgentToolRegistry
**File:** `lifearchivist/llm/agent/tool_registry.py`

**Responsibilities:**
- Registers all available tools
- Provides tool lookup
- Validates tool availability

**Available Tools:**

#### Tool 1: document_search
**File:** `lifearchivist/llm/agent/tools/search/document_search_tool.py`
**Purpose:** Find documents using semantic, keyword, hybrid, or metadata search

**Parameters:**
```python
class DocumentSearchParams:
    query: str
    search_method: SearchMethod  # semantic | keyword | hybrid | metadata
    top_k: int = 10
    semantic_weight: float = 0.6
    similarity_threshold: float = 0.5
    mime_types: Optional[List[str]] = None
    themes: Optional[List[str]] = None
    date_filter: Optional[DateFilter] = None
    allow_rerank: bool = False
```

**Returns:**
```python
{
    "documents": [
        {
            "document_id": str,
            "score": float,
            "search_type": str,
            "metadata": dict,
            "text_preview": str
        }
    ],
    "metrics": {
        "total_found": int,
        "returned": int,
        "search_method": str,
        "avg_score": float
    }
}
```

#### Tool 2: text_extraction
**File:** `lifearchivist/llm/agent/tools/text_extraction/text_extraction.py`
**Purpose:** Extract and summarize text from documents

**Parameters:**
```python
class TextExtractionParams:
    document_ids: List[str]
    summary_style: SummaryStyle  # brief | detailed | bullet_points
    summary_focus: SummaryFocus  # general | key_points | action_items
    max_length: Optional[int] = None
```

#### Tool 3: structured_extraction
**File:** `lifearchivist/llm/agent/tools/structured_extraction/structured_extraction.py`
**Purpose:** Extract structured data from documents using LLM

**Parameters:**
```python
class StructuredExtractionParams:
    document_ids: List[str]
    schema: Dict[str, Any]  # JSON schema
    instructions: str
    filters: Optional[ExtractionFilters] = None
```

---

## Complete Example: Blood Test Query

### User Query
```
"Find all my blood test results from 2024, extract cholesterol and glucose levels, 
and create a summary showing trends over time"
```

### Execution Flow

#### Step 1: Gateway Classification
```python
# gateway.py: process()
classification = await classifier.classify(query, context)
# Result: complexity="complex", confidence=0.85, estimated_steps=4
# Routes to: phase_coordinator.execute_query()
```

#### Step 2: Strategic Planning
```python
# strategic_planner.py: create_strategic_plan()
strategic_plan = StrategicPlan(
    strategy="Multi-phase document discovery, extraction, and analysis",
    phases=[
        StrategicPhase(
            phase_id="discover",
            description="Find blood test documents from 2024",
            required_tools=["document_search"],
            depends_on=[],
            estimated_complexity=PhaseComplexity.SIMPLE
        ),
        StrategicPhase(
            phase_id="extract",
            description="Extract cholesterol and glucose levels",
            required_tools=["structured_extraction"],
            depends_on=["discover"],
            estimated_complexity=PhaseComplexity.MEDIUM
        ),
        StrategicPhase(
            phase_id="analyze",
            description="Analyze trends and create summary",
            required_tools=["text_extraction"],
            depends_on=["extract"],
            estimated_complexity=PhaseComplexity.SIMPLE
        )
    ]
)
```

#### Step 3: Phase 1 Execution (Discover)
```python
# phase_coordinator.py: _execute_phase()
tactical_planner_1 = factory.create()  # NEW isolated instance

# tactical_planner.py: create_tactical_plan()
plan_1 = ExecutionPlan(
    tasks=[
        AgentTask(
            task_id="search_blood_tests",
            tool_name="document_search",
            parameters={
                "query": "blood test cholesterol glucose",
                "search_method": "hybrid",
                "date_filter": {"after": "2024-01-01"},
                "top_k": 20
            },
            depends_on=[]
        )
    ]
)

# executor.py: execute_plan()
# spawner.py: spawn_and_execute()
# document_search_tool.py: execute_with_llm()
results_1 = {
    "search_blood_tests": {
        "documents": [
            {"document_id": "doc_123", "score": 0.92},
            {"document_id": "doc_456", "score": 0.88}
        ]
    }
}
```

#### Step 4: Phase 2 Execution (Extract)
```python
# phase_coordinator.py: _execute_phase()
tactical_planner_2 = factory.create()  # NEW isolated instance

# tactical_planner.py: create_tactical_plan()
plan_2 = ExecutionPlan(
    tasks=[
        AgentTask(
            task_id="extract_lab_values",
            tool_name="structured_extraction",
            parameters={
                "document_ids": ["doc_123", "doc_456"],
                "schema": {
                    "type": "object",
                    "properties": {
                        "test_date": {"type": "string"},
                        "cholesterol": {"type": "number"},
                        "glucose": {"type": "number"}
                    }
                },
                "instructions": "Extract cholesterol and glucose with dates"
            },
            depends_on=[]
        )
    ]
)

# structured_extraction_tool.py: execute_with_llm()
results_2 = {
    "extract_lab_values": {
        "extracted_data": [
            {
                "document_id": "doc_123",
                "data": {
                    "test_date": "2024-03-15",
                    "cholesterol": 185,
                    "glucose": 92
                }
            }
        ]
    }
}
```

#### Step 5: Phase 3 Execution (Analyze)
```python
# phase_coordinator.py: _execute_phase()
tactical_planner_3 = factory.create()  # NEW isolated instance

# Similar flow...
results_3 = {
    "analyze_trends": {
        "summary": "Cholesterol improved from 210 to 185..."
    }
}
```

#### Step 6: Final Synthesis
```python
# phase_coordinator.py: execute_query()
synthesis_planner = factory.create()  # NEW instance

# tactical_planner.py: _synthesize_response()
final_response = """
Based on your blood test results from 2024:

**Documents Found:** 5 blood test reports

**Cholesterol Trends:**
- March: 210 mg/dL → September: 185 mg/dL (↓ Improving)

**Glucose Trends:**
- March: 98 mg/dL → September: 89 mg/dL (↓ Improving)

Your levels are trending positively...
"""
```

---

## Event Streaming

All components yield `AgentEvent` objects for real-time progress:

```python
class AgentEventType(Enum):
    PLAN_CREATED = "plan_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    PLAN_FAILED = "plan_failed"
    SYNTHESIS_STARTED = "synthesis_started"
    RESPONSE_CHUNK = "response_chunk"
    ERROR = "error"
    COMPLETE = "complete"
```

---

## Key Design Principles

### 1. Factory Pattern for Isolation
Each phase gets completely isolated resources:
- ✅ Independent TaskExecutor (own concurrency limits)
- ✅ Independent AgentSpawner
- ✅ Independent PlanValidator
- ✅ No shared state between phases

### 2. Hierarchical Planning
- **Strategic:** High-level phases (what to do)
- **Tactical:** Detailed tasks (how to do it)
- Separation enables better planning and resource allocation

### 3. Resource Management
- Global concurrency limits: `max_concurrency=32`
- Per-tool limits: `{"structured_extraction": 8}`
- Timeout handling: `task_timeout_s=60.0`
- Retry logic: `max_retries=2`

### 4. Dependency Management
- Phase-level dependencies (strategic)
- Task-level dependencies (tactical)
- Topological sort for execution order
- Concurrent execution where possible

---

## File Reference

### Core Orchestration
| File | Purpose | Key Method |
|------|---------|------------|
| `gateway.py` | Entry point, routing | `process()` |
| `phase_coordinator.py` | Multi-phase coordination | `execute_query()` |
| `strategic_planner.py` | Strategic planning | `create_strategic_plan()` |
| `tactical_planner.py` | Tactical planning | `create_tactical_plan()` |
| `tactical_planner_factory.py` | Factory pattern | `create()` |
| `executor.py` | Task execution | `execute_plan()` |
| `agent_spawner.py` | Agent creation | `spawn_and_execute()` |
| `tool_registry.py` | Tool management | `get_tool()` |

### Supporting
| File | Purpose |
|------|---------|
| `complexity_classifier.py` | Query classification |
| `plan_validator.py` | Plan validation |
| `utils/prompt_builder.py` | Prompt generation |

### Models
| File | Models |
|------|--------|
| `models/strategic_plan.py` | `StrategicPlan`, `StrategicPhase`, `PhaseComplexity` |
| `models/task.py` | `AgentTask`, `ExecutionPlan` |
| `models/context.py` | `ConversationContext` |
| `models/events.py` | `AgentEvent`, `AgentEventType` |

### Tools
| File | Tool |
|------|------|
| `tools/search/document_search_tool.py` | `document_search` |
| `tools/text_extraction/text_extraction.py` | `text_extraction` |
| `tools/structured_extraction/structured_extraction.py` | `structured_extraction` |

---

## Initialization

**File:** `lifearchivist/server/service_container.py`
**Method:** `init_agent_orchestrator()`

```python
# 1. Create shared components
tool_registry = AgentToolRegistry(...)
prompt_builder = PromptBuilder()
complexity_classifier = ComplexityClassifier(...)

# 2. Create factory
tactical_planner_factory = TacticalPlannerFactory(
    llm_provider_manager=self.llm_provider_manager,
    tool_registry=tool_registry,
    prompt_builder=prompt_builder,
    complexity_classifier=complexity_classifier,
    max_concurrency=32,
    per_tool_limits={"structured_extraction": 8},
)

# 3. Create strategic planner
strategic_planner = StrategicPlanner(
    llm_provider_manager=self.llm_provider_manager,
    tool_registry=tool_registry,
    prompt_builder=prompt_builder,
    max_phases=7,
)

# 4. Create phase coordinator
self.phase_coordinator = PhaseCoordinator(
    strategic_planner=strategic_planner,
    tactical_planner_factory=tactical_planner_factory,
)

# 5. Create single tactical planner for direct queries (optional)
self.tactical_planner = tactical_planner_factory.create()
```

---

## Summary

LifeArchivist's agent orchestration implements **production-grade hierarchical planning** with:

✅ **Intelligent Routing:** Simple → RAG, Complex → Hierarchical
✅ **Strategic Planning:** 3-7 high-level phases
✅ **Tactical Planning:** Detailed task DAGs per phase
✅ **Factory Pattern:** Isolated resources per phase
✅ **Concurrent Execution:** Configurable limits, dependency management
✅ **Event Streaming:** Real-time progress updates
✅ **3 Powerful Tools:** Search, extraction, analysis
✅ **Production Ready:** Error handling, retries, timeouts, observability

This architecture enables complex multi-step queries while maintaining performance, scalability, and reliability.
