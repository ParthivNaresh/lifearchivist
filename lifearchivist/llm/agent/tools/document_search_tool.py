import json
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from ...llm_io import _unwrap_result_or_raise, _parse_json_maybe, _response_text
from ....utils.result import Result
from ... import LLMMessage, LLMResponse
from ....utils.logx import log_event
from ..exceptions import ToolExecutionError
from .base import BaseAgentTool

if TYPE_CHECKING:
    from storage.metadata_service import MetadataService
    from storage.search_service import SearchService


class SearchMethod(str, Enum):
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    METADATA = "metadata"


class DateFilter(BaseModel):
    after: Optional[str] = Field(None, description="ISO8601 date string (YYYY-MM-DD)")
    before: Optional[str] = Field(None, description="ISO8601 date string (YYYY-MM-DD)")


class DocumentSearchParams(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language search query or keywords",
    )

    search_method: SearchMethod = Field(
        SearchMethod.HYBRID,
        description="Search method: semantic (vector), keyword (BM25), hybrid (both), or metadata (filters only)",
    )

    top_k: int = Field(
        10,
        ge=1,
        le=100,
        description="Maximum number of documents to return",
    )

    similarity_threshold: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for semantic/hybrid search (0-1)",
    )

    semantic_weight: float = Field(
        0.6,
        ge=0.0,
        le=1.0,
        description="Weight for semantic search in hybrid mode (0-1, higher = more semantic)",
    )

    mime_types: Optional[List[str]] = Field(
        None,
        description="Filter by document types (e.g., ['application/pdf', 'text/plain'])",
    )

    themes: Optional[List[str]] = Field(
        None,
        description="Filter by document themes/categories",
    )

    date_filter: Optional[DateFilter] = Field(
        None,
        description="Filter by upload date range",
    )

    status: Optional[str] = Field(
        None,
        description="Filter by document status (e.g., 'indexed', 'processing')",
    )

    include_metadata: bool = Field(
        True,
        description="Include full document metadata in results",
    )

    include_text_preview: bool = Field(
        True,
        description="Include text preview/snippet in results",
    )

    allow_query_expansion: bool = True
    allow_filter_synthesis: bool = True
    allow_rerank: bool = True
    rerank_top_k: int = 50
    instructions: Optional[str] = None
    model: Optional[str] = None

    @model_validator(mode="after")
    def _validate_search_params(self) -> "DocumentSearchParams":
        if self.search_method == SearchMethod.METADATA and not any(
            [
                self.mime_types,
                self.themes,
                self.date_filter,
                self.status,
            ]
        ):
            raise ValueError(
                "Metadata search requires at least one filter (mime_types, themes, date_filter, or status)"
            )
        return self


@dataclass(slots=True)
class SearchMetrics:
    documents_found: int = 0
    search_method_used: str = ""
    avg_score: float = 0.0
    filters_applied: int = 0


class DocumentSearchTool(BaseAgentTool):
    """
    Searches for documents using semantic, keyword, hybrid, or metadata-based search.

    This tool integrates with the storage layer's search services to find relevant
    documents based on natural language queries, keywords, or structured filters.
    Returns document IDs and metadata that can be used by downstream tools.

    Contract:
      - requires_llm = False (pure search, no LLM needed)
      - input_model = DocumentSearchParams
      - Returns: {documents: List[Dict], metrics: Dict}
    """

    name = "document_search"
    description = (
        "Searches for documents using natural language queries, keywords, or metadata filters. "
        "Supports semantic (meaning-based), keyword (exact match), hybrid (combined), "
        "and metadata (structured filter) search methods. "
        "Returns document IDs, scores, and metadata for use in downstream tasks."
    )
    requires_llm = True
    input_model = DocumentSearchParams

    def __init__(
        self,
        *,
        search_service: Optional["SearchService"] = None,
        metadata_service: Optional["MetadataService"] = None,
    ) -> None:
        self.search_service = search_service
        self.metadata_service = metadata_service

    async def execute_typed(
        self, *, params: BaseModel, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute document search with validated parameters.

        Returns:
            Dictionary with:
              - documents: List of document results with IDs, scores, metadata
              - metrics: Search performance metrics
              - query_info: Information about the search query
        """
        self._assert_ready_llm_friendly(method=params.search_method)

        p = (
            params
            if isinstance(params, DocumentSearchParams)
            else DocumentSearchParams.model_validate(params.model_dump())
        )

        metrics = SearchMetrics()

        try:
            if p.search_method == SearchMethod.METADATA:
                documents = await self._metadata_search(p, metrics)
            elif p.search_method == SearchMethod.SEMANTIC:
                documents = await self._semantic_search(p, metrics)
            elif p.search_method == SearchMethod.KEYWORD:
                documents = await self._keyword_search(p, metrics)
            else:
                documents = await self._hybrid_search(p, metrics)

            processed_documents = self._process_results(documents, p)

            out = {
                "documents": processed_documents,
                "metrics": {
                    "total_found": metrics.documents_found,
                    "returned": len(processed_documents),
                    "search_method": metrics.search_method_used,
                    "avg_score": metrics.avg_score,
                    "filters_applied": metrics.filters_applied,
                },
                "query_info": {
                    "query": p.query,
                    "method": p.search_method.value,
                    "top_k": p.top_k,
                },
            }

            try:
                ids_preview = [d.get("document_id") for d in processed_documents[:10]]
                log_event(
                    "document_search_result_preview",
                    {
                        "returned": len(processed_documents),
                        "ids_preview": ids_preview,
                        "search_method": metrics.search_method_used,
                        "avg_score": metrics.avg_score,
                    },
                )
            except Exception:
                pass

            return out

        except Exception as e:
            log_event(
                "document_search_failed",
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "search_method": p.search_method.value,
                },
                level=40,
            )
            raise ToolExecutionError(f"Document search failed: {str(e)}") from e

    async def execute_with_llm(self, *, llm_provider, prompt: str, params: BaseModel, context: Dict[str, Any]) -> Any:
        self._assert_ready_llm_friendly(params.search_method)
        p = DocumentSearchParams.model_validate(params.model_dump())

        # 1) Call LLM to propose a strategy
        strategy_request = {
            "task_description": context.get("task_description"),
            "original_query": p.query,
            "instructions": p.instructions,
            "allow_query_expansion": p.allow_query_expansion,
            "allow_filter_synthesis": p.allow_filter_synthesis,
            "defaults": {
                "search_method": p.search_method.value,
                "top_k": p.top_k,
                "semantic_weight": getattr(p, "semantic_weight", 0.6),
                "similarity_threshold": getattr(p, "similarity_threshold", 0.5),
                "rerank_top_k": p.rerank_top_k,
            },
            "user_filters_present": bool(p.mime_types or p.themes or p.date_filter or p.status),
        }

        system = LLMMessage(
            role="system",
            content=(
                "You are a retrieval strategist. "
                "Return ONLY compact JSON with keys: "
                "method ('semantic'|'keyword'|'hybrid'|'metadata'), "
                "query, filters (optional), top_k, semantic_weight, similarity_threshold, rerank_top_k."
            ),
        )
        user = LLMMessage(
            role="user",
            content=json.dumps(strategy_request, ensure_ascii=False),
            metadata={"payload": strategy_request},
        )
        model = p.model or "qwen2.5:7b"

        try:
            result: Result[LLMResponse, str] = await llm_provider.generate(
                messages=[system, user],
                model=model,
                temperature=0.0,
                max_tokens=300,
            )
        except Exception as e:
            raise ToolExecutionError(f"{self.name}: LLM generate raised {type(e).__name__}: {e}") from e

        try:
            resp = _unwrap_result_or_raise(result)
            raw = _response_text(resp)
            strategy = _parse_json_maybe(raw) or {}
        except Exception as e:
            log_event("docsearch_llm_strategy_parse_failed", {"error": str(e), "preview": raw[:400] if isinstance(raw, str) else None}, level=30)
            strategy = {}

        # 2) Merge strategy into params (fallback to typed defaults)
        method = strategy.get("method", p.search_method.value)
        p2 = p.model_copy(update={
            "search_method": SearchMethod(method),
            "query": strategy.get("query", p.query),
            "top_k": int(strategy.get("top_k", p.top_k)),
            "semantic_weight": float(strategy.get("semantic_weight", getattr(p, "semantic_weight", 0.6))),
            "similarity_threshold": float(strategy.get("similarity_threshold", getattr(p, "similarity_threshold", 0.5))),
        })

        # 3) Run the existing typed path (this keeps one code path for the actual search)
        self._assert_ready_llm_friendly(p2.search_method)
        raw_results = await self.execute_typed(params=p2, context=context)

        if p.allow_rerank and strategy.get("rerank_top_k", p.rerank_top_k) > 0 and raw_results.get("documents"):
            k = int(strategy.get("rerank_top_k", p.rerank_top_k))
            candidates = raw_results["documents"][:k]
            shallow = [
                {
                    "document_id": d["document_id"],
                    "title": d.get("title"),
                    "score": d.get("final_score") or d.get("semantic_score") or d.get("keyword_score"),
                    "preview": (d.get("text_preview") or "")[:320],
                    "metadata": {key: d.get(key) for key in ("mime_type", "theme", "status", "uploaded_at") if key in d},
                }
                for d in candidates
            ]
            rerank_sys = LLMMessage(role="system", content="Re-rank the documents for the given task. Return ONLY a JSON list of document_id in best-first order.")
            rerank_user = LLMMessage(role="user", content=json.dumps({
                "task": context.get("task_description"),
                "query": p2.query,
                "docs": shallow,
            }, ensure_ascii=False))
            try:
                r2 = await llm_provider.generate(messages=[rerank_sys, rerank_user], model=model, temperature=0.0, max_tokens=400)
                r2_resp = _unwrap_result_or_raise(r2)
                r2_text = _response_text(r2_resp)
                order_ids = _parse_json_maybe(r2_text) or []
                id2doc = {d["document_id"]: d for d in candidates}
                seen = set()
                reranked = []
                for _id in order_ids:
                    if _id in id2doc and _id not in seen:
                        reranked.append(id2doc[_id]); seen.add(_id)
                for d in candidates:
                    if d["document_id"] not in seen:
                        reranked.append(d)
                raw_results["documents"] = reranked + raw_results["documents"][len(candidates):]
                raw_results.setdefault("metrics", {})["post_reranked"] = True
            except Exception as e:
                log_event("docsearch_llm_rerank_failed", {"error": str(e)}, level=30)

        # 5) Trace what happened
        raw_results.setdefault("metrics", {})["strategy"] = {
            "model": model,
            "method": p2.search_method.value,
            "semantic_weight": getattr(p2, "semantic_weight", None),
            "similarity_threshold": getattr(p2, "similarity_threshold", None),
        }
        # Optional: keep a tiny preview of the strategy raw text for observability
        if isinstance(locals().get("raw"), str):
            raw_results["metrics"]["llm_strategy_preview"] = raw[:160]

        return raw_results

    async def _semantic_search(
        self, params: DocumentSearchParams, metrics: SearchMetrics
    ) -> List[Dict[str, Any]]:
        """Execute semantic (vector) search."""
        filters = self._build_metadata_filters(params)
        metrics.filters_applied = len(filters)
        metrics.search_method_used = "semantic"

        result = await self.search_service.semantic_search(
            query=params.query,
            top_k=params.top_k,
            similarity_threshold=params.similarity_threshold,
            filters=filters if filters else None,
        )

        if result.is_failure():
            raise ToolExecutionError(f"Semantic search failed: {result.error}")

        documents = result.unwrap()
        metrics.documents_found = len(documents)
        metrics.avg_score = self._calculate_avg_score(documents)

        return documents

    async def _keyword_search(
        self, params: DocumentSearchParams, metrics: SearchMetrics
    ) -> List[Dict[str, Any]]:
        """Execute keyword (BM25) search."""
        filters = self._build_metadata_filters(params)
        metrics.filters_applied = len(filters)
        metrics.search_method_used = "keyword"

        result = await self.search_service.keyword_search(
            query=params.query,
            top_k=params.top_k,
            filters=filters if filters else None,
        )

        if result.is_failure():
            raise ToolExecutionError(f"Keyword search failed: {result.error}")

        documents = result.unwrap()
        metrics.documents_found = len(documents)
        metrics.avg_score = self._calculate_avg_score(documents)

        return documents

    async def _hybrid_search(
        self, params: DocumentSearchParams, metrics: SearchMetrics
    ) -> List[Dict[str, Any]]:
        """Execute hybrid (semantic + keyword) search."""
        filters = self._build_metadata_filters(params)
        metrics.filters_applied = len(filters)
        metrics.search_method_used = "hybrid"

        result = await self.search_service.hybrid_search(
            query=params.query,
            top_k=params.top_k,
            semantic_weight=params.semantic_weight,
            filters=filters if filters else None,
        )

        if result.is_failure():
            raise ToolExecutionError(f"Hybrid search failed: {result.error}")

        documents = result.unwrap()
        metrics.documents_found = len(documents)
        metrics.avg_score = self._calculate_avg_score(documents)

        return documents

    async def _metadata_search(
        self, params: DocumentSearchParams, metrics: SearchMetrics
    ) -> List[Dict[str, Any]]:
        """Execute metadata-only search (no text query)."""
        filters = self._build_metadata_filters(params)
        metrics.filters_applied = len(filters)
        metrics.search_method_used = "metadata"

        if not filters:
            raise ToolExecutionError("Metadata search requires at least one filter")

        result = await self.metadata_service.query_documents_by_metadata(
            filters=filters,
            limit=params.top_k,
            offset=0,
        )

        if result.is_failure():
            raise ToolExecutionError(f"Metadata search failed: {result.error}")

        raw_documents = result.unwrap()

        documents = [
            {
                "document_id": doc.get("document_id"),
                "score": 1.0,
                "metadata": doc.get("metadata", {}),
                "text": doc.get("text_preview", ""),
                "search_type": "metadata",
            }
            for doc in raw_documents
        ]

        metrics.documents_found = len(documents)
        metrics.avg_score = 1.0

        return documents

    def _build_metadata_filters(self, params: DocumentSearchParams) -> Dict[str, Any]:
        """Build metadata filter dictionary from search parameters."""
        filters: Dict[str, Any] = {}

        if params.mime_types:
            filters["mime_type"] = params.mime_types

        if params.themes:
            filters["theme"] = params.themes

        if params.status:
            filters["status"] = params.status

        if params.date_filter:
            date_range = {}
            if params.date_filter.after:
                date_range["after"] = params.date_filter.after
            if params.date_filter.before:
                date_range["before"] = params.date_filter.before
            if date_range:
                filters["uploaded_at"] = date_range

        return filters

    def _process_results(
        self, documents: List[Dict[str, Any]], params: DocumentSearchParams
    ) -> List[Dict[str, Any]]:
        """Process and format search results based on parameters."""
        processed = []
        for doc in documents:
            result: Dict[str, Any] = {
                "document_id": doc.get("document_id"),
                "score": float(doc.get("score", 0.0)),
                "search_type": doc.get("search_type", "unknown"),
            }

            if params.include_metadata:
                result["metadata"] = doc.get("metadata", {})

            if params.include_text_preview:
                raw_text = doc.get("text") or doc.get("text_preview") or doc.get("snippet") or ""
                result["text_preview"] = raw_text[:500]

            if "semantic_score" in doc:
                result["semantic_score"] = doc["semantic_score"]
            if "keyword_score" in doc:
                result["keyword_score"] = doc["keyword_score"]
            if "final_score" in doc:
                result["final_score"] = float(doc["final_score"])

            processed.append(result)
        return processed

    def _calculate_avg_score(self, documents: List[Dict[str, Any]]) -> float:
        """Calculate average score from search results."""
        if not documents:
            return 0.0

        scores = [doc.get("score", 0.0) for doc in documents]
        return round(sum(scores) / len(scores), 3)

    def _has_filters(self, params: DocumentSearchParams) -> bool:
        """Check if any filters are applied."""
        return bool(
            params.mime_types or params.themes or params.date_filter or params.status
        )

    def _assert_ready_llm_friendly(self, method: Optional[SearchMethod] = None) -> None:
        m = method or SearchMethod.HYBRID
        if m in (SearchMethod.SEMANTIC, SearchMethod.KEYWORD, SearchMethod.HYBRID):
            if self.search_service is None:
                raise ToolExecutionError("search_service is not configured")
        if m is SearchMethod.METADATA:
            if self.metadata_service is None:
                raise ToolExecutionError("metadata_service is not configured")
