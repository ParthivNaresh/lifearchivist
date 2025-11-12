/**
 * TypeScript interfaces for SearchPage
 */

export interface SearchResult {
  document_id: string;
  title: string;
  score: number;
  snippet: string | null;
  metadata: Record<string, unknown>;
}

export interface Tag {
  id: number;
  name: string;
  category: string | null;
  document_count: number;
}

export interface SearchDocumentsResponse {
  results: SearchResult[];
  count: number;
  mode: string;
  query: string;
}

export interface Citation {
  doc_id: string;
  title: string;
  snippet: string;
  score: number;
}

export interface AskQuestionRequest {
  question: string;
  context_limit?: number;
  filters?: Record<string, unknown>;
}

export interface AskQuestionResponse {
  answer: string;
  confidence: number;
  citations: Citation[];
  method: string;
  context_length: number;
  statistics: Record<string, unknown>;
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
  mime_type?: string;
  status?: string;
}
