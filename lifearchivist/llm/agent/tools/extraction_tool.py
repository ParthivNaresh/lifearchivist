import asyncio
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence

from pydantic import BaseModel, Field

from ....llm import LLMMessage
from ..exceptions import ToolExecutionError
from .base import BaseAgentTool

if TYPE_CHECKING:
    from llm import LLMProviderManager
    from storage.document_service import LlamaIndexDocumentService


class DataExtractionParams(BaseModel):
    """
    Parameters controlling data extraction from one or more documents.
    """

    document_ids: List[str] = Field(
        ..., min_length=1, description="List of source document IDs to extract from."
    )
    fields: Optional[List[str]] = Field(
        default=None,
        min_length=1,
        description="Optional list of target field names (acts as hints to the LLM).",
    )
    queries: Optional[List[str]] = Field(
        default=None,
        min_length=1,
        description="Optional list of natural language queries guiding extraction.",
    )

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

    # LLM steering knobs
    model: str = Field(
        default="llama3.2:1b", description="Optional LLM model hint/override."
    )
    temperature: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Sampling temperature (0.0 = deterministic).",
    )
    max_tokens: int = Field(
        1500,
        ge=128,
        le=4096,
        description="Maximum tokens requested from the LLM.",
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

    name: str = "data_extraction"
    requires_llm: bool = True
    input_model = DataExtractionParams
    summary: str = (
        "Extract structured data from specified documents. "
        "Supports field/query hints, bounded chunk retrieval, and strict size budgets."
    )

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

        # Coerce/validate parameters to expected schema
        p = (
            params
            if isinstance(params, DataExtractionParams)
            else DataExtractionParams.model_validate(params.model_dump())
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

        # Build compact payload for the LLM
        request_payload = {
            "instruction": prompt,  # already composed by PromptBuilder
            "hints": {
                "fields": p.fields or [],
                "queries": p.queries or [],
            },
            "documents": [{"doc_id": c["doc_id"], "text": c["text"]} for c in chunks],
        }

        # Compose messages for your manager.generate(...) API
        # We send a strict system directive + a user message carrying the payload.
        messages: List[LLMMessage] = [
            LLMMessage(
                role="system",
                content="You are an information extraction engine. ONLY return valid JSON with extractions—no prose.",
            ),
            LLMMessage(
                role="user",
                content=json.dumps(request_payload, ensure_ascii=False),
                metadata={
                    "payload": request_payload
                },  # optional: keep the structured form
            ),
        ]

        llm_data = await self._call_llm_generate(
            llm_provider=llm_provider,
            messages=messages,
            model=p.model,
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
            error_msg = result.error_or("LLM call failed")
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
