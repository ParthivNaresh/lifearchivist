"""
Test fixtures for Life Archivist testing framework.

This package provides comprehensive fixtures for testing routes and functionality
that depends on processed documents and populated data stores.
"""

from .document_lifecycle import (
    single_processed_document,
    multiple_processed_documents, 
    populated_vault_with_search_ready_docs,
    domain_specific_documents,
    quick_test_document,
    empty_then_populated_vault,
    document_categories,
    search_test_queries
)

__all__ = [
    "single_processed_document",
    "multiple_processed_documents",
    "populated_vault_with_search_ready_docs", 
    "domain_specific_documents",
    "quick_test_document",
    "empty_then_populated_vault",
    "document_categories",
    "search_test_queries"
]