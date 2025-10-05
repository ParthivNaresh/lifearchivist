/**
 * Type definitions for DocumentDetailPage components
 */

export interface DocumentAnalysis {
  document_id: string;
  status: string;
  metadata: Record<string, any>;
  theme?: Record<string, any>;
  processing_info: {
    total_chars: number;
    total_words: number;
    num_chunks: number;
    avg_chunk_size: number;
    min_chunk_size: number;
    max_chunk_size: number;
    avg_word_count: number;
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

export interface DocumentNeighbor {
  document_id: string;
  score: number;
  text_preview: string;
  metadata: Record<string, any>;
}

export interface DocumentNeighborsResponse {
  document_id: string;
  neighbors: DocumentNeighbor[];
  total: number;
}

export interface DocumentTextResponse {
  document_id: string;
  text: string;
  text_lower: string;
  metadata: Record<string, any>;
  stats: {
    total_nodes: number;
    text_length: number;
    text_length_lower: number;
    word_count: number;
    line_count: number;
    paragraph_count: number;
  };
}