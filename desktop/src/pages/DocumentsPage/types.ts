/**
 * Type definitions for DocumentsPage
 */

export interface Document {
  id: string;
  file_hash: string;
  original_path: string;
  mime_type: string | null;
  size_bytes: number;
  created_at: string;
  modified_at: string | null;
  ingested_at: string;
  status: string;
  error_message: string | null;
  word_count: number | null;
  language: string | null;
  extraction_method: string | null;
  text_preview: string | null;
  has_content: boolean;
  tags: string[];
  tag_count: number;
}

export interface DocumentsResponse {
  documents: Document[];
  total: number;
  limit: number;
  offset: number;
}

export type DocumentStatus = 'all' | 'ready' | 'pending' | 'failed';

export interface StatusOption {
  value: DocumentStatus;
  label: string;
}