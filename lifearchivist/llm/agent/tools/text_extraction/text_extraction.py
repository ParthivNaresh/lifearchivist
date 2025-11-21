import asyncio
import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence

from pydantic import BaseModel

from .....llm import LLMMessage
from .....llm.agent.exceptions import ToolExecutionError
from .....llm.agent.tools.base import BaseAgentTool
from .....llm.agent.tools.text_extraction.models import (
    TextExtractionMetrics,
    TextExtractionParams,
)
from .....llm.agent.utils.parsing import (
    _response_text,
    _unwrap_result_or_raise,
    clean_extraction_chunks,
)
from .....llm.agent.utils.prompt_builder import _build_text_extraction_system_message
from .....utils.logx import log_event

if TYPE_CHECKING:
    from llm import LLMProviderManager
    from storage.document_service import LlamaIndexDocumentService


class TextExtractionTool(BaseAgentTool):
    """
    Extracts and summarizes document content as free-form text using an LLM.

    Unlike structured_extraction which produces JSON, this tool generates prose,
    narratives, summaries, or analyses in natural language. Ideal for document
    summarization, content analysis, and narrative generation tasks.

    Contract:
      - requires_llm = True
      - input_model = TextExtractionParams
      - Returns: {text, citations, meta}
    """

    name = "text_extraction"
    description = (
        "Extracts and summarizes document content as free-form text. "
        "Produces prose, narratives, summaries, or analyses rather than structured JSON. "
        "Supports multiple output styles (concise, detailed, bullet points, narrative, technical, executive) "
        "and focus areas (overview, key points, insights, recommendations, analysis, comparison). "
        "Ideal for document summarization and content analysis tasks."
    )
    requires_llm = True
    input_model = TextExtractionParams

    def __init__(
        self,
        *,
        document_service: Optional["LlamaIndexDocumentService"] = None,
        llm_timeout_s: float = 60.0,
    ) -> None:
        self.document_service = document_service
        self.llm_timeout_s = float(llm_timeout_s)

    async def execute_typed(self, *, params: BaseModel, context: Dict[str, Any]) -> Any:
        """
        This tool requires an LLM; non-LLM execution is not supported.
        """
        raise ToolExecutionError(
            f"{self.name} requires LLM; use execute_with_llm via the orchestrator."
        )

    async def execute_with_llm(
        self,
        *,
        llm_provider: "LLMProviderManager",
        prompt: str,
        params: BaseModel,
        context: Dict[str, Any],
    ) -> Any:
        """
        Steps:
          1) Fetch & clean chunks from documents
          2) Build extraction request with style/focus guidance
          3) Call LLM to generate free-form text output
          4) Return text with optional citations and metadata
        """
        self._assert_ready()

        log_event(
            "================================================  TEXT EXTRACTION  ================================================"
        )
        log_event("")

        p = (
            params
            if isinstance(params, TextExtractionParams)
            else TextExtractionParams.model_validate(params.model_dump())
        )

        metrics = TextExtractionMetrics()
        raw_chunks = await self._gather_chunks(
            document_ids=p.document_ids,
            max_chunks=p.max_chunks_per_doc,
            max_chars_per_chunk=p.max_chars_per_chunk,
            max_total_chars=p.max_total_chars,
            fetch_concurrency=p.fetch_concurrency,
            metrics=metrics,
        )

        chunks = clean_extraction_chunks(
            raw_chunks,
            normalize_unicode=True,
            skip_empty=True,
        )

        metrics.chunks_used = len(chunks)
        metrics.chars_used = sum(len(c.get("text", "")) for c in chunks)

        if not chunks:
            log_event(
                "text_extraction_no_chunks",
                {"document_ids": p.document_ids},
                level=30,
            )
            return {
                "text": "No content available from the specified documents.",
                "citations": [],
                "meta": {
                    "documents_seen": metrics.documents_seen,
                    "chunks_used": 0,
                    "chars_used": 0,
                    "output_length_words": 0,
                    "output_length_chars": 0,
                    "model": p.model,
                    "temperature": p.temperature,
                },
            }

        request_payload = {
            "instruction": prompt,
            "user_instructions": p.instructions,
            "style": p.style.value,
            "focus": p.focus.value if p.focus else None,
            "max_output_length": p.max_output_length,
            "include_citations": p.include_citations,
            "documents": [{"doc_id": c["doc_id"], "text": c["text"]} for c in chunks],
        }

        system_content = _build_text_extraction_system_message(
            style=p.style.value,
            focus=p.focus.value if p.focus else None,
            max_output_length=p.max_output_length,
            include_citations=p.include_citations,
        )

        messages: List[LLMMessage] = [
            LLMMessage(
                role="system",
                content=system_content,
            ),
            LLMMessage(
                role="user",
                content=json.dumps(request_payload, ensure_ascii=False),
                metadata={"payload": request_payload},
            ),
        ]

        model_to_use = p.model or "qwen2.5:7b"

        log_event(
            "-------------------------------------- REQUEST PAYLOAD --------------------------------------"
        )
        log_event("SYSTEM")
        log_event(system_content)
        log_event("USER")
        log_event({"prompt": prompt})
        log_event(json.dumps({"user_instructions": p.instructions}, indent=2))
        log_event(
            json.dumps(
                {"style": p.style.value, "focus": p.focus.value if p.focus else None},
                indent=2,
            )
        )
        log_event(
            json.dumps(
                {"document_count": len(chunks), "total_chars": metrics.chars_used},
                indent=2,
            )
        )

        extracted_text = await self._call_llm_generate(
            llm_provider=llm_provider,
            messages=messages,
            model=model_to_use,
            temperature=p.temperature,
            max_tokens=p.max_tokens,
            timeout_s=self.llm_timeout_s,
        )

        log_event(
            "-------------------------------------- LLM RESPONSE --------------------------------------"
        )
        log_event(
            extracted_text[:1000] if len(extracted_text) > 1000 else extracted_text
        )

        citations = (
            self._extract_citations(extracted_text, chunks)
            if p.include_citations
            else []
        )

        metrics.output_length_chars = len(extracted_text)
        metrics.output_length_words = len(extracted_text.split())

        result: Dict[str, Any] = {
            "text": extracted_text,
            "citations": citations,
            "meta": {
                "documents_seen": metrics.documents_seen,
                "chunks_used": metrics.chunks_used,
                "chars_used": metrics.chars_used,
                "output_length_words": metrics.output_length_words,
                "output_length_chars": metrics.output_length_chars,
                "model": p.model,
                "temperature": p.temperature,
                "max_tokens": p.max_tokens,
                "style": p.style.value,
                "focus": p.focus.value if p.focus else None,
            },
        }

        log_event(
            "text_extraction_success",
            {
                "documents_seen": metrics.documents_seen,
                "chunks_used": metrics.chunks_used,
                "chars_used": metrics.chars_used,
                "output_length_words": metrics.output_length_words,
                "output_length_chars": metrics.output_length_chars,
            },
        )

        return result

    def _assert_ready(self) -> None:
        if self.document_service is None:
            raise ToolExecutionError(f"{self.name}: document_service is not configured")

    async def _gather_chunks(
        self,
        *,
        document_ids: Sequence[str],
        max_chunks: int,
        max_chars_per_chunk: int,
        max_total_chars: int,
        fetch_concurrency: int,
        metrics: TextExtractionMetrics,
    ) -> List[Dict[str, str]]:
        """
        Fetch chunks per document asynchronously with bounded concurrency.
        Enforces per-chunk and total character budgets.
        """
        sem = asyncio.Semaphore(fetch_concurrency)
        all_chunks: List[Dict[str, str]] = []

        async def _fetch_one(doc_id: str) -> List[Dict[str, str]]:
            async with sem:
                doc_service = self.document_service
                if doc_service is None:
                    return []
                try:
                    chunks_result = await doc_service.get_document_chunks(
                        doc_id, limit=max_chunks
                    )
                except Exception:
                    return []

                if hasattr(chunks_result, "is_failure") and chunks_result.is_failure():
                    return []

                data = (
                    chunks_result.unwrap()
                    if hasattr(chunks_result, "unwrap")
                    else chunks_result
                )
                raw_chunks = (
                    (data or {}).get("chunks", []) if isinstance(data, dict) else data
                )

                out: List[Dict[str, str]] = []
                for ch in raw_chunks or []:
                    text = (
                        ch.get("text")
                        if isinstance(ch, dict)
                        else getattr(ch, "text", "")
                    ) or ""
                    if not text:
                        continue
                    if len(text) > max_chars_per_chunk:
                        text = text[:max_chars_per_chunk]
                    out.append({"doc_id": doc_id, "text": text})
                return out

        per_doc_lists = await asyncio.gather(
            *[_fetch_one(doc_id) for doc_id in document_ids],
            return_exceptions=False,
        )

        metrics.documents_seen = len(document_ids)
        running_chars = 0
        for chunk_list in per_doc_lists:
            for ch in chunk_list:
                t = ch["text"]
                if running_chars + len(t) > max_total_chars:
                    return all_chunks
                all_chunks.append(ch)
                running_chars += len(t)

        return all_chunks

    async def _call_llm_generate(
        self,
        *,
        llm_provider: "LLMProviderManager",
        messages: List[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_s: float,
    ) -> str:
        """
        Call LLM to generate free-form text output.
        Returns the raw text response.
        """
        try:
            result = await llm_provider.generate(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout_s=timeout_s,
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            raise ToolExecutionError(
                f"{self.name}: LLM generate raised {type(e).__name__}: {e}"
            ) from e

        if hasattr(result, "is_failure") and result.is_failure():
            error_msg = result.unwrap_error()
            log_event(
                "text_extraction_llm_failed",
                {
                    "error": str(error_msg),
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                level=40,
            )
            raise ToolExecutionError(f"{self.name}: LLM call failed: {error_msg}")

        resp = _unwrap_result_or_raise(result)
        raw = _response_text(resp)

        if not raw or not isinstance(raw, str):
            log_event(
                "text_extraction_empty_response",
                {"response_type": type(raw).__name__},
                level=30,
            )
            return "No content could be extracted from the documents."

        return raw.strip()

    def _extract_citations(
        self, text: str, chunks: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Extract document citations from the generated text.
        Looks for document IDs mentioned in the text and creates citation entries.
        """
        citations: List[Dict[str, str]] = []
        doc_ids_seen = set()

        for chunk in chunks:
            doc_id = chunk.get("doc_id", "")
            if doc_id and doc_id not in doc_ids_seen:
                if doc_id in text or f"[{doc_id}]" in text or f"({doc_id})" in text:
                    citations.append(
                        {
                            "document_id": doc_id,
                            "type": "source_document",
                        }
                    )
                    doc_ids_seen.add(doc_id)

        if not citations and chunks:
            for chunk in chunks[:3]:
                doc_id = chunk.get("doc_id", "")
                if doc_id and doc_id not in doc_ids_seen:
                    citations.append(
                        {
                            "document_id": doc_id,
                            "type": "source_document",
                        }
                    )
                    doc_ids_seen.add(doc_id)

        return citations
