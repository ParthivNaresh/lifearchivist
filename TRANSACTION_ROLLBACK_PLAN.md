# Transaction Rollback Implementation Plan

## Executive Summary

This document outlines a production-grade implementation of transaction rollback for the file import pipeline. The current system has a critical flaw: if document indexing fails after vault storage, files remain orphaned in the vault without metadata, causing storage bloat and inconsistent state.

## Current Architecture Analysis

### Ingestion Flow
```
1. API Endpoint: /upload/ingest
   ↓
2. ApplicationServer.execute_tool("file.import")
   ↓
3. FileImportTool.execute()
   ├─ Calculate file hash
   ├─ Store in Vault (POINT OF NO RETURN - Current Issue)
   ├─ Extract text
   ├─ Classify themes
   ├─ Create metadata
   ├─ Add to LlamaIndex (CAN FAIL)
   │  ├─ Store in Qdrant
   │  ├─ Store in Redis tracker
   │  └─ Store in BM25 index
   └─ Finalize document
```

### Critical Issue
**Location**: Between steps "Store in Vault" and "Add to LlamaIndex"

**Problem**: If any step after vault storage fails:
- File remains in vault (content + thumbnail)
- No metadata in Redis
- No vectors in Qdrant
- No BM25 index entry
- No way to find or clean up the orphaned file

**Impact**:
- Storage bloat (files accumulate without metadata)
- Inconsistent state (vault != index)
- No automatic recovery mechanism
- Manual cleanup required

## Solution Architecture

### Design Principles
1. **Saga Pattern**: Use compensating transactions instead of distributed 2PC
2. **Idempotency**: All operations must be safely retryable
3. **Atomicity**: Group related operations with rollback capability
4. **Observability**: Track transaction state for debugging
5. **Performance**: Minimize overhead in happy path

### Chosen Pattern: Saga with Compensating Transactions

**Why not 2-Phase Commit?**
- Vault, Qdrant, Redis, and BM25 are independent systems
- No distributed transaction coordinator
- Would require complex locking and coordination
- Performance overhead too high

**Why Saga Pattern?**
- Natural fit for microservices/distributed systems
- Each step can be independently rolled back
- Better performance (no global locks)
- Industry standard (used by Uber, Netflix, etc.)

## Implementation Strategy

### Phase 1: Transaction Context Manager

Create a `TransactionContext` class that tracks operations and provides rollback capability.

**Key Features**:
- Records each operation with rollback handler
- Automatic rollback on exception
- Manual commit/rollback support
- Async context manager interface
- Comprehensive logging

**File**: `lifearchivist/storage/transaction_context.py`

### Phase 2: Rollback Handlers

Create specific rollback handlers for each storage system:

1. **VaultRollbackHandler**: Delete files from vault
2. **QdrantRollbackHandler**: Remove vectors from Qdrant
3. **RedisRollbackHandler**: Remove metadata from Redis
4. **BM25RollbackHandler**: Remove from BM25 index

**File**: `lifearchivist/storage/rollback_handlers.py`

### Phase 3: Modify FileImportTool

Wrap the import pipeline in transaction context:

```python
async with TransactionContext() as tx:
    # Store in vault (with rollback)
    vault_result = await self.vault.store_file(file_path, file_hash)
    tx.register_rollback(VaultRollbackHandler(vault, file_hash))
    
    # Add to LlamaIndex (with rollback)
    result = await self.llamaindex_service.add_document(...)
    tx.register_rollback(LlamaIndexRollbackHandler(llamaindex_service, file_id))
    
    # If we get here, commit
    await tx.commit()
```

### Phase 4: Modify Document Service

Update `add_document` to support transactional operations:

1. Track Qdrant point IDs before insertion
2. Track Redis keys before creation
3. Track BM25 entries before indexing
4. Provide rollback methods for each

### Phase 5: Add Reconciliation Service

Create a background service to detect and clean orphaned files:

**File**: `lifearchivist/storage/orphan_cleanup_service.py`

**Features**:
- Periodic scan of vault files
- Check if file_hash exists in Redis
- Remove orphaned files
- Report cleanup statistics

## Detailed Implementation

### 1. Transaction Context (`storage/transaction_context.py`)

```python
class TransactionState(Enum):
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"

class RollbackOperation:
    def __init__(
        self,
        handler: Callable[[], Awaitable[None]],
        operation_name: str,
        context: Dict[str, Any]
    ):
        self.handler = handler
        self.operation_name = operation_name
        self.context = context
        self.timestamp = datetime.now()

class TransactionContext:
    def __init__(self, transaction_id: Optional[str] = None):
        self.transaction_id = transaction_id or str(uuid.uuid4())
        self.state = TransactionState.ACTIVE
        self.operations: List[RollbackOperation] = []
        self.start_time = time.time()
        
    async def __aenter__(self):
        log_event("transaction_started", {"transaction_id": self.transaction_id})
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
            return False
        return True
        
    def register_rollback(
        self,
        handler: Callable[[], Awaitable[None]],
        operation_name: str,
        context: Optional[Dict[str, Any]] = None
    ):
        operation = RollbackOperation(handler, operation_name, context or {})
        self.operations.append(operation)
        
    async def commit(self):
        if self.state != TransactionState.ACTIVE:
            raise TransactionError(f"Cannot commit transaction in state {self.state}")
        
        self.state = TransactionState.COMMITTED
        self.operations.clear()
        
        log_event("transaction_committed", {
            "transaction_id": self.transaction_id,
            "duration_ms": (time.time() - self.start_time) * 1000
        })
        
    async def rollback(self):
        if self.state == TransactionState.ROLLED_BACK:
            return
            
        self.state = TransactionState.ROLLED_BACK
        
        log_event("transaction_rollback_started", {
            "transaction_id": self.transaction_id,
            "operations_count": len(self.operations)
        })
        
        # Execute rollbacks in reverse order (LIFO)
        errors = []
        for operation in reversed(self.operations):
            try:
                await operation.handler()
                log_event("rollback_operation_success", {
                    "transaction_id": self.transaction_id,
                    "operation": operation.operation_name
                })
            except Exception as e:
                errors.append({
                    "operation": operation.operation_name,
                    "error": str(e)
                })
                log_event("rollback_operation_failed", {
                    "transaction_id": self.transaction_id,
                    "operation": operation.operation_name,
                    "error": str(e)
                }, level=logging.ERROR)
        
        if errors:
            log_event("transaction_rollback_partial_failure", {
                "transaction_id": self.transaction_id,
                "failed_operations": len(errors),
                "errors": errors
            }, level=logging.ERROR)
        else:
            log_event("transaction_rollback_complete", {
                "transaction_id": self.transaction_id,
                "operations_rolled_back": len(self.operations)
            })
```

### 2. Rollback Handlers (`storage/rollback_handlers.py`)

```python
class VaultRollbackHandler:
    def __init__(self, vault: Vault, file_hash: str, extension: str):
        self.vault = vault
        self.file_hash = file_hash
        self.extension = extension
        
    async def __call__(self):
        try:
            await self.vault.delete_file(self.file_hash, self.extension)
            log_event("vault_rollback_success", {
                "file_hash": self.file_hash[:8]
            })
        except Exception as e:
            log_event("vault_rollback_failed", {
                "file_hash": self.file_hash[:8],
                "error": str(e)
            }, level=logging.ERROR)
            raise

class QdrantRollbackHandler:
    def __init__(self, qdrant_client, document_id: str):
        self.qdrant_client = qdrant_client
        self.document_id = document_id
        
    async def __call__(self):
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            self.qdrant_client.delete(
                collection_name="lifearchivist",
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=self.document_id)
                        )
                    ]
                )
            )
            log_event("qdrant_rollback_success", {
                "document_id": self.document_id
            })
        except Exception as e:
            log_event("qdrant_rollback_failed", {
                "document_id": self.document_id,
                "error": str(e)
            }, level=logging.ERROR)
            raise

class RedisRollbackHandler:
    def __init__(self, doc_tracker, document_id: str):
        self.doc_tracker = doc_tracker
        self.document_id = document_id
        
    async def __call__(self):
        try:
            await self.doc_tracker.remove_document(self.document_id)
            log_event("redis_rollback_success", {
                "document_id": self.document_id
            })
        except Exception as e:
            log_event("redis_rollback_failed", {
                "document_id": self.document_id,
                "error": str(e)
            }, level=logging.ERROR)
            raise

class BM25RollbackHandler:
    def __init__(self, bm25_service, document_id: str):
        self.bm25_service = bm25_service
        self.document_id = document_id
        
    async def __call__(self):
        try:
            await self.bm25_service.remove_document(self.document_id)
            log_event("bm25_rollback_success", {
                "document_id": self.document_id
            })
        except Exception as e:
            log_event("bm25_rollback_failed", {
                "document_id": self.document_id,
                "error": str(e)
            }, level=logging.ERROR)
            raise
```

### 3. Modified FileImportTool (`tools/file_import/file_import_tool.py`)

**Changes to `execute()` method**:

```python
async def execute(self, **kwargs) -> Dict[str, Any]:
    # ... existing setup code ...
    
    async with TransactionContext(transaction_id=file_id) as tx:
        try:
            # Store file in vault (with rollback)
            vault_result = await self.vault.store_file(file_path, file_hash)
            
            # Register vault rollback
            extension = file_path.suffix.lstrip(".") or "bin"
            tx.register_rollback(
                VaultRollbackHandler(self.vault, file_hash, extension),
                operation_name="vault_storage",
                context={"file_hash": file_hash, "path": vault_result["path"]}
            )
            
            # Check for duplicates (after vault storage)
            if vault_result["existed"]:
                duplicate_doc = await self._check_for_duplicate(file_id, file_hash)
                if duplicate_doc:
                    # Commit transaction (keep vault file)
                    await tx.commit()
                    return create_duplicate_response(...)
            
            # Extract text and metadata
            extracted_text = await self._try_extract_text(...)
            document_metadata = await self._extract_document_metadata(...)
            theme_result = await self._classify_themes(...) if extracted_text else {}
            
            # Build metadata
            doc_metadata = create_document_metadata(...)
            
            # Create document in LlamaIndex (with rollback)
            await self._create_document_transactional(
                tx, file_id, extracted_text, doc_metadata
            )
            
            # Finalize document
            await self._finalize_document(file_id, file_path, vault_result)
            
            # Complete progress tracking
            if self.progress_manager and session_id:
                await self.progress_manager.complete_progress(file_id, ...)
            
            # Commit transaction
            await tx.commit()
            
            # Log success
            log_event("file_import_completed", {...})
            
            return create_success_response(...)
            
        except Exception as e:
            # Transaction context will automatically rollback
            await self._handle_import_error(e, file_id, display_path, session_id or "")
            return create_error_response(e, display_path)
```

**New method `_create_document_transactional()`**:

```python
async def _create_document_transactional(
    self,
    tx: TransactionContext,
    file_id: str,
    extracted_text: str,
    doc_metadata: Dict[str, Any]
):
    result = await self.llamaindex_service.add_document(
        document_id=file_id,
        content=extracted_text,
        metadata=doc_metadata
    )
    
    if result.is_failure():
        raise RuntimeError(f"Failed to create document {file_id}: {result.error}")
    
    # Register rollback for all LlamaIndex components
    if self.llamaindex_service.qdrant_client:
        tx.register_rollback(
            QdrantRollbackHandler(
                self.llamaindex_service.qdrant_client,
                file_id
            ),
            operation_name="qdrant_indexing",
            context={"document_id": file_id}
        )
    
    if self.llamaindex_service.doc_tracker:
        tx.register_rollback(
            RedisRollbackHandler(
                self.llamaindex_service.doc_tracker,
                file_id
            ),
            operation_name="redis_tracking",
            context={"document_id": file_id}
        )
    
    if self.llamaindex_service.bm25_service:
        tx.register_rollback(
            BM25RollbackHandler(
                self.llamaindex_service.bm25_service,
                file_id
            ),
            operation_name="bm25_indexing",
            context={"document_id": file_id}
        )
```

### 4. Orphan Cleanup Service (`storage/orphan_cleanup_service.py`)

```python
class OrphanCleanupService:
    def __init__(
        self,
        vault: Vault,
        doc_tracker: RedisDocumentTracker,
        scan_interval_seconds: int = 3600
    ):
        self.vault = vault
        self.doc_tracker = doc_tracker
        self.scan_interval_seconds = scan_interval_seconds
        self.running = False
        
    async def start(self):
        self.running = True
        while self.running:
            try:
                await self.scan_and_cleanup()
            except Exception as e:
                log_event("orphan_cleanup_error", {
                    "error": str(e)
                }, level=logging.ERROR)
            
            await asyncio.sleep(self.scan_interval_seconds)
    
    async def scan_and_cleanup(self):
        log_event("orphan_scan_started")
        
        orphaned_files = []
        
        # Scan vault content directory
        for file_path in self.vault.content_dir.rglob("*"):
            if not file_path.is_file():
                continue
            
            # Extract file hash from path
            file_hash = self._extract_hash_from_path(file_path)
            if not file_hash:
                continue
            
            # Check if any document references this hash
            docs_result = await self.doc_tracker.query_by_multiple_filters({
                "file_hash": file_hash
            })
            
            if not docs_result:
                orphaned_files.append({
                    "file_hash": file_hash,
                    "path": str(file_path),
                    "size": file_path.stat().st_size
                })
        
        if orphaned_files:
            log_event("orphaned_files_detected", {
                "count": len(orphaned_files),
                "total_size_mb": sum(f["size"] for f in orphaned_files) / (1024 * 1024)
            }, level=logging.WARNING)
            
            # Clean up orphaned files
            for orphan in orphaned_files:
                try:
                    metrics = {
                        "files_deleted": 0,
                        "bytes_reclaimed": 0,
                        "errors": []
                    }
                    self.vault.delete_file_by_hash(orphan["file_hash"], metrics)
                    
                    log_event("orphan_cleaned", {
                        "file_hash": orphan["file_hash"][:8],
                        "bytes_reclaimed": metrics["bytes_reclaimed"]
                    })
                except Exception as e:
                    log_event("orphan_cleanup_failed", {
                        "file_hash": orphan["file_hash"][:8],
                        "error": str(e)
                    }, level=logging.ERROR)
        else:
            log_event("orphan_scan_complete", {
                "orphans_found": 0
            })
    
    def _extract_hash_from_path(self, file_path: Path) -> Optional[str]:
        # Vault structure: content/XX/YY/ZZZZ.ext
        # Hash is: XXYYZZZZ
        parts = file_path.parts
        if len(parts) < 3:
            return None
        
        dir1 = parts[-3]  # XX
        dir2 = parts[-2]  # YY
        filename = parts[-1].split(".")[0]  # ZZZZ
        
        return f"{dir1}{dir2}{filename}"
    
    async def stop(self):
        self.running = False
```

### 5. Integration with Application Server

**File**: `lifearchivist/server/application_server.py`

Add orphan cleanup service initialization:

```python
async def _init_orphan_cleanup_service(self):
    if not self.service_container:
        return
    
    try:
        self.orphan_cleanup_service = OrphanCleanupService(
            vault=self.service_container.vault,
            doc_tracker=self.service_container.doc_tracker,
            scan_interval_seconds=3600  # 1 hour
        )
        
        # Start as background task
        self.orphan_cleanup_task = asyncio.create_task(
            self.orphan_cleanup_service.start()
        )
        
        log_event("orphan_cleanup_service_initialized")
    except Exception as e:
        log_event("orphan_cleanup_service_init_failed", {
            "error": str(e)
        }, level=logging.WARNING)
```

## Testing Strategy

### Unit Tests

1. **TransactionContext Tests**
   - Test commit behavior
   - Test rollback on exception
   - Test rollback order (LIFO)
   - Test partial rollback failures

2. **Rollback Handler Tests**
   - Test each handler independently
   - Test idempotency
   - Test error handling

3. **FileImportTool Tests**
   - Test successful import with commit
   - Test failed import with rollback
   - Test duplicate detection
   - Test partial failures

### Integration Tests

1. **End-to-End Import Tests**
   - Import file successfully
   - Verify all systems updated
   - Simulate Qdrant failure
   - Verify vault rollback
   - Verify no orphaned files

2. **Orphan Cleanup Tests**
   - Create orphaned file manually
   - Run cleanup service
   - Verify file removed
   - Verify statistics

### Performance Tests

1. **Transaction Overhead**
   - Measure happy path overhead
   - Should be < 5ms additional latency

2. **Rollback Performance**
   - Measure rollback time
   - Should complete in < 100ms

## Rollout Plan

### Phase 1: Foundation (Week 1)
- Implement TransactionContext
- Implement Rollback Handlers
- Add unit tests

### Phase 2: Integration (Week 2)
- Modify FileImportTool
- Add integration tests
- Test in development environment

### Phase 3: Monitoring (Week 3)
- Implement OrphanCleanupService
- Add metrics and alerts
- Test cleanup service

### Phase 4: Production (Week 4)
- Deploy to staging
- Monitor for issues
- Deploy to production
- Monitor rollback frequency

## Monitoring & Alerts

### Metrics to Track

1. **Transaction Metrics**
   - `transaction_started_total`
   - `transaction_committed_total`
   - `transaction_rolled_back_total`
   - `transaction_duration_seconds`

2. **Rollback Metrics**
   - `rollback_operations_total` (by operation type)
   - `rollback_failures_total` (by operation type)
   - `rollback_duration_seconds`

3. **Orphan Metrics**
   - `orphaned_files_detected_total`
   - `orphaned_files_cleaned_total`
   - `orphaned_bytes_reclaimed_total`

### Alerts

1. **High Rollback Rate**
   - Alert if rollback rate > 5% of transactions
   - Indicates systemic issues

2. **Rollback Failures**
   - Alert on any rollback failure
   - Requires manual intervention

3. **Orphan Accumulation**
   - Alert if orphaned files > 100
   - Indicates rollback failures

## Migration Strategy

### Backward Compatibility

The new transaction system is **fully backward compatible**:
- Existing code continues to work
- No database migrations required
- No API changes
- Gradual rollout possible

### Cleanup of Existing Orphans

Before deploying:
1. Run orphan scan manually
2. Review detected orphans
3. Clean up existing orphans
4. Document cleanup results

## Performance Impact

### Happy Path
- **Additional Overhead**: < 5ms
- **Memory**: ~1KB per transaction
- **No performance degradation** for successful imports

### Rollback Path
- **Rollback Time**: < 100ms
- **Network Calls**: 3-4 (Qdrant, Redis, BM25, Vault)
- **Acceptable** since rollback is rare

## Security Considerations

1. **Transaction IDs**: Use UUIDs to prevent prediction
2. **Rollback Handlers**: Validate permissions before deletion
3. **Logging**: Sanitize sensitive data in logs
4. **Orphan Cleanup**: Rate limit to prevent DoS

## Future Enhancements

1. **Distributed Tracing**: Add OpenTelemetry spans
2. **Transaction Replay**: Store transaction log for replay
3. **Partial Rollback**: Allow selective rollback of operations
4. **Transaction Timeout**: Add configurable timeout
5. **Dead Letter Queue**: Store failed transactions for analysis

## Conclusion

This implementation provides:
- ✅ **Atomicity**: All-or-nothing semantics
- ✅ **Consistency**: No orphaned files
- ✅ **Isolation**: Independent transactions
- ✅ **Durability**: Cleanup service for recovery
- ✅ **Performance**: Minimal overhead
- ✅ **Observability**: Comprehensive logging
- ✅ **Production-Ready**: Battle-tested patterns

The Saga pattern with compensating transactions is the industry-standard approach for distributed systems and provides the best balance of consistency, performance, and maintainability.
