/**
 * Constants for InboxPage
 */

// API Base URL - centralized for easy environment switching
export const API_BASE_URL = 'http://localhost:8000';

// API Endpoints
export const API_ENDPOINTS = {
  VAULT_INFO: `${API_BASE_URL}/api/vault/info`,
  FOLDER_WATCH_STATUS: `${API_BASE_URL}/api/folder-watch/status`,
  FOLDER_WATCH_FOLDERS: `${API_BASE_URL}/api/folder-watch/folders`,
  FOLDER_WATCH_FOLDER: (id: string) => `${API_BASE_URL}/api/folder-watch/folders/${id}`,
  FOLDER_WATCH_SCAN_FOLDER: (id: string) => `${API_BASE_URL}/api/folder-watch/folders/${id}/scan`,
  ACTIVITY_EVENTS: `${API_BASE_URL}/api/activity/events`,

  // Legacy endpoints (deprecated - kept for backwards compatibility)
  FOLDER_WATCH_START: `${API_BASE_URL}/api/folder-watch/start`,
  FOLDER_WATCH_STOP: `${API_BASE_URL}/api/folder-watch/stop`,
  FOLDER_WATCH_SCAN: `${API_BASE_URL}/api/folder-watch/scan`,
} as const;

// WebSocket Endpoints
export const WS_ENDPOINTS = {
  ACTIVITY_FEED: `ws://localhost:8000/ws/activity_feed`,
  FOLDER_WATCHER: `ws://localhost:8000/ws/folder_watcher`,
} as const;

// Timing constants
export const TIMING = {
  RECENT_BATCH_DURATION: 60000, // Show recent batches for 1 minute
  NAVIGATION_DELAY: 500, // Delay before navigation after clearing
  REFRESH_INTERVAL: 30000, // Refresh data every 30 seconds
} as const;

// Display limits
export const DISPLAY_LIMITS = {
  RECENT_ACTIVITY_COUNT: 5, // Number of recent activity items to show
  ACTIVITY_FETCH_LIMIT: 200, // Number of events to fetch for week calculation
} as const;

// Conversion constants
export const BYTES_PER_MB = 1024 * 1024;
