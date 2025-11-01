from typing import Any, Dict
from unittest.mock import Mock

from tests.mocks.background import (
    MockActivityManager,
    MockBackgroundTasks,
    MockEnrichmentQueue,
    MockFolderWatcher,
    MockProgressManager,
)
from tests.mocks.llm import MockLLMProviderManager
from tests.mocks.messaging import MockConversationService, MockMessageService
from tests.mocks.services import MockLlamaIndexService
from tests.mocks.storage import MockSettings, MockVault


class MockServiceContainer:
    def __init__(self):
        self.conversation_service = MockConversationService()
        self.message_service = MockMessageService()
        self.llm_provider_manager = MockLLMProviderManager()
        self.llamaindex_service = MockLlamaIndexService()


class MockApplicationServer:
    def __init__(self):
        self.vault = MockVault()
        self.llamaindex_service = MockLlamaIndexService()
        self.progress_manager = MockProgressManager()
        self.document_service = Mock()
        self.metadata_service = Mock()
        self.enrichment_queue = MockEnrichmentQueue()
        self.folder_watcher = MockFolderWatcher()
        self.activity_manager = MockActivityManager()
        self.settings = MockSettings()
        self.service_container = MockServiceContainer()
        self.llm_manager = None
        self.credential_service = None
        self.provider_loader = None
        self.background_tasks = MockBackgroundTasks()

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "file.import":
            return {
                "success": True,
                "result": {
                    "file_id": "test_file_id",
                    "status": "completed",
                    "path": params.get("path", ""),
                },
            }
        return {"success": False, "error": "Unknown tool"}
