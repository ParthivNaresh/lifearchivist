/**
 * FolderWatcher component - manages automatic folder watching
 */

import React, { useState, useEffect } from 'react';
import { FolderOpen, Eye, EyeOff, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { cn } from '../../../utils/cn';

interface FolderWatcherProps {
  className?: string;
}

interface WatchStatus {
  enabled: boolean;
  watched_path: string | null;
  pending_files: number;
  supported_extensions: string[];
  debounce_seconds: number;
}

export const FolderWatcher: React.FC<FolderWatcherProps> = ({ className }) => {
  const [status, setStatus] = useState<WatchStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  // Fetch status on mount and subscribe to WebSocket updates
  useEffect(() => {
    // Initial fetch
    fetchStatus();
    
    // Connect to WebSocket for real-time updates
    const ws = new WebSocket('ws://localhost:8000/ws/folder_watcher');
    
    ws.onopen = () => {
      console.log('🔌 Folder watcher WebSocket connected');
    };
    
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
    
    ws.onerror = (error) => {
      console.error('Folder watcher WebSocket error:', error);
      setError('WebSocket connection error');
    };
    
    ws.onclose = () => {
      console.log('Folder watcher WebSocket disconnected');
    };
    
    return () => {
      ws.close();
    };
  }, []);

  const fetchStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/folder-watch/status');
      const data = await response.json();
      setStatus(data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch folder watch status:', err);
      setError('Failed to connect to server');
    }
  };

  const handleSelectFolder = async () => {
    setLoading(true);
    setError(null);

    try {
      // Use Electron IPC to open folder dialog
      const result = await (window as any).electronAPI.selectDirectory();
      
      if (result.canceled || !result.filePaths || result.filePaths.length === 0) {
        setLoading(false);
        return;
      }

      const folderPath = result.filePaths[0];

      // Start watching the folder
      const response = await fetch('http://localhost:8000/api/folder-watch/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_path: folderPath }),
      });

      const data = await response.json();

      if (data.success) {
        await fetchStatus();
        setIsExpanded(true);
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
      const response = await fetch('http://localhost:8000/api/folder-watch/stop', {
        method: 'POST',
      });

      const data = await response.json();

      if (data.success) {
        await fetchStatus();
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
      const response = await fetch('http://localhost:8000/api/folder-watch/scan', {
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

  const getShortPath = (path: string | null): string => {
    if (!path) return '';
    const parts = path.split('/');
    if (parts.length <= 3) return path;
    return `.../${parts.slice(-2).join('/')}`;
  };

  return (
    <div className={cn('glass-card rounded-xl p-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-primary/20 to-purple-500/20 blur-xl" />
            <FolderOpen className="h-5 w-5 text-primary relative z-10" />
          </div>
          <h3 className="font-semibold text-sm">Auto-Watch Folder</h3>
        </div>

        {status?.enabled && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 hover:bg-secondary/50 rounded transition-colors"
            title={isExpanded ? 'Collapse' : 'Expand'}
          >
            {isExpanded ? (
              <EyeOff className="h-4 w-4 text-muted-foreground" />
            ) : (
              <Eye className="h-4 w-4 text-muted-foreground" />
            )}
          </button>
        )}
      </div>

      {/* Status Display */}
      {status?.enabled ? (
        <div className="space-y-3">
          {/* Active Status */}
          <div className="flex items-start space-x-2 text-sm">
            <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-muted-foreground">
                Watching: <span className="text-foreground font-medium" title={status.watched_path || ''}>
                  {getShortPath(status.watched_path)}
                </span>
              </p>
              {status.pending_files > 0 && (
                <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                  {status.pending_files} file{status.pending_files !== 1 ? 's' : ''} pending...
                </p>
              )}
            </div>
          </div>

          {/* Expanded Details */}
          {isExpanded && (
            <div className="space-y-2 pt-2 border-t border-border/50">
              <div className="text-xs text-muted-foreground space-y-1">
                <p>
                  <span className="font-medium">Debounce:</span> {status.debounce_seconds}s
                </p>
                <p>
                  <span className="font-medium">Supported:</span> {status.supported_extensions.length} file types
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex space-x-2 pt-2">
                <button
                  onClick={handleManualScan}
                  disabled={loading}
                  className="flex-1 px-3 py-1.5 text-xs bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/80 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  {loading ? (
                    <Loader2 className="h-3 w-3 animate-spin mx-auto" />
                  ) : (
                    'Scan Now'
                  )}
                </button>
                <button
                  onClick={handleStopWatching}
                  disabled={loading}
                  className="flex-1 px-3 py-1.5 text-xs bg-destructive/10 text-destructive rounded-lg hover:bg-destructive/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  Stop Watching
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Automatically ingest new files from a folder
          </p>
          
          <button
            onClick={handleSelectFolder}
            disabled={loading}
            className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-all hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 font-medium text-sm flex items-center justify-center space-x-2"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Starting...</span>
              </>
            ) : (
              <>
                <FolderOpen className="h-4 w-4" />
                <span>Select Folder to Watch</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mt-3 flex items-start space-x-2 text-xs text-destructive bg-destructive/10 rounded-lg p-2">
          <AlertCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
          <p>{error}</p>
        </div>
      )}
    </div>
  );
};
