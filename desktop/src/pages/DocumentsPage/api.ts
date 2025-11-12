import apiClient from '../../utils/api-client';
import { type DocumentsResponse, type DocumentStatus } from './types';

export const fetchDocuments = async (status?: DocumentStatus): Promise<DocumentsResponse> => {
  const params: Record<string, string> = {};

  if (status && status !== 'all') {
    params.status = status;
  }

  return await apiClient.get<DocumentsResponse>('/api/documents', { params });
};
