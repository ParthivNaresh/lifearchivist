/**
 * API service layer for QAPage
 */

import axios from 'axios';
import { type QAResponse, type QARequest } from './types';
import { API_BASE_URL, API_ENDPOINTS } from './constants';

/**
 * Submit a question to the Q&A API
 */
export const askQuestion = async (request: QARequest): Promise<QAResponse> => {
  const response = await axios.post<QAResponse>(`${API_BASE_URL}${API_ENDPOINTS.ASK}`, request);
  return response.data;
};
