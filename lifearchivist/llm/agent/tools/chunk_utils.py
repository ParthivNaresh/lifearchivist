import asyncio
import logging
from typing import Any, Dict, List, Optional, Protocol, Sequence


class ChunkMetrics(Protocol):
    documents_seen: int
    chunks_used: int
    chars_used: int


async def gather_document_chunks(
    *,
    document_service: Any,
    document_ids: Sequence[str],
    max_chunks_per_doc: int,
    max_chars_per_chunk: int,
    max_total_chars: int,
    fetch_concurrency: int,
    metrics: Optional[ChunkMetrics] = None,
    logger: Optional[logging.Logger] = None,
) -> List[Dict[str, str]]:
    sem = asyncio.Semaphore(fetch_concurrency)
    all_chunks: List[Dict[str, str]] = []

    async def _fetch_one(doc_id: str) -> List[Dict[str, str]]:
        async with sem:
            try:
                chunks_result = await document_service.get_document_chunks(
                    doc_id, limit=max_chunks_per_doc
                )
            except Exception as e:
                if logger:
                    logger.warning("Failed to fetch chunks for %s: %s", doc_id, e)
                return []

            if hasattr(chunks_result, "is_failure") and chunks_result.is_failure():
                if logger:
                    logger.warning("Chunk fetch failure for %s", doc_id)
                return []

            data: Any = (
                chunks_result.unwrap()
                if hasattr(chunks_result, "unwrap")
                else chunks_result
            )

            raw_chunks: List[Any]
            if isinstance(data, dict):
                raw_chunks = data.get("chunks", []) or []
            elif isinstance(data, list):
                raw_chunks = data
            else:
                raw_chunks = []

            out: List[Dict[str, str]] = []
            for ch in raw_chunks:
                text = (
                    ch.get("text") if isinstance(ch, dict) else getattr(ch, "text", "")
                ) or ""
                if not text:
                    continue
                if len(text) > max_chars_per_chunk:
                    text = text[:max_chars_per_chunk]
                out.append({"doc_id": doc_id, "text": text})
            return out

    per_doc_lists: List[List[Dict[str, str]]] = await asyncio.gather(
        *[_fetch_one(doc_id) for doc_id in document_ids],
        return_exceptions=False,
    )

    if metrics is not None:
        metrics.documents_seen = len(document_ids)

    running_chars = 0
    for chunk_list in per_doc_lists:
        for ch in chunk_list:
            t = ch["text"]
            if running_chars + len(t) > max_total_chars:
                if metrics is not None:
                    metrics.chunks_used = len(all_chunks)
                    metrics.chars_used = running_chars
                return all_chunks
            all_chunks.append(ch)
            running_chars += len(t)

    if metrics is not None:
        metrics.chunks_used = len(all_chunks)
        metrics.chars_used = running_chars

    return all_chunks
