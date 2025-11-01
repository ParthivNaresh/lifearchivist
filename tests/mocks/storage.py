from typing import Any, Dict


class MockVault:
    def __init__(self):
        from pathlib import Path
        self.content_dir = Path("/test/vault/content")

    async def delete_file_by_hash(self, file_hash: str, metrics: Dict[str, Any]) -> None:
        metrics["files_deleted"] = 0
        metrics["bytes_reclaimed"] = 0

    async def clear_all_files(self, exclude_hashes: list[str]) -> Dict[str, Any]:
        return {
            "files_deleted": 0,
            "bytes_reclaimed": 0,
            "orphaned_files_deleted": 0,
            "orphaned_bytes_reclaimed": 0,
            "errors": [],
        }

    async def get_vault_statistics(self) -> Dict[str, Any]:
        return {
            "total_files": 0,
            "total_size_bytes": 0,
            "file_types": {},
        }


class MockSettings:
    def __init__(self):
        self.max_file_size_mb = 100
        self.llm_model = "llama3.2:1b"
        self.embedding_model = "all-MiniLM-L6-v2"
        self.theme = "dark"
        self.vault_path = "/test/vault"
        self.lifearch_home = "/test/home"
