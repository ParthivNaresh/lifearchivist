from typing import Optional
from unittest.mock import Mock


class MockProgressManager:
    async def get_progress(self, file_id: str) -> Optional[Mock]:
        if file_id == "valid_id":
            progress = Mock()
            progress.to_dict.return_value = {
                "status": "completed",
                "progress": 100,
                "stage": "done",
            }
            return progress
        return None


class MockActivityManager:
    def __init__(self):
        self.MAX_EVENTS = 50

    async def get_recent_events(self, limit: int) -> list:
        return []

    async def get_event_count(self) -> int:
        return 0

    async def clear_all(self) -> int:
        return 0


class MockBackgroundTasks:
    async def get_status(self) -> dict:
        return {
            "enabled": True,
            "worker_status": "running",
            "processing": False,
        }


class MockEnrichmentQueue:
    async def get_stats(self) -> dict:
        return {
            "queue_size": 0,
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
        }


class MockFolderWatcher:
    SUPPORTED_EXTENSIONS = [".pdf", ".txt", ".docx"]

    async def add_folder(self, path, enabled: bool = True) -> str:
        return "test-folder-id"

    async def list_folders(self, enabled_only: bool = False) -> list:
        return []

    async def get_folder(self, folder_id: str):
        if folder_id == "nonexistent-id":
            return None
        if folder_id == "test-folder-id":
            from datetime import datetime
            from pathlib import Path
            mock_folder = Mock()
            mock_folder.id = folder_id
            mock_folder.path = Path("/test/path")
            mock_folder.enabled = True
            mock_folder.created_at = datetime.now()
            mock_folder.status = Mock()
            mock_folder.status.value = "active"
            mock_folder.stats = Mock()
            mock_folder.stats.get_health_status.return_value = Mock(value="healthy")
            mock_folder.stats.get_success_rate.return_value = 1.0
            mock_folder.stats.to_dict.return_value = {}
            mock_folder.is_active.return_value = True
            return mock_folder
        return None

    async def remove_folder(self, folder_id: str) -> bool:
        return folder_id != "nonexistent-id"

    async def enable_folder(self, folder_id: str) -> None:
        pass

    async def disable_folder(self, folder_id: str) -> None:
        pass

    async def schedule_ingestion(self, folder_id: str, file_path) -> None:
        pass

    async def get_aggregate_status(self) -> dict:
        return {
            "total_folders": 0,
            "active_folders": 0,
            "total_pending": 0,
            "total_detected": 0,
            "total_ingested": 0,
            "total_failed": 0,
            "total_bytes_processed": 0,
            "supported_extensions": self.SUPPORTED_EXTENSIONS,
            "ingestion_concurrency": 3,
        }
