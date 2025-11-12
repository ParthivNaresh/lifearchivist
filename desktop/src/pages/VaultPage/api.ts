import apiClient from '../../utils/api-client';
import { type VaultInfo, type Document } from './types';

export const fetchVaultInfo = async (): Promise<VaultInfo> => {
  return await apiClient.get<VaultInfo>('/api/vault/info');
};

export const fetchDocuments = async (limit = 500): Promise<Document[]> => {
  try {
    const response = await apiClient.get<{ documents: Document[] }>(
      `/api/documents?limit=${limit}`
    );
    return response.documents;
  } catch (error) {
    if (error instanceof Error && !error.message.includes('Backend is not available')) {
      console.error('Failed to fetch documents:', error);
    }
    return [];
  }
};

export const clearVault = async (): Promise<void> => {
  await apiClient.delete<void>('/api/documents');
};

export const reconcileVault = async (): Promise<void> => {
  await apiClient.post<void>('/api/vault/reconcile');
};
