# Life Archivist - Project Summary

## Overview
Life Archivist is a local-first, privacy-preserving personal knowledge management system that enables users to upload, process, and query their local documents using AI. The system processes documents entirely on the user's machine, extracts text, identifies themes/subthemes, creates searchable embeddings, uses Ollama for LLM inference, and provides natural language Q&A capabilities through a desktop Electron application.

---

## Core Architecture

### Technology Stack

**Backend**
- Python 3.12
- FastAPI + Uvicorn (ASGI server)
- Result types for explicit error handling

**Frontend**
- React 18 + TypeScript
- Vite build tool
- Tailwind CSS

**Desktop**
- Electron for cross-platform application

**Vector Storage & AI**
- Qdrant for vector storage
- LlamaIndex 0.13.2 (QdrantVectorStore integration)
- Ollama (local LLM inference) with llama3.2 models
- Sentence Transformers (all-MiniLM-L6-v2, 384 dimensions)

**Document Processing**
- PyPDF for PDF text extraction
- python-docx for Word documents
- openpyxl for Excel files
- Pillow for image thumbnails
- python-magic for MIME type detection

**Storage & Caching**
- Content-addressed vault with SHA256 hashing
- Redis for task queuing and progress tracking
- JSON-based document tracker (doc_tracker.json)

**Development**
- Poetry for Python dependency management
- Just for task automation
- Black for code formatting
- Pytest for testing

---

## System Components

### 1. Service Layer Architecture

The system uses a **modular service-oriented architecture** with clear separation of concerns:

**LlamaIndexQdrantService** (`lifearchivist/storage/llamaindex_service/llamaindex_service_qdrant.py`)
- Main orchestration layer
- Delegates to specialized services:
  - **DocumentService**: CRUD operations (add, delete, count, clear)
  - **MetadataService**: Metadata management and queries
  - **SearchService**: Semantic, keyword, and hybrid search
  - **QueryService**: Q&A and RAG operations
- All write operations return `Result` types for explicit error handling
- Async initialization pattern to avoid event loop issues

**Document Tracker** (`lifearchivist/storage/document_tracker.py`)
- JSON-based tracking of document-to-node mappings
- Stores full metadata separately from vector chunks
- Path: `~/.lifearchivist/llamaindex_storage/doc_tracker.json`

**Metadata Optimization**
- **Minimal metadata in chunks**: 8 fields (~243 bytes)
  - document_id, title, mime_type, status, theme, primary_subtheme, uploaded_date, file_hash_short
- **Full metadata in tracker**: All fields (~1.5 KB)
- **84% storage reduction** compared to storing full metadata in every chunk
- Retrieval: Chunks have minimal metadata, full metadata fetched from tracker when needed

### 2. MCP Server (`lifearchivist/server/mcp_server.py`)
- Central orchestration layer implementing Model Context Protocol
- Manages tool execution, session management, and WebSocket connections
- Initializes and coordinates vault storage, LlamaIndex service, and tool registry
- Handles progress tracking through Redis-backed ProgressManager
- **Note**: Not an actual MCP server currently - doesn't autonomously call tools, just helps route them

### 3. Tool Registry System (`lifearchivist/tools/`)

**File Processing Tools**
- `FileImportTool`: File ingestion, hash calculation, deduplication
- `ExtractTextTool`: Text extraction from PDFs, DOCX, and text files
- `ContentDateExtractionTool`: Date extraction from document content (currently disabled)

**AI Tools**
- `OllamaTool`: Interfaces with local Ollama LLM for text generation
- `ThemeClassifierTool`: Assigns high-level theme (Financial, Healthcare, etc.)
- `SubthemeClassificationTool`: Assigns precise subtheme

**Search & Query Tools**
- `IndexSearchTool`: Keyword, semantic, and hybrid searches
- `LlamaIndexQueryTool`: RAG queries for Q&A functionality

### 4. Storage Layer

**Vault Storage** (`lifearchivist/storage/vault/`)
- Content-addressed file storage using SHA256 hashes
- Directory structure: `content/ab/cd/efgh123.pdf` (hash-based organization)
- Automatic deduplication at file level
- Thumbnail generation for images (256x256 WEBP format)
- Temporary file management with automatic cleanup

**Vector Storage**
- Qdrant collection: "lifearchivist"
- Vector dimension: 384 (all-MiniLM-L6-v2)
- Distance metric: COSINE
- Document chunking: 2600 chars with 200 char overlap
- Separator: `\n\n` (paragraph breaks)

**Storage Context**
- SimpleDocumentStore for document metadata
- SimpleIndexStore for index metadata
- QdrantVectorStore for vectors
- Persistence: `~/.lifearchivist/llamaindex_storage/`

### 5. API Routes (`lifearchivist/server/api/routes/`)

**Document Management**
- `upload.py`: Single/bulk file upload and ingestion endpoints
- `documents.py`: CRUD operations for document management
- `vault.py`: Storage statistics and file management

**Search & Query**
- `search.py`: Keyword, semantic, and hybrid search with filters
- `ask.py`: Natural language Q&A using RAG pipeline

**Metadata & Organization**
- `tags.py`: Auto-tagging and tag management (extraction not yet implemented)
- `enrichment.py`: Queue and worker management

**System**
- `settings.py`: Configuration endpoints
- `debug.py`: Debugging and health check endpoints

### 6. Desktop Application (`desktop/`)
- Electron wrapper with React frontend
- Multiple views: Inbox, Documents, Timeline, Q&A, Search, Settings
- Drag-and-drop file upload with progress tracking
- WebSocket integration for real-time updates
- IPC handlers for native file system operations

---

## Document Processing Pipeline

### 1. File Import
- Calculate SHA256 hash for deduplication
- Detect MIME type using python-magic
- Store in content-addressed vault
- Check for duplicates in both vault and LlamaIndex

### 2. Text Extraction
- **PDF**: PyPDF for text extraction
- **DOCX**: python-docx for Word documents
- **Images**: Pillow for thumbnail generation (OCR planned)
- **Plain text**: Direct reading

### 3. Theme/Subtheme Identification
- Uses Regex pattern and keyword matching
- Assigns high-level theme (Financial, Healthcare, Legal, etc.)
- Assigns specific subtheme for finer categorization

### 4. Indexing
- Split text into chunks (2600 chars with 200 char overlap)
- Generate embeddings using Sentence Transformers
- Store minimal metadata in vector chunks
- Store full metadata in doc_tracker.json
- Update LlamaIndex with document

### 5. Metadata Enrichment
- Extract content dates from text (feature currently disabled)
- Auto-generate tags (not yet implemented)
- Track provenance and processing history
- Store file metadata (size, MIME type, timestamps)

---

## Query & Retrieval System

### Search Modes

**Semantic Search**
- Vector similarity search using embeddings
- Cosine distance metric
- Configurable similarity threshold (default: 0.7)
- Supports metadata filters

**Keyword Search**
- **Status**: Not fully implemented (TODO)
- Currently falls back to semantic search
- Planned: BM25-based text search

**Hybrid Search**
- Combination of semantic and keyword search
- Configurable weighting (default: 50/50)
- Merges and ranks results from both methods

### Q&A Pipeline (RAG)

1. User submits natural language question
2. Question embedded using Sentence Transformers
3. Retrieve relevant document chunks (default: top 5)
4. Pass context to Ollama LLM with question
5. Generate answer using tree_summarize response mode
6. Return response with:
   - Answer text
   - Source citations
   - Confidence score
   - Context used
   - Statistics (answer length, num sources, etc.)

**Error Handling**: Returns structured dict with `{"error": True, "error_message": "..."}` on failure

---

## Error Handling & Result Types

### Result Type System (`lifearchivist/utils/result.py`)

**Pattern**: Explicit error handling using `Result[T, E]` types
- `Success(value)`: Successful operation with value
- `Failure(error)`: Failed operation with error details


**API Response Format**:
```json
{
  "success": true/false,
  "data": {...},           // on success
  "error": "message",      // on failure
  "error_type": "...",     // on failure
  "status_code": 404,      // on failure
  "context": {...}         // additional context
}
```

---

## Logging & Monitoring

### Smart Logging System (`lifearchivist/utils/logging/`)

**Features**:
- Decorator-based tracking with `@track()` annotation
- Automatic performance metrics collection
- Sampling for high-frequency operations
- Structured event logging with correlation IDs
- Sensitive data redaction
- Operation categorization and frequency-based sampling

**Usage**:
```python
@track(
    operation="document_addition",
    include_args=["document_id"],
    include_result=True,
    track_performance=True,
    frequency="low_frequency"
)
async def add_document(self, document_id: str, ...):
    ...
```

---

## Development Workflow

### Key Commands (via Justfile)

**Setup & Start**
- `just setup`: Complete development environment setup
- `just fullstack`: Start all services + server + UI
- `just api-only`: API-only mode for testing
- `just services`: Start Docker containers (Ollama, Qdrant, Redis)

**Development**
- `just verify`: Check all systems operational

### Testing Infrastructure
- Comprehensive curl commands in `COMMANDS.md`
- Support for single file, bulk upload, search, and Q&A testing
- Pytest-based test suite with fixtures and factories
- Mock implementations for testing without external dependencies

---

### Architecture Notes
- **No backwards compatibility needed**: Project is in active development
- **Scalability is priority**: Designed to handle 10,000+ documents
- **Local-first**: All processing happens on user's machine
- **Privacy-preserving**: No data sent to external services

---

## File Structure

```
lifearchivist/
├── server/
│   ├── api/routes/          # API endpoints
│   ├── mcp_server.py        # MCP orchestration
│   ├── background_tasks.py  # Async task management
│   └── progress_manager.py  # Progress tracking
├── storage/
│   ├── llamaindex_service/  # Vector storage service
│   ├── document_service.py  # Document CRUD
│   ├── metadata_service.py  # Metadata management
│   ├── search_service.py    # Search operations
│   ├── query_service.py     # Q&A operations
│   ├── document_tracker.py  # Document-node mapping
│   └── vault/               # File storage
├── tools/                   # Tool implementations
├── utils/
│   ├── logging/             # Smart logging system
│   └── result.py            # Result type system
├── config/                  # Configuration
└── models/                  # Data models

desktop/
├── src/
│   ├── pages/               # React pages
│   ├── components/          # React components
│   └── hooks/               # React hooks
└── main.js                  # Electron main process
```

---

## Quick Start

1. **Install dependencies**: `just setup`
2. **Start services**: `just services` (Ollama, Qdrant, Redis)
3. **Start application**: `just fullstack`
4. **Test API**: See `COMMANDS.md` for curl examples
