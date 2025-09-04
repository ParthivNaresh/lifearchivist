# Life Archivist Testing Framework

This document describes the comprehensive testing framework for Life Archivist API routes. The framework is designed to be powerful, flexible, and extensible while following enterprise best practices.

## 🏗️ Architecture Overview

The testing framework is organized into several layers:

```
tests/
├── conftest.py              # Core fixtures and pytest configuration
├── base.py                  # Base test classes with common patterns
├── factories/               # Data factories for creating test objects
│   ├── file_factory.py      # File and content creation
│   ├── document_factory.py  # Document metadata creation
│   ├── metadata_factory.py  # Production-aligned metadata
│   ├── request_factory.py   # API request payload creation
│   └── response_factory.py  # Expected response creation
├── utils/                   # Testing utilities and helpers
│   ├── assertions.py        # Custom assertion functions
│   ├── helpers.py          # Common helper functions
│   ├── mocks.py            # Mock service implementations
│   └── fixtures.py         # Resource management utilities
└── routes/                  # Route-specific tests
    ├── test_upload.py      # Upload route tests (example)
    └── test_search.py      # Search route tests (example)
```

## 🚀 Quick Start

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/routes/test_upload.py

# Run with coverage
pytest --cov=lifearchivist --cov-report=html

# Run only unit tests
pytest -m unit

# Run integration tests
pytest -m integration
```

### Writing a Simple Test

```python
from tests import BaseUploadTest


class TestMyUploadFeature(BaseUploadTest):
    async def test_upload_basic_file(self, async_client):
        response_data = await self.perform_upload(
            async_client,
            file_content=b"test content",
            filename="test.txt"
        )

        assert_valid_file_id(response_data["file_id"])
        assert response_data["status"] == "completed"
```

## 📋 Core Components

### Base Test Classes

The framework provides specialized base classes for different types of route testing:

#### `BaseRouteTest`
- Foundation class with common utilities
- Resource management (automatic cleanup)
- Standard assertion methods
- Request/response factory integration

#### `BaseUploadTest`
- Specialized for upload-related routes
- Methods: `perform_upload()`, `perform_ingest()`, `perform_bulk_ingest()`
- File creation and management helpers

#### `BaseDocumentTest`  
- Document management operations
- Methods: `list_documents()`, `clear_all_documents()`, `get_document_analysis()`
- Document lifecycle testing

#### `BaseSearchTest`
- Search and Q&A functionality
- Methods: `perform_search_post()`, `perform_search_get()`, `perform_qa_query()`
- Search validation helpers

#### `BaseVaultTest`
- Vault operations
- Methods: `get_vault_info()`, `list_vault_files()`
- Storage testing utilities

#### `ParameterizedRouteTest`
- Parameterized testing patterns
- Pre-built test cases for pagination, error scenarios
- Boundary condition testing

#### `IntegrationRouteTest`
- Multi-route workflow testing
- Document lifecycle testing (upload → search → query)
- End-to-end scenarios

### Data Factories

Data factories create realistic test data that matches production patterns:

#### `FileFactory`
```python
# Create different file types
text_file = FileFactory.create_text_file(content="test content")
pdf_file = FileFactory.create_pdf_like_file(content="PDF content")
large_file = FileFactory.create_large_text_file(size_kb=100)

# Create test file sets
medical_docs = create_sample_documents()  # Returns medical, financial, etc.
```

#### `DocumentFactory`
```python
# Create document metadata
doc = DocumentFactory.create_document_metadata(
    title="Test Document",
    tags=["test", "document"]
)

# Create search results
results = DocumentFactory.create_multiple_documents(count=5)
```

#### `RequestFactory`
```python
# Create API request payloads
search_request = RequestFactory.create_search_request(
    query="test query",
    mode="semantic",
    limit=20
)

qa_request = RequestFactory.create_ask_request(
    question="What is this about?",
    context_limit=5
)
```

#### `ResponseFactory`
```python
# Create expected responses for testing
upload_response = ResponseFactory.create_successful_upload_response(
    file_id="test_123",
    mime_type="text/plain"
)
```

### Mock Services

The framework provides realistic mock implementations:

#### `MockVault`
- File storage simulation
- Content-addressed storage patterns  
- Cleanup and statistics

#### `MockLlamaIndexService`
- Document indexing simulation
- Search and Q&A responses
- Realistic document management

#### `MockProgressManager`
- Progress tracking simulation
- Webhook and WebSocket integration
- Processing stage management

### Custom Assertions

Specialized assertions for API testing:

```python
from tests.utils import (
    assert_successful_response,
    assert_error_response,
    assert_pagination_response,
    assert_search_response,
    assert_upload_response,
    assert_qa_response,
)

# Validate successful responses
data = assert_successful_response(
    response,
    required_fields=["file_id", "status"],
    forbidden_fields=["internal_data"]
)

# Validate error responses
assert_error_response(
    response,
    expected_status=400,
    expected_detail_contains="invalid parameter"
)

# Validate search responses
assert_search_response(
    response,
    min_results=1,
    expected_mode="semantic"
)
```

## 🎯 Testing Patterns

### 1. Basic Route Testing

```python
class TestUploadRoutes(BaseUploadTest):
    async def test_upload_text_file(self, async_client):
        response_data = await self.perform_upload(
            async_client,
            file_content=b"test content",
            filename="test.txt"
        )
        
        assert_valid_file_id(response_data["file_id"])
```

### 2. Parameterized Testing

```python
class TestSearchParameterized(ParameterizedRouteTest):
    @pytest.mark.parametrize("mode", ["keyword", "semantic", "hybrid"])
    async def test_all_search_modes(self, async_client, mode):
        response = await async_client.get(
            f"/api/search?q=test&mode={mode}"
        )
        data = await self.assert_successful_response(response)
        assert data["mode"] == mode
```

### 3. Integration Testing

```python
class TestSearchIntegration(IntegrationRouteTest):
    async def test_upload_then_search(self, async_client):
        # Upload document
        file_id = await self.create_test_document(
            async_client,
            content="mortgage rates information"
        )
        
        # Search for uploaded content
        search_data = await self.perform_search_get(
            async_client,
            q="mortgage rates"
        )
        
        assert len(search_data["results"]) > 0
```

### 4. Error Testing

```python
async def test_invalid_parameters(self, async_client):
    response = await async_client.get("/api/search?q=&mode=invalid")
    
    assert_error_response(
        response,
        expected_status=400,
        expected_detail_contains="Invalid mode"
    )
```

### 5. Using Both Sync and Async Clients

```python
def test_sync_upload(self, sync_client: TestClient):
    """Demonstrate sync client usage."""
    form_data = {"tags": "[]", "metadata": "{}"}
    files = {"file": ("test.txt", b"content", "text/plain")}
    
    response = sync_client.post("/api/upload", data=form_data, files=files)
    data = assert_upload_response(response)
    assert_valid_file_id(extract_file_id(data))

async def test_async_upload(self, async_client: AsyncClient):
    """Demonstrate async client usage."""
    response_data = await self.perform_upload(
        async_client,
        file_content=b"async content",
        filename="async_test.txt"
    )
    assert_valid_file_id(response_data["file_id"])
```

## 🔧 Configuration

### Pytest Configuration

The framework automatically configures pytest with:

- **Markers**: `unit`, `integration`, `live`, `slow`, `requires_docker`
- **Asyncio mode**: Auto-detection for async tests
- **Test discovery**: Automatic test collection
- **Fixtures**: Global fixtures available to all tests

### Environment Setup

Tests use isolated environments:

```python
# Fixtures provide isolated services
async def test_with_clean_environment(test_server, async_client):
    # test_server provides fresh vault, LlamaIndex service, etc.
    # No state pollution between tests
    pass
```

### Test Data Management

```python
# Automatic cleanup
class TestMyFeature(BaseRouteTest):
    def setup_method(self):
        # Automatic setup
        super().setup_method()
    
    def teardown_method(self):
        # Automatic cleanup of temp files, services
        super().teardown_method()
```

## 📊 Advanced Usage

### Resource Management

```python
from tests.utils import TestResourceManager


async def test_with_resource_management():
    manager = TestResourceManager()

    # Resources are automatically tracked and cleaned up
    vault = await manager.create_temp_vault()
    server = await manager.create_test_server(populate_with_data=True)

    # Test logic here...
    # Cleanup happens automatically
```

### Custom Test Environments

```python
from tests.utils import create_medical_test_environment


async def test_medical_workflow():
    server, docs = await create_medical_test_environment()
    # Test with pre-populated medical documents
```

### Mock Service Customization

```python
async def test_custom_mock_behavior(async_client):
    # Customize mock responses for specific test scenarios
    with mock_successful_tool_execution({"file_id": "custom_123"}):
        response_data = await self.perform_upload(async_client, ...)
        assert response_data["file_id"] == "custom_123"
```

## 🎨 Best Practices

### 1. Test Organization
- Group related tests in classes
- Use descriptive test names
- Follow arrange-act-assert pattern

### 2. Data Management
- Use factories for consistent test data
- Prefer realistic data over minimal examples
- Clean up resources automatically

### 3. Assertions
- Use specialized assertion functions
- Validate both positive and negative cases
- Check error messages and status codes

### 4. Mocking
- Mock external dependencies only
- Keep mocks realistic and consistent
- Test both success and failure scenarios

### 5. Performance
- Use async clients for better performance
- Batch related operations
- Use appropriate test markers

## 🔍 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure proper Python path configuration
2. **Fixture Issues**: Check fixture dependencies and scopes
3. **Async Issues**: Ensure proper async/await usage
4. **Mock Issues**: Verify mock service configurations

### Debugging Tests

```bash
# Run with verbose output
pytest -v tests/routes/test_upload.py

# Run specific test
pytest tests/routes/test_upload.py::TestUploadRoutes::test_upload_simple_text_file

# Debug with pdb
pytest --pdb tests/routes/test_upload.py
```

## 🚀 Extension Points

The framework is designed for easy extension:

### Adding New Route Tests

1. Create new test file in `tests/routes/`
2. Inherit from appropriate base class
3. Implement route-specific test methods
4. Add any specialized fixtures or utilities

### Adding New Mock Services

1. Add mock class to `tests/utils/mocks.py`
2. Integrate with existing fixtures
3. Update base test classes if needed

### Adding New Assertions

1. Add assertion functions to `tests/utils/assertions.py`
2. Follow existing patterns for error handling
3. Update base classes to use new assertions

This testing framework provides a solid foundation for ensuring the reliability and maintainability of the Life Archivist API while being flexible enough to grow with the project's needs.