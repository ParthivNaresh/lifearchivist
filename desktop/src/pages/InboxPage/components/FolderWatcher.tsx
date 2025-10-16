/**
 * FolderWatcher component - manages automatic folder watching
 */

import React, { useState, useEffect } from 'react';
import { FolderOpen, Pencil, Loader2, CheckCircle2, AlertCircle, RefreshCw, StopCircle } from 'lucide-react';
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
    <div className={cn('flex flex-col h-full', className)}>
      {/* Icon and Title - Always Visible */}
      <div className="flex flex-col items-center gap-3 mb-3">
        <FolderOpen className="h-8 w-8 text-primary" />
        <div className="text-center">
          <div className="font-medium">Auto-Watch Folder</div>
          <div className="text-xs text-muted-foreground mt-1">
            {status?.enabled ? 'Monitoring for new files' : 'Auto-sync files from a folder'}
          </div>
        </div>
      </div>

      {/* Watched Folders List */}
      {status?.enabled ? (
        <div className="flex-1 space-y-2 mb-2">
          {/* Single folder for now - ready for multiple */}
          <div className="flex items-center gap-2 p-2 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 flex-shrink-0" />
            <span 
              className="text-xs text-muted-foreground truncate flex-1 min-w-0" 
              title={status.watched_path || ''}
            >
              {getShortPath(status.watched_path)}
            </span>
            
            {/* Inline Action Icons */}
            <div className="flex items-center gap-1 flex-shrink-0">
              <button
                onClick={handleSelectFolder}
                disabled={loading}
                className="p-1 hover:bg-secondary rounded transition-colors"
                title="Change folder"
              >
                <Pencil className="h-3.5 w-3.5 text-muted-foreground" />
              </button>
              <button
                onClick={handleManualScan}
                disabled={loading}
                className="p-1 hover:bg-secondary rounded transition-colors"
                title="Scan now"
              >
                {loading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                ) : (
                  <RefreshCw className="h-3.5 w-3.5 text-muted-foreground" />
                )}
              </button>
              <button
                onClick={handleStopWatching}
                disabled={loading}
                className="p-1 hover:bg-amber-500/20 rounded transition-colors"
                title="Stop watching"
              >
                <StopCircle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-500" />
              </button>
            </div>
          </div>
        </div>
      ) : (
        <button
          onClick={handleSelectFolder}
          disabled={loading}
          className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm flex items-center justify-center gap-2 mt-auto"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Starting...</span>
            </>
          ) : (
            <>
              <FolderOpen className="h-4 w-4" />
              <span>Select Folder</span>
            </>
          )}
        </button>
      )}

      {/* Error Display */}
      {error && (
        <div className="mt-2 flex items-start gap-2 text-xs text-destructive bg-destructive/10 rounded-lg p-2">
          <AlertCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
          <p className="flex-1">{error}</p>
        </div>
      )}
    </div>
  );
};
