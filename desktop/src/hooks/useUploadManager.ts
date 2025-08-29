import { useCallback } from 'react';
import axios from 'axios';
import { useUploadQueue } from '../contexts/UploadQueueContext';
import { useProgressTracking } from './useProgressTracking';
import { ProgressUpdate } from '../types/upload';

interface UploadOptions {
  onProgress?: (progress: number) => void;
  batchName?: string;
}

interface UploadResult {
  success: boolean;
  file_id?: string;
  error?: string;
  original_path?: string;
}

export const useUploadManager = () => {
  const { addBatch, updateItemStatus, updateItemProgress } = useUploadQueue();
  
  const progressTracking = useProgressTracking({
    onProgressUpdate: (update: ProgressUpdate) => {
      // The file_id from backend should match our item_id
      const itemId = update.file_id;
      
      console.log(`Progress update for item ${itemId}:`, {
        stage: update.stage,
        progress: update.progress,
        message: update.message
      });
      
      updateItemProgress(
        itemId,
        update.progress,
        update.stage,
        update.message
      );
      
      // Update status based on stage and progress
      if (update.error) {
        updateItemStatus(itemId, 'error', update.error);
      } else if (update.stage === 'complete' && update.progress >= 100) {
        updateItemStatus(itemId, 'completed', undefined, update.metadata);
      } else if (update.progress > 0) {
        updateItemStatus(itemId, 'processing');
      }
    },
    onError: (error: string) => {
      console.error('Progress tracking error:', error);
    },
    onConnectionChange: (connected: boolean) => {
      console.log('Progress tracking connection:', connected ? 'connected' : 'disconnected');
    }
  });

  const uploadActualFile = useCallback(async (
    file: File, 
    itemId: string,
    onProgress?: (progress: number) => void
  ): Promise<UploadResult> => {
    let sessionId: string | undefined;
    
    try {
      // Create progress tracking session
      sessionId = await progressTracking.createSession(itemId);
      console.log(`Created progress session ${sessionId} for file ${file.name} (item ${itemId})`);
      
      const formData = new FormData();
      formData.append('file', file);
      formData.append('session_id', sessionId); // Pass session ID to backend
      formData.append('metadata', JSON.stringify({
        original_filename: file.name,
        upload_source: 'drag_drop',
        file_id: itemId // Use itemId as the file_id for progress tracking
      }));

      updateItemStatus(itemId, 'uploading');
      updateItemProgress(itemId, 0, 'upload', 'Starting upload...');

      const response = await axios.post<UploadResult>(
        'http://localhost:8000/api/upload',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          // Note: We rely on WebSocket progress updates instead of onUploadProgress
          // onUploadProgress gives only upload progress, not processing progress
        }
      );

      if (response.data.success) {
        // Handle duplicate files specially
        if (response.data.status === 'duplicate') {
          updateItemStatus(itemId, 'completed', undefined, {
            ...response.data,
            isDuplicate: true,
            message: response.data.message || 'File already exists in archive'
          });
        }
        // For non-duplicate files, progress tracking will handle status updates via WebSocket
        
        return response.data;
      } else {
        updateItemStatus(itemId, 'error', response.data.error || 'Upload failed');
        return response.data;
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || error.message || 'Upload failed';
      updateItemStatus(itemId, 'error', errorMessage);
      return {
        success: false,
        error: errorMessage,
      };
    }
  }, [updateItemStatus, updateItemProgress, progressTracking]);

  const uploadFilePath = useCallback(async (
    filePath: string, 
    itemId: string,
    onProgress?: (progress: number) => void
  ): Promise<UploadResult> => {
    let sessionId: string | undefined;
    
    try {
      // Create progress tracking session
      console.log(`🚀 Starting uploadFilePath for ${filePath} with itemId ${itemId}`);
      sessionId = await progressTracking.createSession(itemId);
      console.log(`✅ Created progress session ${sessionId} for file path ${filePath} (item ${itemId})`);
      
      updateItemStatus(itemId, 'uploading');
      updateItemProgress(itemId, 0, 'upload', 'Starting file import...');

      console.log(`📤 Sending API request to /api/ingest for ${filePath}`);
      const response = await axios.post<UploadResult>(
        'http://localhost:8000/api/ingest',
        {
          path: filePath,
          tags: [],
          metadata: {
            upload_source: 'file_selection',
            file_id: itemId // Use itemId as the file_id for progress tracking
          },
          session_id: sessionId // Pass session ID to backend
        }
      );
      
      console.log(`📥 Received response from /api/ingest:`, response.data);

      if (response.data.success) {
        // Handle duplicate files specially
        if (response.data.status === 'duplicate') {
          // Close any progress tracking for this item since processing is complete
          progressTracking.closeSession(sessionId);
          
          updateItemStatus(itemId, 'duplicate', undefined, {
            ...response.data,
            isDuplicate: true,
            message: response.data.message || 'This document already exists in your archive'
          });
        }
        // For non-duplicate files, progress tracking will handle status updates via WebSocket
        
        return response.data;
      } else {
        updateItemStatus(itemId, 'error', response.data.error || 'Upload failed');
        return response.data;
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || error.message || 'Upload failed';
      updateItemStatus(itemId, 'error', errorMessage);
      return {
        success: false,
        error: errorMessage,
      };
    }
  }, [updateItemStatus, updateItemProgress, progressTracking]);

  const uploadFile = useCallback(async (
    file: File | { name: string; path?: string }, 
    itemId: string,
    onProgress?: (progress: number) => void
  ): Promise<UploadResult> => {
    // Check if this is a real File object or a file path object
    if (file instanceof File) {
      return uploadActualFile(file, itemId, onProgress);
    } else if ('path' in file && file.path) {
      return uploadFilePath(file.path, itemId, onProgress);
    } else {
      updateItemStatus(itemId, 'error', 'Invalid file data');
      return {
        success: false,
        error: 'Invalid file data',
      };
    }
  }, [uploadActualFile, uploadFilePath]);

  const uploadFiles = useCallback(async (
    files: (File | { name: string; size?: number; path?: string })[], 
    options: UploadOptions = {}
  ): Promise<UploadResult[]> => {
    if (files.length === 0) return [];

    // Create batch and get item IDs
    const { batchId, itemIds } = addBatch(files, options.batchName);
    
    const results: UploadResult[] = [];

    // Upload files concurrently (but limit concurrency to prevent overwhelming the server)
    const concurrencyLimit = 3;
    
    for (let i = 0; i < files.length; i += concurrencyLimit) {
      const batchFiles = files.slice(i, i + concurrencyLimit);
      const batchItemIds = itemIds.slice(i, i + concurrencyLimit);
      
      const batchPromises = batchFiles.map(async (file, index) => {
        const itemId = batchItemIds[index];
        return uploadFile(file, itemId, options.onProgress);
      });

      const batchResults = await Promise.allSettled(batchPromises);
      
      batchResults.forEach((result) => {
        if (result.status === 'fulfilled') {
          results.push(result.value);
        } else {
          results.push({
            success: false,
            error: result.reason?.message || 'Upload failed',
          });
        }
      });
    }

    return results;
  }, [addBatch, uploadFile]);

  const uploadFolder = useCallback(async (
    files: (File | { name: string; size?: number; path?: string })[],
    folderName: string,
    options: Omit<UploadOptions, 'batchName'> = {}
  ): Promise<UploadResult[]> => {
    return uploadFiles(files, {
      ...options,
      batchName: `${folderName} (${files.length} files)`,
    });
  }, [uploadFiles]);

  return {
    uploadFiles,
    uploadFolder,
    uploadFile,
    progressTracking: {
      isConnected: progressTracking.isConnected,
      activeConnections: progressTracking.activeConnections,
      closeAllConnections: progressTracking.closeAllConnections,
    }
  };
};