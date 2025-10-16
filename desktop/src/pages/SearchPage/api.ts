/**
 * API service layer for SearchPage
 */

import axios from 'axios';
import { SearchResponse, SearchResult, Tag, SearchParams } from './types';
import { API_BASE_URL, API_ENDPOINTS } from './constants';

/**
 * Perform document search
 */
export const searchDocuments = async (params: SearchParams): Promise<SearchResponse> => {
  const response = await axios.get<any>(
    `${API_BASE_URL}${API_ENDPOINTS.SEARCH}`,
    { params }
  );
  
  // Transform API response to flatten metadata
  const transformedResults: SearchResult[] = response.data.results.map((result: any) => ({
    document_id: result.document_id,
    title: result.metadata?.title || 'Untitled',
    snippet: result.text || '',
    score: result.score,
    created_at: result.metadata?.document_created_at || null,
    ingested_at: result.metadata?.uploaded_at || null,
    mime_type: result.metadata?.mime_type || null,
    size_bytes: result.metadata?.size_bytes || 0,
    word_count: result.metadata?.word_count || null,
    match_type: result.search_type || 'unknown',
    tags: result.metadata?.tags || [],
    matched_tags: result.matched_tags || [],
  }));
  
  return {
    results: transformedResults,
    total: response.data.count || transformedResults.length,
    query_time_ms: 0, // API doesn't return this
  };
};

/**
 * Fetch available tags
 */
export const fetchTags = async (): Promise<Tag[]> => {
  const response = await axios.get<{ tags: Tag[] }>(
    `${API_BASE_URL}${API_ENDPOINTS.TAGS}`
  );
  return response.data.tags || [];
};