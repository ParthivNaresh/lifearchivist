import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import { UploadQueueState, UploadQueueAction, UploadQueueContextType, UploadBatch, UploadItem } from '../types/upload';

const STORAGE_KEY = 'lifearchivist-upload-queue';
const AUTO_CLEAR_DELAY = 30000; // 30 seconds
const AUTO_MINIMIZE_DELAY = 10000; // 10 seconds

const initialState: UploadQueueState = {
  batches: [],
  isVisible: false,
  isMinimized: false,
  activeUploads: 0,
  totalProgress: 0,
};

function uploadQueueReducer(state: UploadQueueState, action: UploadQueueAction): UploadQueueState {
  switch (action.type) {
    case 'ADD_BATCH': {
      const newState = {
        ...state,
        batches: [...state.batches, action.payload],
        isVisible: state.isVisible || state.batches.length === 0, // Only auto-show if this is the first batch
        isMinimized: false, // Un-minimize when new uploads start
        activeUploads: state.activeUploads + action.payload.items.length,
      };
      return calculateTotalProgress(newState);
    }

    case 'UPDATE_ITEM_STATUS': {
      const { itemId, status, error, result } = action.payload;
      
      const updatedBatches = state.batches.map(batch => {
        const itemIndex = batch.items.findIndex(item => item.id === itemId);
        if (itemIndex === -1) return batch;

        const updatedItems = [...batch.items];
        const item = updatedItems[itemIndex];
        
        updatedItems[itemIndex] = {
          ...item,
          status,
          error,
          result,
          completedTime: status === 'completed' || status === 'error' || status === 'duplicate' ? Date.now() : undefined,
        };

        const completedFiles = updatedItems.filter(item => item.status === 'completed').length;
        const duplicateFiles = updatedItems.filter(item => item.status === 'duplicate').length;
        const errorFiles = updatedItems.filter(item => item.status === 'error').length;
        const finishedFiles = completedFiles + duplicateFiles;
        
        // Smart batch status logic
        let batchStatus: 'active' | 'completed' | 'error' | 'partial' | 'duplicate';
        
        if (finishedFiles + errorFiles < updatedItems.length) {
          // Still processing
          batchStatus = 'active';
        } else if (errorFiles > 0) {
          // Has errors (highest priority)
          batchStatus = 'error';
        } else if (duplicateFiles === updatedItems.length) {
          // All duplicates
          batchStatus = 'duplicate';
        } else if (completedFiles === updatedItems.length) {
          // All completed successfully
          batchStatus = 'completed';
        } else {
          // Mixed results (some completed, some duplicates)
          batchStatus = 'partial';
        }

        return {
          ...batch,
          items: updatedItems,
          status: batchStatus,
          completedFiles,
          errorFiles,
        };
      });

      const activeUploads = updatedBatches.reduce((acc, batch) => 
        acc + batch.items.filter(item => item.status === 'uploading' || item.status === 'processing').length, 0
      );

      const newState = {
        ...state,
        batches: updatedBatches,
        activeUploads,
      };
      
      return calculateTotalProgress(newState);
    }

    case 'UPDATE_ITEM_PROGRESS': {
      const { itemId, progress, stage, message } = action.payload;
      
      const updatedBatches = state.batches.map(batch => ({
        ...batch,
        items: batch.items.map(item =>
          item.id === itemId ? { 
            ...item, 
            progress,
            progressStage: stage,
            progressMessage: message
          } : item
        ),
      }));

      const newState = {
        ...state,
        batches: updatedBatches,
      };
      
      return calculateTotalProgress(newState);
    }

    case 'REMOVE_BATCH': {
      const updatedBatches = state.batches.filter(batch => batch.id !== action.payload);
      const newState = {
        ...state,
        batches: updatedBatches,
        // Don't auto-hide when removing batches - let user control visibility
      };
      return calculateTotalProgress(newState);
    }

    case 'CLEAR_COMPLETED': {
      const activeBatches = state.batches.filter(batch => batch.status === 'active');
      const newState = {
        ...state,
        batches: activeBatches,
        // Don't auto-hide when clearing - let user control visibility
      };
      return calculateTotalProgress(newState);
    }

    case 'SET_VISIBILITY':
      return { ...state, isVisible: action.payload };

    case 'SET_MINIMIZED':
      return { ...state, isMinimized: action.payload };

    case 'LOAD_PERSISTED_STATE':
      return { ...state, ...action.payload };

    default:
      return state;
  }
}

function calculateTotalProgress(state: UploadQueueState): UploadQueueState {
  const allItems = state.batches.flatMap(batch => batch.items);
  const totalItems = allItems.length;
  
  if (totalItems === 0) {
    return { ...state, totalProgress: 0 };
  }

  const totalProgress = allItems.reduce((acc, item) => {
    if (item.status === 'completed') return acc + 100;
    if (item.status === 'duplicate') return acc + 100;
    if (item.status === 'error') return acc + 0;
    return acc + item.progress;
  }, 0);

  return {
    ...state,
    totalProgress: totalProgress / totalItems,
  };
}

function generateId(): string {
  return Math.random().toString(36).substring(2) + Date.now().toString(36);
}

function persistState(state: UploadQueueState): void {
  try {
    const persistable = {
      batches: state.batches.map(batch => ({
        ...batch,
        items: batch.items.map(item => ({
          ...item,
          file: item.file instanceof File ? { name: item.file.name, size: item.file.size } : item.file,
        })),
      })),
      isVisible: state.isVisible,
      isMinimized: state.isMinimized,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(persistable));
  } catch (error) {
    console.error('Failed to persist upload queue state:', error);
  }
}

function loadPersistedState(): Partial<UploadQueueState> {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return {};

    const parsed = JSON.parse(stored);
    
    // More aggressive filtering to handle stuck uploads
    const now = Date.now();
    const oneHourAgo = now - 60 * 60 * 1000;
    const thirtyMinutesAgo = now - 30 * 60 * 1000;
    
    const validBatches = (parsed.batches || []).filter((batch: UploadBatch) => {
      // Always keep recent batches (less than 30 minutes old)
      if (batch.createdAt > thirtyMinutesAgo) {
        return true;
      }
      
      // For older batches, only keep if completed successfully
      if (batch.createdAt > oneHourAgo && batch.status === 'completed') {
        return true;
      }
      
      // Remove all older batches and stuck active batches (older than 30 minutes)
      return false;
    });

    // Clean up items in remaining batches - remove stuck processing items
    const cleanedBatches = validBatches.map((batch: UploadBatch) => ({
      ...batch,
      items: batch.items.filter((item: any) => {
        // Keep recently started items (less than 30 minutes)
        if (item.startTime > thirtyMinutesAgo) {
          return true;
        }
        
        // Remove old processing/uploading items that are clearly stuck
        if ((item.status === 'uploading' || item.status === 'processing') && 
            item.startTime < thirtyMinutesAgo) {
          console.log(`Removing stuck upload item: ${item.file.name} (started ${new Date(item.startTime)})`);
          return false;
        }
        
        // Keep completed and error items for a while
        return item.status === 'completed' || item.status === 'error';
      })
    })).filter((batch: UploadBatch) => batch.items.length > 0); // Remove empty batches

    return {
      batches: cleanedBatches,
      isVisible: cleanedBatches.length > 0 && parsed.isVisible,
      isMinimized: parsed.isMinimized || false,
    };
  } catch (error) {
    console.error('Failed to load persisted upload queue state:', error);
    localStorage.removeItem(STORAGE_KEY);
    return {};
  }
}

const UploadQueueContext = createContext<UploadQueueContextType | null>(null);

export const useUploadQueue = (): UploadQueueContextType => {
  const context = useContext(UploadQueueContext);
  if (!context) {
    throw new Error('useUploadQueue must be used within an UploadQueueProvider');
  }
  return context;
};

interface UploadQueueProviderProps {
  children: React.ReactNode;
}

export const UploadQueueProvider: React.FC<UploadQueueProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(uploadQueueReducer, initialState);

  // Load persisted state on mount
  useEffect(() => {
    const persistedState = loadPersistedState();
    if (Object.keys(persistedState).length > 0) {
      dispatch({ type: 'LOAD_PERSISTED_STATE', payload: persistedState });
    }
  }, []);

  // Persist state changes
  useEffect(() => {
    if (state.batches.length > 0 || state.isVisible) {
      persistState(state);
    }
  }, [state]);

  // Note: Removed auto-minimize and auto-clear behaviors to give users full control

  const addBatch = useCallback((files: (File | { name: string; size?: number; path?: string })[], batchName?: string): { batchId: string; itemIds: string[] } => {
    const batchId = generateId();
    const now = Date.now();
    
    const batchDisplayName = batchName || 
      (files.length === 1 ? files[0].name : `${files.length} Files`);

    const items: UploadItem[] = files.map(file => ({
      id: generateId(),
      file,
      status: 'pending',
      progress: 0,
      batchId,
      startTime: now,
    }));

    const batch: UploadBatch = {
      id: batchId,
      name: batchDisplayName,
      items,
      status: 'active',
      createdAt: now,
      totalFiles: files.length,
      completedFiles: 0,
      errorFiles: 0,
    };

    dispatch({ type: 'ADD_BATCH', payload: batch });
    return { 
      batchId, 
      itemIds: items.map(item => item.id) 
    };
  }, []);

  const updateItemStatus = useCallback((itemId: string, status: UploadItem['status'], error?: string, result?: any) => {
    dispatch({ type: 'UPDATE_ITEM_STATUS', payload: { itemId, status, error, result } });
  }, []);

  const updateItemProgress = useCallback((itemId: string, progress: number, stage?: string, message?: string) => {
    dispatch({ type: 'UPDATE_ITEM_PROGRESS', payload: { itemId, progress, stage, message } });
  }, []);

  const removeBatch = useCallback((batchId: string) => {
    dispatch({ type: 'REMOVE_BATCH', payload: batchId });
  }, []);

  const clearCompleted = useCallback(() => {
    dispatch({ type: 'CLEAR_COMPLETED' });
  }, []);

  const toggleVisibility = useCallback(() => {
    dispatch({ type: 'SET_VISIBILITY', payload: !state.isVisible });
  }, [state.isVisible]);

  const toggleMinimized = useCallback(() => {
    dispatch({ type: 'SET_MINIMIZED', payload: !state.isMinimized });
  }, [state.isMinimized]);

  const retryFailedUploads = useCallback((batchId?: string) => {
    const batchesToRetry = batchId 
      ? state.batches.filter(batch => batch.id === batchId)
      : state.batches;

    batchesToRetry.forEach(batch => {
      batch.items
        .filter(item => item.status === 'error')
        .forEach(item => {
          updateItemStatus(item.id, 'pending');
        });
    });
  }, [state.batches, updateItemStatus]);

  const clearAllData = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE_KEY);
      dispatch({ type: 'LOAD_PERSISTED_STATE', payload: {} });
      console.log('Upload queue localStorage data cleared');
    } catch (error) {
      console.error('Failed to clear upload queue localStorage:', error);
    }
  }, []);

  const resetQueue = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE_KEY);
      const newState = {
        batches: [],
        isVisible: false,
        isMinimized: false,
        activeUploads: 0,
        totalProgress: 0,
      };
      dispatch({ type: 'LOAD_PERSISTED_STATE', payload: newState });
      console.log('Upload queue completely reset');
    } catch (error) {
      console.error('Failed to reset upload queue:', error);
    }
  }, []);

  const contextValue: UploadQueueContextType = {
    state,
    dispatch,
    addBatch,
    updateItemStatus,
    updateItemProgress,
    removeBatch,
    clearCompleted,
    toggleVisibility,
    toggleMinimized,
    retryFailedUploads,
    clearAllData,
    resetQueue,
  };

  return (
    <UploadQueueContext.Provider value={contextValue}>
      {children}
    </UploadQueueContext.Provider>
  );
};