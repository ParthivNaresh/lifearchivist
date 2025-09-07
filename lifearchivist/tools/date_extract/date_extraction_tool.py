"""
Content date extraction tool for extracting dates from document text using LLM.
"""

from typing import Any, Dict

from lifearchivist.schemas.tool_schemas import (
    ContentDateExtractionInput,
    ContentDateExtractionOutput,
)
from lifearchivist.storage.llamaindex_service import LlamaIndexService
from lifearchivist.tools.base import BaseTool, ToolMetadata
from lifearchivist.tools.date_extract.date_extraction_utils import (
    create_date_extraction_prompt,
    truncate_text_for_llm,
)
from lifearchivist.tools.ollama.ollama_tool import OllamaTool
from lifearchivist.utils.logging import log_event, track


class ContentDateExtractionTool(BaseTool):
    """Tool for extracting content dates from document text using LLM."""

    def __init__(self, llamaindex_service: LlamaIndexService):
        super().__init__()
        self.llamaindex_service = llamaindex_service
        self.ollama_tool = None

    def _get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="extract.content_dates",
            description="Extract dates from document content using AI language model analysis",
            input_schema=ContentDateExtractionInput.model_json_schema(),
            output_schema=ContentDateExtractionOutput.model_json_schema(),
            async_tool=True,
            idempotent=True,
        )

    @track(
        operation="llm_date_extraction",
        include_args=["document_id"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def extract_date_from_text(self, text: str, document_id: str) -> str:
        """Extract dates from text using LLM analysis."""
        # Truncate text if too long to avoid token limits
        original_length = len(text)
        text = truncate_text_for_llm(text, max_chars=10000, document_id=document_id)

        if len(text) < original_length:
            log_event(
                "text_truncated_for_llm",
                {
                    "document_id": document_id,
                    "original_length": original_length,
                    "truncated_length": len(text),
                    "truncation_ratio": len(text) / original_length,
                },
            )

        # Create prompt and call LLM using direct tool usage
        prompt = create_date_extraction_prompt(text)

        log_event(
            "llm_prompt_created",
            {
                "document_id": document_id,
                "text_length": len(text),
                "prompt_length": len(prompt),
            },
        )

        ollama_tool = OllamaTool()
        response = await ollama_tool.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=1000,
        )

        # Log the raw LLM response for debugging
        log_event(
            "llm_response_received",
            {
                "document_id": document_id,
                "response": response.strip() if response else "None",
                "response_length": len(response) if response else 0,
            },
        )

        return response.strip() if response else ""

    @track(
        operation="date_metadata_storage",
        include_args=["document_id"],
        track_performance=True,
        emit_events=False,  # Silent operation - metadata updates are logged by LlamaIndex service
    )
    async def store_extracted_date(self, document_id: str, extracted_date: str):
        """Store extracted dates in LlamaIndex metadata."""
        metadata_updates = {"content_date": extracted_date}

        success = await self.llamaindex_service.update_document_metadata(
            document_id, metadata_updates, merge_mode="update"
        )

        if not success:
            raise RuntimeError(f"Failed to store content dates for {document_id}")

    @track(
        operation="date_extraction_pipeline",
        include_args=["document_id"],
        include_result=True,
        track_performance=True,
    )
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the content date extraction tool."""
        # Extract input_data from kwargs
        input_data = kwargs.get("input_data")
        if not input_data:
            raise ValueError("input_data is required")
        if not isinstance(input_data, ContentDateExtractionInput):
            input_data = ContentDateExtractionInput(**input_data)

        document_id = input_data.document_id
        word_count = len(input_data.text_content.split())

        log_event(
            "date_extraction_started",
            {
                "document_id": document_id,
                "word_count": word_count,
            },
        )

        # Extract dates from text
        extracted_date = await self.extract_date_from_text(
            input_data.text_content, document_id
        )

        # Check if we got a valid date (not empty, not error message)
        has_valid_date = (
            extracted_date
            and extracted_date.strip()
            and not extracted_date.lower().startswith(
                ("no date", "none", "not found", "unable")
            )
        )

        if has_valid_date:
            await self.store_extracted_date(document_id, extracted_date)
            dates_found = 1
            log_event(
                "date_extraction_completed",
                {
                    "document_id": document_id,
                    "dates_found": dates_found,
                    "extracted_date": extracted_date,
                },
            )
        else:
            dates_found = 0
            extracted_date = ""
            log_event(
                "date_extraction_completed",
                {
                    "document_id": document_id,
                    "dates_found": dates_found,
                },
            )

        result = ContentDateExtractionOutput(
            document_id=document_id,
            extracted_date=extracted_date,
            total_dates_found=dates_found,
        )
        return result.dict()
