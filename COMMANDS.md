# Life Archivist API Testing Commands

This file contains curl commands for testing all API endpoints during development.

## Quick Reference

### System Health
- [Server Health Check](#server-health-check)
- [Ollama Service Check](#ollama-service-check)
- [Ollama Model Test](#ollama-model-test)

### Document Management
- [Single File Ingest](#single-file-ingest-from-file-path)
- [File Upload & Ingest](#file-upload--ingest)
- [Bulk File Ingest](#bulk-file-ingest-from-file-paths)
- [List Documents](#list-documents)
- [Get Document Details](#get-document-details)

### Search & Retrieval
- [Keyword Search](#keyword-search)
- [Semantic Search](#semantic-search)
- [Hybrid Search](#hybrid-search)

### Q&A System
- [Ask Questions](#ask-questions-rag)
- [Different Question Types](#different-question-types)

### MCP Tools
- [Tool Execution](#direct-tool-execution)
- [Available Tools](#available-tools)

### Storage & Organization
- [Vault Information](#vault-information)
- [Tags Management](#tags-management)
- [Embeddings](#embeddings)

---

## System Health

### Server Health Check
```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```
**Tests**: Server startup, database connection, vault initialization

### Ollama Service Check
```bash
curl -s http://localhost:11434/api/tags | python3 -m json.tool
```
**Tests**: Ollama availability, installed models

### Ollama Model Test
```bash
curl -s -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{"model": "llama3.2:3b", "prompt": "Hello, how are you?", "stream": false}' | python3 -m json.tool
```
**Tests**: Model loading, text generation

---

## Document Management

### Single File Ingest (from file path)
```bash
# Create a test file first
echo "This is a test mortgage document about interest rates and loan terms." > /tmp/test_mortgage.txt

# Ingest the file from its path
curl -s -X POST http://localhost:8000/api/ingest -H "Content-Type: application/json" -d '{"path": "/tmp/test_mortgage.txt", "tags": ["test", "mortgage"], "metadata": {"source": "curl_test", "category": "financial"}}' | python3 -m json.tool

# Clean up
rm /tmp/test_mortgage.txt
```
**Tests**: File path ingestion, metadata handling, tags

### File Upload & Ingest
```bash
# Create a test file
echo "This is a test document about AI and machine learning concepts." > test_ai.txt

# Upload and ingest the file
curl -s -X POST http://localhost:8000/api/upload -F "file=@test_ai.txt" -F 'tags=["test", "ai", "machine-learning"]' -F 'metadata={"source": "curl_upload", "author": "tester"}' | python3 -m json.tool

# Clean up
rm test_ai.txt
```
**Tests**: File upload, ingestion pipeline, text extraction, auto-tagging, embedding generation

### Bulk File Ingest (from file paths)
```bash
# Create multiple test files
echo "Medical report about patient diagnosis and treatment plan." > /tmp/medical_report.txt
echo "Financial statement showing quarterly earnings and projections." > /tmp/financial_statement.txt
echo "Legal contract with terms and conditions for service agreement." > /tmp/legal_contract.txt

# Bulk ingest multiple files
curl -s -X POST http://localhost:8000/api/bulk-ingest -H "Content-Type: application/json" -d '{"file_paths": ["/Users/parthivnaresh/Documents/Personal/AccountStatements/2018/01_29.pdf", "/Users/parthivnaresh/Documents/Personal/AccountStatements/2018/02_26.pdf", "/Users/parthivnaresh/Documents/Personal/AccountStatements/2018/03_28.pdf", "/Users/parthivnaresh/Documents/Personal/AccountStatements/2018/04_26.pdf", "/Users/parthivnaresh/Documents/Personal/AccountStatements/2018/05_29.pdf", "/Users/parthivnaresh/Documents/Personal/AccountStatements/2018/06_27.pdf", "/Users/parthivnaresh/Documents/Personal/AccountStatements/2018/07_27.pdf", "/Users/parthivnaresh/Documents/Personal/AccountStatements/2018/08_29.pdf", "/Users/parthivnaresh/Documents/Personal/AccountStatements/2018/09_26.pdf", "/Users/parthivnaresh/Documents/Personal/AccountStatements/2018/10_29.pdf", "/Users/parthivnaresh/Documents/Personal/AccountStatements/2018/11_28.pdf", "/Users/parthivnaresh/Documents/Personal/AccountStatements/2018/12_27.pdf"], "folder_path": "/Users/parthivnaresh/Documents/Personal/AccountStatements/2018"}' | python3 -m json.tool
# Clean up
rm /tmp/medical_report.txt /tmp/financial_statement.txt /tmp/legal_contract.txt
```
**Tests**: Bulk ingestion, batch processing, error handling for multiple files

### List Documents
```bash
curl -s "http://localhost:8000/api/documents?limit=10" | python3 -m json.tool
```
**Tests**: Database queries, document metadata

### Get Document Details
```bash
# Replace DOCUMENT_ID with actual ID from upload response
curl -s "http://localhost:8000/api/documents/DOCUMENT_ID" | python3 -m json.tool
```
**Tests**: Document retrieval, metadata storage

---

## Search & Retrieval

### Keyword Search
```bash
curl -s "http://localhost:8000/api/search?q=mortgage&mode=keyword&limit=5" | python3 -m json.tool
```
**Tests**: Text search, BM25 ranking, database queries

### Semantic Search
```bash
curl -s "http://localhost:8000/api/search?q=mortgage%20interest%20rate&mode=semantic&limit=5" | python3 -m json.tool
```
**Tests**: Vector embeddings, similarity search, sentence-transformers

### Hybrid Search
```bash
curl -s "http://localhost:8000/api/search?q=loan&mode=hybrid&limit=5" | python3 -m json.tool
```
**Tests**: Combined keyword + semantic search

---

## Q&A System

### Ask Questions (RAG)
```bash
curl -s -X POST http://localhost:8000/api/ask -H "Content-Type: application/json" -d '{"question": "What is my mortgage interest rate?", "context_limit": 5}' | python3 -m json.tool
```
**Tests**: RAG pipeline, document retrieval, Ollama integration, answer generation

### Different Question Types
```bash
# Direct question
curl -s -X POST http://localhost:8000/api/ask -H "Content-Type: application/json" -d '{"question": "How much is the loan amount?"}' | python3 -m json.tool

# Summarization request
curl -s -X POST http://localhost:8000/api/ask -H "Content-Type: application/json" -d '{"question": "Summarize the key terms of my mortgage"}' | python3 -m json.tool
```
**Tests**: Question detection, context preparation, LLM prompting

---

## MCP Tools

### Direct Tool Execution

#### LlamaIndex Query Tool
```bash
curl -s -X POST http://localhost:8000/api/tools/execute -H "Content-Type: application/json" -d '{"tool": "llamaindex.query", "params": {"question": "What are the key points about mortgages?", "similarity_top_k": 3}}' | python3 -m json.tool
```

#### Ollama Tool
```bash
curl -s -X POST http://localhost:8000/api/tools/execute -H "Content-Type: application/json" -d '{"tool": "llm.ollama", "params": {"prompt": "What is 2+2?", "temperature": 0.1}}' | python3 -m json.tool
```

#### File Import Tool
```bash
curl -s -X POST http://localhost:8000/api/tools/execute -H "Content-Type: application/json" -d '{"tool": "file.import", "params": {"path": "/path/to/document.pdf", "tags": ["imported"], "metadata": {"source": "tool_test"}}}' | python3 -m json.tool
```

#### Text Extraction Tool
```bash
curl -s -X POST http://localhost:8000/api/tools/execute -H "Content-Type: application/json" -d '{"tool": "extract.text", "params": {"file_id": "DOCUMENT_ID"}}' | python3 -m json.tool
```

### Available Tools
```bash
curl -s http://localhost:8000/api/tools | python3 -m json.tool
```
**Tests**: Tool registry, available tools listing

---

## Storage & Organization

### Vault Information
```bash
# Get vault statistics
curl -s http://localhost:8000/api/vault/info | python3 -m json.tool

# List vault files
curl -s "http://localhost:8000/api/vault/files?directory=content&limit=10" | python3 -m json.tool
```
**Tests**: File storage, vault directory structure, content-addressed storage

### Tags Management
```bash
# Get all tags
curl -s http://localhost:8000/api/tags | python3 -m json.tool

# Re-tag a document
curl -s -X POST "http://localhost:8000/api/documents/DOCUMENT_ID/retag" | python3 -m json.tool
```
**Tests**: Auto-tagging system, tag storage

### Embeddings
```bash
# Check embedding statistics
curl -s http://localhost:8000/api/embeddings/stats | python3 -m json.tool

# List actual embeddings
curl -s "http://localhost:8000/api/embeddings?limit=5" | python3 -m json.tool
```
**Tests**: Embedding generation, vector storage, chunking system

---

## Debugging Common Issues

### Q&A Returns "no_context"
1. **Check if semantic search works:**
   ```bash
   curl -s "http://localhost:8000/api/search?q=mortgage&mode=semantic&limit=5" | python3 -m json.tool
   ```

2. **Test LlamaIndex query tool directly:**
   ```bash
   curl -s -X POST http://localhost:8000/api/tools/execute -H "Content-Type: application/json" -d '{"tool": "llamaindex.query", "params": {"question": "mortgage interest rate", "similarity_top_k": 5}}' | python3 -m json.tool
   ```

3. **Verify Ollama is working:**
   ```bash
   curl -s -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{"model": "llama3.2:3b", "prompt": "What is 2+2?", "stream": false}' | python3 -m json.tool
   ```

4. **Test Ollama tool with error handling:**
   ```bash
   curl -s -X POST http://localhost:8000/api/tools/execute -H "Content-Type: application/json" -d '{"tool": "llm.ollama", "params": {"prompt": "Hello", "temperature": 0.1}}' | python3 -m json.tool
   ```

### File Upload/Ingest Issues
1. **Check server health first:**
   ```bash
   curl -s http://localhost:8000/health | python3 -m json.tool
   ```

2. **Test with simple text file:**
   ```bash
   echo "Simple test content" > simple_test.txt
   curl -s -X POST http://localhost:8000/api/upload -F "file=@simple_test.txt" | python3 -m json.tool
   rm simple_test.txt
   ```

3. **Check vault status:**
   ```bash
   curl -s http://localhost:8000/api/vault/info | python3 -m json.tool
   ```

### Tool Execution Failures
1. **List available tools:**
   ```bash
   curl -s http://localhost:8000/api/tools | python3 -m json.tool
   ```

2. **Test basic tool first:**
   ```bash
   curl -s -X POST http://localhost:8000/api/tools/execute -H "Content-Type: application/json" -d '{"tool": "llm.ollama", "params": {"prompt": "test"}}' | python3 -m json.tool
   ```

---

## Example Workflow

### Complete Document Processing Test
```bash
#!/bin/bash
# Complete workflow test script

echo "1. Check server health"
curl -s http://localhost:8000/health | python3 -m json.tool

echo -e "\n2. Create test document"
echo "This is a comprehensive mortgage document discussing loan terms, interest rates, monthly payments, and closing procedures." > test_comprehensive.txt

echo -e "\n3. Upload and ingest document"
RESPONSE=$(curl -s -X POST http://localhost:8000/api/upload -F "file=@test_comprehensive.txt" -F 'tags=["test", "mortgage", "comprehensive"]' -F 'metadata={"source": "workflow_test"}')
echo "$RESPONSE" | python3 -m json.tool

echo -e "\n4. Extract document ID"
DOC_ID=$(echo "$RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin)['file_id'])")
echo "Document ID: $DOC_ID"

echo -e "\n5. Wait for processing (5 seconds)"
sleep 5

echo -e "\n6. Get document details"
curl -s "http://localhost:8000/api/documents/$DOC_ID" | python3 -m json.tool

echo -e "\n7. Test semantic search"
curl -s "http://localhost:8000/api/search?q=mortgage%20interest&mode=semantic&limit=3" | python3 -m json.tool

echo -e "\n8. Ask question about document"
curl -s -X POST http://localhost:8000/api/ask -H "Content-Type: application/json" -d '{"question": "What are the key mortgage terms?"}' | python3 -m json.tool

echo -e "\n9. Clean up"
rm test_comprehensive.txt

echo -e "\nWorkflow test complete!"
```

This workflow tests the complete document lifecycle from ingestion to querying.