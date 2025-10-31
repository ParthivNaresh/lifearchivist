/**
 * API service for VaultPage
 */

import axios from 'axios';
import { type VaultInfo, type Document } from './types';

const API_BASE_URL = 'http://localhost:8000/api';

/**
 * Fetch vault information
 */
export const fetchVaultInfo = async (): Promise<VaultInfo> => {
  const response = await axios.get<VaultInfo>(`${API_BASE_URL}/vault/info`);
  return response.data;
};

/**
 * Fetch all documents with optional limit
 */
export const fetchDocuments = async (limit = 500): Promise<Document[]> => {
  try {
    const response = await axios.get<{ documents: Document[] }>(
      `${API_BASE_URL}/documents?limit=${limit}`
    );
    return response.data.documents;
  } catch (error) {
    console.error('Failed to fetch documents:', error);
    return [];
  }
};

/**
 * Clear the entire vault
 */
export const clearVault = async (): Promise<void> => {
  await axios.delete(`${API_BASE_URL}/documents`);
};

/**
 * Reconcile vault files with metadata stores
 *
 * Checks all documents in Redis and removes metadata for any documents
 * whose vault files are missing. Ensures data consistency.
 */
export const reconcileVault = async (): Promise<void> => {
  await axios.post(`${API_BASE_URL}/vault/reconcile`);
};
