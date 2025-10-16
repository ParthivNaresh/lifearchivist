/**
 * API service layer for InboxPage
 * 
 * Note: Most upload API logic is handled by useUploadManager hook
 * This file is for any additional API calls specific to InboxPage
 */

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

/**
 * Get upload status from server
 */
export const getUploadStatus = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/upload/status`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch upload status:', error);
    throw error;
  }
};

/**
 * Get recent uploads
 */
export const getRecentUploads = async (limit: number = 10) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/upload/recent`, {
      params: { limit }
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch recent uploads:', error);
    throw error;
  }
};

/**
 * Cancel an upload batch
 */
export const cancelUploadBatch = async (batchId: string) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/upload/cancel/${batchId}`);
    return response.data;
  } catch (error) {
    console.error('Failed to cancel upload batch:', error);
    throw error;
  }
};