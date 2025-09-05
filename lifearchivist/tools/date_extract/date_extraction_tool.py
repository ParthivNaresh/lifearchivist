"""
Content date extraction tool for extracting dates from document text using LLM.
"""

import logging
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
from lifearchivist.utils.logging import log_context, log_method
from lifearchivist.utils.logging.structured import MetricsCollector

logger = logging.getLogger(__name__)


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

    @log_method(
        operation_name="llm_date_extraction",
        include_args=True,
        include_result=True,
        indent=4,
    )
    async def extract_date_from_text(self, text: str, document_id: str) -> str:
        """Extract dates from text using LLM analysis."""
        # Truncate text if too long to avoid token limits
        text = truncate_text_for_llm(text, max_chars=10000, document_id=document_id)

        # Create prompt and call LLM using direct tool usage
        prompt = create_date_extraction_prompt(text)
        prompt_length = len(prompt)

        ollama_tool = OllamaTool()
        response = await ollama_tool.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=1000,
        )

        return response

    @log_method(operation_name="date_storage", include_args=True, include_result=True)
    async def store_extracted_date(self, document_id: str, extracted_date: str):
        """Store extracted dates in LlamaIndex metadata."""
        metadata_updates = {"content_date": extracted_date}

        success = await self.llamaindex_service.update_document_metadata(
            document_id, metadata_updates, merge_mode="update"
        )

        if not success:
            raise RuntimeError(f"Failed to store content dates for {document_id}")

    @log_method(
        operation_name="date_extraction_pipeline",
        include_args=True,
        include_result=True,
        indent=3,
    )
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the content date extraction tool."""
        # Extract input_data from kwargs
        input_data = kwargs.get("input_data")
        if not input_data:
            raise ValueError("input_data is required")
        if not isinstance(input_data, ContentDateExtractionInput):
            input_data = ContentDateExtractionInput(**input_data)

        with log_context(
            operation="date_extraction",
            document_id=input_data.document_id,
            text_length=len(input_data.text_content),
        ) as _:

            # Initialize metrics collector
            metrics = MetricsCollector("date_extraction")
            metrics.start()

            metrics.add_metric("text_length", len(input_data.text_content))
            metrics.add_metric("document_id", input_data.document_id)

            try:
                # Extract dates from text
                extracted_date = await self.extract_date_from_text(
                    input_data.text_content, input_data.document_id
                )

                metrics.add_metric("date_extracted", bool(extracted_date))
                metrics.add_metric(
                    "extracted_date_length",
                    len(extracted_date) if extracted_date else 0,
                )

                if extracted_date:
                    # Store extracted dates in database
                    await self.store_extracted_date(
                        input_data.document_id, extracted_date
                    )

                    metrics.set_success(True)
                    metrics.add_metric("dates_stored", True)
                else:
                    metrics.set_success(False)
                    metrics.add_metric("dates_stored", False)

                # Report metrics
                metrics.report("date_extraction_completed")

                result = ContentDateExtractionOutput(
                    document_id=input_data.document_id,
                    extracted_dates=extracted_date,
                    total_dates_found=len(extracted_date),
                )
                return result.dict()

            except Exception as e:
                metrics.set_error(e)
                metrics.report("date_extraction_failed")
                raise
