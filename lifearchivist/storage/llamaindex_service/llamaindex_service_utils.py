"""
Utility functions and classes for LlamaIndex service operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class DocumentFilter:
    """Handles document metadata filtering operations."""

    @staticmethod
    def matches_filters(metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if document metadata matches the provided filters."""
        try:
            for filter_key, filter_value in filters.items():
                if filter_key == "status":
                    if metadata.get("status") != filter_value:
                        return False
                elif filter_key == "date_range":
                    if not DocumentFilter._matches_date_range(metadata, filter_value):
                        return False
                elif filter_key == "tags":
                    if not DocumentFilter._matches_tags(metadata, filter_value):
                        return False
                elif filter_key == "mime_type":
                    if metadata.get("mime_type") != filter_value:
                        return False
                else:
                    # Generic field matching
                    if metadata.get(filter_key) != filter_value:
                        return False

            return True

        except Exception as e:
            return False

    @staticmethod
    def _matches_date_range(
        metadata: Dict[str, Any], date_range: Dict[str, str]
    ) -> bool:
        """Check if document has content dates within the specified range."""
        try:
            content_dates = metadata.get("content_dates", [])
            if not content_dates:
                return False

            start_date = datetime.fromisoformat(
                date_range["start"].replace("Z", "+00:00")
            )
            end_date = datetime.fromisoformat(date_range["end"].replace("Z", "+00:00"))

            for date_info in content_dates:
                if isinstance(date_info, dict) and date_info.get("extracted_date"):
                    try:
                        extracted_date = datetime.fromisoformat(
                            date_info["extracted_date"].replace("Z", "+00:00")
                        )
                        if start_date <= extracted_date <= end_date:
                            return True
                    except ValueError:
                        continue

            return False

        except Exception as e:
            return False

    @staticmethod
    def _matches_tags(metadata: Dict[str, Any], tag_filters: List[str]) -> bool:
        """Check if document has any of the specified tags."""
        try:
            document_tags = metadata.get("tags", [])
            if not document_tags:
                return False

            document_tag_names = {
                tag.get("name") if isinstance(tag, dict) else str(tag)
                for tag in document_tags
            }

            # Check if any filter tag matches
            return bool(set(tag_filters) & document_tag_names)

        except Exception as e:
            return False


class NodeProcessor:
    """Utilities for processing LlamaIndex nodes."""

    @staticmethod
    def get_document_nodes_from_ref_doc_info(
        index, document_id: str
    ) -> List[Dict[str, Any]]:
        """Efficiently retrieve all nodes for a document using ref_doc_info."""
        if not index:
            return []

        ref_doc_info = index.ref_doc_info.get(document_id)
        if not ref_doc_info:
            return []

        docstore = index.storage_context.docstore
        nodes_data = []

        for node_id in ref_doc_info.node_ids:
            try:
                node = docstore.get_node(node_id)
                if node:
                    node_data = {
                        "node_id": node.node_id,
                        "text": getattr(node, "text", ""),
                        "metadata": node.metadata or {},
                        "start_char": getattr(node, "start_char_idx", None),
                        "end_char": getattr(node, "end_char_idx", None),
                        "relationships": getattr(node, "relationships", {}),
                    }
                    nodes_data.append(node_data)
            except Exception as e:
                continue

        return nodes_data

    @staticmethod
    def generate_text_preview(node, max_length: int = 200) -> str:
        """Generate text preview from a node with consistent truncation."""
        try:
            if node and hasattr(node, "text") and node.text:
                # Ensure we're working with a string type
                text = str(node.text)
                return text[:max_length] + "..." if len(text) > max_length else text
            return ""
        except Exception:
            return ""

    @staticmethod
    def extract_source_info(node_with_score) -> Optional[Dict[str, Any]]:
        """Extract source information from a node with score."""
        try:
            metadata = node_with_score.node.metadata or {}

            return {
                "document_id": metadata.get("document_id", "unknown"),
                "score": float(node_with_score.score) if node_with_score.score else 0.0,
                "text": NodeProcessor.generate_text_preview(node_with_score.node, 300),
                "metadata": metadata,
            }
        except Exception as e:
            return None


def create_error_response(error_message: str, **additional_fields) -> Dict[str, Any]:
    """Create consistent error response dictionary."""
    response = {"error": error_message}
    response.update(additional_fields)
    return response


def calculate_document_metrics(nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate metrics for a list of document nodes."""
    total_chunks = len(nodes)
    total_tokens = sum(len(node.get("text", "").split()) for node in nodes)
    avg_chunk_size = total_tokens / total_chunks if total_chunks > 0 else 0

    return {
        "total_chunks": total_chunks,
        "total_tokens": total_tokens,
        "avg_chunk_size": int(avg_chunk_size),
    }
