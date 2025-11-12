import apiClient from '../../utils/api-client';
import { type Settings } from './types';
import { API_ENDPOINTS } from './constants';

export const fetchSettings = async (): Promise<Settings> => {
  return await apiClient.get<Settings>(API_ENDPOINTS.SETTINGS);
};

interface UpdateSettingsResponse {
  message: string;
  updated_fields: string[];
  current_llm_model: string;
  note: string;
}

export const saveSettingsToServer = async (settings: Settings): Promise<UpdateSettingsResponse> => {
  const updateData = {
    theme: settings.theme,
    interface_density: settings.interface_density,
  };

  return await apiClient.put<UpdateSettingsResponse>(API_ENDPOINTS.SETTINGS, updateData);
};
