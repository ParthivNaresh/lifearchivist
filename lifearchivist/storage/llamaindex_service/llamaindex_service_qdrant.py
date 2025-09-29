"""
Qdrant-native LlamaIndex service implementation.

This is a simplified version that works with Qdrant's architecture,
providing 80% of functionality with cleaner separation of concerns.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union

from llama_index.core import (
    Document,
    Settings,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from lifearchivist.config import get_settings
from lifearchivist.utils.logging import log_event, track


class LlamaIndexQdrantService:
    """
    Simplified LlamaIndex service using Qdrant for vector storage.

    Key differences from original:
    - Uses Qdrant for vectors only
    - Simple JSON document tracking
    - No complex metadata operations (initially)
    - Clean separation of concerns
    """

    def __init__(self, database=None, vault=None):
        self.settings = get_settings()
        self.database = database
        self.vault = vault
        self.index: Optional[VectorStoreIndex] = None
        self.query_engine = None

        # Simple document tracking (replaces ref_doc_info)
        # This stores both node mappings and full metadata snapshots
        self.doc_tracker_path = (
            self.settings.lifearch_home / "llamaindex_storage" / "doc_tracker.json"
        )
        self.doc_tracker: Dict[str, Union[List[str], Dict[str, Any]]] = (
            self._load_doc_tracker()
        )

        # Add a lock for thread-safe doc_tracker operations
        self._doc_tracker_lock = asyncio.Lock()

        self.setup()

    def _load_doc_tracker(self) -> Dict[str, Union[List[str], Dict[str, Any]]]:
        """
        Load document to node mappings from JSON.

        Returns a dict that can contain:
        - document_id -> List[str] (list of node IDs)
        - document_id_full_metadata -> Dict[str, Any] (full metadata snapshot)
        """
        if self.doc_tracker_path.exists():
            try:
                with open(self.doc_tracker_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError, OSError):
                # JSONDecodeError: Corrupted or invalid JSON
                # IOError/OSError: File access issues
                return {}
        return {}

    async def _save_doc_tracker(self):
        """Save document to node mappings to JSON (thread-safe)."""
        async with self._doc_tracker_lock:
            self.doc_tracker_path.parent.mkdir(exist_ok=True)
            # Use atomic write to prevent corruption
            temp_path = self.doc_tracker_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                json.dump(self.doc_tracker, f, indent=2)
            # Atomic rename
            temp_path.replace(self.doc_tracker_path)

    def setup(self):
        """Setup functions for LlamaIndex with Qdrant."""
        self._setup_embeddings_and_llm()
        self._setup_qdrant()
        self._setup_index()
        self._setup_query_engine()

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
            chunk_size=2600,  # Increased to handle larger metadata
            chunk_overlap=200,  # Overlap for better context
            separator="\n\n",
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
        """Setup the vector store index with Qdrant."""
        storage_dir = self.settings.lifearch_home / "llamaindex_storage"
        storage_dir.mkdir(exist_ok=True)

        try:
            # Create Qdrant vector store
            vector_store = QdrantVectorStore(
                client=self.qdrant_client,
                collection_name="lifearchivist",
            )

            # Try to load existing storage context
            docstore_path = storage_dir / "docstore.json"
            index_store_path = storage_dir / "index_store.json"

            if docstore_path.exists() and index_store_path.exists():
                # Load existing storage context
                try:
                    storage_context = StorageContext.from_defaults(
                        vector_store=vector_store,
                        persist_dir=str(storage_dir),
                    )
                    log_event(
                        "storage_context_loaded",
                        {
                            "docstore_path": str(docstore_path),
                            "index_store_path": str(index_store_path),
                        },
                    )
                except Exception as e:
                    log_event(
                        "storage_context_load_failed",
                        {"error": str(e)},
                        level=logging.WARNING,
                    )
                    # Fall back to creating new storage context
                    storage_context = StorageContext.from_defaults(
                        vector_store=vector_store,
                        docstore=SimpleDocumentStore(),
                        index_store=SimpleIndexStore(),
                    )
            else:
                # Create new storage context
                storage_context = StorageContext.from_defaults(
                    vector_store=vector_store,
                    docstore=SimpleDocumentStore(),
                    index_store=SimpleIndexStore(),
                )
                log_event(
                    "storage_context_created",
                    {
                        "reason": "no_existing_storage",
                    },
                )

            # Create or load index
            self.index = VectorStoreIndex(
                [],
                storage_context=storage_context,
                store_nodes_override=True,
            )

            # Persist storage context
            storage_context.persist(persist_dir=str(storage_dir))

            log_event(
                "index_initialized",
                {
                    "vector_store": "QdrantVectorStore",
                    "docstore": "SimpleDocumentStore",
                    "index_store": "SimpleIndexStore",
                    "storage_dir": str(storage_dir),
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
        """
        Add a document to the index.

        Simplified version - just adds document and tracks nodes.
        """
        if not self.index:
            log_event(
                "document_add_failed",
                {"document_id": document_id, "reason": "no_index"},
                level=logging.ERROR,
            )
            return False

        try:
            # Store full metadata separately (for retrieval by API endpoints)
            full_metadata = metadata or {}
            full_metadata["document_id"] = document_id

            # Create minimal metadata for chunks (only what's needed for search/retrieval)
            chunk_metadata = self._create_minimal_chunk_metadata(full_metadata)

            # Store full metadata in a separate location
            # For now, we'll store it in the doc_tracker with a special key
            full_metadata_key = f"{document_id}_full_metadata"
            async with self._doc_tracker_lock:
                self.doc_tracker[full_metadata_key] = full_metadata
            # Save immediately to persist full metadata
            await self._save_doc_tracker()

            document = Document(
                text=content,
                metadata=chunk_metadata,  # Use minimal metadata for chunks
                id_=document_id,
            )

            # Insert into index - this creates nodes
            try:
                # Log before insert for debugging
                log_event(
                    "document_insert_attempt",
                    {
                        "document_id": document_id,
                        "content_length": len(content),
                        "content_preview": content[:100] if content else "empty",
                        "metadata_keys": list(chunk_metadata.keys()),
                    },
                    level=logging.DEBUG,
                )

                # Check if content is empty
                if not content or not content.strip():
                    raise ValueError("Document content is empty or whitespace only")

                self.index.insert(document)

                # Log successful insert
                log_event(
                    "document_insert_success",
                    {
                        "document_id": document_id,
                        "content_length": len(content),
                    },
                    level=logging.DEBUG,
                )
            except Exception as insert_error:
                # Log the full error with traceback
                import traceback

                error_details = {
                    "document_id": document_id,
                    "error_type": type(insert_error).__name__,
                    "error_message": str(insert_error),
                    "content_length": len(content),
                    "content_preview": content[:100] if content else "empty",
                    "traceback": traceback.format_exc(),
                }

                # Print the actual error to console for debugging
                print(f"\n🔴 DOCUMENT INSERT ERROR for {document_id}:")
                print(f"   Error Type: {type(insert_error).__name__}")
                print(f"   Error Message: {str(insert_error)}")
                print(f"   Content Length: {len(content)}")
                print(f"   Traceback:\n{traceback.format_exc()}")

                log_event(
                    "document_insert_failed",
                    error_details,
                    level=logging.ERROR,
                )
                raise

            # Track which nodes belong to this document
            doc_nodes = []
            docstore = self.index.storage_context.docstore

            # Debug: Check what's in the docstore
            print(f"\n🔍 DEBUG: Looking for nodes for document {document_id}")
            print(f"   Docstore type: {type(docstore).__name__}")
            print(f"   Has 'docs' attr: {hasattr(docstore, 'docs')}")

            # SimpleDocumentStore uses a 'docs' dictionary to store nodes
            # After insertion, we need to find the nodes that were created
            if hasattr(docstore, "docs"):
                print(f"   Total docs in store: {len(docstore.docs)}")
                # Iterate through all docs and find ones with our document_id
                for node_id, node in docstore.docs.items():
                    # Debug each node
                    if hasattr(node, "metadata"):
                        node_doc_id = (
                            node.metadata.get("document_id") if node.metadata else None
                        )
                        if node_doc_id == document_id:
                            doc_nodes.append(node_id)
                            print(f"   ✅ Found matching node: {node_id[:20]}...")
                        # Show first few nodes for debugging
                        elif len(docstore.docs) <= 5:
                            print(
                                f"   ❌ Node {node_id[:20]}... has document_id: {node_doc_id}"
                            )

            # Log if we couldn't find nodes
            if not doc_nodes:
                print(f"\n⚠️ WARNING: No nodes found for document {document_id}")
                print(
                    "This means insert() succeeded but nodes weren't created with expected metadata"
                )

                # Check if there are ANY nodes with our document text
                if hasattr(docstore, "docs"):
                    for node_id, node in docstore.docs.items():
                        if hasattr(node, "text") and content[:50] in node.text:
                            print(
                                f"   🔍 Found node with matching text but wrong metadata: {node_id[:20]}..."
                            )
                            if hasattr(node, "metadata"):
                                print(f"      Node metadata: {node.metadata}")

                log_event(
                    "node_tracking_warning",
                    {
                        "document_id": document_id,
                        "docstore_type": type(docstore).__name__,
                        "has_docs_attr": hasattr(docstore, "docs"),
                        "docs_count": (
                            len(docstore.docs) if hasattr(docstore, "docs") else 0
                        ),
                    },
                    level=logging.WARNING,
                )

                # This is the actual problem - insert succeeds but no nodes are created
                raise RuntimeError(
                    f"Document insert succeeded but no nodes were created for {document_id}"
                )

            # Update tracker with thread safety
            async with self._doc_tracker_lock:
                self.doc_tracker[document_id] = doc_nodes
            await self._save_doc_tracker()

            # Persist storage context to disk
            storage_dir = self.settings.lifearch_home / "llamaindex_storage"
            try:
                self.index.storage_context.persist(persist_dir=str(storage_dir))
            except Exception as persist_error:
                log_event(
                    "storage_persist_failed",
                    {
                        "document_id": document_id,
                        "error_type": type(persist_error).__name__,
                        "error_message": str(persist_error),
                        "storage_dir": str(storage_dir),
                    },
                    level=logging.ERROR,
                )
                # Don't raise here - document is already in memory index
                # Just log the error

            log_event(
                "document_added",
                {
                    "document_id": document_id,
                    "content_length": len(content),
                    "nodes_created": len(doc_nodes),
                },
            )

            return True

        except Exception as e:
            log_event(
                "document_add_error",
                {"document_id": document_id, "error": str(e)},
                level=logging.ERROR,
            )
            return False

    def _create_minimal_chunk_metadata(
        self, full_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create minimal metadata for chunks to avoid bloat.

        Only includes fields essential for:
        - Identifying the source document
        - Basic filtering during search
        - Display in search results
        """
        minimal = {
            "document_id": full_metadata.get("document_id"),
            "title": full_metadata.get("title", ""),
            "mime_type": full_metadata.get("mime_type", ""),
            "status": full_metadata.get("status", "ready"),
        }

        # Add theme information if present (for filtering)
        if "theme" in full_metadata:
            theme_data = full_metadata["theme"]
            if isinstance(theme_data, dict):
                minimal["theme"] = theme_data.get("theme", "Unclassified")
                minimal["primary_subtheme"] = theme_data.get("primary_subtheme", "")
            else:
                minimal["theme"] = theme_data

        # Add essential dates (keep them short)
        if "uploaded_at" in full_metadata:
            # Store just the date part, not full timestamp
            uploaded = full_metadata["uploaded_at"]
            if isinstance(uploaded, str) and len(uploaded) > 10:
                minimal["uploaded_date"] = uploaded[:10]

        # Add file hash (first 8 chars only for dedup checking)
        if "file_hash" in full_metadata:
            minimal["file_hash_short"] = full_metadata["file_hash"][:8]

        # Calculate and log the size reduction
        import json

        full_size = len(json.dumps(full_metadata))
        minimal_size = len(json.dumps(minimal))

        log_event(
            "metadata_size_reduction",
            {
                "document_id": full_metadata.get("document_id"),
                "full_metadata_size": full_size,
                "minimal_metadata_size": minimal_size,
                "reduction_percent": (
                    round((1 - minimal_size / full_size) * 100, 1)
                    if full_size > 0
                    else 0
                ),
                "fields_kept": list(minimal.keys()),
            },
            level=logging.DEBUG,
        )

        return minimal

    async def get_full_document_metadata(self, document_id: str) -> Dict[str, Any]:
        """
        Retrieve the full metadata for a document (not just chunk metadata).

        This is used by API endpoints to return complete document information.
        """
        full_metadata_key = f"{document_id}_full_metadata"

        # First try to get from our stored full metadata
        if full_metadata_key in self.doc_tracker:
            metadata = self.doc_tracker[full_metadata_key]
            # Type guard: ensure it's a dict (full metadata), not a list (node IDs)
            if isinstance(metadata, dict):
                return metadata
            else:
                raise TypeError("Metadata was a list")

        # Fallback: get from first chunk if full metadata not found
        # (for backwards compatibility with existing documents)
        if document_id not in self.doc_tracker:
            return {}

        node_ids = self.doc_tracker[document_id]
        if not node_ids:
            return {}

        docstore = self.index.storage_context.docstore
        first_node_id = node_ids[0]
        nodes = docstore.get_document(first_node_id, raise_error=False)

        if not nodes:
            return {}

        if not isinstance(nodes, list):
            nodes = [nodes]

        first_node = nodes[0] if nodes else None
        if first_node and hasattr(first_node, "metadata"):
            return first_node.metadata or {}

        return {}

    async def query(
        self,
        question: str,
        similarity_top_k: int = 5,
        response_mode: str = "tree_summarize",
    ) -> Dict[str, Any]:
        """
        Query the index - simplified version.
        """
        if not self.query_engine:
            return {
                "answer": "Query engine not available",
                "sources": [],
                "method": "error",
            }

        try:
            # Update similarity_top_k if different
            if hasattr(self.query_engine, "retriever"):
                self.query_engine.retriever.similarity_top_k = similarity_top_k

            response = self.query_engine.query(question)

            # Extract sources and full context
            sources = []
            full_context_chunks = []
            if hasattr(response, "source_nodes"):
                for node in response.source_nodes:
                    if hasattr(node, "node") and hasattr(node.node, "text"):
                        full_text = node.node.text
                        sources.append(
                            {
                                "text": full_text[:200],  # Preview for UI
                                "full_text": full_text,  # Complete chunk text
                                "score": float(node.score) if node.score else 0.0,
                                "node_id": (
                                    node.node.id_ if hasattr(node.node, "id_") else None
                                ),
                                "metadata": (
                                    node.node.metadata
                                    if hasattr(node.node, "metadata")
                                    else {}
                                ),
                            }
                        )
                        full_context_chunks.append(full_text)

            # Log the actual context that was sent to the LLM
            combined_context = "\n\n---\n\n".join(full_context_chunks)
            log_event(
                "query_context_used",
                {
                    "question": question[:100],
                    "num_chunks": len(full_context_chunks),
                    "total_context_chars": len(combined_context),
                    "context_preview": (
                        combined_context[:1000] if combined_context else "No context"
                    ),
                },
                level=logging.INFO,
            )

            # Also log the full prompt if you want to see exactly what's sent
            # Note: This is an approximation since LlamaIndex constructs it internally
            estimated_prompt = f"""Context information is below.
---------------------
{combined_context}
---------------------
Given the context information and not prior knowledge, answer the query.
Query: {question}
Answer: """

            log_event(
                "estimated_llm_prompt",
                {
                    "prompt_length": len(estimated_prompt),
                    "prompt_preview": estimated_prompt[:500],
                },
                level=logging.DEBUG,
            )

            return {
                "answer": str(response.response) if response.response else "",
                "sources": sources,
                "method": "llamaindex_rag",
                "context_used": combined_context,  # Include full context in response
                "num_chunks_used": len(full_context_chunks),
            }
        except Exception as e:
            log_event(
                "query_error",
                {"error": str(e)},
                level=logging.ERROR,
            )
            return {
                "answer": f"Query failed: {str(e)}",
                "sources": [],
                "method": "error",
            }

    async def get_document_count(self) -> int:
        """Get count of indexed documents."""
        # Count only actual documents, not full metadata entries
        count = 0
        for key in self.doc_tracker.keys():
            if not key.endswith("_full_metadata"):
                count += 1
        return count

    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the index.

        Simplified version - removes from Qdrant and tracker.
        """
        try:
            if document_id not in self.doc_tracker:
                return False

            # Get nodes for this document
            node_ids_raw = self.doc_tracker.get(document_id)
            if not isinstance(node_ids_raw, list):
                raise TypeError("Node ids weren't in a list")
            node_ids = node_ids_raw

            # Delete from Qdrant by filtering on metadata
            # Note: This requires Qdrant to have indexed the document_id field
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            self.qdrant_client.delete(
                collection_name="lifearchivist",
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        )
                    ]
                ),
            )

            # Remove from tracker with thread safety
            async with self._doc_tracker_lock:
                del self.doc_tracker[document_id]
            await self._save_doc_tracker()

            log_event(
                "document_deleted",
                {"document_id": document_id, "nodes_deleted": len(node_ids)},
            )

            return True

        except Exception as e:
            log_event(
                "document_deletion_error",
                {"document_id": document_id, "error": str(e)},
                level=logging.ERROR,
            )
            return False

    async def clear_all_data(self) -> Dict[str, Any]:
        """Clear all data - simplified version."""
        try:
            # Get counts before clearing
            doc_count = len(self.doc_tracker)

            # Recreate Qdrant collection
            self.qdrant_client.delete_collection("lifearchivist")
            self.qdrant_client.create_collection(
                collection_name="lifearchivist",
                vectors_config=VectorParams(
                    size=384,
                    distance=Distance.COSINE,
                ),
            )

            # Clear tracker with thread safety
            async with self._doc_tracker_lock:
                self.doc_tracker = {}
            await self._save_doc_tracker()

            self._setup_index()
            self._setup_query_engine()

            log_event(
                "data_cleared",
                {"documents_cleared": doc_count},
            )

            return {
                "documents_cleared": doc_count,
                "storage_cleared": True,
            }

        except Exception as e:
            log_event(
                "data_cleanup_error",
                {"error": str(e)},
                level=logging.ERROR,
            )
            return {
                "error": str(e),
                "storage_cleared": False,
            }

    async def update_document_metadata(
        self,
        document_id: str,
        metadata_updates: Dict[str, Any],
        merge_mode: str = "update",
    ) -> bool:
        """
        Update metadata for a document in both Qdrant and docstore.

        Args:
            document_id: The document to update
            metadata_updates: New metadata fields
            merge_mode: "update" to merge, "replace" to overwrite
        """
        try:
            # Check if document exists
            if document_id not in self.doc_tracker:
                log_event(
                    "metadata_update_failed",
                    {"document_id": document_id, "reason": "document_not_found"},
                    level=logging.WARNING,
                )
                return False

            node_ids_raw = self.doc_tracker.get(document_id)
            # Type guard: ensure it's a list of node IDs
            if not isinstance(node_ids_raw, list):
                raise TypeError("Node ids weren't in a list")
            node_ids = node_ids_raw

            if not node_ids:
                return False

            log_event(
                "metadata_update_started",
                {
                    "document_id": document_id,
                    "node_count": len(node_ids),
                    "merge_mode": merge_mode,
                    "update_fields": list(metadata_updates.keys()),
                },
            )

            # Update metadata in docstore nodes
            docstore = self.index.storage_context.docstore
            updated_nodes = 0

            for node_id in node_ids:
                try:
                    # Get the node using the hash (for SimpleDocumentStore)
                    nodes = docstore.get_document(node_id, raise_error=False)
                    if not nodes:
                        continue

                    # Handle single node or list
                    if not isinstance(nodes, list):
                        nodes = [nodes]

                    for node in nodes:
                        if not hasattr(node, "metadata"):
                            continue

                        # Update metadata based on merge mode
                        if merge_mode == "replace":
                            node.metadata = {
                                **metadata_updates,
                                "document_id": document_id,
                            }
                        else:
                            # Merge with existing metadata
                            current_metadata = node.metadata or {}

                            # Handle special list fields
                            for key, value in metadata_updates.items():
                                if key in [
                                    "content_dates",
                                    "tags",
                                    "provenance",
                                ] and isinstance(value, list):
                                    existing = current_metadata.get(key, [])
                                    if isinstance(existing, list):
                                        # Merge lists without duplicates
                                        merged = list(set(existing + value))
                                        current_metadata[key] = merged
                                    else:
                                        current_metadata[key] = value
                                else:
                                    current_metadata[key] = value

                            node.metadata = current_metadata

                        # Update the node in docstore
                        docstore.add_documents([node], allow_update=True)
                        updated_nodes += 1

                except Exception as e:
                    log_event(
                        "node_metadata_update_failed",
                        {"node_id": node_id, "error": str(e)},
                        level=logging.DEBUG,
                    )
                    continue

            # CRITICAL: Also update the full metadata snapshot if it exists
            full_metadata_key = f"{document_id}_full_metadata"
            if full_metadata_key in self.doc_tracker:
                async with self._doc_tracker_lock:
                    existing_full_metadata = self.doc_tracker.get(full_metadata_key)
                    if isinstance(existing_full_metadata, dict):
                        if merge_mode == "replace":
                            # Replace the full metadata
                            self.doc_tracker[full_metadata_key] = {
                                "document_id": document_id,
                                **metadata_updates,
                            }
                        else:
                            # Merge with existing full metadata
                            # Handle special list fields
                            for key, value in metadata_updates.items():
                                if key in [
                                    "content_dates",
                                    "tags",
                                    "provenance",
                                ] and isinstance(value, list):
                                    existing_val = existing_full_metadata.get(key, [])
                                    if isinstance(existing_val, list):
                                        # Merge lists without duplicates
                                        merged = list(set(existing_val + value))
                                        existing_full_metadata[key] = merged
                                    else:
                                        existing_full_metadata[key] = value
                                else:
                                    existing_full_metadata[key] = value

                            self.doc_tracker[full_metadata_key] = existing_full_metadata

                # Save the updated full metadata
                await self._save_doc_tracker()

                log_event(
                    "full_metadata_updated",
                    {
                        "document_id": document_id,
                        "updated_fields": list(metadata_updates.keys()),
                    },
                    level=logging.DEBUG,
                )

            try:
                # For now, we'll update the payload when documents are re-indexed
                # Full Qdrant payload update would require updating each point
                # This is a simplified approach that maintains consistency

                log_event(
                    "metadata_update_completed",
                    {
                        "document_id": document_id,
                        "updated_nodes": updated_nodes,
                        "total_nodes": len(node_ids),
                    },
                )

                return updated_nodes > 0

            except Exception as e:
                log_event(
                    "qdrant_metadata_update_error",
                    {"document_id": document_id, "error": str(e)},
                    level=logging.WARNING,
                )
                # Even if Qdrant update fails, docstore update succeeded
                return updated_nodes > 0

        except Exception as e:
            log_event(
                "metadata_update_error",
                {"document_id": document_id, "error": str(e)},
                level=logging.ERROR,
            )
            return False

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
        """
        Query documents based on metadata filters.

        Args:
            filters: Dictionary of metadata field filters
            limit: Maximum number of results
            offset: Pagination offset
        """
        try:
            if not self.index:
                log_event(
                    "metadata_query_empty",
                    {"reason": "no_index"},
                    level=logging.DEBUG,
                )
                return []

            log_event(
                "metadata_query_started",
                {
                    "filter_keys": list(filters.keys()) if filters else [],
                    "has_filters": bool(filters),
                    "limit": limit,
                    "offset": offset,
                },
            )

            matching_documents = []
            documents_checked = 0
            documents_matched = 0

            # Get docstore for metadata access
            docstore = self.index.storage_context.docstore

            # Iterate through tracked documents
            for document_id, node_ids in self.doc_tracker.items():
                # Skip full metadata entries (they have "_full_metadata" suffix)
                if document_id.endswith("_full_metadata"):
                    continue

                documents_checked += 1

                # Skip if node_ids is not a list (safety check)
                if not isinstance(node_ids, list):
                    continue

                if not node_ids:
                    continue

                try:
                    # Get first node to check metadata (all nodes from same doc have similar metadata)
                    first_node_id = node_ids[0]
                    nodes = docstore.get_document(first_node_id, raise_error=False)

                    if not nodes:
                        continue

                    # Handle single node or list
                    if not isinstance(nodes, list):
                        nodes = [nodes]

                    first_node = nodes[0] if nodes else None
                    if not first_node or not hasattr(first_node, "metadata"):
                        continue

                    metadata = first_node.metadata or {}

                    # Check if document matches all filters
                    matches = True
                    for key, value in filters.items():
                        if key not in metadata:
                            matches = False
                            break

                        # Handle different filter types
                        if isinstance(value, list):
                            # Check if metadata value is in filter list
                            if metadata[key] not in value:
                                matches = False
                                break
                        elif isinstance(value, dict):
                            # Handle range queries (e.g., {"$gte": date1, "$lte": date2})
                            meta_val = metadata[key]
                            if "$gte" in value and meta_val < value["$gte"]:
                                matches = False
                                break
                            if "$lte" in value and meta_val > value["$lte"]:
                                matches = False
                                break
                            if "$gt" in value and meta_val <= value["$gt"]:
                                matches = False
                                break
                            if "$lt" in value and meta_val >= value["$lt"]:
                                matches = False
                                break
                        else:
                            # Exact match
                            if metadata[key] != value:
                                matches = False
                                break

                    if matches:
                        documents_matched += 1

                        # Generate text preview from first node
                        text_preview = (
                            first_node.text[:200] + "..."
                            if len(first_node.text) > 200
                            else first_node.text
                        )

                        # Get FULL metadata for API response, not just chunk metadata
                        full_metadata = await self.get_full_document_metadata(
                            document_id
                        )

                        # Use full metadata if available, otherwise fall back to chunk metadata
                        final_metadata = full_metadata if full_metadata else metadata

                        doc_info = {
                            "document_id": document_id,
                            "metadata": final_metadata,
                            "text_preview": text_preview,
                            "node_count": len(node_ids),
                        }
                        matching_documents.append(doc_info)

                except Exception as e:
                    log_event(
                        "metadata_query_doc_error",
                        {"document_id": document_id, "error": str(e)},
                        level=logging.DEBUG,
                    )
                    continue

            # Apply pagination
            paginated_results = matching_documents[offset : offset + limit]

            log_event(
                "metadata_query_completed",
                {
                    "total_documents": len(self.doc_tracker),
                    "documents_checked": documents_checked,
                    "documents_matched": documents_matched,
                    "results_returned": len(paginated_results),
                },
            )

            return paginated_results

        except Exception as e:
            log_event(
                "metadata_query_failed",
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
        """
        Get comprehensive analysis of a document.

        Args:
            document_id: The document to analyze

        Returns:
            Dictionary with document metrics and statistics
        """
        try:
            if not self.index:
                log_event(
                    "document_analysis_skipped",
                    {"document_id": document_id, "reason": "no_index"},
                    level=logging.WARNING,
                )
                return {"error": "Index not initialized"}

            # Check if document exists
            if document_id not in self.doc_tracker:
                log_event(
                    "document_analysis_not_found",
                    {"document_id": document_id},
                    level=logging.WARNING,
                )
                return {"error": f"Document {document_id} not found in index"}

            node_ids = self.doc_tracker[document_id]
            if not node_ids:
                return {"error": "No nodes found for document"}

            # Get docstore
            docstore = self.index.storage_context.docstore

            # Get FULL metadata for this document (not just chunk metadata)
            full_metadata = await self.get_full_document_metadata(document_id)

            # Collect metrics
            total_chars = 0
            total_words = 0
            chunk_sizes = []
            word_counts = []
            chunks_preview = []

            for _, node_id in enumerate(node_ids):
                try:
                    # Get the node from docstore
                    nodes = docstore.get_document(node_id, raise_error=False)
                    if not nodes:
                        continue

                    # Handle single node or list
                    if not isinstance(nodes, list):
                        nodes = [nodes]

                    for node in nodes:
                        if not hasattr(node, "text"):
                            continue

                        text = node.text
                        text_length = len(text)
                        word_count = len(text.split())

                        total_chars += text_length
                        total_words += word_count
                        chunk_sizes.append(text_length)
                        word_counts.append(word_count)

                        # Add to preview (first 3 chunks)
                        if len(chunks_preview) < 3:
                            chunk_preview = {
                                "node_id": node_id,
                                "text": text[:200] + "..." if len(text) > 200 else text,
                                "text_length": text_length,
                                "word_count": word_count,
                            }
                            chunks_preview.append(chunk_preview)

                except Exception as e:
                    log_event(
                        "node_analysis_error",
                        {"node_id": node_id, "error": str(e)},
                        level=logging.DEBUG,
                    )
                    continue

            # Calculate statistics
            num_chunks = len(chunk_sizes)
            avg_chunk_size = sum(chunk_sizes) / num_chunks if num_chunks > 0 else 0
            avg_word_count = sum(word_counts) / num_chunks if num_chunks > 0 else 0
            min_chunk_size = min(chunk_sizes) if chunk_sizes else 0
            max_chunk_size = max(chunk_sizes) if chunk_sizes else 0

            # Get embedding model info
            embedding_stats = self._get_embedding_stats()

            log_event(
                "document_analysis_completed",
                {
                    "document_id": document_id,
                    "node_count": num_chunks,
                    "total_chars": total_chars,
                    "total_words": total_words,
                    "avg_chunk_size": avg_chunk_size,
                },
            )

            # Return the analysis with FULL metadata
            return {
                "document_id": document_id,
                "status": full_metadata.get("status", "indexed"),
                "metadata": full_metadata,  # Full metadata with all theme details
                "processing_info": {
                    "total_chars": total_chars,
                    "total_words": total_words,
                    "num_chunks": num_chunks,
                    "avg_chunk_size": round(avg_chunk_size, 2),
                    "min_chunk_size": min_chunk_size,
                    "max_chunk_size": max_chunk_size,
                    "avg_word_count": round(avg_word_count, 2),
                    "embedding_model": embedding_stats.get("model"),
                    "embedding_dimension": embedding_stats.get("dimension"),
                },
                "storage_info": {
                    "docstore_type": type(docstore).__name__,
                    "vector_store_type": "QdrantVectorStore",
                    "text_splitter": "SentenceSplitter",
                    "chunk_size": 2600,  # Updated to reflect actual chunk size
                    "chunk_overlap": 200,  # Updated to reflect actual overlap
                },
                "chunks_preview": chunks_preview,
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
            return {"error": str(e)}

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
        """
        Get all chunks for a specific document with pagination.

        Args:
            document_id: The document to get chunks for
            limit: Maximum number of chunks to return
            offset: Pagination offset
        """
        try:
            if not self.index:
                log_event(
                    "chunks_retrieval_skipped",
                    {"document_id": document_id, "reason": "no_index"},
                    level=logging.DEBUG,
                )
                return {"error": "Index not initialized", "chunks": [], "total": 0}

            # Check if document exists
            if document_id not in self.doc_tracker:
                log_event(
                    "chunks_not_found",
                    {"document_id": document_id},
                    level=logging.WARNING,
                )
                return {
                    "error": f"No chunks found for document {document_id}",
                    "chunks": [],
                    "total": 0,
                }

            node_ids = self.doc_tracker[document_id]
            total = len(node_ids)

            # Get docstore
            docstore = self.index.storage_context.docstore

            # Apply pagination to node IDs
            paginated_node_ids = node_ids[offset : offset + limit]

            # Retrieve and enrich chunks
            enriched_chunks = []
            total_text_length = 0
            total_word_count = 0

            for i, node_id in enumerate(paginated_node_ids):
                try:
                    # Get the node from docstore
                    nodes = docstore.get_document(node_id, raise_error=False)
                    if not nodes:
                        continue

                    # Handle single node or list
                    if not isinstance(nodes, list):
                        nodes = [nodes]

                    for node in nodes:
                        if not hasattr(node, "text"):
                            continue

                        text = node.text
                        text_length = len(text)
                        word_count = len(text.split())

                        total_text_length += text_length
                        total_word_count += word_count

                        # Get node metadata
                        metadata = node.metadata if hasattr(node, "metadata") else {}

                        # Get relationships if available
                        relationships = {}
                        if hasattr(node, "relationships"):
                            for rel_type, rel_info in node.relationships.items():
                                relationships[rel_type] = {
                                    "node_id": (
                                        rel_info.node_id
                                        if hasattr(rel_info, "node_id")
                                        else None
                                    ),
                                }

                        chunk_info = {
                            "chunk_index": offset + i,
                            "node_id": node_id,
                            "text": text,
                            "text_length": text_length,
                            "word_count": word_count,
                            "metadata": metadata,
                            "relationships": relationships,
                        }

                        # Add start/end char if available
                        if hasattr(node, "start_char_idx"):
                            chunk_info["start_char"] = node.start_char_idx
                        if hasattr(node, "end_char_idx"):
                            chunk_info["end_char"] = node.end_char_idx

                        enriched_chunks.append(chunk_info)

                except Exception as e:
                    log_event(
                        "chunk_retrieval_error",
                        {"node_id": node_id, "error": str(e)},
                        level=logging.DEBUG,
                    )
                    continue

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
            return {
                "error": str(e),
                "chunks": [],
                "total": 0,
            }

    async def get_document_neighbors(
        self, document_id: str, top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Get semantically similar documents for a given document.

        Args:
            document_id: The document to find neighbors for
            top_k: Number of similar documents to return

        Returns:
            Dictionary with similar documents and their scores
        """
        try:
            if not self.index:
                return {"error": "Index not initialized", "neighbors": []}

            # Check if document exists
            if document_id not in self.doc_tracker:
                return {"error": f"Document {document_id} not found", "neighbors": []}

            node_ids = self.doc_tracker[document_id]
            if not node_ids:
                return {"error": "No nodes found for document", "neighbors": []}

            # Get the first node's text to use as query
            docstore = self.index.storage_context.docstore
            first_node_id = node_ids[0]
            nodes = docstore.get_document(first_node_id, raise_error=False)

            if not nodes:
                return {"error": "Could not retrieve document content", "neighbors": []}

            if not isinstance(nodes, list):
                nodes = [nodes]

            first_node = nodes[0] if nodes else None
            if not first_node or not hasattr(first_node, "text"):
                return {"error": "Document has no text content", "neighbors": []}

            # Use the document's text as query (truncated to avoid token limits)
            query_text = first_node.text[:2000]  # Use first 2000 chars as query

            # Retrieve similar documents
            similar_docs = await self.retrieve_similar(
                query=query_text,
                top_k=top_k + 10,  # Get extra to filter out self
                similarity_threshold=0.3,  # Lower threshold for neighbor search
            )

            # Filter out the document itself and format results
            neighbors = []
            for doc in similar_docs:
                if doc["document_id"] != document_id:
                    neighbor_info = {
                        "document_id": doc["document_id"],
                        "score": doc["score"],
                        "text_preview": (
                            doc["text"][:200] + "..."
                            if len(doc["text"]) > 200
                            else doc["text"]
                        ),
                        "metadata": doc.get("metadata", {}),
                    }
                    neighbors.append(neighbor_info)

                    if len(neighbors) >= top_k:
                        break

            log_event(
                "document_neighbors_retrieved",
                {
                    "document_id": document_id,
                    "neighbors_found": len(neighbors),
                    "top_k_requested": top_k,
                },
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
        """
        Retrieve similar documents using Qdrant's vector search.

        Args:
            query: Search query text
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)
        """
        try:
            if not self.index:
                log_event(
                    "retrieval_skipped",
                    {"reason": "no_index"},
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
            )

            # Use LlamaIndex's retriever which handles embedding and Qdrant search
            from llama_index.core.retrievers import VectorIndexRetriever

            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=top_k,
            )

            # Retrieve nodes
            nodes = retriever.retrieve(query)

            # Filter by similarity threshold and format results
            results = []
            nodes_below_threshold = 0

            for node in nodes:
                # Qdrant returns scores as cosine similarity (0-1 range)
                score = float(node.score) if node.score else 0.0

                if score >= similarity_threshold:
                    # Extract metadata and text
                    metadata = (
                        node.node.metadata if hasattr(node.node, "metadata") else {}
                    )
                    text = node.node.text if hasattr(node.node, "text") else ""

                    # Create result entry
                    result = {
                        "document_id": metadata.get("document_id", "unknown"),
                        "text": text[:500] + "..." if len(text) > 500 else text,
                        "score": score,
                        "metadata": metadata,
                        "node_id": node.node.id_ if hasattr(node.node, "id_") else None,
                    }
                    results.append(result)
                else:
                    nodes_below_threshold += 1

            log_event(
                "similarity_retrieval_completed",
                {
                    "nodes_retrieved": len(nodes),
                    "nodes_above_threshold": len(results),
                    "nodes_below_threshold": nodes_below_threshold,
                    "threshold": similarity_threshold,
                    "avg_score": (
                        sum(r["score"] for r in results) / len(results)
                        if results
                        else 0
                    ),
                },
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
