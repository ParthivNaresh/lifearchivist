/**
 * API service layer for InboxPage
 */

import { type VaultInfo, type WatchStatus } from './types';
import { API_ENDPOINTS } from './constants';

/**
 * Fetch vault information (document count, storage usage, etc.)
 */
export const fetchVaultInfo = async (): Promise<VaultInfo | null> => {
  try {
    const response = await fetch(API_ENDPOINTS.VAULT_INFO);
    const data = (await response.json()) as VaultInfo;

    // Validate the response has expected structure
    if (data && typeof data === 'object' && 'success' in data && data.success) {
      return data;
    }

    console.error('Failed to fetch vault info:', data);
    return null;
  } catch (error) {
    console.error('Failed to fetch vault info:', error);
    return null;
  }
};

/**
 * Fetch folder watch status
 */
export const fetchWatchStatus = async (): Promise<WatchStatus | null> => {
  try {
    const response = await fetch(API_ENDPOINTS.FOLDER_WATCH_STATUS);
    const data = (await response.json()) as WatchStatus;

    // Validate the response has expected structure
    if (data && typeof data === 'object') {
      return data;
    }

    return null;
  } catch (error) {
    console.error('Failed to fetch watch status:', error);
    return null;
  }
};
