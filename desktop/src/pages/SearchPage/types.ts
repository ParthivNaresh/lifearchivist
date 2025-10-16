/**
 * TypeScript interfaces for SearchPage
 */

export interface SearchResult {
  document_id: string;
  title: string;
  snippet: string;
  score: number;
  created_at: string | null;
  ingested_at: string | null;
  mime_type: string;
  size_bytes: number;
  word_count: number | null;
  match_type: string;
  tags?: string[];
  matched_tags?: string[];
}

export interface Tag {
  id: number;
  name: string;
  category: string | null;
  document_count: number;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query_time_ms: number;
}

export type SearchMode = 'keyword' | 'semantic' | 'hybrid';

export interface SearchState {
  query: string;
  results: SearchResult[];
  isLoading: boolean;
  queryTime: number | null;
  error: string | null;
  selectedTags: string[];
  availableTags: Tag[];
  showFilters: boolean;
  tagsLoading: boolean;
  searchMode: SearchMode;
}

export interface SearchParams {
  q?: string;
  mode: SearchMode;
  limit: number;
  tags?: string;
}