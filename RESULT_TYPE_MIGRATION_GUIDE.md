# Result Type Migration Guide

## Overview

This guide shows how to migrate from the current mixed error handling to the Result type pattern.

## Core Concept

Every operation returns a `Result` which is either:
- `Success(value)` - operation succeeded with a value
- `Failure(error, error_type, context)` - operation failed with details

## Benefits for Your Use Case

### 1. Consistent UI Error Handling

**Before (inconsistent):**
```typescript
// Some endpoints return this
{success: true, result: {...}}

// Others return this  
{file_id: "123", status: "ready"}

// Errors might be
{success: false, error: "..."}
// or
{error: "...", status: 500}
```

**After (always consistent):**
```typescript
// EVERY response has this shape
interface ApiResponse<T> {
  success: boolean;
  data?: T;              // Present if success=true
  error?: string;        // Present if success=false
  error_type?: string;   // Present if success=false
  context?: object;      // Optional additional info
  recoverable?: boolean; // Can user retry?
}

// Single handler for ALL responses
function handleResponse<T>(response: ApiResponse<T>) {
  if (response.success) {
    return response.data;
  } else {
    showError(response.error, {
      type: response.error_type,
      canRetry: response.recoverable,
      details: response.context
    });
  }
}
```

### 2. WebSocket Integration

**Current WebSocket Handler:**
```python
# lifearchivist/server/api/routes/websocket.py
@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    # ... connection logic ...
    
    # Send progress updates
    await websocket.send_json({
        "type": "progress",
        "data": {"stage": "indexing", "progress": 50}
    })
```

**With Result Types:**
```python
@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    try:
        # Process document
        result = await process_document(doc_id)
        
        # Send result (success or failure) - same format!
        await websocket.send_json({
            "type": "completion",
            **result.to_dict()  # Automatically correct format
        })
        
    except Exception as e:
        # Even exceptions become consistent Results
        error_result = internal_error(str(e), {"session_id": session_id})
        await websocket.send_json({
            "type": "error",
            **error_result.to_dict()
        })
```

## Migration Examples

### Example 1: Document Service

**Before:**
```python
async def add_document(
    self,
    document_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    if not self.index:
        log_event("document_add_failed", {"reason": "no_index"})
        return False
    
    try:
        # ... logic ...
        return True
    except Exception as e:
        log_event("document_add_error", {"error": str(e)})
        return False
```

**After:**
```python
from lifearchivist.utils.result import Result, Success, internal_error, validation_error

async def add_document(
    self,
    document_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Result[Dict[str, Any], str]:
    """
    Add a document to the index.
    
    Returns:
        Success with document info, or Failure with error details
    """
    if not self.index:
        return internal_error(
            "Index not initialized",
            context={"document_id": document_id}
        )
    
    if not content or not content.strip():
        return validation_error(
            "Document content cannot be empty",
            context={"document_id": document_id}
        )
    
    try:
        # ... document addition logic ...
        nodes_created = await self._insert_document_into_index(...)
        
        return Success({
            "document_id": document_id,
            "nodes_created": len(nodes_created),
            "status": "indexed",
            "content_length": len(content)
        })
        
    except Exception as e:
        return internal_error(
            f"Failed to add document: {str(e)}",
            context={
                "document_id": document_id,
                "error_type": type(e).__name__
            }
        )
```

### Example 2: API Route

**Before:**
```python
@router.post("/api/ingest")
async def ingest_document(request: IngestRequest):
    server = get_server()
    params = request.model_dump()
    
    try:
        result = await server.execute_tool("file.import", params)
        
        if result["success"]:
            return result["result"]
        else:
            raise HTTPException(status_code=500, detail=result["error"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**After:**
```python
from fastapi.responses import JSONResponse

@router.post("/api/ingest")
async def ingest_document(request: IngestRequest):
    server = get_server()
    params = request.model_dump()
    
    # execute_tool now returns Result
    result = await server.execute_tool("file.import", params)
    
    # Convert Result to HTTP response
    if result.is_success():
        return JSONResponse(result.to_dict(), status_code=200)
    else:
        return JSONResponse(
            result.to_dict(),
            status_code=result.status_code  # Automatically correct status
        )
```

### Example 3: Tool Execution

**Before:**
```python
async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}
        
        result = await tool.execute(**params)
        return {"success": True, "result": result}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**After:**
```python
from lifearchivist.utils.result import Result, Success, not_found_error, internal_error

async def execute_tool(
    self, 
    tool_name: str, 
    params: Dict[str, Any]
) -> Result[Dict[str, Any], str]:
    """
    Execute a tool with parameters.
    
    Returns:
        Success with tool result, or Failure with error details
    """
    tool = self.tool_registry.get_tool(tool_name)
    if not tool:
        return not_found_error(
            f"Tool '{tool_name}' not found",
            context={
                "tool_name": tool_name,
                "available_tools": list(self.tool_registry.list_tools().keys())
            }
        )
    
    try:
        # Tool execution now returns Result
        result = await tool.execute(**params)
        return result  # Already a Result!
        
    except Exception as e:
        return internal_error(
            f"Tool execution failed: {str(e)}",
            context={
                "tool_name": tool_name,
                "params": params,
                "error_type": type(e).__name__
            }
        )
```

## UI Integration Examples

### React/TypeScript

```typescript
// types/api.ts
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  error_type?: string;
  context?: Record<string, any>;
  recoverable?: boolean;
}

// hooks/useApi.ts
export function useApi() {
  const handleResponse = <T>(response: ApiResponse<T>) => {
    if (response.success) {
      return response.data!;
    }
    
    // Consistent error handling
    const error = new ApiError(
      response.error!,
      response.error_type!,
      response.context,
      response.recoverable
    );
    
    // Show appropriate UI based on error type
    switch (response.error_type) {
      case 'ValidationError':
        toast.error(response.error, { action: 'Fix input' });
        break;
      case 'ServiceUnavailable':
        if (response.recoverable) {
          toast.error(response.error, { action: 'Retry' });
        }
        break;
      default:
        toast.error(response.error);
    }
    
    throw error;
  };
  
  return { handleResponse };
}

// Usage in component
function UploadDocument() {
  const { handleResponse } = useApi();
  
  const uploadFile = async (file: File) => {
    const response = await api.post<{document_id: string}>('/api/ingest', {
      file
    });
    
    try {
      const data = handleResponse(response);
      // data is typed as {document_id: string}
      navigate(`/documents/${data.document_id}`);
    } catch (error) {
      // Error already shown to user via toast
      console.error('Upload failed:', error);
    }
  };
  
  return <FileUploader onUpload={uploadFile} />;
}
```

### WebSocket Handler

```typescript
// hooks/useWebSocket.ts
export function useDocumentUpload(sessionId: string) {
  const [status, setStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      // ALL messages have consistent Result format
      if (message.success) {
        switch (message.type) {
          case 'progress':
            setProgress(message.data.progress);
            break;
          case 'completion':
            setStatus('success');
            break;
        }
      } else {
        // Error handling is identical for all error types
        setStatus('error');
        setError(message.error);
        
        // Can check if recoverable
        if (message.recoverable) {
          showRetryButton();
        }
      }
    };
    
    return () => ws.close();
  }, [sessionId]);
  
  return { status, progress, error };
}
```

## Migration Strategy

### Phase 1: Add Result Type (✅ Done)
- Created `lifearchivist/utils/result.py`
- Defined Success, Failure, and helper functions

### Phase 2: Update Service Layer (Recommended First)
1. **Document Service** - Core CRUD operations
2. **Metadata Service** - Metadata operations  
3. **Query Service** - Search and query
4. **Search Service** - Search operations

### Phase 3: Update Tool Layer
1. **FileImportTool** - File ingestion
2. **ExtractTextTool** - Text extraction
3. **LlamaIndexQueryTool** - RAG queries
4. **Other tools** - Remaining tools

### Phase 4: Update API Layer
1. **Upload routes** - File upload endpoints
2. **Document routes** - CRUD endpoints
3. **Search routes** - Search endpoints
4. **WebSocket handler** - Real-time updates

### Phase 5: Update UI
1. **API client** - Centralized response handling
2. **Error components** - Consistent error display
3. **WebSocket hooks** - Real-time error handling

## Testing Strategy

### Unit Tests
```python
def test_document_service_success():
    service = DocumentService(...)
    result = await service.add_document("doc1", "content")
    
    assert result.is_success()
    assert result.unwrap()["document_id"] == "doc1"
    assert result.to_dict() == {
        "success": True,
        "data": {"document_id": "doc1", ...}
    }

def test_document_service_failure():
    service = DocumentService(index=None)  # No index
    result = await service.add_document("doc1", "content")
    
    assert result.is_failure()
    assert result.error == "Index not initialized"
    assert result.error_type == "InternalError"
    assert result.status_code == 500
```

### Integration Tests
```python
async def test_upload_endpoint():
    response = await client.post("/api/ingest", json={...})
    data = response.json()
    
    # Response always has this structure
    assert "success" in data
    if data["success"]:
        assert "data" in data
        assert "document_id" in data["data"]
    else:
        assert "error" in data
        assert "error_type" in data
```

## Rollback Plan

If needed, you can run both systems in parallel:

```python
async def add_document_legacy(self, ...) -> bool:
    """Legacy boolean return."""
    result = await self.add_document(...)
    return result.is_success()

async def add_document(self, ...) -> Result:
    """New Result return."""
    # ... implementation ...
```

## Next Steps

1. **Review this guide** - Make sure it fits your needs
2. **Start with one service** - I recommend DocumentService
3. **Update corresponding API routes** - Keep them in sync
4. **Test thoroughly** - Both success and failure cases
5. **Update UI gradually** - One component at a time

Would you like me to start implementing this? I can begin with:
1. Migrating DocumentService to use Result types
2. Updating the corresponding API routes
3. Creating example UI code for handling the new format

Let me know and I'll get started!
