# ════════════════════════════════════════════════════════════════════════════════
# 🏗️  Life Archivist Development Commands
# ════════════════════════════════════════════════════════════════════════════════

# Show available commands
default:
    @just --list

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Installation & Setup
# ────────────────────────────────────────────────────────────────────────────────

# Install all dependencies (Python + Node.js)
install:
    @echo "🔄 Cleaning Poetry environment..."
    poetry cache clear --all . || true
    rm -f poetry.lock
    @echo "🔄 Installing Python dependencies..."
    PYTHONIOENCODING=utf-8 poetry install --no-cache || poetry install
    @echo "🔄 Installing Node.js dependencies..."
    just install-desktop

# Install only desktop app dependencies
install-desktop:
    cd desktop && npm install

# Full development setup (install + start services + init models)
setup: install services init-models
    @echo "✅ Development environment ready!"
    @echo ""
    @echo "Available commands:"
    @echo "  just server      - Start MCP server only"
    @echo "  just ui          - Start web UI only"
    @echo "  just desktop     - Start full Electron app"
    @echo "  just fullstack   - Start services + server + UI"
    @echo "  just verify      - Check all systems"

# ────────────────────────────────────────────────────────────────────────────────
# 🐳 Docker Services Management
# ────────────────────────────────────────────────────────────────────────────────

# Start development services (Qdrant, Redis, Ollama)
services:
    docker-compose up -d ollama
    docker exec -it lifearchivist-ollama-1 ollama pull llama3.2:1b
    docker-compose up -d qdrant redis ollama

# Stop development services
services-stop:
    docker-compose down

# Initialize Ollama models (run once after first setup)
init-models:
    docker exec lifearchivist-ollama-1 ollama pull llama3.2:3b
    docker exec lifearchivist-ollama-1 ollama list

# Debug: check Docker containers and service health
check-docker:
    docker ps -a
    @echo ""
    @echo "Checking service health..."
    @echo "Qdrant:" && curl -s http://localhost:6333 | python -c "import sys,json; print('✅ Running' if 'qdrant' in json.load(sys.stdin).get('title','').lower() else '❌ Error')" || echo "❌ Not responding"
    @echo "Redis:" && redis-cli -h localhost -p 6379 ping || echo "❌ Not responding" 
    @echo "Ollama:" && curl -s http://localhost:11434/api/version || echo "❌ Not responding"

# ────────────────────────────────────────────────────────────────────────────────
# 🖥️  Backend Server
# ────────────────────────────────────────────────────────────────────────────────

# Start the MCP server
server:
    @echo "🔄 Clearing port 8000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    poetry run python -m lifearchivist.server.main

# Start the MCP server with auto-reload (for development)
server-dev:
    @echo "🔄 Clearing port 8000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    poetry run uvicorn lifearchivist.server.main:create_app --host localhost --port 8000 --reload --factory

# Test the server health endpoint
health:
    curl -s http://localhost:8000/health | python -m json.tool

# Check project status
status:
    poetry run lifearchivist status

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Frontend / Desktop App
# ────────────────────────────────────────────────────────────────────────────────

# Start the full desktop app in development mode (Vite + Electron)
desktop:
    @echo "🔄 Clearing port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    cd desktop && npm run dev

# Start only the web UI (Vite dev server)
ui:
    @echo "🔄 Clearing port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    cd desktop && npm run dev-server

# Start the web UI in background and open browser
ui-browser:
    @echo "🔄 Clearing port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    cd desktop && npm run dev-server & sleep 4 && open http://localhost:3000 &

# Clean desktop build artifacts
clean-desktop:
    cd desktop && rm -rf dist/ build/ node_modules/.vite

# ────────────────────────────────────────────────────────────────────────────────
# 🚀 Development Workflows
# ────────────────────────────────────────────────────────────────────────────────

# Quick start: services + server
start: services
    poetry run uvicorn lifearchivist.server.main:create_app --host localhost --port 8000 --reload --factory

# API-only mode: services + server (no UI)
api-only: services
    #!/usr/bin/env bash
    echo "🚀 Starting Life Archivist API-only mode..."
    echo "🔄 Clearing port 8000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 1
    echo "📱 Starting MCP server (API-only)..."
    export LIFEARCH_API_ONLY_MODE=true
    export LIFEARCH_ENABLE_UI=false
    export LIFEARCH_ENABLE_AGENTS=false  
    export LIFEARCH_ENABLE_WEBSOCKETS=false
    poetry run uvicorn lifearchivist.server.main:create_app --host localhost --port 8000 --reload --factory &
    SERVER_PID=$!
    echo "⏳ Waiting for server to start..."
    sleep 3
    echo ""
    echo "✅ Life Archivist API ready!"
    echo "📊 API Server: http://localhost:8000 (PID: $SERVER_PID)"
    echo "🐳 Docker services: Running"
    echo "🔍 API Docs: http://localhost:8000/docs"
    echo ""
    echo "💡 Use 'just stop-all' to stop everything"
    echo "📋 Use 'just health' to check server status"
    echo "Press Ctrl+C to stop server"
    wait

# Full stack start: services + server + UI (all in parallel)  
fullstack: services
    #!/usr/bin/env bash
    echo "🚀 Starting full Life Archivist stack..."
    echo "🔄 Clearing ports 8000 and 3000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    sleep 1
    echo "📱 Starting MCP server..."
    poetry run uvicorn lifearchivist.server.main:create_app --host localhost --port 8000 --reload --factory &
    SERVER_PID=$!
    echo "⏳ Waiting for MCP server to start..."
    sleep 3
    echo "🎨 Starting Electron Desktop App..."
    cd desktop && npm run dev &
    UI_PID=$!
    echo "⚡ Electron app will launch automatically (this may take 10-15 seconds)..."
    echo ""
    echo "✅ Full stack starting!"
    echo "📊 MCP Server: http://localhost:8000 (PID: $SERVER_PID)"
    echo "⚡ Electron Desktop App: Starting (PID: $UI_PID)"
    echo "🐳 Docker services: Running"
    echo ""
    echo "💡 Use 'just stop-all' to stop everything"
    echo "📋 Use 'just health' to check server status"
    echo "🔍 Use 'just check-docker' to check services"
    echo ""
    echo "⏳ Please wait for the Electron app to fully load..."
    echo "Press Ctrl+C to stop all processes"
    wait

# Start everything in background for testing
start-all: services
    #!/usr/bin/env bash
    echo "🚀 Starting full Life Archivist stack..."
    just server-dev &
    SERVER_PID=$!
    just ui &
    UI_PID=$!
    echo "Server PID: $SERVER_PID"
    echo "UI PID: $UI_PID"
    echo "Use 'just stop-all' to stop everything"

# Stop all background processes
stop-all: services-stop
    @echo "🛑 Stopping all Life Archivist processes..."
    pkill -f "lifearchivist server" || true
    pkill -f "vite" || true
    pkill -f "electron" || true
    pkill -f "uvicorn" || true
    @echo "✅ All processes stopped"

# Check everything is working
verify: check-docker test-cli health
    @echo "✅ All systems operational!"

# Reset development environment
reset: services-stop clean
    docker-compose down -v
    @echo "🧹 Environment reset complete"

# ────────────────────────────────────────────────────────────────────────────────
# 🧪 Testing & Debugging
# ────────────────────────────────────────────────────────────────────────────────

# Test basic CLI functionality
test-cli:
    poetry run lifearchivist --help
    poetry run lifearchivist server --help
    poetry run lifearchivist status

# Run tests
test:
    poetry run pytest

# Run tests with coverage
test-cov:
    poetry run pytest --cov=lifearchivist --cov-report=html --cov-report=term

# ────────────────────────────────────────────────────────────────────────────────
# 🎯 Code Quality
# ────────────────────────────────────────────────────────────────────────────────

# Code quality checks
lint:
    poetry run black --check lifearchivist/
    poetry run isort --check-only lifearchivist/
    poetry run ruff check lifearchivist/
    poetry run mypy lifearchivist/

# Fix code formatting and imports
lint-fix:
    poetry run black lifearchivist/
    poetry run isort lifearchivist/
    poetry run ruff check --fix lifearchivist/

# Development workflow: fix code and run tests
dev: lint-fix test
    @echo "✅ Code fixed and tests passed"

# Full CI check (lint + test)
ci: lint test
    @echo "✅ All checks passed"

# ─────────────────────────────────────────────���──────────────────────────────────
# 📚 Documentation
# ────────────────────────────────────────────────────────────────────────────────

# Build documentation
docs-build:
    @echo "📚 Building documentation with Sphinx..."
    cd docs && poetry run make clean
    cd docs && poetry run make html
    @echo "✅ Documentation built at docs/_build/html/index.html"

# Build documentation with strict checking (for CI)
docs-ci:
    @echo "📚 Building documentation with strict checking..."
    cd docs && poetry run make clean
    cd docs && poetry run sphinx-build -W --keep-going -b html . _build/html
    @echo "✅ Documentation built successfully"

# Check documentation links
docs-linkcheck:
    @echo "🔗 Checking documentation links..."
    cd docs && poetry run sphinx-build -b linkcheck . _build/linkcheck
    @echo "�� Link check complete - see docs/_build/linkcheck/output.txt for details"

# Serve documentation locally with auto-reload
docs-serve:
    @echo "📚 Starting documentation server with auto-reload..."
    @echo "📍 Documentation will be available at http://localhost:8001"
    poetry run sphinx-autobuild docs docs/_build/html --port 8001

# Open documentation in browser
docs-open:
    @echo "📚 Opening documentation in browser..."
    open docs/_build/html/index.html 2>/dev/null || xdg-open docs/_build/html/index.html 2>/dev/null || echo "Please open docs/_build/html/index.html manually"

# Generate API documentation from code
docs-api:
    @echo "📚 Generating API documentation..."
    poetry run sphinx-apidoc -f -o docs/api lifearchivist
    @echo "✅ API documentation generated in docs/api/"

# Clean documentation build
docs-clean:
    @echo "🧹 Cleaning documentation build..."
    rm -rf docs/_build
    rm -rf docs/api/*.rst
    @echo "✅ Documentation cleaned"

# Full documentation workflow: clean, generate API docs, build, and serve
docs: docs-clean docs-api docs-build docs-open
    @echo "✅ Documentation ready!"

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Building & Distribution
# ────────────────────────────────────────────────────────────────────────────────

# Build Python package
build:
    poetry build

# Build desktop app for distribution
build-desktop:
    cd desktop && npm run build && npm run pack

# Clean build artifacts
clean:
    rm -rf dist/
    rm -rf build/
    rm -rf desktop/dist/
    rm -rf desktop/build/
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type d -name "*.egg-info" -exec rm -rf {} +
    rm -rf docs/_build

# ════════════════════════════════════════════════════════════════════════════════
# 📋 Command Reference
# ════════════════════════════════════════════════════════════════════════════════
#
# Quick Start:
#   just setup          - Complete initial setup
#   just fullstack      - Start everything for development
#   just verify         - Check all systems are working
#
# Individual Components:
#   just services       - Start Docker services only  
#   just server-dev     - Start backend with auto-reload
#   just ui             - Start frontend only
#   just desktop        - Start full Electron app
#
# Workflows:
#   just dev            - Fix code + run tests
#   just ci             - Full CI checks
#   just reset          - Clean restart
#
# ════════════════════════════════════════════════════════════════════════════════