import asyncio
import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..exceptions import ExtractionError
from .base import BaseAgentTool

if TYPE_CHECKING:
    from ...llm import LLMProviderManager
    from ...storage.document_service import LlamaIndexDocumentService


class DataExtractionTool(BaseAgentTool):

    def __init__(
        self,
        document_service: "LlamaIndexDocumentService",
    ):
        self.document_service = document_service

    @property
    def name(self) -> str:
        return "DataExtractionTool"

    @property
    def description(self) -> str:
        return """Extract structured data from documents using LLM.
        
Capabilities:
- Extract specific fields (dates, amounts, names, etc.)
- Handle multiple documents in batch
- Return structured JSON output
- Validate extracted data against schema

Parameters:
- document_ids: List of document IDs to process
- fields: List of field names to extract
- schema: Optional JSON schema for validation"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "document_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Document IDs to extract from",
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Field names to extract",
                },
                "schema": {
                    "type": "object",
                    "description": "Optional JSON schema for validation",
                },
            },
            "required": ["document_ids", "fields"],
        }

    @property
    def requires_llm(self) -> bool:
        return True

    async def execute_with_llm(
        self,
        llm_provider: "LLMProviderManager",
        prompt: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        document_ids = parameters["document_ids"]
        fields = parameters["fields"]
        schema = parameters.get("schema")

        documents = await self._get_documents(document_ids)

        if not documents:
            return {
                "extractions": [],
                "document_count": 0,
                "field_count": len(fields),
                "success_rate": 0.0,
                "error": "No documents found",
            }

        batches = self._create_batches(documents, batch_size=3)

        extraction_tasks = [
            self._extract_batch(batch, fields, schema, llm_provider, prompt)
            for batch in batches
        ]

        batch_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

        all_extractions = []
        for result in batch_results:
            if isinstance(result, Exception):
                continue
            all_extractions.extend(result)

        return {
            "extractions": all_extractions,
            "document_count": len(documents),
            "field_count": len(fields),
            "success_rate": self._calculate_success_rate(all_extractions),
        }

    async def _get_documents(self, document_ids: List[str]) -> List[Dict[str, Any]]:
        documents = []

        for doc_id in document_ids:
            try:
                if not await self.document_service.document_exists(doc_id):
                    continue

                node_ids = await self.document_service.get_node_ids(doc_id)
                if not node_ids:
                    continue

                chunks_result = await self.document_service.get_document_chunks(
                    doc_id, limit=100
                )

                if chunks_result.is_failure():
                    continue

                chunks_data = chunks_result.unwrap()
                chunks = chunks_data.get("chunks", [])

                if not chunks:
                    continue

                full_text = "\n\n".join(chunk.get("text", "") for chunk in chunks)

                documents.append(
                    {"id": doc_id, "text": full_text, "chunk_count": len(chunks)}
                )

            except Exception:
                continue

        return documents

    def _create_batches(
        self, documents: List[Dict[str, Any]], batch_size: int
    ) -> List[List[Dict[str, Any]]]:
        return [
            documents[i : i + batch_size] for i in range(0, len(documents), batch_size)
        ]

    async def _extract_batch(
        self,
        documents: List[Dict],
        fields: List[str],
        schema: Optional[Dict],
        llm_provider: "LLMProviderManager",
        agent_prompt: str,
    ) -> List[Dict]:
        from ...llm.base_provider import LLMMessage

        docs_text = "\n\n---\n\n".join(
            [
                f"Document {i+1} (ID: {doc['id']}):\n{doc['text'][:2000]}"
                for i, doc in enumerate(documents)
            ]
        )

        extraction_prompt = f"""{agent_prompt}

Documents to process:
{docs_text}

Fields to extract: {', '.join(fields)}

{f"Validation schema: {json.dumps(schema, indent=2)}" if schema else ""}

Extract the specified fields from each document. Return JSON array:
[
  {{
    "document_id": "doc_id",
    "extractions": {{
      "field_name": "extracted_value",
      ...
    }},
    "confidence": 0.0-1.0
  }},
  ...
]

Rules:
1. Only extract if clearly stated in document
2. Follow schema types if provided
3. Include confidence score
4. Return empty extractions if field not found"""

        result = await llm_provider.generate(
            messages=[LLMMessage(role="user", content=extraction_prompt)],
            model="gpt-4o-mini",
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        if result.is_failure():
            raise ExtractionError(result.error)

        response = result.unwrap()
        data = json.loads(response.content)

        if isinstance(data, dict) and "extractions" in data:
            return data["extractions"]
        elif isinstance(data, list):
            return data
        else:
            return []

    def _calculate_success_rate(self, extractions: List[Dict]) -> float:
        if not extractions:
            return 0.0

        successful = sum(
            1
            for e in extractions
            if e.get("extractions") and any(e["extractions"].values())
        )

        return successful / len(extractions)
