"""
Basic test to verify document lifecycle fixtures work.
"""

import pytest
from httpx import AsyncClient
from typing import Dict, Any

from .base import PopulatedRouteTest


class TestBasicFixtures(PopulatedRouteTest):
    """Basic test to verify fixtures work."""
    
    @pytest.mark.asyncio
    async def test_single_document_fixture(
        self,
        async_client: AsyncClient,
        single_processed_document: Dict[str, Any]
    ):
        """Test that single document fixture provides a processed document."""
        # Verify document structure
        assert "file_id" in single_processed_document
        assert "content" in single_processed_document
        assert "status" in single_processed_document
        
        # Verify document is processed
        assert single_processed_document["status"] == "ready"
        assert len(single_processed_document["content"]) > 0
        assert len(single_processed_document["file_id"]) > 0
        
        print(f"✅ Single document fixture provided: {single_processed_document['file_id']}")
        print(f"✅ Document content length: {len(single_processed_document['content'])}")
        
        # Test that we can search for this document
        search_response = await async_client.get(
            f"/api/search?q=test+document&limit=5"
        )
        
        assert search_response.status_code == 200
        search_data = search_response.json()
        
        # Should be able to search (may or may not find results depending on content)
        assert "results" in search_data
        assert "total" in search_data
        
        print(f"✅ Search worked: {len(search_data['results'])} results found")
        
        return True