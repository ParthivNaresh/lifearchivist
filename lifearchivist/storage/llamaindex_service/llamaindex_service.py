"""
LlamaIndex service for advanced RAG functionality.
"""

import asyncio
import logging
import shutil
from typing import Any, Dict, List, Optional

from llama_index.core import (
    Document,
    Settings,
    StorageContext,
    VectorStoreIndex,
    get_response_synthesizer,
    load_index_from_storage,
)
from llama_index.core.base.response.schema import Response
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama

from lifearchivist.config import get_settings
from lifearchivist.utils.logging import log_event, track

from .llamaindex_service_utils import (
    DocumentFilter,
    NodeProcessor,
    calculate_document_metrics,
    create_error_response,
)


class LlamaIndexService:
    """LlamaIndex service for advanced document processing and RAG."""

    def __init__(self, database=None, vault=None):
        self.settings = get_settings()
        self.database = database
        self.vault = vault
        self.index: Optional[VectorStoreIndex] = None
        self.query_engine = None
        self.setup()

    def setup(self):
        """Setup functions for LlamaIndex."""
        self._setup_llamaindex()
        self._setup_query_engine()

    @track(
        operation="llama_index_setup",
        track_performance=True,
        frequency="low_frequency",
    )
    def _setup_llamaindex(self):
        """Configure LlamaIndex with local models and services."""

        # Log configuration being used
        log_event(
            "llamaindex_config",
            {
                "embedding_model": self.settings.embedding_model,
                "llm_model": self.settings.llm_model,
                "ollama_url": self.settings.ollama_url,
                "chunk_size": 800,
                "chunk_overlap": 100,
                "storage_dir": str(self.settings.lifearch_home / "llamaindex_storage"),
            },
        )

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
            chunk_size=800,
            chunk_overlap=100,
            separator="\n\n",
        )

        storage_dir = self.settings.lifearch_home / "llamaindex_storage"
        storage_dir.mkdir(exist_ok=True)

        try:
            storage_context = StorageContext.from_defaults(persist_dir=str(storage_dir))
            loaded_index = load_index_from_storage(storage_context)
            if isinstance(loaded_index, VectorStoreIndex):
                self.index = loaded_index

                # Log successful index loading
                doc_count = (
                    len(self.index.ref_doc_info)
                    if hasattr(self.index, "ref_doc_info")
                    else 0
                )
                log_event(
                    "llamaindex_loaded",
                    {
                        "storage_type": "SimpleVectorStore",
                        "document_count": doc_count,
                        "index_type": type(loaded_index).__name__,
                    },
                )
            else:
                log_event(
                    "llamaindex_wrong_type",
                    {
                        "expected_type": "VectorStoreIndex",
                        "actual_type": type(loaded_index).__name__,
                    },
                    level=logging.WARNING,
                )
        except FileNotFoundError:
            # This is expected on first run
            log_event(
                "llamaindex_not_found",
                {
                    "storage_dir": str(storage_dir),
                    "action": "will_create_new",
                },
                level=logging.INFO,
            )
        except Exception as e:
            log_event(
                "llamaindex_load_failed",
                {
                    "storage_dir": str(storage_dir),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            raise e

    @track(
        operation="query_engine_setup",
        track_performance=True,
        frequency="low_frequency",
    )
    def _setup_query_engine(self):
        """Setup the query engine with retriever and response synthesizer."""
        if not self.index:
            log_event(
                "query_engine_skipped",
                {
                    "reason": "no_index",
                },
                level=logging.DEBUG,
            )
            return

        retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=1,
        )

        response_synthesizer = get_response_synthesizer(
            response_mode=ResponseMode.COMPACT,
            streaming=False,
        )

        # Create query engine without post-processors for maximum speed
        self.query_engine = RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=response_synthesizer,
            node_postprocessors=[],  # No post-processing for speed
        )

        log_event(
            "query_engine_created",
            {
                "retriever_type": "VectorIndexRetriever",
                "similarity_top_k": 1,
                "response_mode": "COMPACT",
                "post_processors": 0,
            },
            level=logging.DEBUG,
        )

    @track(
        operation="document_addition",
        include_args=["document_id"],
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
    )
    async def add_document(
        self,
        document_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a document to the LlamaIndex."""
        if not self.index:
            log_event(
                "document_add_failed",
                {
                    "document_id": document_id,
                    "reason": "no_index",
                },
                level=logging.ERROR,
            )
            return False

        # Log document characteristics
        content_length = len(content)
        word_count = len(content.split()) if content else 0
        metadata_fields = len(metadata) if metadata else 0

        log_event(
            "document_add_started",
            {
                "document_id": document_id,
                "content_length": content_length,
                "word_count": word_count,
                "metadata_fields": metadata_fields,
                "mime_type": metadata.get("mime_type") if metadata else None,
            },
        )

        # Create LlamaIndex document
        doc_metadata = metadata or {}
        doc_metadata["document_id"] = document_id

        document = Document(
            text=content,
            metadata=doc_metadata,
            id_=document_id,
        )

        try:
            # Add to index
            self.index.insert(document)

            # Log successful insertion
            nodes_created = len(
                self.index.ref_doc_info.get(document_id, {}).get("node_ids", [])
            )
            log_event(
                "document_indexed",
                {
                    "document_id": document_id,
                    "nodes_created": nodes_created,
                    "content_length": content_length,
                },
            )

            # Persist the index (handle version compatibility)
            await self._persist_index()
            return True

        except Exception as e:
            log_event(
                "document_indexing_error",
                {
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return False

    @track(
        operation="metadata_update",
        include_args=["document_id", "merge_mode"],
        include_result=True,
        track_performance=True,
        frequency="medium_frequency",
    )
    async def update_document_metadata(
        self,
        document_id: str,
        metadata_updates: Dict[str, Any],
        merge_mode: str = "update",
    ) -> bool:
        """Update metadata for an existing document by updating all its nodes."""
        if not self.index:
            log_event(
                "metadata_update_failed",
                {
                    "document_id": document_id,
                    "reason": "no_index",
                },
                level=logging.ERROR,
            )
            return False

        # Get the nodes associated with this document using ref_doc_info
        ref_doc_info = self.index.ref_doc_info.get(document_id)
        if not ref_doc_info:
            log_event(
                "metadata_update_failed",
                {
                    "document_id": document_id,
                    "reason": "document_not_found",
                },
                level=logging.WARNING,
            )
            return False

        node_ids = ref_doc_info.node_ids

        # Log update operation details
        log_event(
            "metadata_update_started",
            {
                "document_id": document_id,
                "node_count": len(node_ids),
                "merge_mode": merge_mode,
                "update_fields": list(metadata_updates.keys()),
                "has_list_fields": any(
                    key in metadata_updates
                    for key in ["content_dates", "tags", "provenance"]
                ),
            },
        )

        # Update metadata on all nodes that belong to this document
        docstore = self.index.storage_context.docstore
        updated_nodes = 0
        failed_nodes = 0

        for node_id in node_ids:
            try:
                # Get the node
                node = docstore.get_node(node_id)
                if not node:
                    failed_nodes += 1
                    continue

                # Update metadata based on merge mode
                if merge_mode == "replace":
                    # Replace entire metadata
                    metadata_updates["document_id"] = document_id
                    node.metadata = metadata_updates
                else:
                    # Update/merge specific fields
                    current_metadata = node.metadata or {}

                    # Handle special list fields that need merging
                    for key, value in metadata_updates.items():
                        if key in [
                            "content_dates",
                            "tags",
                            "provenance",
                        ] and isinstance(value, list):
                            # Merge lists by appending new items
                            existing_items = current_metadata.get(key, [])
                            if isinstance(existing_items, list):
                                current_metadata[key] = existing_items + value
                            else:
                                current_metadata[key] = value
                        else:
                            # Simple field update
                            current_metadata[key] = value

                    node.metadata = current_metadata

                # Update the node in docstore using the correct method (plural)
                docstore.add_documents([node], allow_update=True)
                updated_nodes += 1
            except Exception as e:
                failed_nodes += 1
                # Log individual node failures at DEBUG level
                log_event(
                    "node_update_failed",
                    {
                        "document_id": document_id,
                        "node_id": node_id,
                        "error": str(e),
                    },
                    level=logging.DEBUG,
                )
                continue

        # Log update results
        if updated_nodes > 0:
            log_event(
                "metadata_update_completed",
                {
                    "document_id": document_id,
                    "updated_nodes": updated_nodes,
                    "failed_nodes": failed_nodes,
                    "success_rate": updated_nodes / len(node_ids),
                },
            )
        else:
            log_event(
                "metadata_update_failed",
                {
                    "document_id": document_id,
                    "reason": "no_nodes_updated",
                    "failed_nodes": failed_nodes,
                },
                level=logging.ERROR,
            )

        if updated_nodes == 0:
            return False

        # Persist changes
        await self._persist_index()
        return True

    @track(
        operation="metadata_query",
        include_args=["limit", "offset"],
        include_result=True,
        track_performance=True,
        frequency="medium_frequency",
    )
    async def query_documents_by_metadata(
        self, filters: Dict[str, Any], limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query documents based on metadata filters by checking their nodes."""
        try:
            if not self.index:
                log_event(
                    "metadata_query_empty",
                    {
                        "reason": "no_index",
                    },
                    level=logging.DEBUG,
                )
                return []

            # Log query parameters
            log_event(
                "metadata_query_started",
                {
                    "filter_keys": list(filters.keys()) if filters else [],
                    "has_filters": bool(filters),
                    "limit": limit,
                    "offset": offset,
                },
            )

            docstore = self.index.storage_context.docstore
            matching_documents = []

            # Get all documents using ref_doc_info (the correct way)
            ref_doc_info = self.index.ref_doc_info
            all_document_ids = list(ref_doc_info.keys())

            total_documents = len(all_document_ids)
            documents_checked = 0
            documents_matched = 0

            for document_id in all_document_ids:
                try:
                    documents_checked += 1

                    # Get the nodes for this document
                    doc_ref_info = ref_doc_info[document_id]
                    node_ids = doc_ref_info.node_ids

                    if not node_ids:
                        continue

                    # Get the first node to check metadata (all nodes from same doc should have similar metadata)
                    first_node = docstore.get_node(node_ids[0])
                    if not first_node or not hasattr(first_node, "metadata"):
                        continue

                    metadata = first_node.metadata or {}

                    # Check if document matches all filters
                    if DocumentFilter.matches_filters(metadata, filters):
                        documents_matched += 1
                        doc_info = {
                            "document_id": document_id,
                            "metadata": metadata,
                            "text_preview": NodeProcessor.generate_text_preview(
                                first_node, 200
                            ),
                            "node_count": len(node_ids),
                        }
                        matching_documents.append(doc_info)

                except Exception as e:
                    # Log individual document errors at DEBUG level
                    log_event(
                        "metadata_query_doc_error",
                        {
                            "document_id": document_id,
                            "error": str(e),
                        },
                        level=logging.DEBUG,
                    )
                    continue  # Don't raise, just continue to next document

            # Log query results
            log_event(
                "metadata_query_completed",
                {
                    "total_documents": total_documents,
                    "documents_checked": documents_checked,
                    "documents_matched": documents_matched,
                    "match_rate": (
                        documents_matched / documents_checked
                        if documents_checked > 0
                        else 0
                    ),
                    "results_returned": min(len(matching_documents[offset:]), limit),
                },
            )

            # Log if no matches found with filters
            if filters and documents_matched == 0:
                log_event(
                    "metadata_query_no_matches",
                    {
                        "filters": filters,
                        "documents_checked": documents_checked,
                    },
                    level=logging.WARNING,
                )

            paginated_results = matching_documents[offset : offset + limit]
            return paginated_results

        except Exception as e:
            log_event(
                "metadata_query_failed",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "filters": filters,
                },
                level=logging.ERROR,
            )
            raise ValueError(e) from None

    @track(
        operation="index_persistence",
        track_performance=True,
        frequency="medium_frequency",
    )
    async def _persist_index(self):
        """Persist the index with version compatibility handling."""
        storage_dir = self.settings.lifearch_home / "llamaindex_storage"
        try:
            if self.index:
                # Log persistence attempt
                doc_count = (
                    len(self.index.ref_doc_info)
                    if hasattr(self.index, "ref_doc_info")
                    else 0
                )
                log_event(
                    "index_persistence_started",
                    {
                        "storage_dir": str(storage_dir),
                        "document_count": doc_count,
                    },
                    level=logging.DEBUG,
                )

                self.index.storage_context.persist(persist_dir=str(storage_dir))

                log_event(
                    "index_persistence_completed",
                    {
                        "storage_dir": str(storage_dir),
                        "document_count": doc_count,
                    },
                    level=logging.DEBUG,
                )
        except AttributeError as persist_error:
            log_event(
                "index_persistence_warning",
                {
                    "error": "AttributeError during persist",
                    "message": str(persist_error),
                    "note": "Index changes still in memory",
                },
                level=logging.WARNING,
            )
            # Index changes are still in memory, just persist failed
        except Exception as e:
            log_event(
                "index_persistence_failed",
                {
                    "storage_dir": str(storage_dir),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            raise e

    @track(
        operation="llamaindex_query",
        include_args=["similarity_top_k", "response_mode"],
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
    )
    async def query(
        self,
        question: str,
        similarity_top_k: int = 5,
        response_mode: str = "tree_summarize",
    ) -> Dict[str, Any]:
        """Query the index and return structured response."""
        if not self.query_engine:
            log_event(
                "query_engine_unavailable",
                {
                    "reason": "not_initialized",
                },
                level=logging.WARNING,
            )
            return self._empty_response("Query engine not available")

        # Log query details
        log_event(
            "llamaindex_query_started",
            {
                "question_length": len(question),
                "question_preview": (
                    question[:100] + "..." if len(question) > 100 else question
                ),
                "similarity_top_k": similarity_top_k,
                "response_mode": response_mode,
            },
        )

        # Execute query with timeout to prevent hanging
        try:
            response: Response = await asyncio.wait_for(
                asyncio.to_thread(self.query_engine.query, question), timeout=30.0
            )

        except asyncio.TimeoutError:
            log_event(
                "llamaindex_query_timeout",
                {
                    "question_preview": question[:50],
                    "timeout_seconds": 30,
                    "reason": "memory_constraints",
                },
                level=logging.ERROR,
            )
            return self._empty_response("Query timed out due to memory constraints")

        except AttributeError as attr_error:
            if "usage" in str(attr_error):
                # This is a known issue with some Ollama responses
                log_event(
                    "llamaindex_query_usage_error",
                    {
                        "error": str(attr_error),
                        "note": "Known Ollama response issue",
                    },
                    level=logging.DEBUG,
                )
            raise attr_error

        except Exception as e:
            log_event(
                "llamaindex_query_failed",
                {
                    "question_preview": question[:50],
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            raise e

        # Extract source information
        sources = []
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes:
                source_info = NodeProcessor.extract_source_info(node)
                if source_info:
                    sources.append(source_info)

        answer = str(response.response) if response.response else ""

        # Log query results
        log_event(
            "llamaindex_query_completed",
            {
                "answer_length": len(answer),
                "sources_count": len(sources),
                "has_answer": bool(answer),
                "response_mode": response_mode,
            },
        )

        return {
            "answer": answer,
            "sources": sources,
            "method": "llamaindex_rag",
            "metadata": {
                "nodes_used": len(sources),
                "response_mode": response_mode,
            },
        }

    def _empty_response(self, error_message: str) -> Dict[str, Any]:
        """Return empty response with error."""
        return {
            "answer": f"I encountered an error: {error_message}",
            "confidence": 0.0,
            "sources": [],
            "method": "llamaindex_error",
            "metadata": {"error": error_message},
        }

    @track(
        operation="document_retrieval",
        include_args=["top_k", "similarity_threshold"],
        include_result=True,
        track_performance=True,
        frequency="medium_frequency",
    )
    async def retrieve_similar(
        self, query: str, top_k: int = 10, similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Retrieve similar documents without generating a response."""
        try:
            if not self.index:
                log_event(
                    "retrieval_skipped",
                    {
                        "reason": "no_index",
                    },
                    level=logging.DEBUG,
                )
                return []

            log_event(
                "similarity_retrieval_started",
                {
                    "query_length": len(query),
                    "query_preview": query[:50],
                    "top_k": top_k,
                    "similarity_threshold": similarity_threshold,
                },
                level=logging.DEBUG,
            )

            retriever = VectorIndexRetriever(index=self.index, similarity_top_k=top_k)

            # Retrieve nodes
            nodes = retriever.retrieve(query)

            # Filter by similarity threshold and format
            results = []
            nodes_below_threshold = 0

            for node in nodes:
                if node.score and node.score >= similarity_threshold:
                    source_info = NodeProcessor.extract_source_info(node)
                    if source_info:
                        results.append(source_info)
                else:
                    nodes_below_threshold += 1

            log_event(
                "similarity_retrieval_completed",
                {
                    "nodes_retrieved": len(nodes),
                    "nodes_above_threshold": len(results),
                    "nodes_below_threshold": nodes_below_threshold,
                    "threshold": similarity_threshold,
                },
                level=logging.DEBUG,
            )

            return results
        except Exception as e:
            log_event(
                "similarity_retrieval_failed",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return []

    @track(
        operation="document_analysis",
        include_args=["document_id"],
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
    )
    async def get_document_analysis(self, document_id: str) -> Dict[str, Any]:
        """Get comprehensive analysis of a document in the LlamaIndex."""
        try:
            if not self.index:
                log_event(
                    "document_analysis_skipped",
                    {
                        "document_id": document_id,
                        "reason": "no_index",
                    },
                    level=logging.WARNING,
                )
                return {"error": "Index not initialized"}

            # Get all nodes for this document using ref_doc_info
            nodes = NodeProcessor.get_document_nodes_from_ref_doc_info(
                self.index, document_id
            )

            if not nodes:
                log_event(
                    "document_analysis_not_found",
                    {
                        "document_id": document_id,
                    },
                    level=logging.WARNING,
                )
                return create_error_response(
                    f"Document {document_id} not found in LlamaIndex"
                )

            # Calculate metrics
            metrics = calculate_document_metrics(nodes)

            # Get embedding stats
            embedding_stats = self._get_embedding_stats()

            # Use first node's metadata (all nodes inherit document metadata)
            original_metadata = nodes[0].get("metadata", {}) if nodes else {}

            log_event(
                "document_analysis_completed",
                {
                    "document_id": document_id,
                    "node_count": len(nodes),
                    "total_chars": metrics.get("total_chars", 0),
                    "total_words": metrics.get("total_words", 0),
                    "avg_chunk_size": metrics.get("avg_chunk_size", 0),
                },
                level=logging.DEBUG,
            )

            return {
                "document_id": document_id,
                "status": "indexed",
                "original_metadata": original_metadata,
                "processing_info": {
                    **metrics,
                    "embedding_model": embedding_stats.get("model"),
                    "embedding_dimension": embedding_stats.get("dimension"),
                },
                "storage_info": {
                    "docstore_type": type(self.index.storage_context.docstore).__name__,
                    "vector_store_type": type(self.index.vector_store).__name__,
                    "text_splitter": "SentenceSplitter",
                },
                "chunks_preview": nodes[:3],  # First 3 chunks for preview
            }

        except Exception as e:
            log_event(
                "document_analysis_failed",
                {
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return create_error_response(str(e))

    @track(
        operation="document_chunks_retrieval",
        include_args=["document_id", "limit", "offset"],
        include_result=True,
        track_performance=True,
        frequency="medium_frequency",
    )
    async def get_document_chunks(
        self, document_id: str, limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        """Get all chunks for a specific document with pagination."""
        try:
            if not self.index:
                log_event(
                    "chunks_retrieval_skipped",
                    {
                        "document_id": document_id,
                        "reason": "no_index",
                    },
                    level=logging.DEBUG,
                )
                return {"error": "Index not initialized", "chunks": [], "total": 0}

            # Get all nodes for this document
            all_nodes = NodeProcessor.get_document_nodes_from_ref_doc_info(
                self.index, document_id
            )

            if not all_nodes:
                log_event(
                    "chunks_not_found",
                    {
                        "document_id": document_id,
                    },
                    level=logging.WARNING,
                )
                return {
                    "error": f"No chunks found for document {document_id}",
                    "chunks": [],
                    "total": 0,
                }

            # Apply pagination
            total = len(all_nodes)
            paginated_nodes = all_nodes[offset : offset + limit]

            # Enrich with additional metadata
            enriched_chunks = []
            total_text_length = 0
            total_word_count = 0

            for i, node_data in enumerate(paginated_nodes):
                text = node_data.get("text", "")
                text_length = len(text)
                word_count = len(text.split())

                total_text_length += text_length
                total_word_count += word_count

                chunk_info = {
                    "chunk_index": offset + i,
                    "node_id": node_data.get("node_id"),
                    "text": text,
                    "text_length": text_length,
                    "word_count": word_count,
                    "start_char": node_data.get("start_char"),
                    "end_char": node_data.get("end_char"),
                    "metadata": node_data.get("metadata", {}),
                    "relationships": node_data.get("relationships", {}),
                }
                enriched_chunks.append(chunk_info)

            log_event(
                "chunks_retrieved",
                {
                    "document_id": document_id,
                    "total_chunks": total,
                    "chunks_returned": len(enriched_chunks),
                    "avg_chunk_length": (
                        total_text_length / len(enriched_chunks)
                        if enriched_chunks
                        else 0
                    ),
                    "avg_word_count": (
                        total_word_count / len(enriched_chunks)
                        if enriched_chunks
                        else 0
                    ),
                    "has_more": offset + limit < total,
                },
                level=logging.DEBUG,
            )

            return {
                "document_id": document_id,
                "chunks": enriched_chunks,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
            }

        except Exception as e:
            log_event(
                "chunks_retrieval_failed",
                {
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return create_error_response(str(e), chunks=[], total=0)

    async def get_document_neighbors(
        self, document_id: str, top_k: int = 10
    ) -> Dict[str, Any]:
        """Find semantically similar documents and chunks."""
        try:
            if not self.index:
                return {"error": "Index not initialized", "neighbors": []}

            # Get a representative chunk from the document
            document_nodes = NodeProcessor.get_document_nodes_from_ref_doc_info(
                self.index, document_id
            )
            if not document_nodes:
                return {
                    "error": f"No chunks found for document {document_id}",
                    "neighbors": [],
                }

            # Use the first chunk as query for similarity
            representative_text = document_nodes[0].get("text", "")
            if not representative_text:
                return {"error": "No text content available", "neighbors": []}

            # Retrieve similar chunks across all documents
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=top_k * 2,  # Get more to filter out self-references
            )

            similar_nodes = retriever.retrieve(representative_text)

            # Filter out nodes from the same document and format results
            neighbors = []
            for node in similar_nodes:
                node_doc_id = node.node.metadata.get("document_id")
                if node_doc_id != document_id:  # Exclude self-references
                    neighbor_info = {
                        "document_id": node_doc_id,
                        "similarity_score": float(node.score) if node.score else 0.0,
                        "text_preview": NodeProcessor.generate_text_preview(
                            node.node, 200
                        ),
                        "metadata": node.node.metadata,
                    }
                    neighbors.append(neighbor_info)

                if len(neighbors) >= top_k:
                    break

            return {
                "document_id": document_id,
                "neighbors": neighbors,
                "total_found": len(neighbors),
                "query_text": (
                    representative_text[:100] + "..."
                    if len(representative_text) > 100
                    else representative_text
                ),
            }

        except Exception as e:
            raise e

    def _get_embedding_stats(self) -> Dict[str, Any]:
        """Get embedding model statistics."""
        try:
            embed_model = Settings.embed_model
            return {
                "model": getattr(embed_model, "model_name", "unknown"),
                "dimension": getattr(embed_model, "embed_dim", None),
                "max_length": getattr(embed_model, "_max_length", None),
            }
        except Exception:
            return {"model": "unknown", "dimension": None}

    @track(
        operation="data_cleanup",
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
    )
    async def clear_all_data(self) -> Dict[str, Any]:
        """Clear all LlamaIndex data and storage."""
        storage_dir = self.settings.lifearch_home / "llamaindex_storage"
        cleared_metrics = {
            "storage_files_deleted": 0,
            "storage_bytes_reclaimed": 0,
            "index_reset": False,
            "errors": [],
        }

        log_event(
            "data_cleanup_started",
            {
                "storage_dir": str(storage_dir),
            },
        )

        try:
            # Clear in-memory index
            doc_count_before = (
                len(self.index.ref_doc_info)
                if self.index and hasattr(self.index, "ref_doc_info")
                else 0
            )
            self.index = None
            self.query_engine = None
            cleared_metrics["index_reset"] = True

            log_event(
                "index_cleared",
                {
                    "documents_cleared": doc_count_before,
                },
                level=logging.DEBUG,
            )

            # Remove storage directory and all files
            if storage_dir.exists():
                total_size = 0
                file_count = 0
                file_list = []

                # Calculate metrics before deletion
                for file_path in storage_dir.rglob("*"):
                    if file_path.is_file():
                        file_size = file_path.stat().st_size
                        total_size += file_size
                        file_count += 1
                        file_list.append(f"{file_path.name} ({file_size} bytes)")

                # Remove the entire storage directory
                shutil.rmtree(storage_dir)

                cleared_metrics["storage_files_deleted"] = file_count
                cleared_metrics["storage_bytes_reclaimed"] = total_size

                log_event(
                    "storage_cleared",
                    {
                        "files_deleted": file_count,
                        "bytes_reclaimed": total_size,
                        "mb_reclaimed": round(total_size / (1024 * 1024), 2),
                    },
                )

            # Reinitialize empty structures
            await self._initialize_empty_index()

            log_event(
                "data_cleanup_completed",
                {
                    "documents_cleared": doc_count_before,
                    "files_deleted": cleared_metrics["storage_files_deleted"],
                    "mb_reclaimed": round(
                        cleared_metrics["storage_bytes_reclaimed"] / (1024 * 1024), 2
                    ),
                },
            )

            return cleared_metrics

        except Exception as e:
            error_msg = f"LlamaIndex clearing failed: {e}"
            if isinstance(cleared_metrics["errors"], list):
                cleared_metrics["errors"].append(error_msg)

            log_event(
                "data_cleanup_failed",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "partial_success": cleared_metrics["index_reset"],
                },
                level=logging.ERROR,
            )

            return cleared_metrics

    @track(
        operation="empty_index_initialization",
        track_performance=True,
        frequency="low_frequency",
    )
    async def _initialize_empty_index(self):
        """Initialize a fresh empty LlamaIndex."""
        try:
            storage_dir = self.settings.lifearch_home / "llamaindex_storage"
            storage_dir.mkdir(exist_ok=True)

            log_event(
                "empty_index_init_started",
                {
                    "storage_dir": str(storage_dir),
                },
                level=logging.DEBUG,
            )

            # Create new storage context with simple stores (don't load from empty directory)
            vector_store = SimpleVectorStore()
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,
                docstore=SimpleDocumentStore(),
                index_store=SimpleIndexStore(),
            )
            self.index = VectorStoreIndex([], storage_context=storage_context)

            # Setup query engine
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=10,
            )

            response_synthesizer = get_response_synthesizer(
                response_mode=ResponseMode.COMPACT
            )

            self.query_engine = RetrieverQueryEngine(
                retriever=retriever,
                response_synthesizer=response_synthesizer,
                node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=0.5)],
            )

            # Persist empty index - this creates storage files
            try:
                self.index.storage_context.persist(persist_dir=str(storage_dir))
            except AttributeError as e:
                # Handle version compatibility issues
                log_event(
                    "empty_index_persist_fallback",
                    {
                        "error": str(e),
                        "action": "creating_manual_files",
                    },
                    level=logging.WARNING,
                )
                (storage_dir / "docstore.json").write_text("{}")
                (storage_dir / "index_store.json").write_text(
                    '{"index_store/data": {}}'
                )

            # Check what files were created
            created_files = []
            total_size = 0
            if storage_dir.exists():
                for file_path in storage_dir.rglob("*"):
                    if file_path.is_file():
                        file_size = file_path.stat().st_size
                        total_size += file_size
                        created_files.append(f"{file_path.name}")

            log_event(
                "empty_index_initialized",
                {
                    "storage_dir": str(storage_dir),
                    "files_created": len(created_files),
                    "total_size_bytes": total_size,
                    "file_names": created_files,
                },
            )

        except Exception as e:
            log_event(
                "empty_index_init_failed",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            raise
