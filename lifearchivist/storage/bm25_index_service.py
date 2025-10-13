"""
BM25 keyword search index service.

Provides production-grade BM25 ranking for keyword search with:
- Redis-backed persistence
- Incremental index updates
- Efficient tokenization
- Configurable parameters

Follows the same Redis patterns as RedisDocumentTracker for consistency.
"""

import logging
import pickle
import re
from typing import Any, Dict, List, Optional, Tuple

import redis.asyncio as redis
from rank_bm25 import BM25Okapi

from lifearchivist.utils.logging import log_event, track


class BM25Tokenizer:
    """
    Simple but effective tokenizer for BM25.

    Features:
    - Lowercase normalization
    - Punctuation removal
    - Stop word filtering
    - Optional stemming
    """

    # Common English stop words
    STOP_WORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "he",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "that",
        "the",
        "to",
        "was",
        "will",
        "with",
        "this",
        "but",
        "they",
        "have",
        "had",
        "were",
        "been",
        "being",
        "or",
        "not",
        "can",
        "could",
        "would",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "do",
        "does",
        "did",
    }

    def __init__(self, use_stemming: bool = False, remove_stop_words: bool = True):
        """
        Initialize tokenizer.

        Args:
            use_stemming: Whether to use Porter stemming (requires nltk)
            remove_stop_words: Whether to remove stop words
        """
        self.use_stemming = use_stemming
        self.remove_stop_words = remove_stop_words
        self.stemmer = None

        if use_stemming:
            try:
                from nltk.stem import PorterStemmer

                self.stemmer = PorterStemmer()
                log_event("bm25_stemming_enabled", {"stemmer": "PorterStemmer"})
            except ImportError:
                log_event(
                    "bm25_stemming_unavailable",
                    {"reason": "nltk not installed, install with: pip install nltk"},
                    level=logging.WARNING,
                )
                self.use_stemming = False

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25 indexing.

        Args:
            text: Input text to tokenize

        Returns:
            List of tokens
        """
        if not text:
            return []

        # Lowercase
        text = text.lower()

        # Remove punctuation and split on word boundaries
        # This regex keeps alphanumeric characters and underscores
        tokens = re.findall(r"\b\w+\b", text)

        # Remove stop words
        if self.remove_stop_words:
            tokens = [t for t in tokens if t not in self.STOP_WORDS]

        # Apply stemming
        if self.stemmer:
            tokens = [self.stemmer.stem(t) for t in tokens]

        # Filter out very short tokens (single characters)
        tokens = [t for t in tokens if len(t) > 1]

        return tokens


class BM25IndexService:
    """
    BM25 index service with Redis persistence.

    This service maintains a BM25 index for keyword search with:
    - Automatic persistence to Redis
    - Incremental updates
    - Efficient serialization
    - Document deletion support

    Follows the same patterns as RedisDocumentTracker for consistency.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        use_stemming: bool = False,
        remove_stop_words: bool = True,
    ):
        """
        Initialize BM25 index service.

        Args:
            redis_url: Redis connection URL
            use_stemming: Whether to use Porter stemming
            remove_stop_words: Whether to remove stop words
        """
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.tokenizer = BM25Tokenizer(use_stemming, remove_stop_words)

        # In-memory index (loaded from Redis on startup)
        self.bm25: Optional[BM25Okapi] = None
        self.document_ids: List[str] = []
        self.corpus: List[List[str]] = []

        # Redis keys following project namespace convention
        self.key_prefix = "lifearchivist:bm25"
        self.corpus_key = f"{self.key_prefix}:corpus"
        self.doc_ids_key = f"{self.key_prefix}:doc_ids"
        self.count_key = f"{self.key_prefix}:count"

        # Connection state
        self._initialized = False

    @track(
        operation="bm25_initialize",
        track_performance=True,
        frequency="low_frequency",
    )
    async def initialize(self) -> None:
        """
        Initialize Redis connection and load existing index.

        This method:
        1. Creates async Redis client with connection pooling
        2. Tests connection with PING
        3. Loads existing index from Redis
        4. Logs initialization metrics

        Raises:
            ConnectionError: If Redis is unreachable
        """
        try:
            # Use decode_responses=False for binary data (pickle)
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,  # We handle binary pickle data
                socket_keepalive=True,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )

            await self.redis_client.ping()

            # Load existing index from Redis
            await self._load_index()

            self._initialized = True

            log_event(
                "bm25_initialized",
                {
                    "redis_url": self.redis_url,
                    "documents_indexed": len(self.document_ids),
                    "use_stemming": self.tokenizer.use_stemming,
                    "remove_stop_words": self.tokenizer.remove_stop_words,
                },
            )

        except Exception as e:
            log_event(
                "bm25_init_failed",
                {
                    "redis_url": self.redis_url,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
            raise ConnectionError(f"Failed to connect to Redis: {str(e)}") from e

    async def close(self) -> None:
        """
        Close Redis connection and cleanup resources.

        This method:
        1. Closes the Redis client connection
        2. Releases connection pool resources
        3. Logs cleanup metrics
        """
        if self.redis_client:
            await self.redis_client.aclose()
            self._initialized = False

            log_event("bm25_closed", {"redis_url": self.redis_url})

    @track(
        operation="bm25_add_document",
        include_args=["document_id"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def add_document(self, document_id: str, text: str) -> None:
        """
        Add a document to the BM25 index.

        This method:
        1. Tokenizes document text
        2. Adds to in-memory corpus
        3. Rebuilds BM25 index (fast for incremental adds)
        4. Persists to Redis atomically

        Args:
            document_id: Unique document identifier
            text: Document text content

        Raises:
            RuntimeError: If service not initialized
        """
        if not self._initialized:
            raise RuntimeError("BM25IndexService not initialized")

        if not document_id:
            raise ValueError("document_id is required")

        # Tokenize document
        tokens = self.tokenizer.tokenize(text)

        if not tokens:
            log_event(
                "bm25_empty_document",
                {
                    "document_id": document_id,
                    "text_length": len(text) if text else 0,
                },
                level=logging.WARNING,
            )
            # Still add with empty tokens to maintain document_id alignment
            tokens = []

        # Add to corpus
        self.corpus.append(tokens)
        self.document_ids.append(document_id)

        # Rebuild BM25 index (fast for incremental adds)
        if self.corpus:
            self.bm25 = BM25Okapi(self.corpus)

        # Persist to Redis atomically
        await self._save_index()

        log_event(
            "bm25_document_added",
            {
                "document_id": document_id,
                "token_count": len(tokens),
                "total_documents": len(self.document_ids),
            },
        )

    @track(
        operation="bm25_remove_document",
        include_args=["document_id"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def remove_document(self, document_id: str) -> bool:
        """
        Remove a document from the BM25 index.

        This method:
        1. Finds document in corpus
        2. Removes from corpus and document_ids
        3. Rebuilds BM25 index
        4. Persists to Redis atomically

        Args:
            document_id: Document to remove

        Returns:
            True if document was removed, False if not found

        Raises:
            RuntimeError: If service not initialized
        """
        if not self._initialized:
            raise RuntimeError("BM25IndexService not initialized")

        try:
            # Find document index
            idx = self.document_ids.index(document_id)

            # Remove from corpus and doc_ids
            del self.corpus[idx]
            del self.document_ids[idx]

            # Rebuild BM25 index
            if self.corpus:
                self.bm25 = BM25Okapi(self.corpus)
            else:
                self.bm25 = None

            # Persist to Redis atomically
            await self._save_index()

            log_event(
                "bm25_document_removed",
                {
                    "document_id": document_id,
                    "remaining_documents": len(self.document_ids),
                },
            )

            return True

        except ValueError:
            log_event(
                "bm25_document_not_found",
                {"document_id": document_id},
                level=logging.WARNING,
            )
            return False

    @track(
        operation="bm25_search",
        include_args=["top_k", "min_score"],
        track_performance=True,
        frequency="high_frequency",
    )
    async def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> List[Tuple[str, float]]:
        """
        Search documents using BM25 ranking.

        Args:
            query: Search query
            top_k: Number of results to return
            min_score: Minimum BM25 score threshold

        Returns:
            List of (document_id, score) tuples, sorted by score descending

        Raises:
            RuntimeError: If service not initialized
        """
        if not self._initialized:
            raise RuntimeError("BM25IndexService not initialized")

        if not self.bm25 or not self.document_ids:
            log_event(
                "bm25_search_empty_index",
                {"query": query[:50]},
                level=logging.DEBUG,
            )
            return []

        # Tokenize query
        query_tokens = self.tokenizer.tokenize(query)

        if not query_tokens:
            log_event(
                "bm25_empty_query",
                {"query": query},
                level=logging.WARNING,
            )
            return []

        # Get BM25 scores for all documents
        scores = self.bm25.get_scores(query_tokens)

        # Create (doc_id, score) pairs for documents above threshold
        results = [
            (self.document_ids[i], float(scores[i]))
            for i in range(len(scores))
            if scores[i] >= min_score
        ]

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        # Return top-k
        top_results = results[:top_k]

        log_event(
            "bm25_search_completed",
            {
                "query_preview": query[:50],
                "query_tokens": len(query_tokens),
                "results_found": len(results),
                "results_returned": len(top_results),
                "top_score": top_results[0][1] if top_results else 0,
            },
        )

        return top_results

    async def get_document_count(self) -> int:
        """
        Get number of documents in index.

        Returns:
            Number of indexed documents
        """
        return len(self.document_ids)

    async def document_exists(self, document_id: str) -> bool:
        """
        Check if a document exists in the index.

        Args:
            document_id: Document to check

        Returns:
            True if document exists in index
        """
        return document_id in self.document_ids

    @track(
        operation="bm25_clear_index",
        track_performance=True,
        frequency="low_frequency",
    )
    async def clear_index(self) -> Dict[str, Any]:
        """
        Clear the entire BM25 index.

        This method:
        1. Gets statistics before clearing
        2. Clears in-memory structures
        3. Deletes all keys from Redis
        4. Returns clearing statistics

        Returns:
            Statistics about what was cleared

        Raises:
            RuntimeError: If service not initialized
        """
        if not self._initialized:
            raise RuntimeError("BM25IndexService not initialized")

        doc_count = len(self.document_ids)

        # Clear in-memory structures
        self.corpus = []
        self.document_ids = []
        self.bm25 = None

        # Clear from Redis
        await self.redis_client.delete(
            self.corpus_key,
            self.doc_ids_key,
            self.count_key,
        )

        log_event("bm25_index_cleared", {"documents_cleared": doc_count})

        return {
            "documents_cleared": doc_count,
            "corpus_cleared": True,
        }

    async def _save_index(self) -> None:
        """
        Save index to Redis atomically.

        Uses Redis pipeline with transaction for atomic multi-key updates.
        Serializes corpus and doc_ids using pickle for efficiency.
        """
        try:
            # Serialize corpus and doc_ids using pickle
            corpus_bytes = pickle.dumps(self.corpus)
            doc_ids_bytes = pickle.dumps(self.document_ids)

            # Save to Redis in atomic transaction
            async with self.redis_client.pipeline(transaction=True) as pipe:
                pipe.set(self.corpus_key, corpus_bytes)
                pipe.set(self.doc_ids_key, doc_ids_bytes)
                pipe.set(self.count_key, len(self.document_ids))
                await pipe.execute()

            log_event(
                "bm25_index_saved",
                {
                    "documents": len(self.document_ids),
                    "corpus_size_kb": round(len(corpus_bytes) / 1024, 2),
                    "doc_ids_size_kb": round(len(doc_ids_bytes) / 1024, 2),
                },
                level=logging.DEBUG,
            )

        except Exception as e:
            log_event(
                "bm25_save_failed",
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
            # Don't raise - index is still in memory and functional

    async def _load_index(self) -> None:
        """
        Load index from Redis.

        Deserializes corpus and doc_ids from Redis and rebuilds BM25 index.
        If no index exists in Redis, starts with empty index.
        """
        try:
            # Load corpus and doc_ids from Redis
            corpus_bytes = await self.redis_client.get(self.corpus_key)
            doc_ids_bytes = await self.redis_client.get(self.doc_ids_key)

            if corpus_bytes and doc_ids_bytes:
                # Deserialize
                self.corpus = pickle.loads(corpus_bytes)
                self.document_ids = pickle.loads(doc_ids_bytes)

                # Rebuild BM25 index from corpus
                if self.corpus:
                    self.bm25 = BM25Okapi(self.corpus)

                log_event(
                    "bm25_index_loaded",
                    {
                        "documents": len(self.document_ids),
                        "corpus_size_kb": round(len(corpus_bytes) / 1024, 2),
                    },
                )
            else:
                log_event(
                    "bm25_no_existing_index",
                    {"message": "Starting with empty index"},
                    level=logging.INFO,
                )

        except Exception as e:
            log_event(
                "bm25_load_failed",
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.WARNING,
            )
            # Start with empty index on load failure
            self.corpus = []
            self.document_ids = []
            self.bm25 = None
