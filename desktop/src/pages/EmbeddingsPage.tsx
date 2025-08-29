import React, { useState, useCallback } from 'react';
import { Brain, Database, FileText, Activity, AlertCircle, Loader2 } from 'lucide-react';
import { useCache } from '../hooks/useCache';
import axios from 'axios';

interface EmbeddingInfo {
  id: string;
  chunk_id: string;
  model_name: string;
  embedding_dimension: number;
  created_at: string;
}

interface ChunkInfo {
  id: string;
  document_id: string;
  chunk_index: number;
  text: string;
  start_char: number;
  end_char: number;
  embedding_id: string;
}

interface EmbeddingStats {
  total_embeddings: number;
  total_chunks: number;
  models_used: string[];
  avg_embedding_dimension: number;
  documents_with_embeddings: number;
  total_documents: number;
}

const EmbeddingsPage: React.FC = () => {
  const [selectedModel, setSelectedModel] = useState<string>('all');

  const fetchEmbeddingStats = useCallback(async () => {
    const response = await axios.get<EmbeddingStats>('http://localhost:8000/api/embeddings/stats');
    return response.data;
  }, []);

  const fetchEmbeddings = useCallback(async () => {
    const params = new URLSearchParams();
    if (selectedModel !== 'all') {
      params.append('model', selectedModel);
    }
    
    const response = await axios.get(`http://localhost:8000/api/embeddings?${params}&limit=50`);
    return response.data;
  }, [selectedModel]);

  const { data: stats, refresh: refreshStats } = useCache(
    'embedding-stats',
    fetchEmbeddingStats,
    2 * 60 * 1000 // 2 minute cache
  );

  const { data: embeddingsData, loading, error, refresh } = useCache(
    `embeddings-${selectedModel}`,
    fetchEmbeddings,
    3 * 60 * 1000 // 3 minute cache
  );

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  if (error) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertCircle className="h-8 w-8 text-red-500 mx-auto" />
            <p className="mt-2 text-red-600">{error}</p>
            <button 
              onClick={() => {
                refreshStats();
                refresh();
              }}
              className="mt-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center">
              <Brain className="h-6 w-6 mr-2" />
              Vector Embeddings
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              AI-powered document understanding and semantic search
            </p>
          </div>
          <button
            onClick={() => {
              refreshStats();
              refresh();
            }}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Refresh
          </button>
        </div>

        {/* Embedding Statistics */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="glass-card p-4 rounded-lg border border-border/30">
              <div className="flex items-center space-x-2 mb-2">
                <Brain className="h-5 w-5 text-blue-500" />
                <h3 className="font-medium">Total Embeddings</h3>
              </div>
              <p className="text-2xl font-bold text-primary">{stats.total_embeddings}</p>
              <p className="text-xs text-muted-foreground">Vector representations</p>
            </div>

            <div className="glass-card p-4 rounded-lg border border-border/30">
              <div className="flex items-center space-x-2 mb-2">
                <FileText className="h-5 w-5 text-green-500" />
                <h3 className="font-medium">Text Chunks</h3>
              </div>
              <p className="text-2xl font-bold text-primary">{stats.total_chunks}</p>
              <p className="text-xs text-muted-foreground">Document segments</p>
            </div>

            <div className="glass-card p-4 rounded-lg border border-border/30">
              <div className="flex items-center space-x-2 mb-2">
                <Database className="h-5 w-5 text-purple-500" />
                <h3 className="font-medium">Documents</h3>
              </div>
              <p className="text-2xl font-bold text-primary">
                {stats.documents_with_embeddings} / {stats.total_documents}
              </p>
              <p className="text-xs text-muted-foreground">With embeddings</p>
            </div>

            <div className="glass-card p-4 rounded-lg border border-border/30">
              <div className="flex items-center space-x-2 mb-2">
                <Activity className="h-5 w-5 text-orange-500" />
                <h3 className="font-medium">Dimensions</h3>
              </div>
              <p className="text-2xl font-bold text-primary">{stats.avg_embedding_dimension}</p>
              <p className="text-xs text-muted-foreground">Vector size</p>
            </div>
          </div>
        )}

        {/* Models Used */}
        {stats && stats.models_used.length > 0 && (
          <div className="mb-6 p-4 glass-card rounded-lg border border-border/30">
            <h3 className="font-medium mb-2 flex items-center">
              <Brain className="h-4 w-4 mr-2" />
              Models Used
            </h3>
            <div className="flex flex-wrap gap-2">
              {stats.models_used.map((model, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                >
                  {model}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Model Filter */}
        <div className="mb-6">
          <div className="flex items-center space-x-4">
            <label className="text-sm font-medium">Filter by model:</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="px-3 py-1 border border-input rounded-md bg-background text-foreground"
            >
              <option value="all">All Models</option>
              {stats?.models_used.map((model) => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Embeddings List */}
        <div className="glass-card rounded-lg border border-border/30">
          <div className="p-4 border-b border-border/30">
            <h2 className="text-lg font-semibold flex items-center">
              Vector Embeddings
              {loading && <Loader2 className="inline-block ml-2 h-4 w-4 animate-spin" />}
            </h2>
            <p className="text-sm text-muted-foreground">
              Showing {embeddingsData?.embeddings?.length || 0} embeddings
            </p>
          </div>

          <div className="divide-y divide-border/30">
            {(!embeddingsData?.embeddings || embeddingsData.embeddings.length === 0) ? (
              <div className="p-8 text-center">
                <Brain className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium text-muted-foreground">No embeddings found</h3>
                <p className="text-sm text-muted-foreground mt-2">
                  Upload some documents to generate embeddings
                </p>
              </div>
            ) : (
              embeddingsData.embeddings.map((embedding: any, index: number) => (
                <div key={index} className="p-4 hover:bg-muted/30 transition-colors">
                  <div className="flex items-start space-x-4">
                    {/* Embedding Type Icon */}
                    <div className="flex-shrink-0 mt-1">
                      <div className="w-8 h-8 rounded bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
                        <Brain className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                      </div>
                    </div>

                    {/* Embedding Details */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        <span className="text-sm font-medium">Embedding {embedding.id.slice(0, 8)}...</span>
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                          {embedding.model_name}
                        </span>
                      </div>

                      {/* Chunk Info */}
                      {embedding.chunk && (
                        <div className="mb-2 p-2 bg-muted/30 rounded text-xs">
                          <div className="text-muted-foreground font-medium mb-1">Text Chunk:</div>
                          <div className="text-foreground">{embedding.chunk.text}</div>
                          <div className="text-muted-foreground mt-1">
                            Characters: {embedding.chunk.start_char} - {embedding.chunk.end_char}
                            {embedding.chunk.document_title && (
                              <span className="ml-2">• Document: {embedding.chunk.document_title}</span>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Technical Details */}
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-xs text-muted-foreground">
                        <div className="flex items-center space-x-1">
                          <Activity className="h-3 w-3" />
                          <span>{embedding.embedding_dimension}D vector</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Database className="h-3 w-3" />
                          <span>Chunk: {embedding.chunk_id.slice(0, 8)}...</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <FileText className="h-3 w-3" />
                          <span>Created: {formatDate(embedding.created_at)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmbeddingsPage;