"""
Pytest configuration and shared fixtures for Life Archivist testing.

This module provides the core testing infrastructure including:
- Real services with temporary storage
- Test client fixtures for API testing
- Temporary vault and storage management
"""

import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from lifearchivist.server.main import create_app
from lifearchivist.server.api.dependencies import set_server_instance
from lifearchivist.server.mcp_server import MCPServer
from lifearchivist.storage.vault.vault import Vault
from lifearchivist.storage.llamaindex_service.llamaindex_service import LlamaIndexService
from lifearchivist.config.settings import Settings
from lifearchivist.server.progress_manager import ProgressManager

# Import document lifecycle fixtures
from .fixtures.document_lifecycle import *  # noqa: F401,F403


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp(prefix="lifearch_test_"))
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_vault_path(temp_dir: Path) -> Path:
    """Create a temporary vault path for testing."""
    vault_path = temp_dir / "test_vault"
    vault_path.mkdir(parents=True, exist_ok=True)
    return vault_path


@pytest.fixture
def test_settings(test_vault_path: Path, temp_dir: Path) -> Settings:
    """Create test settings with temporary paths."""
    # Create temporary llamaindex storage
    llamaindex_storage = temp_dir / "llamaindex_storage" 
    llamaindex_storage.mkdir(parents=True, exist_ok=True)
    
    return Settings(
        vault_path=test_vault_path,
        lifearch_home=temp_dir,
        # Disable external dependencies for unit tests
        enable_agents=False,
        enable_websockets=False,
        api_only_mode=True,
        # Use minimal models for testing
        llm_model="llama3.2:1b",
        embedding_model="all-MiniLM-L6-v2",
    )


@pytest_asyncio.fixture
async def test_vault(test_vault_path: Path) -> Vault:
    """Create a real Vault instance for testing with temporary storage."""
    vault = Vault(test_vault_path)
    await vault.initialize()
    yield vault
    # Cleanup happens automatically when temp_dir is removed


@pytest_asyncio.fixture 
async def test_llamaindex_service(test_settings: Settings, test_vault: Vault) -> LlamaIndexService:
    """Create a real LlamaIndex service for testing."""
    # Create in-memory/temp storage for LlamaIndex
    service = LlamaIndexService(vault=test_vault)
    yield service
    # Clear data after test
    try:
        await service.clear_all_data()
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture
def test_progress_manager() -> ProgressManager:
    """Create a mock ProgressManager for testing."""
    from unittest.mock import AsyncMock, MagicMock
    
    # ProgressManager requires Redis, so we'll mock it for now
    # But we need to properly mock async methods
    mock_manager = MagicMock()
    
    # Mock the async get_progress method to return None for any file_id
    # This simulates the behavior for nonexistent progress records
    mock_manager.get_progress = AsyncMock(return_value=None)
    
    return mock_manager


@pytest_asyncio.fixture
async def test_server(
    test_settings: Settings,
    test_vault: Vault,
    test_llamaindex_service: LlamaIndexService,
    test_progress_manager: ProgressManager
) -> MCPServer:
    """Create a real MCP server for testing with real services."""
    server = MCPServer()
    server.settings = test_settings
    server.vault = test_vault
    server.llamaindex_service = test_llamaindex_service
    server.progress_manager = test_progress_manager
    
    # Initialize tool registry with real services
    from lifearchivist.tools.registry import ToolRegistry
    server.tool_registry = ToolRegistry(
        vault=test_vault,
        llamaindex_service=test_llamaindex_service,
        progress_manager=test_progress_manager,
    )
    await server.tool_registry.register_all()
    
    # Set as global instance for dependency injection
    set_server_instance(server)
    
    yield server
    
    # Cleanup
    set_server_instance(None)


@pytest.fixture
def test_app(test_server: MCPServer) -> FastAPI:
    """Create a test FastAPI application."""
    app = create_app()
    yield app


@pytest.fixture
def sync_client(test_app: FastAPI) -> TestClient:
    """Create a synchronous test client for simple API testing."""
    return TestClient(test_app)


@pytest_asyncio.fixture
async def async_client(test_app: FastAPI):
    """Create an async test client for advanced API testing."""
    from httpx import ASGITransport
    async with AsyncClient(
        transport=ASGITransport(app=test_app), 
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def api_headers() -> Dict[str, str]:
    """Standard headers for API requests."""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# Test data fixtures
@pytest.fixture
def sample_metadata() -> Dict[str, Any]:
    """Sample document metadata for testing."""
    return {
        "source": "test_upload",
        "author": "Test User",
        "created_date": "2024-01-01T00:00:00Z",
        "category": "test_document",
    }


@pytest.fixture
def sample_tags() -> list[str]:
    """Sample tags for testing."""
    return ["test", "document", "sample"]


@pytest.fixture
def search_request_payload() -> Dict[str, Any]:
    """Sample search request payload."""
    return {
        "query": "test query",
        "mode": "keyword",
        "limit": 20,
        "offset": 0,
        "include_content": False,
        "filters": {},
    }


@pytest.fixture
def ask_request_payload() -> Dict[str, Any]:
    """Sample Q&A request payload."""
    return {
        "question": "What is this document about?",
        "context_limit": 5,
    }




# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests with mocked dependencies"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests with real local services"
    )
    config.addinivalue_line(
        "markers", "live: Live tests with real external services"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests"
    )
    config.addinivalue_line(
        "markers", "requires_docker: Tests that require Docker services"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on their location."""
    for item in items:
        # Auto-mark unit tests
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Auto-mark integration tests
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            
        # Auto-mark live tests
        elif "live" in str(item.fspath):
            item.add_marker(pytest.mark.live)
            item.add_marker(pytest.mark.requires_docker)