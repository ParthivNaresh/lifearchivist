import apiClient from '../../utils/api-client';
import { type SearchDocumentsResponse, type Tag, type SearchParams } from './types';
import { API_ENDPOINTS } from './constants';

export const searchDocuments = async (params: SearchParams): Promise<SearchDocumentsResponse> => {
  return await apiClient.get<SearchDocumentsResponse>(API_ENDPOINTS.SEARCH, {
    params,
  });
};

export const fetchTags = async (): Promise<Tag[]> => {
  const response = await apiClient.get<{ tags: Tag[] }>(API_ENDPOINTS.TAGS);
  return response.tags ?? [];
};
