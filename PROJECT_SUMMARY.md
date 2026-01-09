# Life Archivist - Project Summary

## Overview

Life Archivist is a local-first, privacy-preserving personal knowledge management system that enables users to upload, process, and query their documents using AI. The system processes documents entirely on the user's machine, extracts text, classifies themes/subthemes, creates searchable embeddings, and provides natural language Q&A capabilities through a desktop Electron application.

---

## Core Architecture

### Technology Stack

**Backend**
- Python 3.12
- FastAPI + Uvicorn (ASGI server)

**Frontend**
- React 18 + TypeScript
- Vite build tool
- Tailwind CSS
- Zustand for state management
- TanStack Query for data fetching
- Radix UI for accessible components

**Desktop**
- Electron 28 for cross-platform application

**Vector Storage & AI**
- Qdrant 1.12 for vector storage
- LlamaIndex 0.13.2 (QdrantVectorStore integration)
- Sentence Transformers (all-MiniLM-L6-v2, 384 dimensions)

**LLM Providers**
- Multi-provider support via `LLMProviderManager`:
  - Ollama (local inference)
  - OpenAI
  - Anthropic
  - Google (Gemini)
  - Groq
  - Mistral
- Provider routing, health monitoring, and cost tracking

**Document Processing**
- PyPDF for PDF text extraction
- python-docx for Word documents
- openpyxl for Excel files
- Pillow for image thumbnails
- python-magic for MIME type detection
- faster-whisper for audio transcription

**Storage & Caching**
- PostgreSQL 16 for relational data (conversations, messages, citations)
- Redis 7 for task queuing, caching, and document tracking
- Content-addressed vault with SHA256 hashing

**Development**
- Poetry for Python dependency management
- Just for task automation
- Ruff for linting
- Pytest for testing

---

## Key Features

### 1. Agent Orchestration System

A hierarchical multi-phase agent orchestration system for complex queries:

**Components:**
- **ComplexityClassifier**: Routes queries to simple RAG or complex agent pipeline
- **StrategicPlanner**: Decomposes complex queries into 3-7 high-level phases
- **TacticalPlannerFactory**: Creates isolated tactical planners per phase (factory pattern)
- **PhaseCoordinator**: Orchestrates multi-phase execution with dependency management
- **TaskExecutor**: Manages concurrent task execution with DAG-based dependencies
- **AgentSpawner**: Creates agents for individual task execution

**Agent Tools:**
- `document_search`: Semantic, keyword, hybrid, and metadata search
- `text_extraction`: Extract and summarize text from documents
- `structured_extraction`: LLM-powered structured data extraction with JSON schemas

**Flow:**
```
User Query → ComplexityClassifier
  ├─ SIMPLE → RAG Pipeline (direct retrieval + generation)
  └─ COMPLEX → StrategicPlanner → PhaseCoordinator
                                    ├─ Phase 1: TacticalPlanner → TaskExecutor
                                    ├─ Phase 2: TacticalPlanner → TaskExecutor
                                    └─ Synthesis: Final response generation
```

### 2. RAG (Retrieval-Augmented Generation)

**ConversationRAGService** (`lifearchivist/rag/service.py`):
- Intent classification (document query vs. chitchat)
- Context retrieval via semantic search
- Conversation history management
- Streaming response generation
- Citation tracking and confidence scoring
- Real-time WebSocket status updates

### 3. Theme Classification

**ThemeClassifier** (`lifearchivist/tools/theme_classifier/`):
- Cascade classification approach (fast filters first)
- Three-tier classification:
  1. Primary: Unique patterns and definitive phrases
  2. Secondary: Document structure patterns
  3. Tertiary: Filename keywords and statistical analysis
- Pre-compiled regex patterns for performance
- Configurable rules via separate definition files

### 4. Multi-Provider LLM Support

**LLMProviderManager** (`lifearchivist/llm/provider_manager.py`):
- Unified interface for multiple LLM providers
- Provider routing with configurable strategies
- Health monitoring with automatic failover
- Cost tracking and budget enforcement
- Streaming and non-streaming generation
- Metadata capabilities (workspaces, usage, costs)

**Supported Providers:**
- Ollama (local)
- OpenAI (with metadata support)
- Anthropic (with metadata support)
- Google (Gemini)
- Groq
- Mistral

### 5. Search Capabilities

**LlamaIndexSearchService** (`lifearchivist/storage/search_service.py`):
- **Semantic Search**: Vector similarity using embeddings
- **Keyword Search**: BM25-based text search
- **Hybrid Search**: Weighted combination of semantic and keyword
- Configurable similarity thresholds
- Metadata filtering support
- Document neighbor discovery

### 6. Document Processing Pipeline

1. **File Import**: SHA256 hashing, MIME detection, vault storage
2. **Text Extraction**: PDF, DOCX, images (OCR planned), audio transcription
3. **Theme Classification**: Cascade approach with confidence scoring
4. **Indexing**: Chunking, embedding generation, vector storage
5. **Metadata Enrichment**: Date extraction, tag generation (planned)

---

## System Components

### Service Container (`lifearchivist/server/service_container.py`)

Centralized dependency injection and lifecycle management:

**Initialization Order:**
1. External connections (Redis, Qdrant, PostgreSQL)
2. Storage services (Vault)
3. Index services (DocTracker, BM25)
4. LLM services (CredentialService, LLMProviderManager)
5. High-level services (LlamaIndex, Conversation, Message)
6. Agent orchestrator and RAG service

### Storage Layer

**Vault** (`lifearchivist/storage/vault/`):
- Content-addressed file storage using SHA256 hashes
- Directory structure: `content/ab/cd/efgh123.pdf`
- Automatic deduplication
- Thumbnail generation (256x256 WEBP)

**RedisDocumentTracker** (`lifearchivist/storage/redis_document_tracker.py`):
- Document-to-node mappings
- Full metadata storage
- Node ID management

**BM25IndexService** (`lifearchivist/storage/bm25_index_service.py`):
- Redis-backed BM25 index
- Configurable stemming and stop word removal
- Incremental index updates

**Database Services** (`lifearchivist/storage/database/`):
- `ConversationService`: Conversation CRUD, archiving
- `MessageService`: Message management, citations, status updates

### API Routes (`lifearchivist/server/api/routes/`)

| Route Group | Purpose |
|-------------|---------|
| `/conversations` | Conversation management, message streaming |
| `/documents` | Document CRUD operations |
| `/search` | Search endpoints (semantic, keyword, hybrid) |
| `/upload` | File upload and ingestion |
| `/vault` | Storage statistics and file management |
| `/providers` | LLM provider management |
| `/settings` | User preferences and configuration |
| `/activity` | Activity feed and analytics |
| `/timeline` | Document timeline view |
| `/enrichment` | Background enrichment queue |
| `/folder_watch` | Folder watching configuration |
| `/websocket` | Real-time updates |

### Desktop Application (`desktop/`)

**Pages:**
- Inbox: New document processing
- Documents: Document library with search
- Document Detail: Individual document view
- Q&A/Conversations: Chat interface with RAG
- Search: Advanced search interface
- Timeline: Chronological document view
- Activity: System activity feed
- Vault: Storage management
- Settings: Configuration

**Key Hooks:**
- `useConversation`: Conversation state management
- `useConversationWebSocket`: Real-time message updates
- `useSearch`: Search functionality
- `useUploadManager`: File upload handling
- `useProgressTracking`: Upload/processing progress

---

## Logging & Observability

**Smart Logging System** (`lifearchivist/utils/logx/`):
- Structured event logging with `log_event()`
- Decorator-based tracking with `@track()`
- Request context middleware
- Configurable log levels and formatters
- Correlation ID support

---

## Infrastructure

**Docker Compose Services:**
- `lifearchivist-server`: Main FastAPI application
- `qdrant`: Vector database (port 6333)
- `redis`: Caching and task queue (port 6379)
- `postgres`: Relational database (port 5432)
- `ollama`: Local LLM inference (port 11434)
- `lifearchivist-worker`: Background task processing
- `nginx`: Reverse proxy (production profile)

---

## Development Workflow

### Key Commands (via Justfile)

- `just setup`: Complete development environment setup
- `just fullstack`: Start all services + server + UI
- `just api-only`: API-only mode for testing
- `just services`: Start Docker containers

### Testing

- Pytest-based test suite with async support
- Mock implementations for external services
- Comprehensive curl commands in `COMMANDS.md`

---

## Architecture Notes

- **Local-first**: All processing happens on user's machine
- **Privacy-preserving**: No data sent to external services (unless using cloud LLM providers)
- **Scalability**: Designed to handle 10,000+ documents
- **No backwards compatibility**: Project is in active development
- **Production-grade**: Result types, proper error handling, observability

---

## File Structure

```
lifearchivist/
├── llm/
│   ├── agent/              # Agent orchestration system
│   │   ├── tools/          # Agent tools (search, extraction)
│   │   ├── prompts/        # Prompt builders
│   │   ├── models/         # Data models
│   │   └── utils/          # DAG validation, parsing
│   ├── providers/          # LLM provider implementations
│   ├── processors/         # Stream processors (gateway, direct)
│   └── provider_manager.py # Main LLM orchestration
├── rag/
│   ├── service.py          # ConversationRAGService
│   ├── prompts.py          # RAG prompt building
│   └── types.py            # RAG data types
├── server/
│   ├── api/routes/         # API endpoints
│   ├── main.py             # FastAPI app creation
│   ├── service_container.py # Dependency injection
│   └── application_server.py # Server lifecycle
├── storage/
│   ├── vault/              # File storage
│   ├── database/           # PostgreSQL services
│   ├── llamaindex_service/ # Vector storage orchestration
│   ├── search_service.py   # Search operations
│   └── bm25_index_service.py # Keyword search
├── tools/
│   ├── theme_classifier/   # Document classification
│   ├── extract/            # Text extraction
│   └── file_import/        # File ingestion
├── utils/
│   ├── logx/               # Logging system
│   └── result.py           # Result type system
└── config/                 # Configuration

desktop/
├── src/
│   ├── pages/              # React pages
│   ├── components/         # React components
│   ├── hooks/              # React hooks
│   ├── contexts/           # React contexts
│   └── types/              # TypeScript types
└── main.cjs                # Electron main process
```

---

## Quick Start

1. **Install dependencies**: `just setup`
2. **Start services**: `just services` (Qdrant, Redis, PostgreSQL, Ollama)
3. **Start application**: `just fullstack`
4. **Test API**: See `COMMANDS.md` for curl examples

---

## Complete Example: Document Upload Flow

This section traces the complete journey of a PDF file from user upload through all backend systems.

### Scenario
User uploads `blood_test_results_2024.pdf` (500KB) via the desktop application.

---

### Step 1: UI Layer (Desktop/React)

**File:** `desktop/src/hooks/useUploadManager.ts`

1. User drags file onto upload zone or clicks to select
2. `useUploadManager` hook captures the file
3. Creates a temporary file path and generates a `session_id` for WebSocket progress tracking
4. Sends POST request to `/api/upload/ingest`

```
UI State: "Uploading..." → WebSocket connection established for progress updates
```

---

### Step 2: API Route Handler

**File:** `lifearchivist/server/api/routes/upload/ingest.py`

```python
@router.post("/ingest")
async def ingest_document(request: IngestRequest) -> IngestResponse:
```

1. Receives request with `path`, `session_id`, optional `tags` and `metadata`
2. Gets `ApplicationServer` instance via `get_server()`
3. Calls `server.execute_tool("file.import", params)`

**Key Interaction:**
- `ApplicationServer` → `ToolRegistry` → `FileImportTool`

---

### Step 3: Tool Execution Layer

**File:** `lifearchivist/server/application_server.py`

```python
async def execute_tool(self, tool_name: str, params: Dict[str, Any]):
    tool = self.tool_registry.get_tool(tool_name)  # Gets FileImportTool
    validated_params = await tool.validate_input(params)
    result = await tool.execute(**validated_params)
    return await tool.validate_output(result)
```

**Services Used:**
- `ToolRegistry` - Manages registered tools
- `ProgressManager` - WebSocket progress updates (Redis-backed)

---

### Step 4: File Import Tool Execution

**File:** `lifearchivist/tools/file_import/file_import_tool.py`

This is the main orchestration point. The `execute()` method performs:

#### 4a. File Analysis
```python
file_hash = await calculate_file_hash(file_path)  # SHA256
mime_type = magic.from_file(str(file_path), mime=True)  # "application/pdf"
file_id = str(uuid.uuid4())  # "a1b2c3d4-..."
```

**Services Used:**
- `python-magic` - MIME type detection

#### 4b. Progress Tracking Initialization
```python
if self.progress_manager and session_id:
    await self.progress_manager.start_progress(file_id, session_id)
```

**Services Used:**
- `ProgressManager` → **Redis** (stores progress state, broadcasts via WebSocket)

#### 4c. Vault Storage
```python
vault_result = await self.vault.store_file(file_path, file_hash)
# Returns: {"file_hash": "abc123...", "path": "content/ab/c1/23...", "existed": False}
```

**File:** `lifearchivist/storage/vault/vault.py`

**What happens:**
1. Checks if file with same hash already exists (deduplication)
2. Creates directory structure: `vault/content/ab/c1/` (first 4 chars of hash)
3. Copies file to: `vault/content/ab/c1/23def456.pdf`
4. For images: generates 256x256 WEBP thumbnail in `vault/thumbnails/`

**Services Used:**
- **Vault** (filesystem) - Content-addressed storage

#### 4d. Duplicate Detection
```python
if vault_result["existed"]:
    duplicate_doc = await self._check_for_duplicate(file_id, file_hash)
    # Queries LlamaIndex metadata for existing document with same hash
```

**Services Used:**
- `LlamaIndexService` → `MetadataService` → **Qdrant** (metadata query)

#### 4e. Text Extraction
```python
extracted_text = await self._try_extract_text(file_id, file_path, mime_type, file_hash)
```

**File:** `lifearchivist/tools/extract/extract_tool.py`

**What happens for PDF:**
1. Uses `pypdf` to extract text from all pages
2. Concatenates text with page separators
3. Returns extracted text (e.g., "Patient: John Doe\nTest Date: 2024-03-15\nCholesterol: 185 mg/dL...")

**Services Used:**
- `ExtractTextTool` - Text extraction orchestration
- `pypdf` - PDF parsing

#### 4f. Document Metadata Extraction
```python
document_metadata = await self._extract_document_metadata(file_id, file_path, mime_type)
# Returns: {"document_created_at": "2024-03-15", "document_author": "Lab Corp"}
```

**What happens:**
1. Extracts PDF internal metadata (creation date, author, title)
2. Falls back to filesystem creation date (macOS extended attributes)

#### 4g. Theme Classification
```python
theme_result = await self._classify_themes(file_id, extracted_text, display_path)
# Returns: {"theme": "Healthcare", "confidence": 0.92, "match_tier": "primary"}
```

**File:** `lifearchivist/tools/theme_classifier/theme_classifier.py`

**What happens (cascade approach):**
1. **Primary Check**: Looks for definitive phrases ("blood test", "cholesterol", "glucose")
2. **Secondary Check**: Analyzes document structure patterns
3. **Tertiary Check**: Filename keywords + statistical word analysis

**Result:** `theme="Healthcare"`, `confidence=0.92`, `match_tier="primary"`

#### 4h. Subtheme Classification
```python
if theme == "Healthcare":
    subtheme_result = await self._classify_subthemes(file_id, extracted_text, theme, filename)
    # Returns: {"primary_subtheme": "Lab Results", "subthemes": ["Lab Results", "Blood Work"]}
```

**File:** `lifearchivist/tools/subtheme_classifier/subtheme_classifier.py`

**Services Used:**
- `SubthemeClassifier` - Theme-specific subclassification

#### 4i. Document Creation in LlamaIndex
```python
doc_metadata = create_document_metadata(
    file_id=file_id,
    file_hash=file_hash,
    original_path=display_path,
    mime_type=mime_type,
    stat=stat,
    text=extracted_text,
    custom_metadata={
        "classifications": theme_result,
        "document_created_at": "2024-03-15",
        ...
    }
)

await self.llamaindex_service.add_document(
    document_id=file_id,
    content=extracted_text,
    metadata=doc_metadata
)
```

---

### Step 5: LlamaIndex Document Service

**File:** `lifearchivist/storage/llamaindex_service/llamaindex_service_qdrant.py`

```python
async def add_document(self, document_id, content, metadata):
    return await self.document_service.add_document(document_id, content, metadata)
```

**File:** `lifearchivist/storage/document_service.py`

#### 5a. Metadata Preparation
```python
# Store full metadata in Redis (for retrieval without bloating vectors)
await self.doc_tracker.store_full_metadata(document_id, full_metadata)

# Create minimal metadata for vector chunks (only essential fields)
chunk_metadata = {
    "document_id": "a1b2c3d4-...",
    "title": "blood_test_results_2024.pdf",
    "mime_type": "application/pdf",
    "status": "ready"
}
```

**Services Used:**
- `RedisDocumentTracker` → **Redis** (stores full metadata as JSON)

#### 5b. Text Chunking
```python
from llama_index.core import Settings
chunks = Settings.node_parser.get_nodes_from_documents([document])
# SentenceSplitter: chunk_size=2600, chunk_overlap=200
```

**What happens:**
- Splits text into ~2600 character chunks with 200 char overlap
- Creates 3 chunks for our 500KB PDF

**Services Used:**
- `LlamaIndex SentenceSplitter` - Text chunking

#### 5c. Embedding Generation
```python
texts_to_embed = [chunk.get_content() for chunk in chunks]
embeddings = Settings.embed_model.get_text_embedding_batch(texts_to_embed)
# HuggingFace all-MiniLM-L6-v2 → 384-dimensional vectors
```

**What happens:**
- Converts each text chunk into a 384-dimensional vector
- Batch processing for efficiency

**Services Used:**
- `HuggingFaceEmbedding` (all-MiniLM-L6-v2) - Local embedding model

#### 5d. Vector Storage in Qdrant
```python
from qdrant_client.models import PointStruct

points = []
for chunk, embedding in zip(chunks, embeddings):
    point = PointStruct(
        id=chunk.node_id,  # UUID for this chunk
        vector=embedding,   # 384-dim vector
        payload={
            "document_id": document_id,
            "_node_content": chunk.json(),  # Full chunk data
            **chunk_metadata
        }
    )
    points.append(point)

# Batch upsert to Qdrant
self.qdrant_client.upsert(
    collection_name="lifearchivist",
    points=points,
    wait=True
)
```

**Services Used:**
- **Qdrant** (vector database) - Stores embeddings + payload

#### 5e. Document Tracking in Redis
```python
node_ids = [chunk.node_id for chunk in chunks]  # ["node-1", "node-2", "node-3"]
await self.doc_tracker.add_document(document_id, node_ids)
```

**What's stored in Redis:**
```
lifearchivist:doc:a1b2c3d4-... → {
    "node_ids": ["node-1", "node-2", "node-3"],
    "metadata": { full document metadata JSON }
}
```

**Services Used:**
- `RedisDocumentTracker` → **Redis** (document-to-node mapping)

#### 5f. BM25 Index Update
```python
await self.bm25_service.add_document(document_id, content)
```

**File:** `lifearchivist/storage/bm25_index_service.py`

**What happens:**
1. Tokenizes text (removes stop words, optional stemming)
2. Calculates term frequencies
3. Updates inverted index in Redis

**Services Used:**
- `BM25IndexService` → **Redis** (keyword search index)

---

### Step 6: Finalization

**File:** `lifearchivist/tools/file_import/file_import_tool.py`

#### 6a. Status Update
```python
await self.llamaindex_service.update_document_metadata(
    file_id, 
    {"status": "ready"}, 
    merge_mode="update"
)
```

#### 6b. Provenance Logging
```python
provenance_entry = {
    "action": "import",
    "agent": "file_import_tool",
    "timestamp": "2024-03-15T10:30:00Z",
    "params": {"original_path": "blood_test_results_2024.pdf"},
    "result": {"vault_path": "content/ab/c1/23def456.pdf"}
}
await self.llamaindex_service.update_document_metadata(
    file_id,
    {"provenance": [provenance_entry]},
    merge_mode="update"
)
```

#### 6c. Progress Completion
```python
await self.progress_manager.complete_progress(
    file_id,
    metadata={
        "original_filename": "blood_test_results_2024.pdf",
        "file_size": 512000,
        "mime_type": "application/pdf"
    }
)
```

**Services Used:**
- `ProgressManager` → **Redis** → **WebSocket** (broadcasts completion to UI)

#### 6d. Activity Event
```python
await self.activity_manager.add_upload_event(
    file_count=1,
    source="manual",
    file_name="blood_test_results_2024.pdf",
    file_size=512000,
    mime_type="application/pdf",
    document_id=file_id
)
```

**Services Used:**
- `ActivityManager` → **Redis** (activity feed storage)

---

### Step 7: Response to UI

**File:** `lifearchivist/server/api/routes/upload/ingest.py`

```python
return IngestResponse(
    success=True,
    document_id="a1b2c3d4-...",
    file_hash="abc123def456...",
    status="ready",
    metadata={
        "theme": "Healthcare",
        "primary_subtheme": "Lab Results",
        "word_count": 1250,
        "nodes_created": 3
    }
)
```

---

### Data Flow Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER UPLOADS FILE                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DESKTOP UI (React/Electron)                                                │
│  • useUploadManager hook captures file                                      │
│  • Establishes WebSocket for progress                                       │
│  • POST /api/upload/ingest                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  FASTAPI ROUTE (ingest.py)                                                  │
│  • Validates request                                                        │
│  • Calls server.execute_tool("file.import", params)                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  FILE IMPORT TOOL (file_import_tool.py)                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │
│  │ 1. Hash + MIME  │→ │ 2. Vault Store  │→ │ 3. Dedup Check  │               │
│  │    Detection    │  │    (SHA256)     │  │                 │               │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘               │
│           │                   │                    │                         │
│           ▼                   ▼                    ▼                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐              │
│  │ 4. Text Extract │→ │ 5. Theme Class  │→ │ 6. Subtheme      │              │
│  │    (pypdf)      │  │    (Cascade)    │  │    Classification│              │
│  └─────────────────┘  └─────────────────┘  └──────────────────┘              │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LLAMAINDEX SERVICE (document_service.py)                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ 7. Chunk Text   │→ │ 8. Generate     │→ │ 9. Store in     │              │
│  │    (2600 chars) │  │    Embeddings   │  │    Qdrant       │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│           │                                        │                        │
│           ▼                                        ▼                        │
│  ┌─────────────────┐                      ┌─────────────────┐               │
│  │ 10. BM25 Index  │                      │ 11. Redis Track │               │
│  │     Update      │                      │     (doc→nodes) │               │
│  └─────────────────┘                      └─────────────────┘               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STORAGE SYSTEMS                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │    VAULT     │  │    QDRANT    │  │    REDIS     │  │  POSTGRESQL  │     │
│  │  (Files)     │  │  (Vectors)   │  │  (Metadata)  │  │ (Convos/Msgs)│     │
│  │              │  │              │  │              │  │              │     │
│  │ content/     │  │ Collection:  │  │ doc:uuid →   │  │ (Not used    │     │
│  │ ab/c1/23...  │  │ lifearchivist│  │ {nodes,meta} │  │  for upload) │     │
│  │ .pdf         │  │ 3 points     │  │              │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  RESPONSE TO UI                                                             │
│  • WebSocket: Progress complete event                                       │
│  • HTTP: IngestResponse with document_id, metadata                          │
│  • Activity feed updated                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Services Summary for Upload Flow

| Service | Technology | Purpose in Upload |
|---------|------------|-------------------|
| **Vault** | Filesystem | Content-addressed file storage |
| **Qdrant** | Vector DB | Stores embeddings + chunk payloads |
| **Redis** | Cache/Queue | Document tracking, progress, BM25 index, activity |
| **PostgreSQL** | Relational DB | Not used in upload (used for conversations) |
| **LlamaIndex** | Framework | Chunking, embedding orchestration |
| **HuggingFace** | ML Model | all-MiniLM-L6-v2 embeddings (384-dim) |
| **pypdf** | Library | PDF text extraction |
| **python-magic** | Library | MIME type detection |

---

## Related Documentation

- `AGENT_ORCHESTRATION.md`: Detailed agent system documentation
- `COMMANDS.md`: API testing commands
- `SYSTEM_DEPENDENCIES.md`: System requirements
- `SETUP_OLLAMA_LOCALLY.md`: Local LLM setup guide
