/**
 * Type definitions for DocumentDetailPage components
 */

import { type TAB_CONFIG } from './constants';

// Tab type derived from TAB_CONFIG values
export type TabType = (typeof TAB_CONFIG)[keyof typeof TAB_CONFIG];

export interface DocumentClassifications {
  theme?: string;
  confidence?: number;
  confidence_level?: string;
  primary_subtheme?: string;
  primary_subclassification?: string;
  subclassification_confidence?: number;
  subclassification_method?: string;
}

export interface DocumentMetadata {
  file_hash?: string;
  title?: string;
  mime_type?: string;
  size_bytes?: number;
  created_at?: string;
  uploaded_at?: string;
  document_created_at?: string;
  original_path?: string;
  tags?: string[];
  classifications?: DocumentClassifications;
  [key: string]: unknown;
}

export interface DocumentTheme {
  name?: string;
  confidence?: number;
  [key: string]: unknown;
}

export interface DocumentAnalysis {
  analysis: {
    document_id: string;
    status: string;
    metadata: DocumentMetadata;
    theme?: DocumentTheme;
    processing_info: {
      total_chars: number;
      total_words: number;
      num_chunks: number;
      avg_chunk_size: number;
      min_chunk_size: number;
      max_chunk_size: number;
      avg_word_count: number;
      embedding_model?: string;
      embedding_dimension?: number;
    };
    storage_info: {
      metadata_store?: string;
      vector_store?: string;
      file_store?: string;
      text_splitter?: string;
      chunk_size?: number;
      chunk_overlap?: number;
    };
    chunks_preview: {
      node_id: string;
      text: string;
      text_length?: number;
      word_count?: number;
    }[];
  };
}

export interface DocumentNeighborMetadata {
  document_id?: string;
  title?: string;
  mime_type?: string;
  status?: string;
  uploaded_date?: string;
  file_hash_short?: string;
  size_bytes?: number;
  document_created_at?: string;
  theme?: string;
  primary_subtheme?: string | null;
  tags?: string[];
  [key: string]: unknown;
}

export interface DocumentNeighbor {
  document_id: string;
  title: string;
  similarity_score: number;
  metadata: DocumentNeighborMetadata;
}

export interface DocumentNeighborsResponse {
  document_id: string;
  neighbors: DocumentNeighbor[];
  top_k: number;
}

export interface DocumentTextResponse {
  document_id: string;
  text: string;
  text_lower: string;
  metadata: DocumentMetadata;
  stats: {
    total_nodes: number;
    text_length: number;
    text_length_lower: number;
    word_count: number;
    line_count: number;
    paragraph_count: number;
  };
}
