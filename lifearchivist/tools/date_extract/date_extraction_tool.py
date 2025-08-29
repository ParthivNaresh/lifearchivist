"""
Content date extraction tool for extracting dates from document text using LLM.
"""

import logging

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
from lifearchivist.utils.logging import log_context, log_event, log_method
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
        operation_name="llm_date_extraction", include_args=True, include_result=True
    )
    async def extract_date_from_text(self, text: str, document_id: str) -> str:
        """Extract dates from text using LLM analysis."""
        # Truncate text if too long to avoid token limits
        text = truncate_text_for_llm(text, max_chars=10000, document_id=document_id)

        # Create prompt and call LLM using direct tool usage
        prompt = create_date_extraction_prompt(text)
        prompt_length = len(prompt)

        log_event(
            "llm_date_extraction_started",
            {
                "document_id": document_id,
                "text_length": len(text),
                "prompt_length": prompt_length,
            },
        )

        ollama_tool = OllamaTool()
        response = await ollama_tool.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=1000,
        )

        log_event(
            "llm_date_extraction_completed",
            {
                "document_id": document_id,
                "response_length": len(response),
                "response_preview": response[:50] if response else "[empty]",
            },
        )

        return response

    @log_method(operation_name="date_storage", include_args=True, include_result=True)
    async def store_extracted_date(self, document_id: str, extracted_date: str):
        """Store extracted dates in LlamaIndex metadata."""
        metadata_updates = {"content_date": extracted_date}

        log_event(
            "date_storage_attempt",
            {
                "document_id": document_id,
                "extracted_date": extracted_date,
                "metadata_keys": list(metadata_updates.keys()),
            },
        )

        success = await self.llamaindex_service.update_document_metadata(
            document_id, metadata_updates, merge_mode="update"
        )

        if success:
            log_event(
                "date_storage_successful",
                {"document_id": document_id, "extracted_date": extracted_date},
            )
        else:
            log_event(
                "date_storage_failed",
                {"document_id": document_id, "extracted_date": extracted_date},
            )
            raise RuntimeError(f"Failed to store content dates for {document_id}")

    @log_method(
        operation_name="date_extraction_pipeline",
        include_args=True,
        include_result=True,
    )
    async def execute(
        self, input_data: ContentDateExtractionInput
    ) -> ContentDateExtractionOutput:
        """Execute the content date extraction tool."""
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

            log_event(
                "date_extraction_started",
                {
                    "document_id": input_data.document_id,
                    "text_length": len(input_data.text_content),
                },
            )

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

                    log_event(
                        "date_extraction_successful",
                        {
                            "document_id": input_data.document_id,
                            "extracted_date": extracted_date,
                            "date_length": len(extracted_date),
                        },
                    )
                else:
                    metrics.set_success(False)
                    metrics.add_metric("dates_stored", False)

                    log_event(
                        "no_dates_found",
                        {
                            "document_id": input_data.document_id,
                            "text_length": len(input_data.text_content),
                        },
                    )

                # Report metrics
                metrics.report("date_extraction_completed")

                return ContentDateExtractionOutput(
                    document_id=input_data.document_id,
                    extracted_dates=extracted_date,
                    total_dates_found=len(extracted_date),
                )

            except Exception as e:
                metrics.set_error(e)
                metrics.report("date_extraction_failed")

                log_event(
                    "date_extraction_error",
                    {
                        "document_id": input_data.document_id,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                )
                raise
