/**
 * Constants for SettingsPage
 */

export const API_BASE_URL = 'http://localhost:8000';

export const API_ENDPOINTS = {
  HEALTH: '/health',
  VAULT_INFO: '/api/vault/info',
  SETTINGS: '/api/settings',
  MODELS: '/api/settings/models',
} as const;

export const FILE_SIZE_OPTIONS = [
  { value: 50, label: '50 MB' },
  { value: 100, label: '100 MB' },
  { value: 200, label: '200 MB' },
  { value: 500, label: '500 MB' },
] as const;

export const SEARCH_LIMIT_OPTIONS = [
  { value: 10, label: '10 results' },
  { value: 25, label: '25 results' },
  { value: 50, label: '50 results' },
  { value: 100, label: '100 results' },
] as const;

export const THEME_OPTIONS = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'System' },
] as const;

export const DENSITY_OPTIONS = [
  { value: 'compact', label: 'Compact' },
  { value: 'comfortable', label: 'Comfortable' },
  { value: 'spacious', label: 'Spacious' },
] as const;

export const DEFAULT_SETTINGS = {
  auto_extract_dates: false,
  generate_text_previews: false,
  max_file_size_mb: 100,
  llm_model: 'llama3.2:1b',
  embedding_model: 'all-MiniLM-L6-v2',
  search_results_limit: 25,
  auto_organize_by_date: false,
  duplicate_detection: false,
  default_import_location: '~/Documents',
  theme: 'system',
  interface_density: 'comfortable',
  vault_path: '~/.lifearchivist/vault',
  lifearch_home: '~/.lifearchivist',
} as const;

export const UI_TEXT = {
  PAGE_TITLE: 'Settings',
  SAVE_BUTTON: 'Save Settings',
  SAVING_BUTTON: 'Saving...',
  SAVE_SUCCESS: 'Settings saved successfully!',
  SAVE_ERROR: 'Failed to save settings. Please try again.',
  LOADING: 'Loading settings...',
  
  SECTIONS: {
    DOCUMENT_PROCESSING: 'Document Processing',
    SEARCH_AI: 'Search & AI',
    FILE_MANAGEMENT: 'File Management',
    SYSTEM_STATUS: 'System Status',
    APPEARANCE: 'Appearance',
  },
  
  DESCRIPTIONS: {
    AUTO_EXTRACT_DATES: 'Automatically detect and extract document dates using AI',
    GENERATE_PREVIEWS: 'Create searchable text previews for documents',
    LLM_MODEL: 'Used for date extraction and document analysis',
    EMBEDDING_MODEL: 'Used for semantic search and document similarity',
    AUTO_ORGANIZE: 'Automatically organize documents by extracted dates',
    DUPLICATE_DETECTION: 'Skip importing files that already exist in your vault',
    THEME_CURRENT: 'Current theme:',
    THEME_SYSTEM: '(following system preference)',
  },
  
  STATUS: {
    HEALTHY: 'Healthy',
    LOADING: 'Loading system status...',
    DOCUMENTS: 'Documents:',
    STORAGE_USED: 'Storage Used:',
    STATUS: 'Status:',
    VAULT_LOCATION: 'Vault location:',
  },
} as const;