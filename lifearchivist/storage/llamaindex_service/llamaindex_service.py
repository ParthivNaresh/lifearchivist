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
from lifearchivist.utils.logging import log_context, log_method
from lifearchivist.utils.logging.structured import MetricsCollector

from .llamaindex_service_utils import (
    DocumentFilter,
    NodeProcessor,
    calculate_document_metrics,
    create_error_response,
)

logger = logging.getLogger(__name__)


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

    @log_method(
        operation_name="llama_index_setup", include_args=True, include_result=True
    )
    def _setup_llamaindex(self):
        """Configure LlamaIndex with local models and services."""

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
        except Exception as e:
            raise e

    @log_method(
        operation_name="query_engine_setup", include_args=True, include_result=True
    )
    def _setup_query_engine(self):
        """Setup the query engine with retriever and response synthesizer."""
        if not self.index:
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

    @log_method(
        operation_name="document_addition", include_args=True, include_result=True
    )
    async def add_document(
        self,
        document_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a document to the LlamaIndex."""
        with log_context(
            operation="document_addition",
            document_id=document_id,
            content_length=len(content),
            metadata_keys=list(metadata.keys()) if metadata else [],
        ):

            metrics = MetricsCollector("document_addition")
            metrics.start()

            metrics.add_metric("document_id", document_id)
            metrics.add_metric("content_length", len(content))
            metrics.add_metric("metadata_count", len(metadata) if metadata else 0)

            if not self.index:
                metrics.set_error(RuntimeError("Index not initialized"))
                metrics.report("document_addition_failed")
                return False

            # Create LlamaIndex document
            doc_metadata = metadata or {}
            doc_metadata["document_id"] = document_id

            document = Document(
                text=content,
                metadata=doc_metadata,
                id_=document_id,
            )

            # Add to index
            self.index.insert(document)
            metrics.add_metric("document_inserted", True)

            # Persist the index (handle version compatibility)
            await self._persist_index()
            metrics.add_metric("index_persisted", True)

            metrics.set_success(True)
            metrics.report("document_addition_completed")
            return True

    @log_method(
        operation_name="metadata_update", include_args=True, include_result=True
    )
    async def update_document_metadata(
        self,
        document_id: str,
        metadata_updates: Dict[str, Any],
        merge_mode: str = "update",
    ) -> bool:
        """Update metadata for an existing document by updating all its nodes."""
        with log_context(
            operation="metadata_update",
            document_id=document_id,
            merge_mode=merge_mode,
            update_keys=list(metadata_updates.keys()),
        ):

            metrics = MetricsCollector("metadata_update")
            metrics.start()

            metrics.add_metric("document_id", document_id)
            metrics.add_metric("merge_mode", merge_mode)
            metrics.add_metric("update_keys_count", len(metadata_updates))

            if not self.index:
                metrics.set_error(RuntimeError("Index not initialized"))
                metrics.report("metadata_update_failed")
                return False

            # Get the nodes associated with this document using ref_doc_info
            ref_doc_info = self.index.ref_doc_info.get(document_id)
            if not ref_doc_info:
                metrics.set_error(KeyError("Document not found"))
                metrics.report("metadata_update_failed")
                return False

            node_ids = ref_doc_info.node_ids
            metrics.add_metric("nodes_to_update", len(node_ids))

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

                except Exception:
                    failed_nodes += 1
                    continue

            metrics.add_metric("updated_nodes", updated_nodes)
            metrics.add_metric("failed_nodes", failed_nodes)

            if updated_nodes == 0:
                metrics.set_error(RuntimeError("No nodes updated"))
                metrics.report("metadata_update_failed")
                return False

            # Persist changes
            await self._persist_index()
            metrics.add_metric("index_persisted", True)

            metrics.set_success(True)
            metrics.report("metadata_update_completed")
            return True

    @log_method(
        operation_name="metadata_query",
        include_args=True,
        include_result=True,
        indent=1,
    )
    async def query_documents_by_metadata(
        self, filters: Dict[str, Any], limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query documents based on metadata filters by checking their nodes."""
        try:
            if not self.index:
                logger.error("❌ Index not initialized")
                return []

            docstore = self.index.storage_context.docstore
            matching_documents = []

            # Get all documents using ref_doc_info (the correct way)
            ref_doc_info = self.index.ref_doc_info
            all_document_ids = list(ref_doc_info.keys())

            for document_id in all_document_ids:
                try:
                    # Get the nodes for this document
                    doc_ref_info = ref_doc_info[document_id]
                    node_ids = doc_ref_info.node_ids

                    if not node_ids:
                        logger.error(f"❌ No nodes found for document {document_id}")
                        continue

                    # Get the first node to check metadata (all nodes from same doc should have similar metadata)
                    first_node = docstore.get_node(node_ids[0])
                    if not first_node or not hasattr(first_node, "metadata"):
                        logger.error(
                            f"❌ First node for document {document_id} has no metadata"
                        )
                        continue

                    metadata = first_node.metadata or {}

                    # Check if document matches all filters
                    if DocumentFilter.matches_filters(metadata, filters):
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
                    logger.error(f"❌ Error checking document {document_id}: {e}")
                    continue  # Don't raise, just continue to next document

            paginated_results = matching_documents[offset : offset + limit]
            return paginated_results

        except Exception as e:
            logger.error(f"❌ Failed to query documents by metadata: {e}")
            raise ValueError(e) from None

    @log_method(operation_name="index_persistence", include_result=True, indent=1)
    async def _persist_index(self):
        """Persist the index with version compatibility handling."""
        storage_dir = self.settings.lifearch_home / "llamaindex_storage"
        try:
            if self.index:
                self.index.storage_context.persist(persist_dir=str(storage_dir))
        except AttributeError as persist_error:
            raise persist_error
            # Index changes are still in memory, just persist failed

    @log_method(
        operation_name="llamaindex_query", include_args=True, include_result=True
    )
    async def query(
        self,
        question: str,
        similarity_top_k: int = 5,
        response_mode: str = "tree_summarize",
    ) -> Dict[str, Any]:
        """Query the index and return structured response."""
        with log_context(
            operation="llamaindex_query",
            question_length=len(question),
            similarity_top_k=similarity_top_k,
            response_mode=response_mode,
        ):

            metrics = MetricsCollector("llamaindex_query")
            metrics.start()

            metrics.add_metric("question_length", len(question))
            metrics.add_metric("similarity_top_k", similarity_top_k)
            metrics.add_metric("response_mode", response_mode)

            if not self.query_engine:
                metrics.set_error(RuntimeError("Query engine not initialized"))
                metrics.report("query_failed")
                return self._empty_response("Query engine not available")
            # Execute query with timeout to prevent hanging
            try:
                response: Response = await asyncio.wait_for(
                    asyncio.to_thread(self.query_engine.query, question), timeout=30.0
                )
                metrics.add_metric("query_completed_within_timeout", True)

            except asyncio.TimeoutError:
                metrics.set_error(asyncio.TimeoutError("Query timeout"))
                metrics.report("query_failed")
                return self._empty_response("Query timed out due to memory constraints")

            except AttributeError as attr_error:
                if "usage" in str(attr_error):
                    metrics.set_error(attr_error)
                    metrics.report("query_failed")
                    raise attr_error
                else:
                    raise attr_error

            # Extract source information
            sources = []
            if hasattr(response, "source_nodes"):
                for node in response.source_nodes:
                    source_info = NodeProcessor.extract_source_info(node)
                    if source_info:
                        sources.append(source_info)

            metrics.add_metric("sources_found", len(sources))
            metrics.add_metric(
                "response_length",
                len(str(response.response)) if response.response else 0,
            )
            metrics.set_success(True)
            metrics.report("query_completed")
            return {
                "answer": str(response.response) if response.response else "",
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

    @log_method(
        operation_name="document_retrieval", include_args=True, include_result=True
    )
    async def retrieve_similar(
        self, query: str, top_k: int = 10, similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Retrieve similar documents without generating a response."""
        try:
            if not self.index:
                return []

            retriever = VectorIndexRetriever(index=self.index, similarity_top_k=top_k)

            # Retrieve nodes
            nodes = retriever.retrieve(query)

            # Filter by similarity threshold and format
            results = []
            for node in nodes:
                if node.score and node.score >= similarity_threshold:
                    source_info = NodeProcessor.extract_source_info(node)
                    if source_info:
                        results.append(source_info)

            return results

        except Exception as e:
            logger.error(f"❌ Retrieval failed: {e}")
            return []

    @log_method(
        operation_name="document_analysis", include_args=True, include_result=True
    )
    async def get_document_analysis(self, document_id: str) -> Dict[str, Any]:
        """Get comprehensive analysis of a document in the LlamaIndex."""
        try:
            if not self.index:
                logger.error("❌ Index not initialized in get_document_analysis")
                return {"error": "Index not initialized"}

            # Get all nodes for this document using ref_doc_info
            nodes = NodeProcessor.get_document_nodes_from_ref_doc_info(
                self.index, document_id
            )

            if not nodes:
                logger.error("❌ No nodes in get_document_analysis")
                return create_error_response(
                    f"Document {document_id} not found in LlamaIndex"
                )

            # Calculate metrics
            metrics = calculate_document_metrics(nodes)

            # Get embedding stats
            embedding_stats = self._get_embedding_stats()

            # Use first node's metadata (all nodes inherit document metadata)
            original_metadata = nodes[0].get("metadata", {}) if nodes else {}

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
            logger.error(f"❌ Failed to analyze document {document_id}: {e}")
            return create_error_response(str(e))

    @log_method(
        operation_name="document_chunks_retrieval",
        include_args=True,
        include_result=True,
    )
    async def get_document_chunks(
        self, document_id: str, limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        """Get all chunks for a specific document with pagination."""
        try:
            if not self.index:
                return {"error": "Index not initialized", "chunks": [], "total": 0}

            # Get all nodes for this document
            all_nodes = NodeProcessor.get_document_nodes_from_ref_doc_info(
                self.index, document_id
            )

            if not all_nodes:
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
            for i, node_data in enumerate(paginated_nodes):
                chunk_info = {
                    "chunk_index": offset + i,
                    "node_id": node_data.get("node_id"),
                    "text": node_data.get("text", ""),
                    "text_length": len(node_data.get("text", "")),
                    "word_count": len(node_data.get("text", "").split()),
                    "start_char": node_data.get("start_char"),
                    "end_char": node_data.get("end_char"),
                    "metadata": node_data.get("metadata", {}),
                    "relationships": node_data.get("relationships", {}),
                }
                enriched_chunks.append(chunk_info)

            return {
                "document_id": document_id,
                "chunks": enriched_chunks,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
            }

        except Exception as e:
            logger.error(f"❌ Failed to get chunks for document {document_id}: {e}")
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
            logger.error(f"❌ Failed to find neighbors for document {document_id}: {e}")
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
        except Exception as e:
            logger.error(f"Failed to get embedding stats: {e}")
            return {"model": "unknown", "dimension": None}

    @log_method(operation_name="data_cleanup", include_result=True)
    async def clear_all_data(self) -> Dict[str, Any]:
        """Clear all LlamaIndex data and storage."""
        storage_dir = self.settings.lifearch_home / "llamaindex_storage"
        cleared_metrics = {
            "storage_files_deleted": 0,
            "storage_bytes_reclaimed": 0,
            "index_reset": False,
            "errors": [],
        }

        try:
            # Clear in-memory index
            self.index = None
            self.query_engine = None
            cleared_metrics["index_reset"] = True
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
            else:
                raise Exception("Storage directory doesn't exist")

            # Reinitialize empty structures
            await self._initialize_empty_index()

            return cleared_metrics

        except Exception as e:
            error_msg = f"❌ LlamaIndex clearing failed: {e}"
            if isinstance(cleared_metrics["errors"], list):
                cleared_metrics["errors"].append(error_msg)
            return cleared_metrics

    async def _initialize_empty_index(self):
        """Initialize a fresh empty LlamaIndex."""
        try:
            storage_dir = self.settings.lifearch_home / "llamaindex_storage"
            storage_dir.mkdir(exist_ok=True)

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
            except AttributeError:
                # Handle version compatibility issues
                (storage_dir / "docstore.json").write_text("{}")
                (storage_dir / "index_store.json").write_text(
                    '{"index_store/data": {}}'
                )

            # Check what files were created
            created_files = []
            if storage_dir.exists():
                for file_path in storage_dir.rglob("*"):
                    if file_path.is_file():
                        created_files.append(
                            f"{file_path.name} ({file_path.stat().st_size} bytes)"
                        )

        except Exception:
            raise
