/**
 * TypeScript interfaces for SettingsPage
 */

export interface SystemHealth {
  status: string;
  vault: boolean;
  llamaindex: boolean;
  agents_enabled: boolean;
  websockets_enabled: boolean;
  ui_enabled: boolean;
}

export interface VaultStats {
  total_files: number;
  total_size_mb: number;
  vault_path: string;
}

export interface Settings {
  auto_extract_dates: boolean;
  generate_text_previews: boolean;
  max_file_size_mb: number;
  llm_model: string;
  embedding_model: string;
  search_results_limit: number;
  auto_organize_by_date: boolean;
  duplicate_detection: boolean;
  default_import_location: string;
  theme: string;
  interface_density: string;
  vault_path: string;
  lifearch_home: string;
}

export interface ModelInfo {
  id: string;
  name: string;
  description: string;
  size?: string;
  dimensions?: number;
  performance: string;
}

export interface AvailableModels {
  llm_models: ModelInfo[];
  embedding_models: ModelInfo[];
}

export type SettingKey = keyof Settings;

export interface SettingsState {
  settings: Settings | null;
  originalSettings: Settings | null;
  hasUnsavedChanges: boolean;
  saving: boolean;
  saveMessage: string | null;
}

export interface SystemState {
  systemHealth: SystemHealth | null;
  vaultStats: VaultStats | null;
  availableModels: AvailableModels | null;
  loading: boolean;
}