import asyncio
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence

from pydantic import BaseModel, Field, model_validator

from ....llm import LLMMessage
from ....utils.logx import log_event
from ..exceptions import ToolExecutionError
from .base import BaseAgentTool

if TYPE_CHECKING:
    from llm import LLMProviderManager
    from storage.document_service import LlamaIndexDocumentService


class ExtractionFilters(BaseModel):
    # Extend as needed (mime types, date ranges, tags, etc.)
    mime_types: Optional[List[str]] = None
    date_from: Optional[str] = None  # ISO8601
    date_to: Optional[str] = None  # ISO8601
    sources: Optional[List[str]] = None


class DataExtractionParams(BaseModel):
    """
    Parameters controlling data extraction from one or more documents.
    """

    document_ids: List[str] = Field(..., min_length=1, description="Target documents")
    fields: Optional[List[str]] = Field(
        default=None,
        description="Structured fields to extract. At least one of fields|queries is required.",
        min_length=1,
    )
    queries: Optional[List[str]] = Field(
        default=None,
        description="Free-form information needs. At least one of fields|queries is required.",
        min_length=1,
    )
    filters: Optional[ExtractionFilters] = None

    # Retrieval knobs
    top_k_chunks_per_doc: int = Field(20, ge=1, le=200)
    max_total_chunks: int = Field(200, ge=1, le=2000)
    max_concurrency: int = Field(16, ge=1, le=64, description="Parallel chunk fetches")

    # Budgeting knobs
    max_input_chars: int = Field(250_000, ge=10_000, le=2_000_000)
    require_provenance: bool = Field(True)

    # LLM steering knobs (hints; orchestrator may override)
    model: Optional[str] = Field(default=None, description="Model hint/override")
    temperature: float = Field(0.0, ge=0.0, le=1.0)
    max_tokens: int = Field(800, ge=64, le=8192)

    max_chunks_per_doc: int = Field(
        100,
        ge=1,
        le=2000,
        description="Hard cap for chunks fetched per document.",
    )
    max_chars_per_chunk: int = Field(
        4000,
        ge=256,
        le=16000,
        description="Trim each chunk to this maximum length (characters).",
    )
    max_total_chars: int = Field(
        200_000,
        ge=1024,
        le=2_000_000,
        description="Aggregate character budget across all chunks (after per-chunk trimming).",
    )
    fetch_concurrency: int = Field(
        8,
        ge=1,
        le=64,
        description="Max concurrent chunk fetches from the document service.",
    )

    @model_validator(mode="after")
    def _at_least_one_guidance(self) -> "DataExtractionParams":
        if not (self.fields or self.queries):
            raise ValueError("At least one of `fields` or `queries` must be provided.")
        return self


class ProvenanceItem(BaseModel):
    document_id: str
    chunk_id: str
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    score: Optional[float] = None
    page: Optional[int] = None


class DataExtractionOutput(BaseModel):
    """
    Strict JSON schema expected from the LLM.
    """

    extracted: Dict[str, Any] = Field(
        default_factory=dict,
        description="Map of field/query -> extracted value(s)",
    )
    provenance: List[ProvenanceItem] = Field(
        default_factory=list,
        description="Per-field citations to source chunks",
    )
    partial: bool = Field(
        False, description="True if any retrieval failed or truncated"
    )
    diagnostics: Dict[str, Any] = Field(
        default_factory=dict, description="Latency, counts, model, budgeting info"
    )


@dataclass(slots=True)
class ExtractionMetrics:
    documents_seen: int = 0
    chunks_used: int = 0
    chars_used: int = 0


class DataExtractionTool(BaseAgentTool):
    """
    Extracts structured data from documents using an LLM.

    Contract:
      - requires_llm = True
      - input_model = DataExtractionParams
      - The spawner passes PromptBuilder's `prompt` and a `context` dict.
      - Returns a dict: {extractions, meta, hints}.
    """

    name = "data_extraction"
    description = (
        "Extracts structured information from specified documents. "
        "Performs targeted retrieval (by fields/queries), compacts context under a strict budget, "
        "and synthesizes a STRICT JSON result with per-field provenance."
    )
    requires_llm = True
    input_model = DataExtractionParams

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

        p = (
            params
            if isinstance(params, DataExtractionParams)
            else DataExtractionParams.model_validate(params.model_dump())
        )

        log_event(
            "extraction_tool_execute_started",
            {
                "document_count": len(p.document_ids),
                "fields_count": len(p.fields) if p.fields else 0,
                "queries_count": len(p.queries) if p.queries else 0,
                "max_chunks_per_doc": p.max_chunks_per_doc,
                "max_total_chars": p.max_total_chars,
            },
        )

        metrics = ExtractionMetrics()
        chunks = await self._gather_chunks(
            document_ids=p.document_ids,
            max_chunks=p.max_chunks_per_doc,
            max_chars_per_chunk=p.max_chars_per_chunk,
            max_total_chars=p.max_total_chars,
            fetch_concurrency=p.fetch_concurrency,
            metrics=metrics,
        )

        log_event(
            "extraction_tool_chunks_gathered",
            {
                "documents_seen": metrics.documents_seen,
                "chunks_used": metrics.chunks_used,
                "chars_used": metrics.chars_used,
            },
        )

        request_payload = {
            "instruction": prompt,
            "hints": {
                "fields": p.fields or [],
                "queries": p.queries or [],
            },
            "documents": [{"doc_id": c["doc_id"], "text": c["text"]} for c in chunks],
        }

        messages: List[LLMMessage] = [
            LLMMessage(
                role="system",
                content="You are an information extraction engine. ONLY return valid JSON with extractions—no prose.",
            ),
            LLMMessage(
                role="user",
                content=json.dumps(request_payload, ensure_ascii=False),
                metadata={"payload": request_payload},
            ),
        ]

        model_to_use = p.model or "qwen2.5:7b"

        llm_data = await self._call_llm_generate(
            llm_provider=llm_provider,
            messages=messages,
            model=model_to_use,
            temperature=p.temperature,
            max_tokens=p.max_tokens,
            timeout_s=self.llm_timeout_s,
        )

        result: Dict[str, Any] = {
            "extractions": self._normalize_extractions(llm_data),
            "meta": {
                "documents_seen": metrics.documents_seen,
                "chunks_used": metrics.chunks_used,
                "chars_used": metrics.chars_used,
                "model": p.model,
                "temperature": p.temperature,
                "max_tokens": p.max_tokens,
            },
            "hints": {
                "fields": p.fields or [],
                "queries": p.queries or [],
            },
        }

        log_event(
            "extraction_tool_execute_success",
            {
                "documents_seen": metrics.documents_seen,
                "chunks_used": metrics.chunks_used,
                "chars_used": metrics.chars_used,
                "extraction_keys": (
                    list(result["extractions"].keys())
                    if isinstance(result["extractions"], dict)
                    else []
                ),
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
        kwargs = {"timeout_s": timeout_s}
        try:
            result = await llm_provider.generate(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
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
            raise ToolExecutionError(f"{self.name}: LLM call failed: {error_msg}")

        response = result.unwrap() if hasattr(result, "unwrap") else result

        # Return something consumable by _normalize_extractions
        # Try common shapes: text/content, message dict, etc.
        if isinstance(response, dict):
            return response

        # LLMResponse-like object normalization
        for attr in ("json", "parsed", "data"):
            if hasattr(response, attr):
                val = getattr(response, attr)
                if callable(val):
                    try:
                        return val()
                    except Exception:
                        pass
                else:
                    return val

        for attr in ("text", "content"):
            if hasattr(response, attr):
                return getattr(response, attr)

        # Fallback to str()
        return str(response)

    def _normalize_extractions(self, llm_output: Any) -> Any:
        """
        Normalize LLM output to predictable structure.
        """
        if isinstance(llm_output, (dict, list)):
            return llm_output
        if isinstance(llm_output, str):
            # Try to decode JSON; otherwise wrap as text
            try:
                import json  # local import on slow path

                return json.loads(llm_output)
            except Exception:
                return {"text": llm_output}
        return {"value": llm_output}
