import axios from 'axios';
import type { AvailableModels, SettingsResponse } from './types';

const API_BASE = 'http://localhost:8000/api';

export const settingsApi = {
  getModels: () => axios.get<AvailableModels>(`${API_BASE}/settings/models`),

  getSettings: () => axios.get<SettingsResponse>(`${API_BASE}/settings`),

  updateModel: (model: string) => axios.put(`${API_BASE}/settings`, { llm_model: model }),
};
