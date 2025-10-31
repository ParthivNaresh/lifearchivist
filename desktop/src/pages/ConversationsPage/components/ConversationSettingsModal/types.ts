export interface LLMModel {
  id: string;
  name: string;
  performance: string;
}

export interface AvailableModels {
  llm_models: LLMModel[];
}

export interface SettingsResponse {
  auto_extract_dates: boolean;
  generate_text_previews: boolean;
  max_file_size_mb: number;
  llm_model: string;
  embedding_model: string;
  search_results_limit: number;
  temperature: number;
  max_output_tokens: number;
  response_format: 'verbose' | 'concise';
  context_window_size: number;
  response_timeout: number;
  auto_organize_by_date: boolean;
  duplicate_detection: boolean;
  default_import_location: string;
  theme: string;
  interface_density: string;
  vault_path: string;
  lifearch_home: string;
}

export interface SettingsUpdateRequest {
  auto_extract_dates?: boolean;
  generate_text_previews?: boolean;
  max_file_size_mb?: number;
  llm_model?: string;
  embedding_model?: string;
  search_results_limit?: number;
  temperature?: number;
  max_output_tokens?: number;
  response_format?: 'verbose' | 'concise';
  context_window_size?: number;
  response_timeout?: number;
  auto_organize_by_date?: boolean;
  duplicate_detection?: boolean;
  default_import_location?: string;
  theme?: 'light' | 'dark' | 'system';
  interface_density?: 'compact' | 'comfortable' | 'spacious';
}

export interface SettingsUpdateResponse {
  success: boolean;
  message: string;
  updated_fields: string[];
  current_llm_model: string;
  note: string;
}

export interface ConversationSettingsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleteAllConversations: () => void;
  onProvidersChanged?: () => void;
}
