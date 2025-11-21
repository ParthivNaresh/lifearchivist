import asyncio
import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence

from pydantic import BaseModel

from .....llm import LLMMessage
from .....llm.agent.exceptions import ToolExecutionError
from .....llm.agent.schema_builder import SchemaBuilder
from .....llm.agent.tools.base import BaseAgentTool
from .....llm.agent.tools.structured_extraction.models import (
    ExtractionMetrics,
    StructuredExtractionParams,
)
from .....llm.agent.utils.parsing import (
    _parse_json_object_lenient,
    _response_text,
    _unwrap_result_or_raise,
    clean_extraction_chunks,
)
from .....utils.logx import log_event
from ...utils.prompt_builder import _build_structured_extraction_system_message

if TYPE_CHECKING:
    from llm import LLMProviderManager
    from storage.document_service import LlamaIndexDocumentService


class StructuredExtractionTool(BaseAgentTool):
    """
    Extracts structured data from documents using an LLM.

    Contract:
      - requires_llm = True
      - input_model = DataExtractionParams
      - The spawner passes PromptBuilder's `prompt` and a `context` dict.
      - Returns a dict: {extractions, meta, hints}.
    """

    name = "structured_extraction"
    description = (
        "Extracts structured information from specified documents. "
        "Performs targeted retrieval, compacts context under a strict budget, "
        "and synthesizes a STRICT JSON result with per-field provenance."
    )
    requires_llm = True
    input_model = StructuredExtractionParams

    def __init__(
        self,
        *,
        document_service: Optional["LlamaIndexDocumentService"] = None,
        llm_timeout_s: float = 30.0,
        logger: Optional[Any] = None,
    ) -> None:
        self.document_service = document_service
        self.llm_timeout_s = float(llm_timeout_s)
        import logging as _logging  # defer stdlib logging import

        self.log = logger or _logging.getLogger(__name__)

    # ---------------------------
    # Public execution API (typed)
    # ---------------------------

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
          1) Fetch & trim chunks (bounded concurrency + budgets)
          2) Build a compact request payload
          3) Call LLMProviderManager.generate(...) and normalize its response
        """
        self._assert_ready()

        log_event(
            "================================================  STRUCTURED EXTRACTION  ================================================"
        )
        log_event("")

        p = (
            params
            if isinstance(params, StructuredExtractionParams)
            else StructuredExtractionParams.model_validate(params.model_dump())
        )

        metrics = ExtractionMetrics()
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

        output_schema = self._resolve_output_schema(p)
        instructions = self._resolve_instructions(p)

        full_schema = SchemaBuilder.wrap_with_provenance(
            output_schema,
            require_provenance=p.require_provenance,
        )

        request_payload = {
            "instruction": prompt,
            "extraction_instructions": instructions,
            "documents": [{"doc_id": c["doc_id"], "text": c["text"]} for c in chunks],
        }

        system_content = _build_structured_extraction_system_message(
            full_schema, instructions
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
        log_event(json.dumps({"extraction_instructions": instructions}, indent=2))
        log_event(
            json.dumps(
                {
                    "documents": [
                        {"doc_id": c["doc_id"], "text": c["text"]} for c in chunks
                    ]
                },
                indent=2,
            )
        )

        llm_data = await self._call_llm_generate(
            llm_provider=llm_provider,
            messages=messages,
            model=model_to_use,
            temperature=p.temperature,
            max_tokens=p.max_tokens,
            timeout_s=self.llm_timeout_s,
        )

        log_event(
            "-------------------------------------- PARSED LLM RESPONSE --------------------------------------"
        )
        log_event(json.dumps(llm_data, indent=4))

        extractions = (
            llm_data.get("extractions", []) if isinstance(llm_data, dict) else []
        )
        provenance = (
            llm_data.get("provenance", []) if isinstance(llm_data, dict) else []
        )

        result: Dict[str, Any] = {
            "extractions": extractions,
            "provenance": provenance,
            "meta": {
                "documents_seen": metrics.documents_seen,
                "chunks_used": metrics.chunks_used,
                "chars_used": metrics.chars_used,
                "model": p.model,
                "temperature": p.temperature,
                "max_tokens": p.max_tokens,
            },
        }

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
        metrics: ExtractionMetrics,
    ) -> List[Dict[str, str]]:
        """
        Fetch chunks per document asynchronously (bounded by a semaphore),
        trim each chunk to a per-chunk char budget, and enforce an overall
        max_total_chars cap (greedy, stable order).
        """
        sem = asyncio.Semaphore(fetch_concurrency)
        all_chunks: List[Dict[str, str]] = []

        async def _fetch_one(doc_id: str) -> List[Dict[str, str]]:
            async with sem:
                doc_service = self.document_service
                if doc_service is None:
                    self.log.warning(
                        "Document service not configured; skipping %s", doc_id
                    )
                    return []
                try:
                    chunks_result = await doc_service.get_document_chunks(
                        doc_id, limit=max_chunks
                    )
                except Exception as e:
                    self.log.warning("Failed to fetch chunks for %s: %s", doc_id, e)
                    return []

                # Support Result-like or raw list/dict responses
                if hasattr(chunks_result, "is_failure") and chunks_result.is_failure():
                    self.log.warning("Chunk fetch failure for %s", doc_id)
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
                    # Stop at first overflow to preserve determinism
                    return all_chunks
                all_chunks.append(ch)
                running_chars += len(t)

        metrics.chunks_used = len(all_chunks)
        metrics.chars_used = running_chars
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
    ) -> Any:
        """
        Adapter to LLMProviderManager.generate(...).
        We honor your Result[...] contract and surface ToolExecutionError on failure.
        """
        # Provide sane defaults; the router can still pick best provider/model if model is None.
        try:
            # Ask adapters to produce pure JSON objects. Providers that don't support these
            # kwargs will ignore them (safe no-ops).
            result = await llm_provider.generate(
                messages=messages,
                model=model,
                temperature=temperature,  # ← honor caller's temperature
                max_tokens=max_tokens,
                timeout_s=timeout_s,  # ← honor timeout
                response_format={"type": "json_object"},  # OpenAI-style adapters
                format="json",  # Ollama-style adapters
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            raise ToolExecutionError(
                f"{self.name}: LLM generate raised {type(e).__name__}: {e}"
            ) from e

        # Result[T, E] handling
        if hasattr(result, "is_failure") and result.is_failure():
            error_msg = result.unwrap_error()
            log_event(
                "extraction_llm_generate_failed",
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
        obj = _parse_json_object_lenient(raw)

        if obj is None:
            log_event(
                "extraction_json_parse_failed",
                {
                    "error": "Failed to parse JSON",
                    "preview": (
                        raw[:1000] + raw[-1000:]
                        if isinstance(raw, str)
                        else str(raw)[:1000] + raw[-1000:]
                    ),
                },
                level=40,
            )
            return {
                "extractions": [],
                "provenance": [],
                "parse_error": True,
                "raw_text": raw[:1000] if isinstance(raw, str) else str(raw)[:1000],
            }

        if isinstance(obj, list):
            obj = {"extractions": obj, "provenance": []}

        # TODO: NEED SOMETHING BETTER THAN THIS
        if isinstance(obj, dict) and "extractions" not in obj.keys():
            obj = {"extractions": obj, "provenance": []}

        if not isinstance(obj, dict):
            log_event(
                "extraction_unexpected_type",
                {"type": type(obj).__name__, "value": str(obj)[:500]},
                level=30,
            )
            return {
                "extractions": [],
                "provenance": [],
                "parse_error": True,
                "raw_value": obj,
            }

        obj.setdefault("extractions", [])
        obj.setdefault("provenance", [])

        return obj

    def _resolve_output_schema(
        self, params: StructuredExtractionParams
    ) -> Dict[str, Any]:
        """
        Resolve the output schema from params, with fallback to field-based generation.
        """
        if params.output_schema:
            if not SchemaBuilder.validate_schema(params.output_schema):
                self.log.warning(
                    "Invalid output_schema provided, falling back to field-based schema"
                )
            else:
                return params.output_schema

        if params.fields:
            return SchemaBuilder.from_fields(
                params.fields,
                item_type="array",
                allow_null=True,
                require_all=False,
            )

        return {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {},
            },
        }

    def _resolve_instructions(self, params: StructuredExtractionParams) -> str:
        """
        Resolve extraction instructions from params.
        """
        return SchemaBuilder.merge_instructions(
            queries=params.queries,
            custom_instructions=params.instructions,
        )
