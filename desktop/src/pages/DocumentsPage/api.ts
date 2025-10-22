/**
 * API service for documents operations
 */

import axios from 'axios';
import { type DocumentsResponse, type DocumentStatus } from './types';
import { API_CONFIG } from './constants';

/**
 * Fetch documents with optional status filter
 */
export const fetchDocuments = async (status?: DocumentStatus): Promise<DocumentsResponse> => {
  const params = new URLSearchParams();

  if (status && status !== 'all') {
    params.append('status', status);
  }

  const response = await axios.get<DocumentsResponse>(`${API_CONFIG.BASE_URL}/documents?${params}`);

  return response.data;
};
