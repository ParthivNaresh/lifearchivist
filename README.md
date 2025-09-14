LifeArchivist

Life Archivist - Project Summary
Overview
Life Archivist is a local-first, privacy-preserving personal knowledge management system that enables users to upload, process, and query their local documents using AI. The system processes documents entirely on the user's machine using Ollama for LLM inference, creates searchable embeddings, and provides natural language Q&A capabilities through a desktop Electron application.
Core Architecture
Technology Stack
* Backend: Python 3.12, FastAPI, Uvicorn (ASGI server)
* Frontend: React 18, TypeScript, Vite, Tailwind CSS
* Desktop: Electron for cross-platform desktop application
* Vector Storage: LlamaIndex 0.13.2 LlamaIndex's SimpleVectorStore
* LLM: Ollama (local inference) with llama3.2 models
* Embeddings: Sentence Transformers (all-MiniLM-L6-v2)
* Document Processing: PyPDF, python-docx, BeautifulSoup4
* Storage: Content-addressed vault system with SHA256 hashing
* Caching: Redis for task queuing and progress tracking
* Development: Poetry for Python dependencies, Just for task automation
  System Components
1. MCP Server (lifearchivist/server/mcp_server.py)
* Central orchestration layer implementing Model Context Protocol
* Manages tool execution, session management, and WebSocket connections
* Initializes and coordinates vault storage, LlamaIndex service, and tool registry
* Handles progress tracking through Redis-backed ProgressManager
2. Tool Registry System (lifearchivist/tools/)
* FileImportTool: Handles file ingestion, hash calculation, deduplication
* ExtractTextTool: Extracts text from PDFs, DOCX, and text files
* ContentDateExtractionTool: Extracts dates from document content
* OllamaTool: Interfaces with local Ollama LLM for text generation
* IndexSearchTool: Performs keyword, semantic, and hybrid searches
* LlamaIndexQueryTool: Executes RAG queries for Q&A functionality
3. Storage Layer
   Vault Storage (lifearchivist/storage/vault/)
* Content-addressed file storage using SHA256 hashes
* Directory structure: content/ab/cd/efgh123.pdf (hash-based organization)
* Automatic deduplication at file level
* Thumbnail generation for images (256x256 WEBP format)
* Temporary file management with automatic cleanup
  LlamaIndex Service (lifearchivist/storage/llamaindex_service/)
* Vector storage and retrieval using LlamaIndex framework
* Document chunking with SentenceSplitter (800 chars, 100 overlap)
* Hybrid search combining semantic vectors and keyword matching
* Metadata management for filtering and document relationships
* Query engine with tree_summarize response mode
4. API Routes (lifearchivist/server/api/routes/)
* Upload: Single/bulk file upload and ingestion endpoints
* Search: Keyword, semantic, and hybrid search with filters
* Documents: CRUD operations for document management
* Ask: Natural language Q&A using RAG pipeline
* Vault: Storage statistics and file management
* Tags: Auto-tagging and tag management
5. Desktop Application (desktop/)
* Electron wrapper with React frontend
* Multiple views: Inbox, Documents, Timeline, Q&A, Search, Settings
* Drag-and-drop file upload with progress tracking
* WebSocket integration for real-time updates
* IPC handlers for native file system operations
  Document Processing Pipeline
1. File Import
    * Calculate SHA256 hash for deduplication
    * Detect MIME type using python-magic
    * Store in content-addressed vault
    * Check for duplicates in both vault and LlamaIndex
2. Text Extraction
    * PDF: PyPDF for text extraction
    * DOCX: python-docx for Word documents
    * Images: Pillow for thumbnail generation (OCR planned)
    * Plain text: Direct reading
3. Indexing
    * Split text into chunks (800 chars with 100 char overlap)
    * Generate embeddings using Sentence Transformers
    * Store in Qdrant vector database
    * Update LlamaIndex with document metadata
4. Metadata Enrichment
    * Extract content dates from text
    * Auto-generate tags (if enabled)
    * Track provenance and processing history
    * Store file metadata (size, MIME type, timestamps)
      Query & Retrieval System
      Search Modes
* Keyword: BM25-based text search
* Semantic: Vector similarity search using embeddings
* Hybrid: Combination of keyword and semantic search
  Q&A Pipeline
1. User submits natural language question
2. Question embedded using Sentence Transformers
3. Retrieve relevant document chunks (default: top 5)
4. Pass context to Ollama LLM with question
5. Generate answer with source citations
6. Return response with confidence score
   Logging & Monitoring
   Smart Logging System (lifearchivist/utils/logging/)
* Decorator-based tracking with @track() annotation
* Automatic performance metrics collection
* Sampling for high-frequency operations
* Structured event logging with correlation IDs
* Sensitive data redaction
* Operation categorization and frequency-based sampling
  Configuration System
  Environment Variables (prefix: LIFEARCH_)
* LIFEARCH_HOME: Base data directory (default: ~/.lifearchivist)
* LIFEARCH_VAULT_PATH: Document storage location
* LIFEARCH_LLM_MODEL: Ollama model (default: llama3.2:1b)
* LIFEARCH_EMBEDDING_MODEL: Embedding model (default: all-MiniLM-L6-v2)
* LIFEARCH_API_ONLY_MODE: Disable UI for API testing
* LIFEARCH_ENABLE_AGENTS: Enable complex agent workflows
  Development Workflow
  Key Commands (via Justfile)
* just setup: Complete development environment setup
* just fullstack: Start all services + server + UI
* just api-only: API-only mode for testing
* just services: Start Docker containers (Ollama, Qdrant, Redis)
* just dev: Fix code formatting + run tests
* just verify: Check all systems operational
  Testing Infrastructure
* Comprehensive curl commands in COMMANDS.md
* Support for single file, bulk upload, search, and Q&A testing
* WebSocket progress tracking for uploads
* Error handling and retry mechanisms
  Current Limitations & Areas for Improvement
1. Performance Issues
    * Memory usage not optimized for large documents
    * Query timeout issues with large indexes
    * No streaming support for LLM responses
2. Feature Gaps
    * No OCR for scanned documents
    * Limited audio/video processing (infrastructure exists but not implemented)
    * Basic date extraction logic needs improvement
    * No document relationship mapping
3. Technical Debt
    * Error handling needs hardening
    * Test coverage is minimal
    * Logging can be excessive in some areas
    * WebSocket implementation needs reliability improvements
4. UI/UX Improvements Needed
    * Better progress feedback for long operations
    * More intuitive search filters
    * Document preview capabilities
    * Batch operations interface
5. Storage & Indexing
    * No incremental indexing
    * Metadata updates require full node traversal
    * No automatic index optimization
    * Limited support for document updates
      Security & Privacy Features
* All processing happens locally (no cloud dependencies)
* Content-addressed storage ensures file integrity
* Optional telemetry (disabled by default)
* Sandboxed document processing
* No external API calls without explicit configuration
  Future Development Priorities
1. Implement OCR for scanned documents
2. Add streaming LLM responses for better UX
3. Improve memory management for large documents
4. Expand test coverage to 80%+
5. Implement incremental indexing
6. Add document relationship mapping
7. Enhance date extraction with NLP
8. Build mobile companion app
9. Add browser extension for web content capture
10. Implement advanced agent workflows for complex queries
    This project follows production-grade patterns with comprehensive logging, error handling, and modular architecture, making it well-suited for continued development and eventual open-source release.
