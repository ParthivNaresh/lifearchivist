"""
Utility functions for search endpoints.
"""

from typing import Any, Dict, List, Optional

from lifearchivist.llm import LLMMessage

from .constants import DEFAULT_SEMANTIC_WEIGHT, DEFAULT_SIMILARITY_THRESHOLD
from .misc_models import Citation


def build_search_filters(
    mime_type: Optional[str],
    status: Optional[str],
    tags: Optional[str],
) -> Dict[str, Any]:
    """Build metadata filters from query parameters."""
    filters: Dict[str, Any] = {}

    if mime_type:
        filters["mime_type"] = mime_type
    if status:
        filters["status"] = status
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        if tag_list:
            filters["tags"] = tag_list

    return filters


async def execute_search(
    search_service,
    mode: str,
    query: str,
    limit: int,
    filters: Dict[str, Any],
):
    """
    Execute search based on mode.

    Returns Result from the appropriate search method.
    """
    if mode == "semantic":
        return await search_service.semantic_search(
            query=query,
            top_k=limit,
            similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD,
            filters=filters,
        )
    elif mode == "keyword":
        return await search_service.keyword_search(
            query=query,
            top_k=limit,
            filters=filters,
        )
    else:
        return await search_service.hybrid_search(
            query=query,
            top_k=limit,
            semantic_weight=DEFAULT_SEMANTIC_WEIGHT,
            filters=filters,
        )


def build_context_from_sources(
    sources: List[Dict[str, Any]], context_limit: int
) -> str:
    """Build context string from search sources."""
    return "\n\n".join(
        f"[Source {i+1}]\n{source.get('text', '')}"
        for i, source in enumerate(sources[:context_limit])
    )


def create_rag_messages(context: str, question: str) -> List[LLMMessage]:
    """Create messages for RAG LLM generation."""
    system_prompt = f"""You are a helpful AI assistant. Use the following context from the user's documents to answer their question. If the context doesn't contain relevant information, say so clearly.

Context:
{context}"""

    return [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=question),
    ]


def create_citations_from_sources(sources: List[Dict[str, Any]]) -> List[Citation]:
    """Create citation objects from search sources."""
    citations = []
    for source in sources:
        snippet = source.get("text", "")[:200] if source.get("text") else ""
        citations.append(
            Citation(
                doc_id=source.get("document_id", ""),
                title=source.get("metadata", {}).get("title", "Unknown Document"),
                snippet=snippet,
                score=source.get("score", 0.0),
            )
        )
    return citations


def calculate_average_score(sources: List[Dict[str, Any]]) -> float:
    """Calculate average score from sources."""
    if not sources:
        return 0.0

    score: float = sum(s.get("score", 0) for s in sources) / len(sources)

    return score
