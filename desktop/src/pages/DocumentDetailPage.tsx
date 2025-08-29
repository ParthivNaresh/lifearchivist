import React, { useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileText, Database, Search, Activity, Copy, ExternalLink, RefreshCw, AlertCircle } from 'lucide-react';
import { useCache } from '../hooks/useCache';
import axios from 'axios';

interface DocumentAnalysis {
  document_id: string;
  status: string;
  original_metadata: Record<string, any>;
  processing_info: {
    total_chunks: number;
    total_tokens: number;
    avg_chunk_size: number;
    embedding_model: string;
    embedding_dimension: number;
  };
  storage_info: {
    docstore_type: string;
    vector_store_type: string;
    text_splitter: string;
  };
  chunks_preview: Array<{
    node_id: string;
    text: string;
    metadata: Record<string, any>;
  }>;
}

interface DocumentChunk {
  chunk_index: number;
  node_id: string;
  text: string;
  text_length: number;
  word_count: number;
  start_char: number | null;
  end_char: number | null;
  metadata: Record<string, any>;
  relationships: Record<string, any>;
}

interface DocumentChunksResponse {
  document_id: string;
  chunks: DocumentChunk[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

interface DocumentNeighbor {
  document_id: string;
  similarity_score: number;
  text_preview: string;
  metadata: Record<string, any>;
}

interface DocumentNeighborsResponse {
  document_id: string;
  neighbors: DocumentNeighbor[];
  total_found: number;
  query_text: string;
}

const DocumentDetailPage: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('analysis');
  const [chunksPage, setChunksPage] = useState(0);
  const [copySuccess, setCopySuccess] = useState('');

  const fetchAnalysis = useCallback(async () => {
    if (!documentId) throw new Error('Document ID required');
    const response = await axios.get<DocumentAnalysis>(`http://localhost:8000/api/documents/${documentId}/llamaindex-analysis`);
    return response.data;
  }, [documentId]);

  const fetchChunks = useCallback(async () => {
    if (!documentId) throw new Error('Document ID required');
    const response = await axios.get<DocumentChunksResponse>(
      `http://localhost:8000/api/documents/${documentId}/llamaindex-chunks?limit=20&offset=${chunksPage * 20}`
    );
    return response.data;
  }, [documentId, chunksPage]);

  const fetchNeighbors = useCallback(async () => {
    if (!documentId) throw new Error('Document ID required');
    const response = await axios.get<DocumentNeighborsResponse>(`http://localhost:8000/api/documents/${documentId}/llamaindex-neighbors?top_k=10`);
    return response.data;
  }, [documentId]);

  const { data: analysis, loading: analysisLoading, error: analysisError, refresh: refreshAnalysis } = useCache(
    `document-analysis-${documentId}`,
    fetchAnalysis,
    5 * 60 * 1000 // 5 minute cache
  );

  const { data: chunks, loading: chunksLoading, error: chunksError, refresh: refreshChunks } = useCache(
    `document-chunks-${documentId}-${chunksPage}`,
    fetchChunks,
    5 * 60 * 1000 // 5 minute cache
  );

  const { data: neighbors, loading: neighborsLoading, error: neighborsError, refresh: refreshNeighbors } = useCache(
    `document-neighbors-${documentId}`,
    fetchNeighbors,
    5 * 60 * 1000 // 5 minute cache
  );

  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopySuccess(`${label} copied!`);
      setTimeout(() => setCopySuccess(''), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const formatNumber = (num: number) => {
    return num.toLocaleString();
  };

  const tabs = [
    { id: 'analysis', label: 'Overview', icon: FileText },
    { id: 'chunks', label: 'Chunks', icon: Database },
    { id: 'neighbors', label: 'Similar Docs', icon: Search },
    { id: 'debug', label: 'Debug', icon: Activity },
  ];

  if (!documentId) {
    return (
      <div className="p-6">
        <div className="text-center">
          <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
          <p className="text-red-600">Document ID is required</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate('/documents')}
              className="p-2 hover:bg-muted rounded-md transition-colors"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div>
              <h1 className="text-2xl font-bold">Document Analysis</h1>
              <p className="text-sm text-muted-foreground font-mono">{documentId}</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {copySuccess && (
              <span className="text-sm text-green-600">{copySuccess}</span>
            )}
            <button
              onClick={() => copyToClipboard(documentId, 'Document ID')}
              className="p-2 hover:bg-muted rounded-md transition-colors"
              title="Copy Document ID"
            >
              <Copy className="h-4 w-4" />
            </button>
            <button
              onClick={() => {
                refreshAnalysis();
                refreshChunks();
                refreshNeighbors();
              }}
              className="p-2 hover:bg-muted rounded-md transition-colors"
              title="Refresh All Data"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-border mb-6">
          <nav className="flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground'
                }`}
              >
                <tab.icon className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'analysis' && (
          <AnalysisTab 
            analysis={analysis} 
            loading={analysisLoading} 
            error={analysisError}
            onRefresh={refreshAnalysis}
          />
        )}

        {activeTab === 'chunks' && (
          <ChunksTab 
            chunks={chunks} 
            loading={chunksLoading} 
            error={chunksError}
            page={chunksPage}
            onPageChange={setChunksPage}
            onRefresh={refreshChunks}
            onCopy={copyToClipboard}
          />
        )}

        {activeTab === 'neighbors' && (
          <NeighborsTab 
            neighbors={neighbors} 
            loading={neighborsLoading} 
            error={neighborsError}
            onRefresh={refreshNeighbors}
            onNavigate={(docId) => navigate(`/documents/${docId}/details`)}
          />
        )}

        {activeTab === 'debug' && (
          <DebugTab 
            analysis={analysis}
            chunks={chunks}
            neighbors={neighbors}
            documentId={documentId}
            onCopy={copyToClipboard}
          />
        )}
      </div>
    </div>
  );
};

// Analysis Tab Component
const AnalysisTab: React.FC<{
  analysis: DocumentAnalysis | undefined;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}> = ({ analysis, loading, error, onRefresh }) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="mt-2 text-muted-foreground">Loading analysis...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
        <p className="text-red-600 mb-4">{error}</p>
        <button 
          onClick={onRefresh}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="text-center py-12">
        <FileText className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
        <p className="text-muted-foreground">No analysis data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Status */}
      <div className="glass-card p-4 rounded-lg">
        <h3 className="text-lg font-semibold mb-3">Document Status</h3>
        <div className="flex items-center space-x-2">
          <span className={`inline-flex items-center px-2 py-1 rounded-full text-sm font-medium ${
            analysis.status === 'indexed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
          }`}>
            {analysis.status}
          </span>
        </div>
      </div>

      {/* Processing Info */}
      <div className="glass-card p-4 rounded-lg">
        <h3 className="text-lg font-semibold mb-3">Processing Information</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-muted/30 rounded">
            <div className="text-2xl font-bold text-primary">{analysis.processing_info.total_chunks}</div>
            <div className="text-sm text-muted-foreground">Chunks</div>
          </div>
          <div className="text-center p-3 bg-muted/30 rounded">
            <div className="text-2xl font-bold text-primary">{analysis.processing_info.total_tokens.toLocaleString()}</div>
            <div className="text-sm text-muted-foreground">Tokens</div>
          </div>
          <div className="text-center p-3 bg-muted/30 rounded">
            <div className="text-2xl font-bold text-primary">{analysis.processing_info.avg_chunk_size}</div>
            <div className="text-sm text-muted-foreground">Avg Chunk Size</div>
          </div>
          <div className="text-center p-3 bg-muted/30 rounded">
            <div className="text-2xl font-bold text-primary">{analysis.processing_info.embedding_dimension}</div>
            <div className="text-sm text-muted-foreground">Embedding Dim</div>
          </div>
        </div>
      </div>

      {/* Storage Info */}
      <div className="glass-card p-4 rounded-lg">
        <h3 className="text-lg font-semibold mb-3">Storage Information</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Document Store:</span>
            <span className="font-mono">{analysis.storage_info.docstore_type}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Vector Store:</span>
            <span className="font-mono">{analysis.storage_info.vector_store_type}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Text Splitter:</span>
            <span className="font-mono">{analysis.storage_info.text_splitter}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Embedding Model:</span>
            <span className="font-mono">{analysis.processing_info.embedding_model}</span>
          </div>
        </div>
      </div>

      {/* Chunks Preview */}
      {analysis.chunks_preview && analysis.chunks_preview.length > 0 && (
        <div className="glass-card p-4 rounded-lg">
          <h3 className="text-lg font-semibold mb-3">Chunk Preview (First 3)</h3>
          <div className="space-y-3">
            {analysis.chunks_preview.map((chunk, index) => (
              <div key={index} className="p-3 bg-muted/30 rounded border-l-4 border-primary">
                <div className="text-xs text-muted-foreground mb-1">
                  Node ID: <span className="font-mono">{chunk.node_id}</span>
                </div>
                <div className="text-sm">{chunk.text.slice(0, 200)}...</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Chunks Tab Component
const ChunksTab: React.FC<{
  chunks: DocumentChunksResponse | undefined;
  loading: boolean;
  error: string | null;
  page: number;
  onPageChange: (page: number) => void;
  onRefresh: () => void;
  onCopy: (text: string, label: string) => void;
}> = ({ chunks, loading, error, page, onPageChange, onRefresh, onCopy }) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="mt-2 text-muted-foreground">Loading chunks...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
        <p className="text-red-600 mb-4">{error}</p>
        <button 
          onClick={onRefresh}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!chunks || chunks.chunks.length === 0) {
    return (
      <div className="text-center py-12">
        <Database className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
        <p className="text-muted-foreground">No chunks found</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Pagination Info */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Showing {chunks.chunks.length} of {chunks.total} chunks (Page {page + 1})
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => onPageChange(Math.max(0, page - 1))}
            disabled={page === 0}
            className="px-3 py-1 bg-muted text-muted-foreground rounded disabled:opacity-50"
          >
            Previous
          </button>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={!chunks.has_more}
            className="px-3 py-1 bg-muted text-muted-foreground rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>

      {/* Chunks List */}
      <div className="space-y-4">
        {chunks.chunks.map((chunk, index) => (
          <div key={chunk.node_id} className="glass-card p-4 rounded-lg">
            <div className="flex items-start justify-between mb-3">
              <div className="text-sm text-muted-foreground">
                <span className="font-semibold">Chunk #{chunk.chunk_index}</span>
                <span className="ml-4">{chunk.word_count} words</span>
                <span className="ml-4">{chunk.text_length} chars</span>
              </div>
              <button
                onClick={() => onCopy(chunk.text, 'Chunk text')}
                className="p-1 hover:bg-muted rounded"
                title="Copy chunk text"
              >
                <Copy className="h-4 w-4" />
              </button>
            </div>
            
            <div className="prose prose-sm max-w-none">
              <p className="whitespace-pre-wrap">{chunk.text}</p>
            </div>
            
            <div className="mt-3 pt-3 border-t border-border/30">
              <div className="text-xs text-muted-foreground">
                <span className="font-mono">Node ID: {chunk.node_id}</span>
                {chunk.start_char !== null && chunk.end_char !== null && (
                  <span className="ml-4">Position: {chunk.start_char}-{chunk.end_char}</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Neighbors Tab Component
const NeighborsTab: React.FC<{
  neighbors: DocumentNeighborsResponse | undefined;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  onNavigate: (documentId: string) => void;
}> = ({ neighbors, loading, error, onRefresh, onNavigate }) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="mt-2 text-muted-foreground">Finding similar documents...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
        <p className="text-red-600 mb-4">{error}</p>
        <button 
          onClick={onRefresh}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!neighbors || neighbors.neighbors.length === 0) {
    return (
      <div className="text-center py-12">
        <Search className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
        <p className="text-muted-foreground">No similar documents found</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="glass-card p-4 rounded-lg bg-muted/30">
        <h3 className="text-sm font-semibold mb-2">Query Text Used for Similarity</h3>
        <p className="text-sm text-muted-foreground italic">"{neighbors.query_text}"</p>
      </div>

      <div className="space-y-3">
        {neighbors.neighbors.map((neighbor, index) => (
          <div key={index} className="glass-card p-4 rounded-lg hover:bg-muted/10 transition-colors">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-2">
                  <div className="text-sm font-semibold">
                    Similarity: {(neighbor.similarity_score * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-muted-foreground font-mono">
                    {neighbor.document_id}
                  </div>
                </div>
                
                <p className="text-sm mb-3 text-muted-foreground">
                  {neighbor.text_preview}
                </p>
                
                {neighbor.metadata.title && (
                  <div className="text-xs text-muted-foreground">
                    <strong>Title:</strong> {neighbor.metadata.title}
                  </div>
                )}
              </div>
              
              <button
                onClick={() => onNavigate(neighbor.document_id)}
                className="ml-4 p-2 hover:bg-muted rounded-md transition-colors"
                title="View this document"
              >
                <ExternalLink className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Debug Tab Component
const DebugTab: React.FC<{
  analysis: DocumentAnalysis | undefined;
  chunks: DocumentChunksResponse | undefined;
  neighbors: DocumentNeighborsResponse | undefined;
  documentId: string;
  onCopy: (text: string, label: string) => void;
}> = ({ analysis, chunks, neighbors, documentId, onCopy }) => {
  const debugData = {
    document_id: documentId,
    analysis_available: !!analysis,
    chunks_available: !!chunks,
    neighbors_available: !!neighbors,
    analysis_data: analysis,
    chunks_summary: chunks ? {
      total_chunks: chunks.total,
      current_page_chunks: chunks.chunks.length,
      has_more: chunks.has_more
    } : null,
    neighbors_summary: neighbors ? {
      total_neighbors: neighbors.total_found,
      query_text_length: neighbors.query_text.length
    } : null,
    timestamp: new Date().toISOString()
  };

  return (
    <div className="space-y-4">
      <div className="glass-card p-4 rounded-lg">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold">Debug Information</h3>
          <button
            onClick={() => onCopy(JSON.stringify(debugData, null, 2), 'Debug data')}
            className="px-3 py-1 bg-muted text-muted-foreground rounded hover:bg-muted/80"
          >
            Copy All
          </button>
        </div>
        
        <div className="space-y-4">
          <div>
            <h4 className="text-sm font-semibold mb-2">API Status</h4>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className={`p-2 rounded ${analysis ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                Analysis: {analysis ? 'Available' : 'Error'}
              </div>
              <div className={`p-2 rounded ${chunks ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                Chunks: {chunks ? 'Available' : 'Error'}
              </div>
              <div className={`p-2 rounded ${neighbors ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                Neighbors: {neighbors ? 'Available' : 'Error'}
              </div>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-semibold mb-2">Raw Debug Data</h4>
            <pre className="text-xs bg-muted/30 p-3 rounded overflow-auto max-h-96">
              {JSON.stringify(debugData, null, 2)}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentDetailPage;