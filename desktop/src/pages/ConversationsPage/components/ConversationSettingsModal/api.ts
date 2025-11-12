import apiClient from '../../../../utils/api-client';
import type {
  AvailableModels,
  SettingsResponse,
  SettingsUpdateRequest,
  SettingsUpdateResponse,
} from './types';

export const settingsApi = {
  getModels: () => apiClient.get<AvailableModels>('/api/settings/models'),

  getSettings: () => apiClient.get<SettingsResponse>('/api/settings'),

  updateModel: (model: string) => apiClient.put('/api/settings', { llm_model: model }),

  updateSettings: (settings: SettingsUpdateRequest) =>
    apiClient.put<SettingsUpdateResponse>('/api/settings', settings),
};
