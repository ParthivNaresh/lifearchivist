/**
 * Custom hooks for InboxPage
 */

import { useCallback, useMemo, useState, useEffect } from 'react';
import { useUploadManager } from '../../hooks/useUploadManager';
import { useUploadQueue } from '../../contexts/useUploadQueue';
import { useActivityFeed } from '../../hooks/useActivityFeed';
import { type FolderFilesResult } from '../../types/electron';
import { TIMING, WS_ENDPOINTS, DISPLAY_LIMITS } from './constants';
import { type VaultInfo, type WatchStatus } from './types';
import { fetchVaultInfo, fetchWatchStatus } from './api';
import { calculateWeekCount } from './utils';

/**
 * Hook for managing file uploads
 */
export const useFileUpload = () => {
  const { uploadFiles, uploadFolder } = useUploadManager();
  const {
    state: uploadQueueState,
    updateItemStatus,
    clearCompleted,
    resetQueue,
  } = useUploadQueue();

  const hasActiveUploads = uploadQueueState.activeUploads > 0;
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  // Move Date.now() outside of useMemo to avoid impure function call
  const [currentTime, setCurrentTime] = useState(() => Date.now());

  // Update current time periodically for accurate batch filtering
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000); // Update every second for accurate recent batch detection

    return () => clearInterval(interval);
  }, []);

  const activeBatches = useMemo(() => {
    return uploadQueueState.batches.filter(
      (batch) =>
        batch.status === 'active' ||
        (batch.createdAt > currentTime - TIMING.RECENT_BATCH_DURATION &&
          (batch.status === 'completed' ||
            batch.status === 'partial' ||
            batch.status === 'duplicate'))
    );
  }, [uploadQueueState.batches, currentTime]);

  const showUploadProgress = activeBatches.length > 0;

  const handleFileDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0 || hasActiveUploads) return;

      const firstFile = acceptedFiles[0];
      const batchName =
        acceptedFiles.length === 1 && firstFile ? firstFile.name : `${acceptedFiles.length} Files`;

      try {
        await uploadFiles(acceptedFiles, { batchName });
      } catch (error) {
        console.error('Upload failed:', error);
      }
    },
    [uploadFiles, hasActiveUploads]
  );

  const handleSelectFiles = useCallback(async () => {
    if (hasActiveUploads) return;

    if (window.electronAPI) {
      try {
        const filePaths = await window.electronAPI.selectFiles();
        if (filePaths.length === 0) return;

        // Create file path objects (not actual File objects)
        const files = filePaths.map((filePath) => {
          const fileName = filePath.split('/').pop() ?? filePath;
          return { name: fileName, path: filePath };
        });

        const firstFile = files[0];
        const batchName =
          files.length === 1 && firstFile ? firstFile.name : `${files.length} Selected Files`;

        await uploadFiles(files, { batchName });
      } catch (error) {
        console.error('Error selecting files:', error);
      }
    }
  }, [hasActiveUploads, uploadFiles]);

  const handleSelectFolder = useCallback(async () => {
    if (hasActiveUploads) return;

    if (window.electronAPI && typeof window.electronAPI.selectFolderFiles === 'function') {
      try {
        const folderResult: FolderFilesResult | null = await window.electronAPI.selectFolderFiles();

        if (!folderResult?.files || folderResult.files.length === 0) {
          return;
        }

        // Create file path objects (not actual File objects)
        const files = folderResult.files.map((filePath) => {
          const fileName = filePath.split('/').pop() ?? filePath;
          return { name: fileName, path: filePath };
        });

        const folderName = folderResult.folderPath.split('/').pop() ?? 'Selected Folder';

        await uploadFolder(files, folderName);
      } catch (error) {
        console.error('Folder upload failed:', error);
      }
    }
  }, [hasActiveUploads, uploadFolder]);

  const handleRetry = useCallback(
    (itemId: string) => {
      updateItemStatus(itemId, 'pending');
    },
    [updateItemStatus]
  );

  const handleClearCompleted = useCallback(() => {
    clearCompleted();
    // Optionally navigate to vault after clearing
    if (!hasActiveUploads) {
      setTimeout(() => {
        // You could navigate to vault here if desired
        // navigate('/vault');
      }, TIMING.NAVIGATION_DELAY);
    }
  }, [clearCompleted, hasActiveUploads]);

  const handleCancelUploads = useCallback(() => {
    setShowCancelConfirm(true);
  }, []);

  const confirmCancelUploads = useCallback(() => {
    resetQueue();
    setShowCancelConfirm(false);
  }, [resetQueue]);

  const cancelCancelUploads = useCallback(() => {
    setShowCancelConfirm(false);
  }, []);

  return {
    hasActiveUploads,
    activeBatches,
    showUploadProgress,
    handleFileDrop,
    handleSelectFiles,
    handleSelectFolder,
    handleRetry,
    handleClearCompleted,
    handleCancelUploads,
    // Expose confirmation state and handlers for proper modal implementation
    showCancelConfirm,
    confirmCancelUploads,
    cancelCancelUploads,
  };
};

/**
 * Hook for managing vault information
 *
 * Fetches vault stats (document count, storage usage) and refreshes periodically
 */
export const useVaultInfo = () => {
  const [vaultInfo, setVaultInfo] = useState<VaultInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInfo = useCallback(async () => {
    try {
      const data = await fetchVaultInfo();
      if (data) {
        setVaultInfo(data);
        setError(null);
      } else {
        setError('Failed to fetch vault info');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchInfo();

    // Refresh periodically
    const interval = setInterval(() => {
      void fetchInfo();
    }, TIMING.REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [fetchInfo]);

  return {
    vaultInfo,
    isLoading,
    error,
    refetch: fetchInfo,
  };
};

/**
 * Hook for managing activity feed with week count calculation
 *
 * Wraps the shared useActivityFeed hook and adds week count calculation
 * specific to InboxPage needs.
 */
export const useInboxActivityFeed = (limit = 5) => {
  const [weekCount, setWeekCount] = useState<number>(0);

  // Use shared activity feed hook
  const { events, isLoading, error, refetch, isConnected } = useActivityFeed({
    limit: DISPLAY_LIMITS.ACTIVITY_FETCH_LIMIT,
  });

  // Calculate week count whenever events change
  useEffect(() => {
    setWeekCount(calculateWeekCount(events));
  }, [events]);

  // Return limited events for display
  const recentActivity = events.slice(0, limit);

  return {
    recentActivity,
    weekCount,
    isLoading,
    error,
    refetch,
    isConnected,
  };
};

/**
 * Hook for managing folder watch status with WebSocket updates
 *
 * Fetches folder watch status and subscribes to real-time updates
 */
export const useFolderWatchStatus = () => {
  const [watchStatus, setWatchStatus] = useState<WatchStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await fetchWatchStatus();
      if (data) {
        setWatchStatus(data);
        setError(null);
      } else {
        setError('Failed to fetch watch status');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial fetch and periodic refresh
  useEffect(() => {
    void fetchStatus();

    // Refresh periodically
    const interval = setInterval(() => {
      void fetchStatus();
    }, TIMING.REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [fetchStatus]);

  // WebSocket for real-time updates - separate effect
  useEffect(() => {
    let ws: WebSocket | null = null;

    const connect = () => {
      try {
        ws = new WebSocket(WS_ENDPOINTS.FOLDER_WATCHER);

        ws.onopen = () => {
          console.log('Folder watcher WebSocket connected');
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data as string) as {
              type: string;
              data?: WatchStatus;
            };

            if (message.type === 'folder_watch_status' && message.data) {
              setWatchStatus(message.data);
            }
          } catch (err) {
            console.error('Failed to parse folder watch WebSocket message:', err);
          }
        };

        ws.onerror = () => {
          // Don't log error - it's expected when server is down
        };

        ws.onclose = () => {
          console.log('Folder watcher WebSocket disconnected');
        };
      } catch (err) {
        console.error('Failed to create WebSocket:', err);
      }
    };

    connect();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []); // No dependencies - connect once

  return {
    watchStatus,
    isLoading,
    error,
    refetch: fetchStatus,
  };
};
