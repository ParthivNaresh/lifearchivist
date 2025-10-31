/**
 * API service layer for SettingsPage
 */

import axios from 'axios';
import { type Settings } from './types';
import { API_BASE_URL, API_ENDPOINTS } from './constants';

/**
 * Fetch current settings
 */
export const fetchSettings = async (): Promise<Settings> => {
  const response = await axios.get<Settings>(`${API_BASE_URL}${API_ENDPOINTS.SETTINGS}`);
  return response.data;
};

/**
 * Save settings to the server
 */
export const saveSettingsToServer = async (settings: Settings): Promise<{ success: boolean }> => {
  const updateData = {
    theme: settings.theme,
    interface_density: settings.interface_density,
  };

  const response = await axios.put<{ success: boolean }>(
    `${API_BASE_URL}${API_ENDPOINTS.SETTINGS}`,
    updateData
  );

  return response.data;
};
