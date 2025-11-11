"""
Utility functions for LlamaIndex service operations.

Provides reusable helpers for document neighbor operations and metadata enrichment.
"""

import logging
from typing import Any, Dict, List, Optional

from lifearchivist.utils.logging import log_event
from lifearchivist.utils.result import Result


class DocumentNeighborUtils:
    """Utility class for document neighbor operations."""

    @staticmethod
    async def validate_document_exists(
        document_id: str,
        document_service: Any,
        doc_tracker: Any,
    ) -> Optional[str]:
        """
        Validate that a document exists.

        Args:
            document_id: Document ID to validate
            document_service: Document service instance
            doc_tracker: Document tracker instance

        Returns:
            Error message if validation fails, None if valid
        """
        if document_service:
            if not await document_service.document_exists(document_id):
                return f"Document {document_id} not found"
        else:
            if not doc_tracker or not await doc_tracker.document_exists(document_id):
                return f"Document {document_id} not found"
        return None

    @staticmethod
    async def get_document_node_ids(
        document_id: str,
        document_service: Any,
        doc_tracker: Any,
    ) -> tuple[Optional[List[str]], Optional[str]]:
        """
        Get node IDs for a document.

        Args:
            document_id: Document ID
            document_service: Document service instance
            doc_tracker: Document tracker instance

        Returns:
            Tuple of (node_ids, error_message)
        """
        if document_service:
            node_ids = await document_service.get_node_ids(document_id)
        else:
            node_ids = await doc_tracker.get_node_ids(document_id)

        if not node_ids:
            return None, "No nodes found for document"

        return node_ids, None

    @staticmethod
    def extract_node_text_from_qdrant(
        qdrant_client: Any,
        node_id: str,
        document_id: str,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Extract text from a Qdrant node.

        Args:
            qdrant_client: Qdrant client instance
            node_id: Node ID to retrieve
            document_id: Document ID for logging

        Returns:
            Tuple of (text, error_message)
        """
        from lifearchivist.storage.utils import QdrantNodeUtils

        try:
            points = qdrant_client.retrieve(
                collection_name="lifearchivist",
                ids=[node_id],
                with_payload=True,
                with_vectors=False,
            )

            if not points or len(points) == 0:
                log_event(
                    "qdrant_node_not_found",
                    {
                        "document_id": document_id,
                        "node_id": node_id,
                    },
                    level=logging.WARNING,
                )
                return None, "Document node not found in Qdrant"

            node_payload = points[0].payload
            if node_payload is None:
                log_event(
                    "node_payload_missing",
                    {"document_id": document_id, "node_id": node_id},
                    level=logging.WARNING,
                )
                return None, "Node payload is missing"

            document_text = QdrantNodeUtils.extract_text_from_node(node_payload)

            if not document_text:
                log_event(
                    "node_text_extraction_failed",
                    {"document_id": document_id, "node_id": node_id},
                    level=logging.WARNING,
                )
                return None, "Could not extract text from node"

            return document_text, None

        except Exception as e:
            log_event(
                "qdrant_retrieval_error",
                {
                    "document_id": document_id,
                    "node_id": node_id,
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            return None, f"Failed to retrieve node from Qdrant: {str(e)}"

    @staticmethod
    async def enrich_neighbor_metadata(
        neighbor: Dict[str, Any],
        metadata_service: Any,
    ) -> Dict[str, Any]:
        """
        Enrich neighbor with full metadata from Redis and add required API fields.

        Args:
            neighbor: Neighbor dictionary to enrich
            metadata_service: Metadata service instance

        Returns:
            Enriched neighbor dictionary with title and similarity_score
        """
        neighbor_doc_id = neighbor.get("document_id")

        if "score" in neighbor and "similarity_score" not in neighbor:
            neighbor["similarity_score"] = neighbor["score"]

        if not neighbor_doc_id or neighbor_doc_id == "unknown":
            neighbor["title"] = "Unknown Document"
            if "similarity_score" not in neighbor:
                neighbor["similarity_score"] = 0.0
            return neighbor

        if not metadata_service:
            neighbor["title"] = neighbor_doc_id
            if "similarity_score" not in neighbor:
                neighbor["similarity_score"] = neighbor.get("score", 0.0)
            return neighbor

        full_metadata_result = await metadata_service.get_full_document_metadata(
            neighbor_doc_id
        )

        if full_metadata_result.is_success():
            full_metadata = full_metadata_result.unwrap()

            neighbor["title"] = full_metadata.get("title", neighbor_doc_id)

            if "metadata" not in neighbor:
                neighbor["metadata"] = {}

            neighbor["metadata"]["size_bytes"] = full_metadata.get("size_bytes", 0)
            neighbor["metadata"]["document_created_at"] = full_metadata.get(
                "document_created_at"
            )

            classifications = full_metadata.get("classifications", {})
            neighbor["metadata"]["theme"] = classifications.get("theme")
            neighbor["metadata"]["primary_subtheme"] = classifications.get(
                "primary_subtheme"
            )
        else:
            neighbor["title"] = neighbor_doc_id

        if "similarity_score" not in neighbor:
            neighbor["similarity_score"] = neighbor.get("score", 0.0)

        return neighbor

    @staticmethod
    def create_error_response(
        document_id: str,
        error_message: str,
        warning: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a standardized error response.

        Args:
            document_id: Document ID
            error_message: Error message
            warning: Whether this is a warning vs error

        Returns:
            Error response dictionary
        """
        response = {
            "document_id": document_id,
            "neighbors": [],
            "total": 0,
        }

        if warning:
            response["warning"] = error_message
        else:
            response["error"] = error_message

        return response

    @staticmethod
    def handle_neighbors_result(
        neighbors_result: Result,
        document_id: str,
    ) -> tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
        """
        Handle the Result from search service.

        Args:
            neighbors_result: Result from search service
            document_id: Document ID for error context

        Returns:
            Tuple of (neighbors_list, error_response)
        """
        if neighbors_result.is_failure():
            error_msg = (
                str(neighbors_result.error)
                if hasattr(neighbors_result, "error")
                else "Unknown error"
            )
            error_response = DocumentNeighborUtils.create_error_response(
                document_id, error_msg
            )
            return None, error_response

        neighbors_list = (
            list(neighbors_result.value) if hasattr(neighbors_result, "value") else []
        )

        return neighbors_list, None
