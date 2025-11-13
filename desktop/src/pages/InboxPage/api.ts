import apiClient from '../../utils/api-client';
import type {
  VaultInfo,
  WatchStatus,
  AggregateStatus,
  AddFolderRequest,
  UpdateFolderRequest,
  RemoveFolderResponse,
  ScanFolderResponse,
  WatchedFolder,
} from './types';
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

export const fetchAggregateStatus = async (): Promise<AggregateStatus> => {
  return await apiClient.get<AggregateStatus>(API_ENDPOINTS.FOLDER_WATCH_STATUS);
};

export const addWatchedFolder = async (request: AddFolderRequest): Promise<WatchedFolder> => {
  return await apiClient.post<WatchedFolder>(API_ENDPOINTS.FOLDER_WATCH_FOLDERS, request);
};

export const updateWatchedFolder = async (
  folderId: string,
  request: UpdateFolderRequest
): Promise<WatchedFolder> => {
  return await apiClient.patch<WatchedFolder>(API_ENDPOINTS.FOLDER_WATCH_FOLDER(folderId), request);
};

export const removeWatchedFolder = async (folderId: string): Promise<RemoveFolderResponse> => {
  return await apiClient.delete<RemoveFolderResponse>(API_ENDPOINTS.FOLDER_WATCH_FOLDER(folderId));
};

export const scanWatchedFolder = async (folderId: string): Promise<ScanFolderResponse> => {
  return await apiClient.post<ScanFolderResponse>(API_ENDPOINTS.FOLDER_WATCH_SCAN_FOLDER(folderId));
};
