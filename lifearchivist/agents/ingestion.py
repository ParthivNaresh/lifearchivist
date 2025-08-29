"""
Ingestion agent for processing documents.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class IngestionAgent:
    """Agent responsible for orchestrating document ingestion."""

    def __init__(self, database, vault, tool_registry):
        self.database = database
        self.vault = vault
        self.tool_registry = tool_registry

    async def process(self, request: str) -> Dict[str, Any]:
        """Process an ingestion request."""
        logger.info(f"Processing ingestion request: {request}")

        # TODO: Implement actual ingestion pipeline
        # This would involve:
        # 1. Parse request (file path, options)
        # 2. Import file using file.import tool
        # 3. Extract text using appropriate extract tool
        # 4. Generate embeddings using index.embed tool
        # 5. Auto-tag using org.tag tool
        # 6. Store in database and vector store

        return {
            "status": "processed",
            "message": f"Ingestion request processed: {request}",
        }

    async def ingest_file(self, file_path: str, **options) -> Dict[str, Any]:
        """Ingest a single file through the complete pipeline."""
        try:
            # Step 1: Import file
            import_tool = self.tool_registry.get_tool("file.import")
            import_result = await import_tool.execute(path=file_path, **options)

            file_id = import_result["file_id"]
            logger.info(f"File imported with ID: {file_id}")

            # Step 2: Extract text
            extract_tool = self.tool_registry.get_tool("extract.text")
            extract_result = await extract_tool.execute(file_id=file_id)

            text_content = extract_result["text"]

            # Step 3: Generate embeddings
            embed_tool = self.tool_registry.get_tool("index.embed")
            embed_result = await embed_tool.execute(text=text_content)

            # Step 4: Auto-tag
            tag_tool = self.tool_registry.get_tool("org.tag")
            tag_result = await tag_tool.execute(file_id=file_id, text=text_content)

            # Step 5: Store everything in database
            await self.database.create_document(
                doc_id=file_id,
                file_hash=import_result["hash"],
                original_path=import_result["original_path"],
                mime_type=import_result["mime_type"],
                size_bytes=import_result["size"],
                created_at=import_result["created_at"],
            )

            await self.database.store_content(
                doc_id=file_id,
                text_content=text_content,
                extraction_method=extract_result["metadata"]["extraction_method"],
            )

            await self.database.update_document_status(file_id, "ready")

            logger.info(f"Document processing completed: {file_id}")

            return {
                "success": True,
                "file_id": file_id,
                "tags": tag_result["tags"],
                "word_count": len(text_content.split()),
            }

        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            if "file_id" in locals():
                await self.database.update_document_status(file_id, "failed", str(e))

            return {"success": False, "error": str(e)}
