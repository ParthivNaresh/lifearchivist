/**
 * FolderWatchManager - Multi-folder watching management
 *
 * Features:
 * - List all watched folders with stats
 * - Add/remove folders
 * - Enable/disable per folder
 * - Manual scan per folder
 * - Real-time WebSocket updates
 * - Per-folder status indicators
 */

import { useState, useEffect } from 'react';
import {
  FolderOpen,
  X,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Search,
  StopCircle,
  Plus,
  Play,
  Trash2,
} from 'lucide-react';
import { cn } from '../../../utils/cn';
import { API_ENDPOINTS, WS_ENDPOINTS } from '../constants';

interface FolderWatchManagerProps {
  isOpen: boolean;
  onClose: () => void;
  onStatusChange?: () => void;
}

interface FolderStats {
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

interface WatchedFolder {
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

interface AggregateStatus {
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

interface WebSocketMessage {
  type: string;
  data?: Partial<AggregateStatus>;
}

interface ElectronDirectoryResult {
  canceled: boolean;
  filePaths?: string[];
}

interface ErrorResponse {
  detail?: string;
}

interface ScanResponse {
  files_found: number;
  files_queued: number;
}

export const FolderWatchManager: React.FC<FolderWatchManagerProps> = ({
  isOpen,
  onClose,
  onStatusChange,
}) => {
  const [status, setStatus] = useState<AggregateStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingFolderId, setLoadingFolderId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [folderToDelete, setFolderToDelete] = useState<WatchedFolder | null>(null);
  const [highlightedFolderId, setHighlightedFolderId] = useState<string | null>(null);
  const [fadingOutFolderId, setFadingOutFolderId] = useState<string | null>(null);

  // Fetch status when modal opens
  useEffect(() => {
    if (isOpen) {
      void fetchStatus();
    }
  }, [isOpen]);

  // Subscribe to WebSocket updates
  useEffect(() => {
    if (!isOpen) return;

    const ws = new WebSocket(WS_ENDPOINTS.FOLDER_WATCHER);

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data as string) as WebSocketMessage;
        if (message.type === 'folder_watch_status' && message.data) {
          // Directly update status from WebSocket data instead of fetching
          // This prevents infinite loops when scan triggers broadcasts
          setStatus((prevStatus) => {
            if (!prevStatus) return null;
            return {
              ...prevStatus,
              ...message.data,
            };
          });
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => ws.close();
  }, [isOpen]);

  const fetchStatus = async () => {
    try {
      const response = await fetch(API_ENDPOINTS.FOLDER_WATCH_STATUS);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = (await response.json()) as AggregateStatus;
      setStatus(data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch folder watch status:', err);
      setError('Failed to connect to server');
    }
  };

  const handleAddFolder = async () => {
    setLoading(true);
    setError(null);

    try {
      // Check if Electron API is available
      if (!window.electronAPI?.selectDirectory) {
        throw new Error('Electron API not available');
      }

      const result =
        (await window.electronAPI.selectDirectory()) as unknown as ElectronDirectoryResult;

      if (result.canceled || !result.filePaths || result.filePaths.length === 0) {
        setLoading(false);
        return;
      }

      const folderPath = result.filePaths[0];

      // Check if folder is already being watched
      const existingFolder = status?.folders.find((folder) => folder.path === folderPath);

      if (existingFolder) {
        // Highlight the existing folder card
        setHighlightedFolderId(existingFolder.id);

        // Scroll to the folder if not in view
        setTimeout(() => {
          const element = document.getElementById(`folder-${existingFolder.id}`);
          element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);

        // Start fade out after 2 seconds
        setTimeout(() => setFadingOutFolderId(existingFolder.id), 2000);
        // Clear highlight after fade completes (2s + 500ms fade)
        setTimeout(() => {
          setHighlightedFolderId(null);
          setFadingOutFolderId(null);
        }, 2500);

        setLoading(false);
        return;
      }

      const response = await fetch(API_ENDPOINTS.FOLDER_WATCH_FOLDERS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          folder_path: folderPath,
          enabled: true,
        }),
      });

      if (!response.ok) {
        const data = (await response.json()) as ErrorResponse;
        // Check if it's a "already watched" error from backend
        const errorMsg = data.detail ?? 'Failed to add folder';
        if (
          errorMsg.toLowerCase().includes('already') &&
          errorMsg.toLowerCase().includes('watch')
        ) {
          // Try to find and highlight the folder
          const existingFolder = status?.folders.find((folder) => folder.path === folderPath);
          if (existingFolder) {
            setHighlightedFolderId(existingFolder.id);
            setTimeout(() => {
              const element = document.getElementById(`folder-${existingFolder.id}`);
              element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 100);
            setTimeout(() => setFadingOutFolderId(existingFolder.id), 2000);
            setTimeout(() => {
              setHighlightedFolderId(null);
              setFadingOutFolderId(null);
            }, 2500);
          }
        } else {
          throw new Error(errorMsg);
        }
        setLoading(false);
        return;
      }

      await fetchStatus();
      onStatusChange?.();
    } catch (err) {
      console.error('Failed to add folder:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to add folder';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveFolder = async (folderId: string) => {
    setLoadingFolderId(folderId);
    setError(null);

    try {
      const response = await fetch(API_ENDPOINTS.FOLDER_WATCH_FOLDER(folderId), {
        method: 'DELETE',
      });

      if (!response.ok) {
        const data = (await response.json()) as ErrorResponse;
        throw new Error(data.detail ?? 'Failed to remove folder');
      }

      await fetchStatus();
      onStatusChange?.();
    } catch (err) {
      console.error('Failed to remove folder:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to remove folder';
      setError(errorMessage);
    } finally {
      setLoadingFolderId(null);
    }
  };

  const handleToggleFolder = async (folderId: string, currentlyEnabled: boolean) => {
    setLoadingFolderId(folderId);
    setError(null);

    try {
      const response = await fetch(API_ENDPOINTS.FOLDER_WATCH_FOLDER(folderId), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !currentlyEnabled }),
      });

      if (!response.ok) {
        const data = (await response.json()) as ErrorResponse;
        throw new Error(data.detail ?? 'Failed to update folder');
      }

      await fetchStatus();
      onStatusChange?.();
    } catch (err) {
      console.error('Failed to toggle folder:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to update folder';
      setError(errorMessage);
    } finally {
      setLoadingFolderId(null);
    }
  };

  const handleScanFolder = async (folderId: string) => {
    setLoadingFolderId(folderId);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await fetch(API_ENDPOINTS.FOLDER_WATCH_SCAN_FOLDER(folderId), {
        method: 'POST',
      });

      if (!response.ok) {
        const data = (await response.json()) as ErrorResponse;
        throw new Error(data.detail ?? 'Failed to scan folder');
      }

      const data = (await response.json()) as ScanResponse;

      // Show success message with scan results
      setSuccessMessage(
        `Scan complete: ${data.files_found} file${data.files_found !== 1 ? 's' : ''} found, ` +
          `${data.files_queued} queued for ingestion`
      );

      // Auto-dismiss after 5 seconds
      setTimeout(() => setSuccessMessage(null), 5000);

      await fetchStatus();
    } catch (err) {
      console.error('Failed to scan folder:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to scan folder';
      setError(errorMessage);
    } finally {
      setLoadingFolderId(null);
    }
  };

  const confirmDelete = (folder: WatchedFolder) => {
    setFolderToDelete(folder);
  };

  const cancelDelete = () => {
    setFolderToDelete(null);
  };

  const executeDelete = async () => {
    if (!folderToDelete) return;

    const folderId = folderToDelete.id;
    setFolderToDelete(null);
    await handleRemoveFolder(folderId);
  };

  const getStatusColor = (folder: WatchedFolder) => {
    if (!folder.enabled) return 'text-muted-foreground';
    if (folder.health === 'unhealthy') return 'text-destructive';
    if (folder.health === 'degraded') return 'text-yellow-500';
    if (folder.is_active) return 'text-emerald-500';
    return 'text-muted-foreground';
  };

  const getStatusBadge = (folder: WatchedFolder) => {
    if (!folder.enabled) {
      return (
        <span className="px-2 py-0.5 text-xs bg-muted text-muted-foreground rounded-full">
          Disabled
        </span>
      );
    }
    if (folder.health === 'unhealthy') {
      return (
        <span className="px-2 py-0.5 text-xs bg-destructive/10 text-destructive rounded-full">
          Unhealthy
        </span>
      );
    }
    if (folder.health === 'degraded') {
      return (
        <span className="px-2 py-0.5 text-xs bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 rounded-full">
          Degraded
        </span>
      );
    }
    if (folder.is_active) {
      return (
        <span className="px-2 py-0.5 text-xs bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded-full">
          Active
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 text-xs bg-muted text-muted-foreground rounded-full">
        Stopped
      </span>
    );
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-50" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="bg-background border border-border rounded-xl shadow-2xl w-full max-w-4xl h-[700px] overflow-hidden flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-border">
            <div className="flex items-center gap-3">
              <FolderOpen className="h-6 w-6 text-primary" />
              <div>
                <h2 className="text-xl font-semibold">Manage Watched Folders</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  {status ? (
                    <>
                      {status.total_folders} folder{status.total_folders !== 1 ? 's' : ''} •{' '}
                      {status.active_folders} active • {status.total_pending} pending
                    </>
                  ) : (
                    'Auto-sync files from folders on your computer'
                  )}
                </p>
              </div>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-accent rounded-lg transition-colors">
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {/* Success Message */}
            {successMessage && (
              <div className="mb-4 flex items-start gap-3 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-medium text-emerald-600 dark:text-emerald-400">Success</p>
                  <p className="text-sm text-emerald-600/80 dark:text-emerald-400/80 mt-1">
                    {successMessage}
                  </p>
                </div>
                <button
                  onClick={() => setSuccessMessage(null)}
                  className="p-1 hover:bg-emerald-500/20 rounded"
                >
                  <X className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                </button>
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div className="mb-4 flex items-start gap-3 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
                <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-medium text-destructive">Error</p>
                  <p className="text-sm text-destructive/80 mt-1">{error}</p>
                </div>
                <button
                  onClick={() => setError(null)}
                  className="p-1 hover:bg-destructive/20 rounded"
                >
                  <X className="h-4 w-4 text-destructive" />
                </button>
              </div>
            )}

            {/* Folders List */}
            {status && status.folders.length > 0 ? (
              <div className="space-y-3">
                {status.folders.map((folder) => (
                  <div
                    key={folder.id}
                    id={`folder-${folder.id}`}
                    className={cn(
                      'relative rounded-lg p-4 transition-all duration-500 ease-in-out',
                      highlightedFolderId === folder.id && fadingOutFolderId !== folder.id
                        ? 'border border-primary/40 bg-gradient-to-br from-primary/10 via-primary/5 to-transparent backdrop-blur-sm shadow-2xl shadow-primary/30'
                        : highlightedFolderId === folder.id && fadingOutFolderId === folder.id
                          ? 'border border-border bg-transparent'
                          : 'border border-border hover:bg-accent/30'
                    )}
                    style={
                      highlightedFolderId === folder.id && fadingOutFolderId !== folder.id
                        ? {
                            boxShadow: `
                              0 0 30px rgba(var(--primary-rgb, 59, 130, 246), 0.3),
                              0 0 60px rgba(var(--primary-rgb, 59, 130, 246), 0.15),
                              inset 0 0 20px rgba(var(--primary-rgb, 59, 130, 246), 0.05)
                            `,
                          }
                        : highlightedFolderId === folder.id && fadingOutFolderId === folder.id
                          ? {
                              boxShadow: `
                              0 0 0px rgba(var(--primary-rgb, 59, 130, 246), 0),
                              0 0 0px rgba(var(--primary-rgb, 59, 130, 246), 0),
                              inset 0 0 0px rgba(var(--primary-rgb, 59, 130, 246), 0)
                            `,
                            }
                          : undefined
                    }
                  >
                    {/* Glassmorphism glow overlay */}
                    {(highlightedFolderId === folder.id || fadingOutFolderId === folder.id) && (
                      <div
                        className={cn(
                          'absolute inset-0 rounded-lg bg-gradient-to-br from-primary/20 via-transparent to-primary/10 pointer-events-none transition-opacity duration-500',
                          fadingOutFolderId === folder.id
                            ? 'opacity-0 animate-none'
                            : 'opacity-100 animate-pulse'
                        )}
                      />
                    )}
                    <div className="flex items-start gap-3">
                      <CheckCircle2
                        className={cn('h-5 w-5 flex-shrink-0 mt-0.5', getStatusColor(folder))}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                          <span className="font-medium truncate" title={folder.path}>
                            {folder.path}
                          </span>
                          {getStatusBadge(folder)}
                          {(highlightedFolderId === folder.id ||
                            fadingOutFolderId === folder.id) && (
                            <span
                              className={cn(
                                'px-2 py-0.5 text-xs bg-primary/20 text-primary rounded-full backdrop-blur-sm border border-primary/30 font-medium shadow-lg shadow-primary/20 transition-opacity duration-500',
                                fadingOutFolderId === folder.id
                                  ? 'opacity-0 animate-none'
                                  : 'opacity-100 animate-pulse'
                              )}
                            >
                              Already watching
                            </span>
                          )}
                        </div>

                        {/* Stats */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm text-muted-foreground mt-3">
                          <div>
                            <span className="text-xs uppercase tracking-wide">Ingested</span>
                            <p className="font-medium text-foreground">
                              {folder.stats.files_ingested}
                            </p>
                          </div>
                          <div>
                            <span className="text-xs uppercase tracking-wide">Failed</span>
                            <p className="font-medium text-foreground">
                              {folder.stats.files_failed}
                            </p>
                          </div>
                          <div>
                            <span className="text-xs uppercase tracking-wide">Success Rate</span>
                            <p className="font-medium text-foreground">
                              {(folder.success_rate * 100).toFixed(0)}%
                            </p>
                          </div>
                          <div>
                            <span className="text-xs uppercase tracking-wide">Processed</span>
                            <p className="font-medium text-foreground">
                              {formatBytes(folder.stats.bytes_processed)}
                            </p>
                          </div>
                        </div>

                        {/* Error message if unhealthy */}
                        {folder.stats.last_error && folder.health !== 'healthy' && (
                          <div className="mt-3 text-xs text-destructive bg-destructive/10 p-2 rounded">
                            {folder.stats.last_error}
                          </div>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-1">
                        {/* Scan button */}
                        <button
                          onClick={() => void handleScanFolder(folder.id)}
                          disabled={!folder.enabled || loadingFolderId === folder.id}
                          className="p-2 hover:bg-secondary rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Scan for files"
                        >
                          {loadingFolderId === folder.id ? (
                            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                          ) : (
                            <Search className="h-4 w-4 text-muted-foreground" />
                          )}
                        </button>

                        {/* Enable/Disable button */}
                        <button
                          onClick={() => void handleToggleFolder(folder.id, folder.enabled)}
                          disabled={loadingFolderId === folder.id}
                          className="p-2 hover:bg-secondary rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title={folder.enabled ? 'Disable' : 'Enable'}
                        >
                          {folder.enabled ? (
                            <StopCircle className="h-4 w-4 text-yellow-500" />
                          ) : (
                            <Play className="h-4 w-4 text-emerald-500" />
                          )}
                        </button>

                        {/* Remove button */}
                        <button
                          onClick={() => confirmDelete(folder)}
                          disabled={loadingFolderId === folder.id}
                          className="p-2 hover:bg-destructive/10 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Remove folder"
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              /* Empty State */
              <div className="text-center py-12">
                <FolderOpen className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-medium mb-2">No Folders Being Watched</h3>
                <p className="text-sm text-muted-foreground mb-6 max-w-md mx-auto">
                  Add folders to automatically sync new files as they&apos;re added to your
                  computer.
                </p>
                <button
                  onClick={() => void handleAddFolder()}
                  disabled={loading}
                  className={cn(
                    'inline-flex items-center gap-2 px-6 py-3',
                    'bg-primary text-primary-foreground rounded-lg',
                    'hover:bg-primary/90 transition-all',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                    'font-medium'
                  )}
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Adding...</span>
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4" />
                      <span>Add Folder to Watch</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>

          {/* Footer */}
          {status && status.folders.length > 0 && (
            <div className="border-t border-border p-4 bg-muted/30">
              <button
                onClick={() => void handleAddFolder()}
                disabled={loading}
                className={cn(
                  'w-full flex items-center justify-center gap-2 px-4 py-2',
                  'border-2 border-dashed border-border rounded-lg',
                  'hover:border-primary hover:bg-accent transition-all',
                  'disabled:opacity-50 disabled:cursor-not-allowed',
                  'text-sm font-medium'
                )}
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Adding...</span>
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4" />
                    <span>Add Another Folder</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      {folderToDelete && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 bg-black/70 z-[60]" onClick={cancelDelete} />

          {/* Confirmation Dialog */}
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
            <div
              className="bg-background border border-border rounded-xl shadow-2xl w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="p-6 border-b border-border">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-6 w-6 text-destructive flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold">Remove Watched Folder?</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      This action cannot be undone.
                    </p>
                  </div>
                </div>
              </div>

              {/* Content */}
              <div className="p-6 space-y-4">
                <div className="bg-muted/50 rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Path:</span>
                    <span
                      className="text-sm text-muted-foreground truncate"
                      title={folderToDelete.path}
                    >
                      {folderToDelete.path}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <div>
                      <span className="font-medium">Ingested:</span>{' '}
                      <span className="text-muted-foreground">
                        {folderToDelete.stats.files_ingested}
                      </span>
                    </div>
                    <div>
                      <span className="font-medium">Processed:</span>{' '}
                      <span className="text-muted-foreground">
                        {formatBytes(folderToDelete.stats.bytes_processed)}
                      </span>
                    </div>
                  </div>
                </div>

                <p className="text-sm text-muted-foreground">
                  This will stop watching the folder. Your files and ingested documents will not be
                  deleted.
                </p>
              </div>

              {/* Actions */}
              <div className="p-6 border-t border-border flex items-center justify-end gap-3">
                <button
                  onClick={cancelDelete}
                  className="px-4 py-2 text-sm font-medium rounded-lg hover:bg-accent transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => void executeDelete()}
                  className="px-4 py-2 text-sm font-medium bg-destructive text-destructive-foreground rounded-lg hover:bg-destructive/90 transition-colors"
                >
                  Remove Folder
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
};
