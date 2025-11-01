from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

from tests.mocks import (
    MockApplicationServer,
    MockCredentialService,
    MockLLMManager,
    MockProviderLoader,
)


def _create_test_client(mock_server: MockApplicationServer) -> TestClient:
    from lifearchivist.server.api import dependencies
    from lifearchivist.server.main import create_app

    dependencies.set_server_instance(mock_server)

    @asynccontextmanager
    async def mock_lifespan(app: FastAPI):
        yield

    with patch("lifearchivist.server.main.server", mock_server):
        with patch("lifearchivist.server.main.lifespan", mock_lifespan):
            app = create_app()
            return TestClient(app)


@pytest.fixture
def mock_server() -> MockApplicationServer:
    return MockApplicationServer()


@pytest.fixture
def mock_server_no_services() -> MockApplicationServer:
    server = MockApplicationServer()
    server.llamaindex_service = None
    server.progress_manager = None
    return server


@pytest.fixture
def mock_server_no_search() -> MockApplicationServer:
    server = MockApplicationServer()
    server.llamaindex_service.search_service = None
    return server


@pytest.fixture
def mock_server_no_query() -> MockApplicationServer:
    server = MockApplicationServer()
    server.llamaindex_service.query_service = None
    return server


@pytest.fixture
def mock_server_no_conversation_service() -> MockApplicationServer:
    server = MockApplicationServer()
    server.service_container.conversation_service = None
    return server


@pytest.fixture
def mock_server_no_message_service() -> MockApplicationServer:
    server = MockApplicationServer()
    server.service_container.message_service = None
    return server


@pytest.fixture
def mock_server_with_llm() -> MockApplicationServer:
    server = MockApplicationServer()
    server.llm_manager = MockLLMManager()
    server.credential_service = MockCredentialService()
    server.provider_loader = MockProviderLoader()
    return server


@pytest.fixture
def mock_server_with_vault() -> MockApplicationServer:
    server = MockApplicationServer()
    return server


@pytest.fixture
def mock_server_no_vault() -> MockApplicationServer:
    server = MockApplicationServer()
    server.vault = None
    return server


@pytest.fixture
def mock_server_with_activity() -> MockApplicationServer:
    server = MockApplicationServer()
    return server


@pytest.fixture
def mock_server_no_activity() -> MockApplicationServer:
    server = MockApplicationServer()
    server.activity_manager = None
    return server


@pytest.fixture
def mock_server_with_enrichment() -> MockApplicationServer:
    server = MockApplicationServer()
    return server


@pytest.fixture
def mock_server_no_enrichment() -> MockApplicationServer:
    server = MockApplicationServer()
    server.background_tasks = None
    server.enrichment_queue = None
    return server


@pytest.fixture
def mock_server_with_folder_watcher() -> MockApplicationServer:
    server = MockApplicationServer()
    return server


@pytest.fixture
def mock_server_no_folder_watcher() -> MockApplicationServer:
    server = MockApplicationServer()
    server.folder_watcher = None
    return server


@pytest.fixture
def client(mock_server: MockApplicationServer) -> TestClient:
    return _create_test_client(mock_server)


@pytest.fixture
def client_no_services(mock_server_no_services: MockApplicationServer) -> TestClient:
    return _create_test_client(mock_server_no_services)


@pytest.fixture
def client_no_search(mock_server_no_search: MockApplicationServer) -> TestClient:
    return _create_test_client(mock_server_no_search)


@pytest.fixture
def client_no_query(mock_server_no_query: MockApplicationServer) -> TestClient:
    return _create_test_client(mock_server_no_query)


@pytest.fixture
def client_no_conversation_service(
    mock_server_no_conversation_service: MockApplicationServer,
) -> TestClient:
    return _create_test_client(mock_server_no_conversation_service)


@pytest.fixture
def client_no_message_service(
    mock_server_no_message_service: MockApplicationServer,
) -> TestClient:
    return _create_test_client(mock_server_no_message_service)


@pytest.fixture
def client_with_llm(mock_server_with_llm: MockApplicationServer) -> TestClient:
    return _create_test_client(mock_server_with_llm)


@pytest.fixture
def client_with_vault(mock_server_with_vault: MockApplicationServer) -> TestClient:
    return _create_test_client(mock_server_with_vault)


@pytest.fixture
def client_no_vault(mock_server_no_vault: MockApplicationServer) -> TestClient:
    return _create_test_client(mock_server_no_vault)


@pytest.fixture
def client_with_activity(mock_server_with_activity: MockApplicationServer) -> TestClient:
    return _create_test_client(mock_server_with_activity)


@pytest.fixture
def client_no_activity(mock_server_no_activity: MockApplicationServer) -> TestClient:
    return _create_test_client(mock_server_no_activity)


@pytest.fixture
def client_with_enrichment(mock_server_with_enrichment: MockApplicationServer) -> TestClient:
    return _create_test_client(mock_server_with_enrichment)


@pytest.fixture
def client_no_enrichment(mock_server_no_enrichment: MockApplicationServer) -> TestClient:
    return _create_test_client(mock_server_no_enrichment)


@pytest.fixture
def client_with_folder_watcher(mock_server_with_folder_watcher: MockApplicationServer) -> TestClient:
    return _create_test_client(mock_server_with_folder_watcher)


@pytest.fixture
def client_no_folder_watcher(mock_server_no_folder_watcher: MockApplicationServer) -> TestClient:
    return _create_test_client(mock_server_no_folder_watcher)
