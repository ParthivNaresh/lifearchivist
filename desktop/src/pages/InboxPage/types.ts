/**
 * Type definitions for InboxPage
 */

/**
 * Vault information from the backend
 */
export interface VaultInfo {
  vault_path: string;
  total_files: number;
  total_size_bytes: number;
  total_size_mb: number;
}

/**
 * Folder watch status from the backend
 */
export interface WatchStatus {
  enabled: boolean;
  watched_path: string | null;
  pending_files: number;
  supported_extensions: string[];
  debounce_seconds: number;
}

export interface FolderStats {
  files_detected: number;
  files_ingested: number;
  files_skipped: number;
  files_failed: number;
  bytes_processed: number;
  last_activity: string | null;
  last_success: string | null;
  last_failure: string | null;
  error_count: number;
  last_error: string;
}

export interface WatchedFolder {
  id: string;
  path: string;
  enabled: boolean;
  created_at: string;
  status: 'active' | 'stopped' | 'paused' | 'error';
  health: 'healthy' | 'degraded' | 'unhealthy' | 'unreachable';
  is_active: boolean;
  success_rate: number;
  stats: FolderStats;
}

export interface AggregateStatus {
  success: boolean;
  total_folders: number;
  active_folders: number;
  total_pending: number;
  total_detected: number;
  total_ingested: number;
  total_failed: number;
  total_bytes_processed: number;
  folders: WatchedFolder[];
  supported_extensions: string[];
  ingestion_concurrency: number;
}

export interface AddFolderRequest {
  folder_path: string;
  enabled: boolean;
}

export interface UpdateFolderRequest {
  enabled?: boolean;
}

export interface RemoveFolderResponse {
  message: string;
  folder_id: string;
}

export interface ScanFolderResponse {
  success: boolean;
  folder_id: string;
  folder_path: string;
  files_found: number;
  files_queued: number;
  files_failed: number;
  message: string;
}
