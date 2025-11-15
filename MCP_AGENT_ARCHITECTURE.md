# Production-Grade MCP Agent Architecture

## Executive Summary

Transform Life Archivist from simple RAG (retrieve context → generate response) to intelligent agent (analyze intent → plan execution → orchestrate tools → synthesize response).

**Architectural Decision**: Tightly integrated service within existing FastAPI application (NOT separate microservice).

**Rationale**: 
- 10-100x faster (direct function calls vs HTTP)
- Shared connection pools and resources
- Atomic transactions across tools
- Single deployment unit
- Industry standard (Notion AI, Slack AI, GitHub Copilot all use integrated approach)

---

## System Architecture

```
FastAPI Application
├── ServiceContainer (existing)
│   ├── Redis, Qdrant, PostgreSQL
│   ├── Vault, DocTracker, BM25
│   ├── LlamaIndex, RAG Service
│   ├── LLM Provider Manager
│   └── Tool Registry
│
├── AgentOrchestrator (NEW)
│   ├── Intent Classification
│   ├── Task Planning
│   ├── Tool Execution
│   └── Response Synthesis
│
├── AgentToolAdapter (NEW)
│   └── Wraps existing tools for agent use
│
└── Agent Tools (NEW)
    ├── DocumentAnalysisTool
    ├── TimelineGeneratorTool
    ├── DataExtractionTool
    ├── ThemeFilterTool
    ├── DateRangeTool
    ├── AggregationTool
    └── VisualizationTool
```

---

## Query Routing & LLM Usage

### **Complete Request Flow**

```
User Query → FastAPI → StreamingService → RAGService.process_message_with_rag()
                                              ↓
                                    ┌─────────┴─────────┐
                                    │                   │
                            [LLM Call #1: Intent Classification - OPTIONAL]
                            Model: gpt-4o-mini
                            Tokens: ~100 input, ~50 output
                            Cost: $0.0001
                            Time: 200-300ms
                            Frequency: 1-5% (heuristics handle 95%+)
                                    │                   │
                                    ├─ Simple Query ────┤
                                    │   (80% of queries)│
                                    │                   │
                                    └→ Existing RAG ────┘
                                         (no changes)
                                    
                                    ├─ Complex Query ───┤
                                    │   (15% of queries)│
                                    │                   │
                                    └→ AgentOrchestrator
                                              ↓
                            [LLM Call #2: Task Planning - REQUIRED]
                            Model: gpt-4o
                            Tokens: ~300 input, ~200 output
                            Cost: $0.0015
                            Time: 400-600ms
                            Purpose: Decompose query into tool execution plan
                            Output: Structured JSON with tool sequence
                                              ↓
                                    Tool Execution Loop
                                    (NO LLM for most tools)
                                              ↓
                            ┌─────────────────┴─────────────────┐
                            │                                   │
                    Non-LLM Tools                      LLM-Based Tools
                    (ThemeFilter,                      (DataExtraction)
                     DateRange,                               ↓
                     Aggregation,              [LLM Call #3: Data Extraction]
                     Timeline,                 Model: gpt-4o-mini (batched)
                     Visualization)            Tokens: ~500 input × N docs
                    Cost: $0                   Cost: $0.004
                    Time: 50-200ms each        Time: 2-3 seconds
                            │                                   │
                            └─────────────────┬─────────────────┘
                                              ↓
                            [LLM Call #4: Response Synthesis - REQUIRED]
                            Model: gpt-4o (streaming)
                            Tokens: ~800 input, ~400 output
                            Cost: $0.006
                            Time: 1-2 seconds
                            Purpose: Generate natural language response
                            Input: Tool results + reasoning trace
                                              ↓
                                    Stream to User (SSE)
```

### **Intent Classification: Two-Tier Approach**

**Tier 1: Heuristic Classification (99% of queries, 0ms, $0)**

```python
class IntentClassifier:
    def _heuristic_classify(self, query: str) -> QueryIntent:
        query_lower = query.lower()
        
        # Simple RAG patterns (80% of queries)
        simple_patterns = [
            r"^what (is|are|was|were)",
            r"^who (is|are|was|were)",
            r"^when (did|was|is)",
            r"tell me about",
            r"explain",
            r"summarize",
        ]
        
        if any(re.search(p, query_lower) for p in simple_patterns):
            if len(query.split()) < 15:
                return QueryIntent(type=IntentType.SIMPLE_RAG, confidence=0.90)
        
        # Agent patterns (15% of queries)
        agent_patterns = [
            (r"(create|generate|make).*(timeline|chart|graph)", 
             IntentType.COMPLEX_ANALYSIS),
            (r"(compare|contrast).*(between|across|over time)", 
             IntentType.COMPARATIVE_ANALYSIS),
            (r"(find|identify).*(and|then).*(extract|calculate)", 
             IntentType.MULTI_STEP),
            (r"(aggregate|sum|total|average).*(by|across)", 
             IntentType.AGGREGATION),
        ]
        
        for pattern, intent_type in agent_patterns:
            if re.search(pattern, query_lower):
                return QueryIntent(type=intent_type, confidence=0.88)
        
        # Ambiguous (5%) - needs LLM
        return QueryIntent(type=IntentType.UNKNOWN, confidence=0.50)
```

**Tier 2: LLM Classification (1-5% of queries, 200-500ms, $0.0001)**

```python
async def _llm_classify(self, query: str) -> QueryIntent:
    prompt = f"""Classify this query's intent and complexity.

Query: "{query}"

Respond with JSON:
{{
  "intent_type": "simple_rag" | "complex_analysis" | "multi_step",
  "confidence": 0.0-1.0,
  "requires_agent": true | false,
  "estimated_tools_needed": 0-10
}}"""

    response = await self.llm_provider.generate(
        messages=[LLMMessage(role="user", content=prompt)],
        model="gpt-4o-mini",
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    
    return QueryIntent.from_json(response.content)
```

---

## Core Components

### **1. AgentOrchestrator** (`lifearchivist/agents/orchestrator.py`)

Main agent coordination engine.

```python
class AgentOrchestrator:
    def __init__(
        self,
        tool_registry: ToolRegistry,
        llm_provider_manager: LLMProviderManager,
        search_service: SearchService,
    ):
        self.tool_registry = tool_registry
        self.llm_provider = llm_provider_manager
        self.search_service = search_service
        self.intent_classifier = IntentClassifier(llm_provider_manager)
        self.planner = AgentPlanner(llm_provider_manager)
        self.executor = ToolExecutor()
        self.synthesizer = ResponseSynthesizer(llm_provider_manager)
    
    async def process_query(
        self,
        query: str,
        context: AgentContext
    ) -> AsyncGenerator[AgentEvent, None]:
        # 1. Classify intent (heuristic + optional LLM)
        intent = await self.intent_classifier.classify_intent(query)
        yield AgentEvent.intent_classified(intent)
        
        # 2. Create execution plan (LLM)
        plan = await self.planner.create_plan(intent, context)
        yield AgentEvent.plan_created(plan)
        
        # 3. Execute tools (parallel where possible)
        async for tool_event in self.executor.execute_plan(plan):
            yield tool_event
        
        # 4. Synthesize response (LLM streaming)
        async for synthesis_event in self.synthesizer.synthesize(
            query, self.executor.results, plan.reasoning_trace
        ):
            yield synthesis_event
```

### **2. AgentPlanner** (`lifearchivist/agents/planner.py`)

Creates execution plans using LLM with structured output.

```python
class AgentPlanner:
    async def create_plan(
        self,
        intent: QueryIntent,
        context: AgentContext
    ) -> ExecutionPlan:
        tool_descriptions = self._format_tool_descriptions(
            context.available_tools
        )
        
        prompt = f"""Create an execution plan to answer this query.

Query: "{context.query}"
Intent: {intent.type.value}

Available Tools:
{tool_descriptions}

Respond with JSON:
{{
  "steps": [
    {{
      "step_number": 1,
      "tool_name": "ThemeFilterTool",
      "description": "Filter documents by theme",
      "parameters": {{"theme": "Healthcare"}},
      "depends_on": [],
      "can_run_parallel": false
    }}
  ],
  "total_estimated_time_ms": 5000,
  "confidence": 0.9
}}"""

        response = await self.llm_provider.generate(
            messages=[LLMMessage(role="user", content=prompt)],
            model="gpt-4o",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        return ExecutionPlan.from_json(response.content)
```

### **3. Agent Tools** (`lifearchivist/agents/tools/`)

#### **ThemeFilterTool** (No LLM)
```python
class ThemeFilterTool(AgentTool):
    async def execute(self, theme: str, subthemes: List[str] = None) -> AgentToolResult:
        # Query Redis metadata index
        filters = {"theme": theme}
        if subthemes:
            filters["subthemes"] = {"$in": subthemes}
        
        result = await self.llamaindex_service.query_documents_by_metadata(
            filters=filters
        )
        
        return AgentToolResult(
            success=True,
            data={"document_ids": result.value, "count": len(result.value)},
            tokens_used=0,
            execution_time_ms=...
        )
```

#### **DataExtractionTool** (LLM-based, batched)
```python
class DataExtractionTool(AgentTool):
    async def execute(
        self,
        document_ids: List[str],
        field: str,
        schema: Dict[str, Any]
    ) -> AgentToolResult:
        documents = await self._get_documents(document_ids)
        
        # Batch documents (3-5 per LLM call)
        batches = self._create_batches(documents, batch_size=3)
        
        # Process batches in parallel
        batch_results = await asyncio.gather(*[
            self._extract_batch(batch, field, schema)
            for batch in batches
        ])
        
        all_extractions = [item for batch in batch_results for item in batch]
        
        return AgentToolResult(
            success=True,
            data={"extractions": all_extractions},
            tokens_used=sum(r.tokens for r in batch_results)
        )
    
    async def _extract_batch(
        self,
        documents: List[Dict],
        field: str,
        schema: Dict
    ) -> List[Dict]:
        docs_text = "\n\n---\n\n".join([
            f"Document {i+1} (ID: {doc['id']}):\n{doc['text'][:2000]}"
            for i, doc in enumerate(documents)
        ])
        
        prompt = f"""Extract "{field}" from these documents.

{docs_text}

Schema: {json.dumps(schema, indent=2)}

Respond with JSON array:
[
  {{
    "document_id": "doc_id",
    "field": "{field}",
    "value": <extracted_value>,
    "confidence": 0.0-1.0
  }}
]"""

        response = await self.llm_provider.generate(
            messages=[LLMMessage(role="user", content=prompt)],
            model="gpt-4o-mini",
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.content)
```

#### **TimelineGeneratorTool** (No LLM)
```python
class TimelineGeneratorTool(AgentTool):
    async def execute(
        self,
        data: List[Dict],
        data_type: str = "numeric",
        format: str = "chart_js"
    ) -> AgentToolResult:
        # Pure data transformation, no LLM
        validated_data = self._validate_and_sort(data)
        chart_config = self._generate_chart_config(validated_data, format)
        
        return AgentToolResult(
            success=True,
            data={"timeline": chart_config, "data_points": len(validated_data)},
            tokens_used=0
        )
```

### **4. ResponseSynthesizer** (`lifearchivist/agents/synthesizer.py`)

Generates final response using LLM streaming.

```python
class ResponseSynthesizer:
    async def synthesize(
        self,
        query: str,
        tool_results: List[AgentToolResult],
        reasoning_trace: List[str]
    ) -> AsyncGenerator[str, None]:
        results_summary = "\n\n".join([
            f"Tool: {r.tool_name}\nResult: {json.dumps(r.data, indent=2)}"
            for r in tool_results
        ])
        
        prompt = f"""Answer the user's query using the tool execution results.

User Query: "{query}"

Tool Results:
{results_summary}

Generate a comprehensive response that:
1. Directly answers the query
2. Presents data clearly (use markdown)
3. Provides insights
4. Is conversational

Do NOT mention tool names or technical details."""

        async for chunk in self.llm_provider.generate_stream(
            messages=[LLMMessage(role="user", content=prompt)],
            model="gpt-4o",
            temperature=0.7
        ):
            yield chunk.content
```

---

## Integration Points

### **1. ServiceContainer** (`server/service_container.py`)

```python
async def _init_agent_orchestrator(self) -> None:
    from ..agents import AgentOrchestrator
    
    self.agent_orchestrator = AgentOrchestrator(
        tool_registry=self.tool_registry,
        llm_provider_manager=self.llm_provider_manager,
        search_service=self.llamaindex_service.search_service,
    )
    
    await self.agent_orchestrator.initialize()
```

### **2. RAG Service** (`rag/service.py`)

```python
class ConversationRAGService:
    def __init__(self, ..., agent_orchestrator: Optional[AgentOrchestrator] = None):
        self.agent_orchestrator = agent_orchestrator
        self.intent_classifier = IntentClassifier(provider_manager)
    
    async def process_message_with_rag(
        self,
        conversation_id: str,
        message_content: str,
        ...
    ) -> AsyncGenerator[StreamEvent, None]:
        # Classify intent
        intent = await self.intent_classifier.classify_intent(message_content)
        
        # Route to agent if needed
        if intent.requires_agent and self.agent_orchestrator:
            async for event in self._process_with_agent(
                conversation_id, message_content, intent
            ):
                yield event
            return
        
        # Existing RAG flow (unchanged)
        async for event in self._process_with_rag(...):
            yield event
```

### **3. Streaming Endpoint** (`server/api/routes/conversations/messages_stream.py`)

```python
class AgentStreamProcessor(StreamProcessor):
    async def process(self, context: StreamContext) -> AsyncGenerator[str, None]:
        agent_context = AgentContext(
            conversation_id=context.conversation_id,
            user_id="default",
            query=context.request.content,
            conversation_history=await self._get_history(context.conversation_id),
        )
        
        async for agent_event in self.agent_orchestrator.process_query(agent_context):
            yield self._format_agent_event(agent_event)
```

---

## Streaming Events

```python
class AgentEventType(Enum):
    INTENT_CLASSIFIED = "intent_classified"
    PLAN_CREATED = "plan_created"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"
    SYNTHESIS_STARTED = "synthesis_started"
    RESPONSE_CHUNK = "response_chunk"
    COMPLETE = "complete"
    ERROR = "error"
```

**SSE Stream Example:**
```
event: intent_classified
data: {"type": "complex_analysis", "confidence": 0.95}

event: plan_created
data: {"stages": 4, "estimated_time_ms": 5000}

event: tool_started
data: {"tool": "ThemeFilterTool", "params": {"theme": "Healthcare"}}

event: tool_completed
data: {"tool": "ThemeFilterTool", "result": {"count": 15}, "time_ms": 250}

event: synthesis_started
data: {"tool_results": 4}

event: response_chunk
data: {"text": "I've analyzed"}

event: complete
data: {"total_time_ms": 5200, "tools_used": 4, "tokens_used": 850}
```

---

## Performance Optimizations

### **1. Multi-Level Caching**

```python
class AgentCache:
    # L1: In-memory LRU (1000 entries)
    intent_cache: Dict[str, QueryIntent]
    plan_cache: Dict[str, ExecutionPlan]
    
    # L2: Redis (1 hour TTL)
    extraction_cache: RedisCache
    
    # L3: PostgreSQL (persistent)
    historical_executions: PostgresCache
```

### **2. Parallel Execution**

```python
class ToolExecutor:
    async def execute_plan(self, plan: ExecutionPlan) -> AsyncGenerator[AgentEvent, None]:
        for stage in plan.stages:
            # Identify independent tools in this stage
            independent_tools = [t for t in stage.tools if not t.depends_on]
            
            # Execute in parallel
            results = await asyncio.gather(*[
                tool.execute(**tool.params)
                for tool in independent_tools
            ])
            
            for result in results:
                yield AgentEvent.tool_completed(result)
```

### **3. Resource Limits**

```python
class ResourceManager:
    max_concurrent_tools: int = 5
    max_llm_calls_per_query: int = 10
    max_execution_time_seconds: int = 60
    max_tokens_per_query: int = 10000
```

---

## Error Handling

### **Tool Failure Recovery**

```python
class ErrorRecoveryStrategy:
    async def handle_tool_failure(
        self,
        tool: AgentTool,
        error: Exception,
        context: AgentContext
    ) -> RecoveryAction:
        if isinstance(error, TransientError):
            return RecoveryAction.RETRY
        
        if alternative := self._find_alternative_tool(tool):
            return RecoveryAction.USE_ALTERNATIVE(alternative)
        
        if tool.is_optional:
            return RecoveryAction.SKIP
        
        return RecoveryAction.FAIL_GRACEFULLY
```

### **Partial Results**

```python
class PartialResultHandler:
    async def synthesize_partial_response(
        self,
        completed_tools: List[AgentToolResult],
        failed_tools: List[str],
        context: AgentContext
    ) -> str:
        prompt = f"""
        Query: {context.query}
        
        Completed: {self._format_completed(completed_tools)}
        Failed: {', '.join(failed_tools)}
        
        Provide best answer with available data.
        """
        
        return await self.llm.generate(prompt)
```

---

## Monitoring

### **Metrics**

```python
class AgentMetrics:
    # Performance
    agent_query_duration_seconds: Histogram
    tool_execution_duration_seconds: Histogram
    llm_call_duration_seconds: Histogram
    
    # Usage
    agent_queries_total: Counter
    tool_executions_total: Counter
    tool_failures_total: Counter
    
    # Quality
    agent_confidence_score: Histogram
    tool_success_rate: Gauge
    partial_result_rate: Gauge
    
    # Resources
    tokens_used_per_query: Histogram
    tools_per_query: Histogram
```

### **Distributed Tracing**

```python
class AgentTracer:
    async def trace_execution(self, query: str, context: AgentContext):
        with tracer.start_as_current_span("agent.process_query") as span:
            span.set_attribute("query", query)
            
            with tracer.start_span("agent.classify_intent"):
                intent = await self.classify_intent(query)
            
            with tracer.start_span("agent.create_plan"):
                plan = await self.create_plan(intent)
            
            for tool in plan.tools:
                with tracer.start_span(f"agent.tool.{tool.name}"):
                    await tool.execute()
```

---

## Security

### **Tool Access Control**

```python
class ToolAccessControl:
    tool_permissions = {
        "user": ["search", "filter", "extract"],
        "admin": ["search", "filter", "extract", "delete", "modify"],
        "agent": ["search", "filter", "extract", "analyze"]
    }
    
    def can_execute_tool(self, user_role: str, tool_name: str) -> bool:
        return tool_name in self.tool_permissions.get(user_role, [])
```

### **Input Validation**

```python
class AgentInputValidator:
    def validate_query(self, query: str) -> ValidationResult:
        if self._contains_injection_patterns(query):
            return ValidationResult.REJECTED
        
        if len(query) > 10000:
            return ValidationResult.TOO_LONG
        
        if self._contains_malicious_patterns(query):
            return ValidationResult.SUSPICIOUS
        
        return ValidationResult.VALID
```

---

## Deployment Strategy

### **8-Week Rollout**

**Phase 1 (Weeks 1-2): Foundation**
- AgentOrchestrator core
- IntentClassifier with heuristics
- AgentPlanner with LLM
- 2-3 basic tools
- Integration with RAG service

**Phase 2 (Weeks 3-4): Tool Ecosystem**
- All 7 agent-specific tools
- Tool caching
- Parallel execution
- Error handling

**Phase 3 (Weeks 5-6): Optimization**
- Performance tuning
- Metrics and monitoring
- Distributed tracing
- Load testing

**Phase 4 (Weeks 7-8): Production**
- Security hardening
- Documentation
- User testing
- Gradual rollout (10% → 50% → 100%)

### **Feature Flags**

```python
class AgentFeatureFlags:
    enable_agent_mode: bool = False
    enable_parallel_execution: bool = False
    max_tools_per_query: int = 5
    
    def should_use_agent(self, user_id: str) -> bool:
        if not self.enable_agent_mode:
            return False
        
        # Gradual rollout: 10% of users
        return hash(user_id) % 100 < 10
```

---

## Cost Analysis

| Metric | Simple RAG | Agent (Complex) |
|--------|-----------|-----------------|
| Tokens | 500-1000 | 2000-5000 |
| Cost | $0.001-0.002 | $0.004-0.010 |
| Latency | 1-3 seconds | 5-15 seconds |
| Capability | Basic Q&A | Multi-step analysis |

**Optimization Strategies:**
1. Heuristic intent classification (95%+ queries, $0 cost)
2. Tool result caching
3. Parallel tool execution
4. Batch LLM calls (data extraction)
5. Smaller models for planning (gpt-4o-mini)

---

## LLM Call Summary

| Step | LLM? | Model | Tokens | Cost | Time | Frequency |
|------|------|-------|--------|------|------|-----------|
| Intent Classification | Optional | gpt-4o-mini | ~150 | $0.0001 | 200ms | 1-5% |
| Task Planning | **Required** | gpt-4o | ~500 | $0.0015 | 500ms | 100% |
| Tool Execution | No | - | 0 | $0 | 200-500ms | 100% |
| Data Extraction | **Required** | gpt-4o-mini | ~4000 | $0.004 | 2-3s | 60% |
| Response Synthesis | **Required** | gpt-4o | ~1200 | $0.006 | 1-2s | 100% |

**Total per complex query**: 3-4 LLM calls, $0.010-0.015, 5-8 seconds
