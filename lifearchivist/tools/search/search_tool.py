"""
Search tool for document retrieval using SearchService.

This tool provides a high-level interface for document search operations,
delegating the actual search logic to the SearchService for better
separation of concerns and maintainability.
"""

import logging
from typing import Any, Dict, List

from lifearchivist.tools.base import BaseTool, ToolMetadata
from lifearchivist.utils.logging import log_event, track


class IndexSearchTool(BaseTool):
    """
    Tool for searching documents in the index.

    This tool acts as a bridge between the MCP server and the search service,
    providing a standardized interface for search operations while delegating
    the actual search logic to the appropriate service.
    """

    def __init__(self, llamaindex_service=None):
        """
        Initialize the search tool.

        Args:
            llamaindex_service: The LlamaIndex service instance that contains
                               the search service for performing searches.
        """
        super().__init__()
        self.llamaindex_service = llamaindex_service
        # Cache the search service reference for direct access
        self._search_service = None

    def _get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="index.search",
            description="Search documents in the index using semantic, keyword, or hybrid search",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["keyword", "semantic", "hybrid"],
                        "description": "Search mode: keyword (exact text matching), semantic (AI meaning-based), or hybrid (combined)",
                        "default": "hybrid",
                    },
                    "filters": {
                        "type": "object",
                        "description": "Metadata filters to apply",
                        "properties": {
                            "mime_type": {"type": "string"},
                            "status": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "description": "Maximum number of results to return",
                        "default": 20,
                    },
                    "offset": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Number of results to skip for pagination",
                        "default": 0,
                    },
                    "include_content": {
                        "type": "boolean",
                        "description": "Whether to include full document content in results",
                        "default": False,
                    },
                },
                "required": ["query"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "document_id": {"type": "string"},
                                "title": {"type": "string"},
                                "snippet": {"type": "string"},
                                "score": {"type": "number"},
                                "mime_type": {"type": "string"},
                                "size_bytes": {"type": "integer"},
                                "match_type": {"type": "string"},
                            },
                        },
                    },
                    "total": {"type": "integer"},
                    "query_time_ms": {"type": "number"},
                },
            },
            async_tool=True,
            idempotent=True,
        )

    def _get_search_service(self):
        """
        Get the search service instance.

        Returns the cached search service or retrieves it from the llamaindex service.
        """
        if self._search_service is None and self.llamaindex_service:
            self._search_service = getattr(
                self.llamaindex_service, "search_service", None
            )
        return self._search_service

    @track(
        operation="index_search",
        include_args=["mode", "limit", "offset", "include_content"],
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
    )
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute document search."""
        query = kwargs.get("query", "").strip()
        mode = kwargs.get("mode", "hybrid")
        filters = kwargs.get("filters", {})
        limit = kwargs.get("limit", 20)
        offset = kwargs.get("offset", 0)
        include_content = kwargs.get("include_content", False)

        if not query:
            return self._empty_search_result("Query cannot be empty")

        # Check if search service is available
        search_service = self._get_search_service()
        if not search_service:
            # Fallback to llamaindex_service if search_service not available
            if not self.llamaindex_service:
                return self._empty_search_result("Search service not available")

        # Log search request with context
        log_event(
            "search_started",
            {
                "query": query[:100] + "..." if len(query) > 100 else query,
                "query_length": len(query),
                "mode": mode,
                "limit": limit,
                "offset": offset,
                "has_filters": bool(filters),
                "filter_types": list(filters.keys()) if filters else [],
                "include_content": include_content,
            },
        )

        try:
            # Determine search strategy based on mode
            if mode == "semantic":
                results = await self._semantic_search(
                    query, limit, offset, filters, include_content
                )
            elif mode == "keyword":
                results = await self._keyword_search(
                    query, limit, offset, filters, include_content
                )
            else:  # hybrid
                results = await self._hybrid_search(
                    query, limit, offset, filters, include_content
                )

            # Log search completion with metrics
            log_event(
                "search_completed",
                {
                    "query_preview": query[:50],
                    "mode": mode,
                    "results_count": len(results.get("results", [])),
                    "total_matches": results.get("total", 0),
                    "query_time_ms": results.get("query_time_ms", 0),
                    "has_results": len(results.get("results", [])) > 0,
                },
            )

            # Log if no results found (potential issue)
            if results.get("total", 0) == 0:
                log_event(
                    "search_no_results",
                    {
                        "query": query,
                        "mode": mode,
                        "filters": filters,
                    },
                    level=logging.WARNING,
                )

            return results  # type: ignore[no-any-return]
        except Exception as e:
            log_event(
                "search_failed",
                {
                    "query_preview": query[:50],
                    "mode": mode,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return self._empty_search_result(f"Search failed: {str(e)}")

    @track(
        operation="semantic_search",
        track_performance=True,
        frequency="medium_frequency",
    )
    async def _semantic_search(
        self, query: str, limit: int, offset: int, filters: Dict, include_content: bool
    ) -> Dict[str, Any]:
        """
        Perform semantic search using SearchService.

        This method delegates to the SearchService for actual search execution,
        then processes and formats the results for the tool's output format.
        """
        import time

        start_time = time.time()

        # Get search service
        search_service = self._get_search_service()

        # Use SearchService if available, otherwise fall back to llamaindex_service
        similarity_threshold = 0.3  # Lower threshold for broader results

        if search_service:
            # Use the new SearchService
            retrieved_nodes = await search_service.semantic_search(
                query=query,
                top_k=min(limit * 2, 50),  # Get more results to filter
                similarity_threshold=similarity_threshold,
                filters=filters,  # Pass filters directly to search service
            )
        else:
            # Fallback to llamaindex_service for backward compatibility
            retrieved_nodes = await self.llamaindex_service.retrieve_similar(
                query=query,
                top_k=min(limit * 2, 50),
                similarity_threshold=similarity_threshold,
            )
            # Apply filters manually if using fallback
            if filters:
                retrieved_nodes = self._apply_filters(retrieved_nodes, filters)

        # Log retrieval metrics
        log_event(
            "semantic_retrieval_completed",
            {
                "query_preview": query[:50],
                "nodes_retrieved": len(retrieved_nodes),
                "similarity_threshold": similarity_threshold,
                "top_k": min(limit * 2, 50),
            },
            level=logging.DEBUG,
        )

        # Note: When using SearchService, filters are already applied
        # This block is only needed for backward compatibility logging
        if not search_service and filters:
            nodes_before_filter = len(retrieved_nodes)
            # Filters were already applied above in the fallback case
            if nodes_before_filter != len(retrieved_nodes):
                log_event(
                    "search_filters_applied",
                    {
                        "nodes_before": nodes_before_filter,
                        "nodes_after": len(retrieved_nodes),
                        "filtered_out": nodes_before_filter - len(retrieved_nodes),
                        "filter_types": list(filters.keys()),
                    },
                    level=logging.DEBUG,
                )

        # Convert to search result format
        results = self._convert_nodes_to_search_results(
            retrieved_nodes, query, "semantic", include_content
        )

        # Apply pagination
        total = len(results)
        paginated_results = results[offset : offset + limit]

        query_time_ms = (time.time() - start_time) * 1000

        # Log slow searches
        if query_time_ms > 1000:  # More than 1 second
            log_event(
                "slow_semantic_search",
                {
                    "query_preview": query[:50],
                    "query_time_ms": round(query_time_ms, 2),
                    "total_results": total,
                    "nodes_processed": len(retrieved_nodes),
                },
                level=logging.WARNING,
            )

        return {
            "results": paginated_results,
            "total": total,
            "query_time_ms": round(query_time_ms, 2),
        }

    @track(
        operation="keyword_search",
        track_performance=True,
        frequency="medium_frequency",
    )
    async def _keyword_search(
        self, query: str, limit: int, offset: int, filters: Dict, include_content: bool
    ) -> Dict[str, Any]:
        """
        Perform keyword search using SearchService.

        Delegates entirely to SearchService for BM25-based keyword search.
        """
        import time

        start_time = time.time()

        # Get search service
        search_service = self._get_search_service()

        if not search_service:
            log_event(
                "keyword_search_failed",
                {"reason": "search_service_not_available"},
                level=logging.ERROR,
            )
            return self._empty_search_result("Search service not available")

        # Use the SearchService for keyword search
        retrieved_nodes = await search_service.keyword_search(
            query=query,
            top_k=min(limit * 2, 50),
            filters=filters,
        )

        # Convert to search result format
        results = self._convert_nodes_to_search_results(
            retrieved_nodes, query, "keyword", include_content
        )

        # Apply pagination
        total = len(results)
        paginated_results = results[offset : offset + limit]

        query_time_ms = (time.time() - start_time) * 1000

        # Log slow searches
        if query_time_ms > 1000:
            log_event(
                "slow_keyword_search",
                {
                    "query_preview": query[:50],
                    "query_time_ms": round(query_time_ms, 2),
                    "total_results": total,
                },
                level=logging.WARNING,
            )

        return {
            "results": paginated_results,
            "total": total,
            "query_time_ms": round(query_time_ms, 2),
        }

    @track(
        operation="hybrid_search",
        track_performance=True,
        frequency="medium_frequency",
    )
    async def _hybrid_search(
        self, query: str, limit: int, offset: int, filters: Dict, include_content: bool
    ) -> Dict[str, Any]:
        """
        Perform hybrid search using SearchService.

        This method delegates to the SearchService for hybrid search,
        or combines semantic and keyword results if SearchService is not available.
        """
        import time

        start_time = time.time()

        # Get search service
        search_service = self._get_search_service()

        if search_service:
            # Use the SearchService for hybrid search
            retrieved_nodes = await search_service.hybrid_search(
                query=query,
                top_k=min(limit * 2, 50),
                semantic_weight=0.6,  # Slightly favor semantic search
                filters=filters,
            )

            # Convert to search result format
            results = self._convert_nodes_to_search_results(
                retrieved_nodes, query, "hybrid", include_content
            )

            # Apply pagination
            total = len(results)
            paginated_results = results[offset : offset + limit]

            query_time_ms = (time.time() - start_time) * 1000

            # Log slow searches
            if query_time_ms > 2000:  # More than 2 seconds for hybrid
                log_event(
                    "slow_hybrid_search",
                    {
                        "query_preview": query[:50],
                        "query_time_ms": round(query_time_ms, 2),
                        "total_results": total,
                    },
                    level=logging.WARNING,
                )

            return {
                "results": paginated_results,
                "total": total,
                "query_time_ms": round(query_time_ms, 2),
            }

        # Fallback: Get results from both methods in parallel for performance
        import asyncio

        semantic_results, keyword_results = await asyncio.gather(
            self._semantic_search(query, limit, 0, filters, include_content),
            self._keyword_search(query, limit, 0, filters, include_content),
        )

        # Combine and deduplicate results
        combined_results = {}

        # Add semantic results with boost
        semantic_count = 0
        for result in semantic_results["results"]:
            doc_id = result["document_id"]
            result["score"] = result["score"] * 1.2  # Boost semantic scores
            result["match_type"] = "hybrid_semantic"
            combined_results[doc_id] = result
            semantic_count += 1

        # Add keyword results, boosting score if document already exists
        keyword_count = 0
        overlap_count = 0
        for result in keyword_results["results"]:
            doc_id = result["document_id"]
            if doc_id in combined_results:
                # Boost existing score
                combined_results[doc_id]["score"] = (
                    combined_results[doc_id]["score"] + result["score"]
                ) / 2 + 0.1
                combined_results[doc_id]["match_type"] = "hybrid_both"
                overlap_count += 1
            else:
                result["match_type"] = "hybrid_keyword"
                combined_results[doc_id] = result
                keyword_count += 1

        # Log hybrid search metrics
        log_event(
            "hybrid_search_combined",
            {
                "semantic_results": semantic_count,
                "keyword_results": keyword_count,
                "overlap_results": overlap_count,
                "total_unique": len(combined_results),
            },
            level=logging.DEBUG,
        )

        # Convert back to list and sort
        final_results = list(combined_results.values())
        final_results.sort(key=lambda x: x["score"], reverse=True)

        # Apply pagination
        total = len(final_results)
        paginated_results = final_results[offset : offset + limit]

        query_time_ms = (time.time() - start_time) * 1000

        # Log slow searches
        if query_time_ms > 2000:  # More than 2 seconds for hybrid
            log_event(
                "slow_hybrid_search",
                {
                    "query_preview": query[:50],
                    "query_time_ms": round(query_time_ms, 2),
                    "total_results": total,
                },
                level=logging.WARNING,
            )

        return {
            "results": paginated_results,
            "total": total,
            "query_time_ms": round(query_time_ms, 2),
        }

    @track(
        operation="apply_search_filters",
        track_performance=False,  # Fast operation
        frequency="high_frequency",
    )
    def _apply_filters(self, nodes: List[Dict], filters: Dict) -> List[Dict]:
        """Apply metadata filters to retrieved nodes."""
        if not filters:
            return nodes

        filtered_nodes = []
        for node in nodes:
            metadata = node.get("metadata", {})

            # Check mime_type filter
            if "mime_type" in filters:
                if metadata.get("mime_type") != filters["mime_type"]:
                    continue

            # Check status filter
            if "status" in filters:
                if metadata.get("status") != filters["status"]:
                    continue

            # Check tags filter (document must have at least one of the specified tags)
            if "tags" in filters and filters["tags"]:
                doc_tags = metadata.get("tags", [])
                if not any(tag in doc_tags for tag in filters["tags"]):
                    continue

            filtered_nodes.append(node)

        return filtered_nodes

    @track(
        operation="convert_search_results",
        track_performance=False,
        frequency="high_frequency",
    )
    def _convert_nodes_to_search_results(
        self, nodes: List[Dict], query: str, match_type: str, include_content: bool
    ) -> List[Dict]:
        """Convert LlamaIndex nodes to search result format."""
        results = []

        for node in nodes:
            metadata = node.get("metadata", {})
            text = node.get("text", "")

            # Create snippet (first 300 chars with query highlighting context)
            snippet = self._create_snippet(text, query, max_length=300)

            result = {
                "document_id": metadata.get("document_id", node.get("document_id", "")),
                "title": metadata.get(
                    "title", metadata.get("original_path", "Untitled")
                ).split("/")[-1],
                "snippet": snippet,
                "score": node.get("score", 0.8),  # Default score if not provided
                "mime_type": metadata.get("mime_type", "unknown"),
                "size_bytes": metadata.get("size_bytes", 0),
                "word_count": metadata.get("word_count"),
                "match_type": match_type,
                "created_at": metadata.get("created_at"),
                "ingested_at": metadata.get("ingested_at")
                or metadata.get("created_at"),
                "tags": metadata.get("tags", []),
            }

            # Include content if requested
            if include_content:
                result["content"] = text

            results.append(result)

        return results

    def _create_snippet(self, text: str, query: str, max_length: int = 300) -> str:
        """Create a snippet showing context around query terms."""
        if not text:
            return ""

        if len(text) <= max_length:
            return text

        # Try to find query terms in text for better context
        query_words = query.lower().split()
        text_lower = text.lower()

        best_position = 0
        best_score = 0

        # Look for positions with query words
        for i in range(0, len(text) - max_length + 1, 50):
            window = text_lower[i : i + max_length]
            score = sum(1 for word in query_words if word in window)
            if score > best_score:
                best_score = score
                best_position = i

        # Extract snippet
        snippet = text[best_position : best_position + max_length]

        # Add ellipsis if needed
        if best_position > 0:
            snippet = "..." + snippet
        if best_position + max_length < len(text):
            snippet = snippet + "..."

        return snippet

    def _empty_search_result(self, error_message: str) -> Dict[str, Any]:
        """Return empty search result with error message."""
        # Log empty results as they may indicate issues
        log_event(
            "search_empty_result",
            {
                "reason": error_message,
            },
            level=logging.DEBUG,
        )

        return {
            "results": [],
            "total": 0,
            "query_time_ms": 0,
            "error": error_message,
        }
