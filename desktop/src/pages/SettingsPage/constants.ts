/**
 * Constants for SettingsPage
 */

export const API_BASE_URL = 'http://localhost:8000';

export const API_ENDPOINTS = {
  SETTINGS: '/api/settings',
} as const;

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
  theme: 'system',
  interface_density: 'comfortable',
} as const;

export const UI_TEXT = {
  PAGE_TITLE: 'Settings',
  SAVE_BUTTON: 'Save Settings',
  SAVING_BUTTON: 'Saving...',
  SAVE_SUCCESS: 'Settings saved successfully!',
  SAVE_ERROR: 'Failed to save settings. Please try again.',
  LOADING: 'Loading settings...',

  SECTIONS: {
    APPEARANCE: 'Appearance',
  },

  DESCRIPTIONS: {
    THEME_CURRENT: 'Current theme:',
    THEME_SYSTEM: '(following system preference)',
  },
} as const;
