/**
 * API service layer for document operations
 */

import axios from 'axios';
import { type DocumentAnalysis, type DocumentNeighborsResponse } from './types';

// TODO: Move to environment config
const API_BASE_URL = 'http://localhost:8000/api';

/**
 * Fetch document analysis data
 */
export const fetchDocumentAnalysis = async (documentId: string): Promise<DocumentAnalysis> => {
  const response = await axios.get<DocumentAnalysis>(
    `${API_BASE_URL}/documents/${documentId}/llamaindex-analysis`
  );
  return response.data;
};

/**
 * Fetch related/neighbor documents
 */
export const fetchDocumentNeighbors = async (
  documentId: string,
  topK = 10
): Promise<DocumentNeighborsResponse> => {
  const response = await axios.get<DocumentNeighborsResponse>(
    `${API_BASE_URL}/documents/${documentId}/llamaindex-neighbors`,
    { params: { top_k: topK } }
  );
  return response.data;
};

/**
 * Delete a document
 */
export const deleteDocument = async (documentId: string): Promise<void> => {
  await axios.delete(`${API_BASE_URL}/documents/${documentId}`);
};

/**
 * Download document file
 */
export const downloadDocumentFile = async (fileHash: string): Promise<Blob> => {
  const response = await axios.get<Blob>(`${API_BASE_URL}/vault/file/${fileHash}`, {
    responseType: 'blob',
  });
  return response.data;
};
