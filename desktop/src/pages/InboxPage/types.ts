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
