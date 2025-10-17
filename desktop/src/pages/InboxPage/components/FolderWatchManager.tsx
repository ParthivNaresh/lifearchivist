/**
 * FolderWatchManager - Modal for managing watched folders
 * 
 * Simple version for Stage 1:
 * - Shows currently watched folder
 * - Add/remove folders
 * - Status indicators
 * - Ready to scale to multiple folders
 */

import React, { useState, useEffect } from 'react';
import {
  FolderOpen,
  X,
  Loader2,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  StopCircle,
  Plus,
} from 'lucide-react';
import { cn } from '../../../utils/cn';
import { API_ENDPOINTS, WS_ENDPOINTS } from '../constants';

interface FolderWatchManagerProps {
  isOpen: boolean;
  onClose: () => void;
  onStatusChange?: () => void;
}

interface WatchStatus {
  enabled: boolean;
  watched_path: string | null;
  pending_files: number;
  supported_extensions: string[];
  debounce_seconds: number;
}

export const FolderWatchManager: React.FC<FolderWatchManagerProps> = ({
  isOpen,
  onClose,
  onStatusChange,
}) => {
  const [status, setStatus] = useState<WatchStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch status when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchStatus();
    }
  }, [isOpen]);

  // Subscribe to WebSocket updates
  useEffect(() => {
    if (!isOpen) return;

    const ws = new WebSocket(WS_ENDPOINTS.FOLDER_WATCHER);

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'folder_watch_status' && message.data) {
          setStatus(message.data);
          setError(null);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    return () => ws.close();
  }, [isOpen]);

  const fetchStatus = async () => {
    try {
      const response = await fetch(API_ENDPOINTS.FOLDER_WATCH_STATUS);
      const data = await response.json();
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
      const result = await (window as any).electronAPI.selectDirectory();

      if (result.canceled || !result.filePaths || result.filePaths.length === 0) {
        setLoading(false);
        return;
      }

      const folderPath = result.filePaths[0];

      const response = await fetch(API_ENDPOINTS.FOLDER_WATCH_START, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_path: folderPath }),
      });

      const data = await response.json();

      if (data.success) {
        await fetchStatus();
        // Trigger parent refetch immediately
        onStatusChange?.();
      } else {
        setError(data.error || 'Failed to start watching folder');
      }
    } catch (err) {
      console.error('Failed to start folder watching:', err);
      setError('Failed to start folder watching');
    } finally {
      setLoading(false);
    }
  };

  const handleStopWatching = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(API_ENDPOINTS.FOLDER_WATCH_STOP, {
        method: 'POST',
      });

      const data = await response.json();

      if (data.success) {
        await fetchStatus();
        // Trigger parent refetch immediately
        onStatusChange?.();
      } else {
        setError(data.error || 'Failed to stop watching folder');
      }
    } catch (err) {
      console.error('Failed to stop folder watching:', err);
      setError('Failed to stop folder watching');
    } finally {
      setLoading(false);
    }
  };

  const handleManualScan = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(API_ENDPOINTS.FOLDER_WATCH_SCAN, {
        method: 'POST',
      });

      const data = await response.json();

      if (data.success) {
        await fetchStatus();
      } else {
        setError(data.error || 'Failed to scan folder');
      }
    } catch (err) {
      console.error('Failed to scan folder:', err);
      setError('Failed to scan folder');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="bg-background border border-border rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-border">
            <div className="flex items-center gap-3">
              <FolderOpen className="h-6 w-6 text-primary" />
              <div>
                <h2 className="text-xl font-semibold">Manage Watched Folders</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Auto-sync files from folders on your computer
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-accent rounded-lg transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {/* Error Display */}
            {error && (
              <div className="mb-4 flex items-start gap-3 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
                <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-medium text-destructive">Error</p>
                  <p className="text-sm text-destructive/80 mt-1">{error}</p>
                </div>
              </div>
            )}

            {/* Watched Folders List */}
            {status?.enabled && status.watched_path ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium">Active Folders</h3>
                  <span className="text-sm text-muted-foreground">
                    {status.pending_files} file{status.pending_files !== 1 ? 's' : ''} pending
                  </span>
                </div>

                {/* Folder Card */}
                <div className="border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-medium truncate" title={status.watched_path}>
                          {status.watched_path}
                        </span>
                        <span className="px-2 py-0.5 text-xs bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded-full">
                          Active
                        </span>
                      </div>
                      <div className="text-sm text-muted-foreground space-y-1">
                        <p>
                          Monitoring {status.supported_extensions.length} file types
                        </p>
                        <p className="text-xs">
                          Debounce: {status.debounce_seconds}s
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleManualScan}
                        disabled={loading}
                        className="p-2 hover:bg-secondary rounded-lg transition-colors"
                        title="Scan now"
                      >
                        {loading ? (
                          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                        ) : (
                          <RefreshCw className="h-4 w-4 text-muted-foreground" />
                        )}
                      </button>
                      <button
                        onClick={handleStopWatching}
                        disabled={loading}
                        className="p-2 hover:bg-destructive/10 rounded-lg transition-colors"
                        title="Stop watching"
                      >
                        <StopCircle className="h-4 w-4 text-destructive" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              /* Empty State */
              <div className="text-center py-12">
                <FolderOpen className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-medium mb-2">No Folders Being Watched</h3>
                <p className="text-sm text-muted-foreground mb-6 max-w-md mx-auto">
                  Add a folder to automatically sync new files as they're added to your computer.
                </p>
                <button
                  onClick={handleAddFolder}
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
                      <span>Starting...</span>
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
          {status?.enabled && (
            <div className="border-t border-border p-4 bg-muted/30">
              <button
                onClick={handleAddFolder}
                disabled={loading}
                className={cn(
                  'w-full flex items-center justify-center gap-2 px-4 py-2',
                  'border-2 border-dashed border-border rounded-lg',
                  'hover:border-primary hover:bg-accent transition-all',
                  'disabled:opacity-50 disabled:cursor-not-allowed',
                  'text-sm font-medium'
                )}
              >
                <Plus className="h-4 w-4" />
                <span>Add Another Folder</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
};
