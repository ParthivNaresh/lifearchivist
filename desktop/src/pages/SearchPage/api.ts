/**
 * API service layer for SearchPage
 */

import axios from 'axios';
import { type SearchResponse, type SearchResult, type Tag, type SearchParams } from './types';
import { API_BASE_URL, API_ENDPOINTS } from './constants';

// Type for the raw API response
interface ApiSearchResult {
  document_id: string;
  text?: string;
  score?: number;
  search_type?: string;
  matched_tags?: string[];
  metadata?: {
    title?: string;
    document_created_at?: string | null;
    uploaded_at?: string | null;
    mime_type?: string | null;
    size_bytes?: number;
    word_count?: number | null;
    tags?: string[];
  };
}

interface ApiSearchResponse {
  results: ApiSearchResult[];
  count?: number;
}

/**
 * Perform document search
 */
export const searchDocuments = async (params: SearchParams): Promise<SearchResponse> => {
  const response = await axios.get<ApiSearchResponse>(`${API_BASE_URL}${API_ENDPOINTS.SEARCH}`, {
    params,
  });

  // Transform API response to flatten metadata
  const transformedResults: SearchResult[] = response.data.results.map((result) => ({
    document_id: result.document_id,
    title: result.metadata?.title ?? 'Untitled',
    snippet: result.text ?? '',
    score: result.score ?? 0, // Default to 0 if score is undefined
    created_at: result.metadata?.document_created_at ?? null,
    ingested_at: result.metadata?.uploaded_at ?? null,
    mime_type: result.metadata?.mime_type ?? 'application/octet-stream', // Default MIME type
    size_bytes: result.metadata?.size_bytes ?? 0,
    word_count: result.metadata?.word_count ?? null,
    match_type: result.search_type ?? 'unknown',
    tags: result.metadata?.tags ?? [],
    matched_tags: result.matched_tags ?? [],
  }));

  return {
    results: transformedResults,
    total: response.data.count ?? transformedResults.length,
    query_time_ms: 0, // API doesn't return this
  };
};

/**
 * Fetch available tags
 */
export const fetchTags = async (): Promise<Tag[]> => {
  const response = await axios.get<{ tags: Tag[] }>(`${API_BASE_URL}${API_ENDPOINTS.TAGS}`);
  return response.data.tags ?? [];
};
