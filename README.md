# Life Archivist

> **Local-first, privacy-preserving personal knowledge system with MCP architecture**

Life Archivist transforms how people organize and interact with their digital documents using AI-powered search and natural language querying, while keeping all data processing completely local and private.

## 🎯 Quick Start

```bash
# 1. Install dependencies
just install

# 2. Start services (Ollama, Qdrant, Redis)
just services

# 3. Initialize models
just init-models

# 4. Start everything
just fullstack
```

The Electron desktop app will launch automatically. The web interface is available at http://localhost:3000 and the API at http://localhost:8000.

## 📋 What It Does

Life Archivist ingests your documents (PDFs, Word docs, text files, images), extracts content, creates searchable embeddings, and enables natural language querying of your personal knowledge base.

**Key Features:**
- **Local-First**: All processing happens on your machine using Ollama LLM
- **Content-Addressed Storage**: Automatic deduplication with hash-based file organization
- **Hybrid Search**: Combines semantic vector search with keyword matching
- **Natural Language Q&A**: Ask questions about your documents in plain English
- **MCP Architecture**: Extensible tool-based system following Model Context Protocol
- **Privacy-Preserving**: No data leaves your machine without explicit consent

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Electron UI   │    │   FastAPI       │    │   Docker        │
│   React/TS      ├────┤   MCP Server    ├────┤   Services      │
│   Port 3000     │    │   Port 8000     │    │   Ollama/Qdrant │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
        ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼─────┐
        │    Tools     │ │   Storage   │ │   Agents  │
        │ Registry     │ │   Layer     │ │ Pipeline  │
        │              │ │             │ │           │
        │ • FileImport │ │ • Vault     │ │ • Ingest  │
        │ • Extract    │ │ • LlamaIdx  │ │ • Query   │
        │ • LLM        │ │ • Embeddings│ │           │
        │ • Search     │ │             │ │           │
        └──────────────┘ └─────────────┘ └───────────┘
```

### Core Components

- **MCP Server**: Central orchestration layer managing tool execution and client communication
- **Tool Registry**: Extensible MCP tools (file import, text extraction, embedding, search)
- **Storage Layer**: Content-addressed vault + LlamaIndex for vector storage
- **Processing Agents**: Higher-level orchestrators combining tools for complex workflows

## 🚀 Development Commands

### Essential Commands
```bash
just setup          # Complete development setup
just fullstack       # Start everything (services + server + UI)
just api-only        # Start just backend services for testing
just verify          # Check all systems are working
just health          # Test server health endpoint
```

### Individual Components
```bash
just services        # Start Docker services (Ollama, Qdrant, Redis)
just server-dev      # Start backend with auto-reload
just ui              # Start React frontend only
just desktop         # Start full Electron app
```

### Development Workflow
```bash
just dev             # Fix code formatting + run tests
just lint-fix        # Auto-fix code style issues
just test            # Run test suite
just ci              # Full CI checks (lint + test)
```

### Debugging
```bash
just check-docker    # Verify Docker services are running
just test-cli        # Test CLI functionality
just stop-all        # Stop all background processes
just reset           # Clean restart everything
```

## 📁 Project Structure

```
lifearchivist/
├── lifearchivist/              # Python package
│   ├── server/                 # FastAPI MCP server
│   │   ├── main.py            # Application entry point
│   │   ├── mcp_server.py      # MCP protocol implementation  
│   │   ├── api/               # REST API routes
│   │   └── progress_manager.py # WebSocket progress tracking
│   ├── storage/               # Storage layer
│   │   ├── vault/             # Content-addressed file storage
│   │   ├── llamaindex_service.py # LlamaIndex integration
│   │   └── llamaindex_service_utils.py # Utilities
│   ├── tools/                 # MCP tools
│   │   ├── base.py           # Base tool class
│   │   ├── registry.py       # Tool registry
│   │   ├── file_tools.py     # File import/management
│   │   ├── extract_tools.py  # Text extraction (PDF, DOCX)
│   │   ├── llamaindex_tools.py # LlamaIndex operations
│   │   └── llm_tools.py      # Ollama LLM integration
│   ├── agents/                # Processing agents
│   │   ├── ingestion.py      # Document ingestion pipeline
│   │   └── query.py          # Search and Q&A pipeline
│   ├── models/               # Pydantic schemas
│   └── config/               # Configuration management
├── desktop/                   # Electron desktop app
│   ├── src/                  # React TypeScript frontend
│   ├── package.json          # Node.js dependencies
│   └── main.js               # Electron main process
├── docker-compose.yml        # Development services
├── pyproject.toml           # Python dependencies
├── justfile                 # Development commands
└── COMMANDS.md              # API testing commands
```

## 🔧 Configuration

### Environment Variables
```bash
# Core paths
LIFEARCH_HOME=/Users/username/.lifearchivist    # Data directory
LIFEARCH_VAULT_PATH=/custom/vault/path          # Custom vault location

# Models
LIFEARCH_LLM_MODEL=llama3.2:3b                 # Ollama model
LIFEARCH_EMBEDDING_MODEL=all-MiniLM-L6-v2      # Embedding model

# Services
LIFEARCH_OLLAMA_URL=http://localhost:11434     # Ollama endpoint
LIFEARCH_QDRANT_URL=http://localhost:6333      # Qdrant vector DB
LIFEARCH_REDIS_URL=redis://localhost:6379      # Redis cache

# Development
LIFEARCH_API_ONLY_MODE=true                    # API-only mode
LIFEARCH_ENABLE_UI=false                       # Disable UI features
LIFEARCH_LOCAL_ONLY=true                       # Force local processing
```

### Directory Structure
```
~/.lifearchivist/
├── vault/                     # Content-addressed file storage
│   ├── content/              # Files organized by hash (ab/cd/efgh123.pdf)
│   ├── thumbnails/           # Auto-generated image previews
│   └── temp/                 # Temporary processing files
├── llamaindex_storage/       # LlamaIndex vector storage
└── models/                   # Downloaded AI models cache
```

## 🛠️ API Usage

### Document Upload
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@document.pdf" \
  -F 'metadata={"source": "test"}' | jq
```

### Semantic Search
```bash
curl "http://localhost:8000/api/search?q=mortgage%20rates&mode=semantic&limit=5" | jq
```

### Natural Language Q&A
```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is my mortgage interest rate?"}' | jq
```

See `COMMANDS.md` for comprehensive API testing commands.

## 🏥 Health Monitoring

### System Check
```bash
# Quick health check
curl http://localhost:8000/health | jq

# Verify all services
just verify

# Check Docker services
just check-docker

# Test basic functionality
just test-cli
```

### Troubleshooting
```bash
# View server logs
just server-dev  # Shows real-time logs

# Check Ollama models
docker exec lifearchivist-ollama-1 ollama list

# Restart services
just services-stop && just services

# Full reset
just reset
```

## 📦 Dependencies

### Python (pyproject.toml)
- **FastAPI + Uvicorn**: Web framework and ASGI server
- **LlamaIndex 0.13.2**: Vector storage and RAG framework
- **Ollama**: Local LLM integration
- **Sentence Transformers**: Local embeddings
- **Qdrant Client**: Vector database client
- **PyPDF + python-docx**: Document parsing
- **Pydantic**: Data validation and settings

### Node.js (desktop/package.json)
- **Electron**: Desktop application framework
- **React + TypeScript**: Frontend framework
- **Vite**: Build tool and dev server
- **Tailwind CSS**: Styling framework

### Docker Services
- **Ollama**: Local LLM inference server
- **Qdrant**: Vector database for embeddings
- **Redis**: Caching and task queue

## 🔒 Privacy & Security

- **Local-First**: All document processing happens locally using Ollama
- **No Cloud Dependencies**: Can operate completely offline
- **Content-Addressed Storage**: Files organized by hash for integrity
- **Optional Telemetry**: Disabled by default, user-controlled
- **Sandboxed Processing**: Document parsing isolated from main application

## 📊 Status

**Current Status**: Development/Alpha
- ✅ Core architecture implemented
- ✅ Document ingestion pipeline working
- ✅ Basic search and Q&A functionality
- ✅ Desktop app with file upload
- 🔄 Hardening error handling and edge cases
- 🔄 Adding test coverage
- 📋 Planned: Mobile app, browser extension, advanced AI features

**Known Limitations**:
- Limited file format support (PDF, DOCX, TXT)
- No OCR for scanned documents yet
- Basic date extraction logic
- Memory usage not optimized for very large documents

## 🤝 Contributing

This is currently a personal project in active development. The codebase follows production-grade patterns and is designed for eventual open source release.

**Development Workflow**:
1. `just setup` - Initial setup
2. `just fullstack` - Start development environment  
3. Make changes
4. `just dev` - Fix formatting + run tests
5. `just ci` - Full CI checks

## 📄 License

MIT License - See LICENSE file for details.