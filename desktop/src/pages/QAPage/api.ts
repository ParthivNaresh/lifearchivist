import apiClient from '../../utils/api-client';
import { type QAResponse, type QARequest } from './types';
import { API_ENDPOINTS } from './constants';

export const askQuestion = async (request: QARequest): Promise<QAResponse> => {
  return await apiClient.post<QAResponse>(API_ENDPOINTS.ASK, request);
};
