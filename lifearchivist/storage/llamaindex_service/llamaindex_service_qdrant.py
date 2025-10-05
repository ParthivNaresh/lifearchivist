"""
Qdrant-native LlamaIndex service implementation.

This is a simplified version that works with Qdrant's architecture,
providing 80% of functionality with cleaner separation of concerns.

All public methods return Result types for explicit error handling and
consistent response formats across the API and UI layers.
"""

import logging
from typing import Any, Dict, List, Optional

from llama_index.core import (
    Settings,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from lifearchivist.config import get_settings
from lifearchivist.storage.document_service import LlamaIndexDocumentService
from lifearchivist.storage.metadata_service import LlamaIndexMetadataService
from lifearchivist.storage.query_service import LlamaIndexQueryService
from lifearchivist.storage.redis_document_tracker import RedisDocumentTracker
from lifearchivist.storage.search_service import LlamaIndexSearchService
from lifearchivist.storage.utils import StorageConstants
from lifearchivist.utils.logging import log_event, track
from lifearchivist.utils.result import (
    Result,
    internal_error,
)


class LlamaIndexQdrantService:
    """
    Simplified LlamaIndex service using Qdrant for vector storage.

    Key features:
    - Uses Qdrant for vector storage
    - Redis-based document tracking for production scalability
    - Service-oriented architecture with clean separation of concerns
    - Async initialization for proper resource management
    """

    def __init__(self, database=None, vault=None):
        self.settings = get_settings()
        self.database = database
        self.vault = vault
        self.index: Optional[VectorStoreIndex] = None
        self.query_engine = None

        # Initialize services to None first
        self.search_service = None
        self.metadata_service = None
        self.document_service = None
        self.query_service = None
        self.qdrant_client = None

        # Initialize Redis document tracker for production-grade scalability
        self.doc_tracker = RedisDocumentTracker(redis_url=self.settings.redis_url)

        # Mark that tracker needs async initialization
        # This will be done during setup to ensure proper initialization
        self._tracker_initialized = False

        self.setup()

    def setup(self):
        """Setup functions for LlamaIndex with Qdrant."""
        try:
            self._setup_embeddings_and_llm()
            self._setup_qdrant()
            self._setup_index()
            self._setup_query_engine()
            self._setup_search_service()
            self._setup_metadata_service()
            self._setup_document_service()
            self._setup_query_service()

            # Log final setup status
            log_event(
                "llamaindex_setup_complete",
                {
                    "has_index": self.index is not None,
                    "has_doc_tracker": self.doc_tracker is not None,
                    "has_document_service": self.document_service is not None,
                    "has_metadata_service": self.metadata_service is not None,
                    "has_search_service": self.search_service is not None,
                    "has_query_service": self.query_service is not None,
                    "tracker_initialized": self._tracker_initialized,
                    "tracker_init_deferred": "Will initialize on first async operation",
                },
            )
        except Exception as e:
            log_event(
                "llamaindex_setup_failed",
                {"error": str(e), "error_type": type(e).__name__},
                level=logging.ERROR,
            )
            # Don't raise, let individual operations fail gracefully

    def _setup_search_service(self):
        """Initialize the search service with the index."""
        if self.index:
            self.search_service = LlamaIndexSearchService(self.index)
            log_event(
                "search_service_initialized",
                {"has_index": True},
            )
        else:
            self.search_service = None
            log_event(
                "search_service_not_initialized",
                {"reason": "no_index"},
                level=logging.WARNING,
            )

    def _setup_metadata_service(self):
        """Initialize the metadata service with the index and tracker."""
        if self.index is not None and self.doc_tracker is not None:
            self.metadata_service = LlamaIndexMetadataService(
                index=self.index,
                doc_tracker=self.doc_tracker,
                qdrant_client=self.qdrant_client,
            )
            log_event(
                "metadata_service_initialized",
                {
                    "has_index": True,
                    "has_tracker": True,
                    "has_qdrant_client": self.qdrant_client is not None,
                },
            )
        else:
            self.metadata_service = None
            log_event(
                "metadata_service_not_initialized",
                {
                    "reason": "missing_dependencies",
                    "has_index": self.index is not None,
                    "has_tracker": self.doc_tracker is not None,
                },
                level=logging.WARNING,
            )

    def _setup_document_service(self):
        """Initialize the document service with all dependencies."""
        try:
            # Log current state for debugging
            log_event(
                "document_service_setup_attempt",
                {
                    "has_index": self.index is not None,
                    "has_doc_tracker": self.doc_tracker is not None,
                    "has_metadata_service": self.metadata_service is not None,
                    "has_qdrant_client": hasattr(self, "qdrant_client")
                    and self.qdrant_client is not None,
                    "tracker_needs_init": getattr(self, "_tracker_needs_init", False),
                },
                level=logging.INFO,
            )

            if self.index is not None and self.doc_tracker is not None:
                self.document_service = LlamaIndexDocumentService(
                    index=self.index,
                    doc_tracker=self.doc_tracker,
                    metadata_service=self.metadata_service,
                    qdrant_client=self.qdrant_client,
                    settings=self.settings,
                )
                log_event(
                    "document_service_initialized",
                    {
                        "has_index": True,
                        "has_tracker": True,
                        "has_metadata_service": self.metadata_service is not None,
                        "has_qdrant_client": self.qdrant_client is not None,
                    },
                )
            else:
                self.document_service = None
                log_event(
                    "document_service_not_initialized",
                    {
                        "reason": "missing_dependencies",
                        "index_exists": self.index is not None,
                        "tracker_exists": self.doc_tracker is not None,
                    },
                    level=logging.WARNING,
                )
        except Exception as e:
            self.document_service = None
            log_event(
                "document_service_setup_error",
                {"error": str(e), "error_type": type(e).__name__},
                level=logging.ERROR,
            )

    def _setup_query_service(self):
        """Initialize the query service with all dependencies."""
        if self.index and self.query_engine:
            self.query_service = LlamaIndexQueryService(
                index=self.index,
                query_engine=self.query_engine,
                search_service=self.search_service,
                metadata_service=self.metadata_service,
            )
            log_event(
                "query_service_initialized",
                {
                    "has_index": True,
                    "has_query_engine": True,
                    "has_search_service": self.search_service is not None,
                    "has_metadata_service": self.metadata_service is not None,
                },
            )
        else:
            self.query_service = None
            log_event(
                "query_service_not_initialized",
                {"reason": "missing_dependencies"},
                level=logging.WARNING,
            )

    @track(
        operation="embeddings_llm_setup",
        track_performance=True,
        frequency="low_frequency",
    )
    def _setup_embeddings_and_llm(self):
        """Configure embeddings and LLM settings."""
        import os

        # Check if we're in test mode
        is_test_mode = os.environ.get("PYTEST_CURRENT_TEST") is not None

        log_event(
            "llm_config",
            {
                "embedding_model": (
                    self.settings.embedding_model if not is_test_mode else "mock"
                ),
                "llm_model": self.settings.llm_model if not is_test_mode else "mock",
                "ollama_url": self.settings.ollama_url if not is_test_mode else "mock",
                "test_mode": is_test_mode,
            },
        )

        if is_test_mode:
            from llama_index.core.embeddings import MockEmbedding
            from llama_index.core.llms import MockLLM

            Settings.embed_model = MockEmbedding(embed_dim=384)
            Settings.llm = MockLLM()
        else:
            Settings.embed_model = HuggingFaceEmbedding(
                model_name=self.settings.embedding_model,
                cache_folder=str(self.settings.lifearch_home / "models"),
                max_length=512,
            )

            Settings.llm = Ollama(
                model=self.settings.llm_model,
                base_url=self.settings.ollama_url,
                temperature=0.1,
                request_timeout=300.0,
            )

        Settings.node_parser = SentenceSplitter(
            chunk_size=StorageConstants.DEFAULT_CHUNK_SIZE,
            chunk_overlap=StorageConstants.DEFAULT_CHUNK_OVERLAP,
            separator=StorageConstants.DEFAULT_CHUNK_SEPARATOR,
        )

    @track(
        operation="qdrant_setup",
        track_performance=True,
        frequency="low_frequency",
    )
    def _setup_qdrant(self):
        """Setup Qdrant client and collection."""
        try:
            self.qdrant_client = QdrantClient(
                url=self.settings.qdrant_url,
                check_compatibility=False,  # Suppress version mismatch warnings
            )

            # Check if collection exists, create if not
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]

            if "lifearchivist" not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name="lifearchivist",
                    vectors_config=VectorParams(
                        size=384,  # all-MiniLM-L6-v2 dimension
                        distance=Distance.COSINE,
                    ),
                )
                log_event(
                    "qdrant_collection_created",
                    {"collection": "lifearchivist"},
                )
            else:
                collection_info = self.qdrant_client.get_collection("lifearchivist")
                log_event(
                    "qdrant_collection_exists",
                    {
                        "collection": "lifearchivist",
                        "points_count": collection_info.points_count,
                    },
                )
        except Exception as e:
            log_event(
                "qdrant_setup_failed",
                {"error": str(e)},
                level=logging.ERROR,
            )
            raise

    @track(
        operation="index_setup",
        track_performance=True,
        frequency="low_frequency",
    )
    def _setup_index(self):
        """
        Setup the vector store index with Qdrant.

        Note: We only use Qdrant for storage. LlamaIndex internally creates
        docstore/index_store but we don't rely on them for any operations.
        All text retrieval is done directly from Qdrant.
        """
        try:
            # Create Qdrant vector store
            vector_store = QdrantVectorStore(
                client=self.qdrant_client,
                collection_name="lifearchivist",
            )

            # Create storage context with only vector store
            # LlamaIndex will create in-memory docstore/index_store internally
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,
            )

            # Create index
            self.index = VectorStoreIndex(
                [],
                storage_context=storage_context,
                store_nodes_override=True,
            )

            log_event(
                "index_initialized",
                {
                    "vector_store": "QdrantVectorStore",
                    "storage_mode": "qdrant_only",
                    "note": "Text retrieval uses Qdrant directly",
                },
            )

        except Exception as e:
            log_event(
                "index_setup_failed",
                {"error": str(e)},
                level=logging.ERROR,
            )
            raise

    def _setup_query_engine(self):
        """Setup basic query engine."""
        if self.index:
            self.query_engine = self.index.as_query_engine(
                similarity_top_k=5,
            )
            log_event(
                "query_engine_created",
                {"similarity_top_k": 5},
            )

    async def add_document(
        self,
        document_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Result[Dict[str, Any], str]:
        """
        Add a document to the index.

        Delegates to the document service for centralized document management.

        Returns:
            Success with document info, or Failure with error details
        """
        # Initialize tracker on first use if not already initialized
        if not self._tracker_initialized:
            try:
                await self.doc_tracker.initialize()
                self._tracker_initialized = True
                log_event(
                    "tracker_initialized_on_first_use", {"document_id": document_id}
                )
            except Exception as e:
                log_event(
                    "tracker_init_failed",
                    {"error": str(e), "error_type": type(e).__name__},
                    level=logging.ERROR,
                )
                return internal_error(
                    f"Failed to initialize document tracker: {str(e)}",
                    context={
                        "document_id": document_id,
                        "error_type": type(e).__name__,
                    },
                )

        if not self.document_service:
            log_event(
                "document_add_skipped",
                {
                    "document_id": document_id,
                    "reason": "no_document_service",
                    "has_index": self.index is not None,
                    "has_tracker": self.doc_tracker is not None,
                },
                level=logging.ERROR,
            )
            return internal_error(
                "Document service not initialized",
                context={
                    "document_id": document_id,
                    "has_index": self.index is not None,
                    "has_tracker": self.doc_tracker is not None,
                },
            )

        # Delegate to document service (which now returns Result)
        return await self.document_service.add_document(document_id, content, metadata)

    def _create_minimal_chunk_metadata(
        self, full_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create minimal metadata for chunks to avoid bloat.

        Delegates to the metadata service for consistent optimization.
        """
        if self.metadata_service:
            return self.metadata_service.create_minimal_chunk_metadata(full_metadata)

        # Fallback implementation if metadata service not available
        minimal = {
            "document_id": full_metadata.get("document_id"),
            "title": full_metadata.get("title", ""),
            "mime_type": full_metadata.get("mime_type", ""),
            "status": full_metadata.get("status", "ready"),
        }
        return minimal

    async def get_full_document_metadata(self, document_id: str) -> Dict[str, Any]:
        """
        Retrieve the full metadata for a document.

        Delegates to the metadata service for centralized metadata management.
        """
        if self.metadata_service:
            return await self.metadata_service.get_full_document_metadata(document_id)

        # Fallback if metadata service not available
        return {}

    async def query(
        self,
        question: str,
        similarity_top_k: int = 5,
        response_mode: str = "tree_summarize",
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Query the index using RAG.

        Delegates to the query service for centralized Q&A operations.
        """
        if self.query_service:
            return await self.query_service.query(
                question=question,
                similarity_top_k=similarity_top_k,
                response_mode=response_mode,
                filters=filters,
            )

        # Fallback if query service not available
        log_event(
            "query_skipped",
            {"reason": "no_query_service"},
            level=logging.ERROR,
        )
        return {
            "answer": "Query service not available",
            "sources": [],
            "method": "error",
            "error": True,
        }

    async def get_document_count(self) -> Result[int, str]:
        """
        Get count of indexed documents.

        Delegates to the document service for centralized document counting.

        Returns:
            Success with document count, or Failure with error details
        """
        if not self.document_service:
            return internal_error(
                "Document service not initialized",
                context={"service": "llamaindex_service"},
            )

        # Delegate to document service (which now returns Result)
        return await self.document_service.get_document_count()

    async def delete_document(self, document_id: str) -> Result[Dict[str, Any], str]:
        """
        Delete a document from the index.

        Delegates to the document service for centralized document deletion.

        Returns:
            Success with deletion info, or Failure with error details
        """
        if not self.document_service:
            log_event(
                "document_delete_skipped",
                {"document_id": document_id, "reason": "no_document_service"},
                level=logging.WARNING,
            )
            return internal_error(
                "Document service not initialized",
                context={"document_id": document_id, "service": "llamaindex_service"},
            )

        # Delegate to document service (which now returns Result)
        return await self.document_service.delete_document(document_id)

    async def clear_all_data(self) -> Result[Dict[str, Any], str]:
        """
        Clear all data and reset the system.

        Delegates to document service and reinitializes all components.

        Returns:
            Success with clearing statistics, or Failure with error details
        """
        try:
            # Use document service to clear data
            if not self.document_service:
                return internal_error(
                    "Document service not initialized",
                    context={"service": "llamaindex_service"},
                )

            # Delegate to document service (which now returns Result)
            clear_result = await self.document_service.clear_all_data()

            if clear_result.is_failure():
                return clear_result  # Propagate the failure

            # Re-initialize all components
            self._setup_index()
            self._setup_query_engine()
            self._setup_search_service()
            self._setup_metadata_service()
            self._setup_document_service()
            self._setup_query_service()

            return clear_result

        except Exception as e:
            log_event(
                "data_cleanup_error",
                {"error": str(e), "error_type": type(e).__name__},
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to clear all data: {str(e)}",
                context={"error_type": type(e).__name__},
            )

    async def update_document_metadata(
        self,
        document_id: str,
        metadata_updates: Dict[str, Any],
        merge_mode: str = "update",
    ) -> bool:
        """
        Update metadata for a document.

        Delegates to the metadata service for centralized metadata management.
        """
        if self.metadata_service:
            return await self.metadata_service.update_document_metadata(
                document_id, metadata_updates, merge_mode
            )

        # Fallback if metadata service not available
        log_event(
            "metadata_update_skipped",
            {"document_id": document_id, "reason": "no_metadata_service"},
            level=logging.WARNING,
        )
        return False

    async def query_documents_by_metadata(
        self, filters: Dict[str, Any], limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query documents based on metadata filters.

        Delegates to the metadata service for centralized metadata queries.
        """
        # Initialize tracker on first use if not already initialized
        if not self._tracker_initialized:
            try:
                await self.doc_tracker.initialize()
                self._tracker_initialized = True
                log_event("tracker_initialized_on_query", {"filters": filters})
            except Exception as e:
                log_event(
                    "tracker_init_failed_on_query",
                    {"error": str(e), "error_type": type(e).__name__},
                    level=logging.ERROR,
                )
                # Return empty list on initialization failure
                return []

        if self.metadata_service:
            return await self.metadata_service.query_documents_by_metadata(
                filters, limit, offset
            )

        # Fallback if metadata service not available
        return []

    async def get_document_analysis(self, document_id: str) -> Dict[str, Any]:
        """
        Get comprehensive analysis of a document.

        Delegates to the metadata service for centralized document analysis.
        """
        if self.metadata_service:
            return await self.metadata_service.get_document_analysis(document_id)

        # Fallback if metadata service not available
        return {"error": "Metadata service not available"}

    def _get_embedding_stats(self) -> Dict[str, Any]:
        """Get embedding model statistics."""
        try:
            embed_model = Settings.embed_model
            return {
                "model": getattr(embed_model, "model_name", "unknown"),
                "dimension": getattr(embed_model, "embed_dim", 384),
                "max_length": getattr(embed_model, "_max_length", 512),
            }
        except Exception:
            return {"model": "unknown", "dimension": 384}

    async def get_document_chunks(
        self, document_id: str, limit: int = 100, offset: int = 0
    ) -> Result[Dict[str, Any], str]:
        """
        Get all chunks for a specific document with pagination.

        Delegates to the document service for centralized chunk retrieval.

        Returns:
            Success with chunks data, or Failure with error details
        """
        if not self.document_service:
            return internal_error(
                "Document service not initialized",
                context={"document_id": document_id, "service": "llamaindex_service"},
            )

        # Delegate to document service (which now returns Result)
        return await self.document_service.get_document_chunks(
            document_id, limit, offset
        )

    async def get_document_neighbors(
        self, document_id: str, top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Get semantically similar documents for a given document.

        Delegates to the search service for neighbor finding.
        """
        try:
            if not self.search_service:
                return {"error": "Search service not initialized", "neighbors": []}

            # Check if document exists using document service
            if self.document_service:
                if not await self.document_service.document_exists(document_id):
                    return {
                        "error": f"Document {document_id} not found",
                        "neighbors": [],
                    }

                node_ids = await self.document_service.get_node_ids(document_id)
                if not node_ids:
                    return {"error": "No nodes found for document", "neighbors": []}
            else:
                # Fallback to direct access if document service not available
                if not self.doc_tracker or not await self.doc_tracker.document_exists(
                    document_id
                ):
                    return {
                        "error": f"Document {document_id} not found",
                        "neighbors": [],
                    }

                node_ids = await self.doc_tracker.get_node_ids(document_id)
                if not node_ids:
                    return {"error": "No nodes found for document", "neighbors": []}

            # Get the first node's text from Qdrant directly
            if not self.qdrant_client:
                return {"error": "Qdrant client not available", "neighbors": []}

            first_node_id = node_ids[0]

            # Query Qdrant for the node payload
            try:
                from lifearchivist.storage.utils import QdrantNodeUtils

                points = self.qdrant_client.retrieve(
                    collection_name="lifearchivist",
                    ids=[first_node_id],
                    with_payload=True,
                    with_vectors=False,
                )

                if not points or len(points) == 0:
                    log_event(
                        "qdrant_node_not_found",
                        {
                            "document_id": document_id,
                            "node_id": first_node_id,
                            "total_nodes_in_redis": len(node_ids),
                        },
                        level=logging.WARNING,
                    )
                    return {
                        "document_id": document_id,
                        "neighbors": [],
                        "total": 0,
                        "warning": "Document node not found in Qdrant",
                    }

                # Extract text from Qdrant payload
                node_payload = points[0].payload
                document_text = QdrantNodeUtils.extract_text_from_node(node_payload)

                if not document_text:
                    log_event(
                        "node_text_extraction_failed",
                        {"document_id": document_id, "node_id": first_node_id},
                        level=logging.WARNING,
                    )
                    return {
                        "document_id": document_id,
                        "neighbors": [],
                        "total": 0,
                        "warning": "Could not extract text from node",
                    }

            except Exception as e:
                log_event(
                    "qdrant_retrieval_error",
                    {
                        "document_id": document_id,
                        "node_id": first_node_id,
                        "error": str(e),
                    },
                    level=logging.ERROR,
                )
                return {
                    "document_id": document_id,
                    "neighbors": [],
                    "total": 0,
                    "error": f"Failed to retrieve node from Qdrant: {str(e)}",
                }

            # Delegate to search service with the extracted text
            neighbors = await self.search_service.get_document_neighbors(
                document_text=document_text,
                document_id=document_id,
                top_k=top_k,
            )

            return {
                "document_id": document_id,
                "neighbors": neighbors,
                "total": len(neighbors),
            }

        except Exception as e:
            log_event(
                "document_neighbors_error",
                {
                    "document_id": document_id,
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            return {
                "error": str(e),
                "neighbors": [],
            }

    async def retrieve_similar(
        self, query: str, top_k: int = 10, similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar documents using vector search.

        Delegates to the search service for consistency.
        """
        if not self.search_service:
            log_event(
                "retrieval_skipped",
                {"reason": "no_search_service"},
                level=logging.DEBUG,
            )
            return []

        # Delegate to search service
        return await self.search_service.retrieve_similar(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )

    # Additional search methods that delegate to the search service
    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform semantic search using the search service."""
        if not self.search_service:
            return []
        return await self.search_service.semantic_search(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            filters=filters,
        )

    async def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform keyword search using the search service."""
        if not self.search_service:
            return []
        return await self.search_service.keyword_search(
            query=query,
            top_k=top_k,
            filters=filters,
        )

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search using the search service."""
        if not self.search_service:
            return []
        return await self.search_service.hybrid_search(
            query=query,
            top_k=top_k,
            semantic_weight=semantic_weight,
            filters=filters,
        )

    async def cleanup(self) -> None:
        """
        Cleanup resources and close connections.

        This method should be called when shutting down the service to ensure
        proper cleanup of Redis connections and other resources.
        """
        try:
            if self.doc_tracker and self._tracker_initialized:
                await self.doc_tracker.close()
                self._tracker_initialized = False
                log_event(
                    "llamaindex_service_cleanup",
                    {"tracker_closed": True},
                )
        except Exception as e:
            log_event(
                "llamaindex_service_cleanup_error",
                {"error": str(e), "error_type": type(e).__name__},
                level=logging.ERROR,
            )
