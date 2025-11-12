import apiClient from '../../utils/api-client';
import { type DocumentAnalysis, type DocumentNeighborsResponse } from './types';

export const fetchDocumentAnalysis = async (documentId: string): Promise<DocumentAnalysis> => {
  return await apiClient.get<DocumentAnalysis>(`/api/documents/${documentId}/llamaindex-analysis`);
};

export const fetchDocumentNeighbors = async (
  documentId: string,
  topK = 10
): Promise<DocumentNeighborsResponse> => {
  return await apiClient.get<DocumentNeighborsResponse>(
    `/api/documents/${documentId}/llamaindex-neighbors`,
    { params: { top_k: topK } }
  );
};

export const deleteDocument = async (documentId: string): Promise<void> => {
  await apiClient.delete<void>(`/api/documents/${documentId}`);
};

export const downloadDocumentFile = async (fileHash: string): Promise<Blob> => {
  return await apiClient.get<Blob>(`/api/vault/file/${fileHash}`, {
    responseType: 'blob',
  });
};
