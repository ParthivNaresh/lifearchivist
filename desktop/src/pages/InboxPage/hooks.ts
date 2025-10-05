/**
 * Custom hooks for InboxPage
 */

import { useCallback, useMemo } from 'react';
import { useUploadManager } from '../../hooks/useUploadManager';
import { useUploadQueue } from '../../contexts/UploadQueueContext';
import { FolderFilesResult } from '../../types/electron';
import { TIMING, UI_TEXT } from './constants';

/**
 * Hook for managing file uploads
 */
export const useFileUpload = () => {
  const { uploadFiles, uploadFolder } = useUploadManager();
  const { 
    state: uploadQueueState, 
    updateItemStatus,
    clearCompleted,
    resetQueue 
  } = useUploadQueue();

  const hasActiveUploads = uploadQueueState.activeUploads > 0;
  
  const activeBatches = useMemo(() => 
    uploadQueueState.batches.filter(
      batch => batch.status === 'active' || 
      (batch.createdAt > Date.now() - TIMING.RECENT_BATCH_DURATION && 
       (batch.status === 'completed' || batch.status === 'partial' || batch.status === 'duplicate'))
    ), 
    [uploadQueueState.batches]
  );
  
  const showUploadProgress = activeBatches.length > 0;

  const handleFileDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0 || hasActiveUploads) return;

    const batchName = acceptedFiles.length === 1 
      ? acceptedFiles[0].name 
      : `${acceptedFiles.length} Files`;
    
    try {
      await uploadFiles(acceptedFiles, { batchName });
    } catch (error) {
      console.error('Upload failed:', error);
    }
  }, [uploadFiles, hasActiveUploads]);

  const handleSelectFiles = useCallback(async () => {
    if (hasActiveUploads) return;
    
    if (window.electronAPI) {
      try {
        const filePaths = await window.electronAPI.selectFiles();
        if (filePaths.length === 0) return;
        
        // Convert file paths to File objects
        const files = filePaths.map(filePath => {
          const fileName = filePath.split('/').pop() || filePath;
          return { name: fileName, path: filePath } as File;
        });
        
        const batchName = files.length === 1 
          ? files[0].name 
          : `${files.length} Selected Files`;
        
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
        
        if (!folderResult || !folderResult.files || folderResult.files.length === 0) {
          return;
        }
        
        // Convert file paths to File objects
        const files = folderResult.files.map(filePath => {
          const fileName = filePath.split('/').pop() || filePath;
          return { name: fileName, path: filePath } as File;
        });
        
        const folderName = folderResult.folderPath.split('/').pop() || 'Selected Folder';
        
        await uploadFolder(files, folderName);
      } catch (error) {
        console.error('Folder upload failed:', error);
      }
    }
  }, [hasActiveUploads, uploadFolder]);

  const handleRetry = useCallback((itemId: string) => {
    updateItemStatus(itemId, 'pending');
  }, [updateItemStatus]);

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
    if (confirm(UI_TEXT.BUTTONS.CANCEL_UPLOADS)) {
      resetQueue();
    }
  }, [resetQueue]);

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
  };
};

/**
 * Hook for handling topic navigation
 */
export const useTopicNavigation = () => {
  const handleTopicClick = useCallback((topic: { name: string }) => {
    // Navigate to documents page with topic filter
    window.location.href = `/documents?tag=${encodeURIComponent(topic.name)}`;
  }, []);

  return handleTopicClick;
};