/**
 * API service layer for SettingsPage
 */

import axios from 'axios';
import { 
  SystemHealth, 
  VaultStats, 
  Settings, 
  AvailableModels 
} from './types';
import { API_BASE_URL, API_ENDPOINTS } from './constants';

/**
 * Fetch system health status
 */
export const fetchSystemHealth = async (): Promise<SystemHealth> => {
  const response = await axios.get<SystemHealth>(
    `${API_BASE_URL}${API_ENDPOINTS.HEALTH}`
  );
  return response.data;
};

/**
 * Fetch vault statistics
 */
export const fetchVaultStats = async (): Promise<VaultStats> => {
  const response = await axios.get<VaultStats>(
    `${API_BASE_URL}${API_ENDPOINTS.VAULT_INFO}`
  );
  return response.data;
};

/**
 * Fetch current settings
 */
export const fetchSettings = async (): Promise<Settings> => {
  const response = await axios.get<Settings>(
    `${API_BASE_URL}${API_ENDPOINTS.SETTINGS}`
  );
  return response.data;
};

/**
 * Fetch available models
 */
export const fetchAvailableModels = async (): Promise<AvailableModels> => {
  const response = await axios.get<AvailableModels>(
    `${API_BASE_URL}${API_ENDPOINTS.MODELS}`
  );
  return response.data;
};

/**
 * Save settings to the server
 */
export const saveSettingsToServer = async (settings: Settings): Promise<{ success: boolean }> => {
  const updateData = {
    auto_extract_dates: settings.auto_extract_dates,
    generate_text_previews: settings.generate_text_previews,
    max_file_size_mb: settings.max_file_size_mb,
    llm_model: settings.llm_model,
    embedding_model: settings.embedding_model,
    search_results_limit: settings.search_results_limit,
    auto_organize_by_date: settings.auto_organize_by_date,
    duplicate_detection: settings.duplicate_detection,
    default_import_location: settings.default_import_location,
    theme: settings.theme,
    interface_density: settings.interface_density,
  };

  const response = await axios.put(
    `${API_BASE_URL}${API_ENDPOINTS.SETTINGS}`,
    updateData
  );
  
  return response.data;
};

/**
 * Fetch all initial data in parallel
 */
export const fetchAllData = async () => {
  const [healthResponse, vaultResponse, settingsResponse, modelsResponse] = await Promise.all([
    fetchSystemHealth(),
    fetchVaultStats(),
    fetchSettings(),
    fetchAvailableModels(),
  ]);
  
  return {
    systemHealth: healthResponse,
    vaultStats: vaultResponse,
    settings: settingsResponse,
    availableModels: modelsResponse,
  };
};