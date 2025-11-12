import apiClient from '../../utils/api-client';
import { type VaultInfo, type WatchStatus } from './types';
import { API_ENDPOINTS } from './constants';

export const fetchVaultInfo = async (): Promise<VaultInfo | null> => {
  try {
    const data = await apiClient.get<VaultInfo>(API_ENDPOINTS.VAULT_INFO);

    if (data && typeof data === 'object' && 'total_files' in data) {
      return data;
    }

    return null;
  } catch (error) {
    if (error instanceof Error && !error.message.includes('Backend is not available')) {
      console.error('Failed to fetch vault info:', error);
    }
    return null;
  }
};

export const fetchWatchStatus = async (): Promise<WatchStatus | null> => {
  try {
    const data = await apiClient.get<WatchStatus>(API_ENDPOINTS.FOLDER_WATCH_STATUS);

    if (data && typeof data === 'object') {
      return data;
    }

    return null;
  } catch (_error) {
    return null;
  }
};
