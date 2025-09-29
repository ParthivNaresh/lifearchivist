/**
 * API service layer for SearchPage
 */

import axios from 'axios';
import { SearchResponse, Tag, SearchParams } from './types';
import { API_BASE_URL, API_ENDPOINTS } from './constants';

/**
 * Perform document search
 */
export const searchDocuments = async (params: SearchParams): Promise<SearchResponse> => {
  const response = await axios.get<SearchResponse>(
    `${API_BASE_URL}${API_ENDPOINTS.SEARCH}`,
    { params }
  );
  return response.data;
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