export interface UploadResult {
  isDuplicate?: boolean;
  message?: string;
  documentId?: string;
  [key: string]: unknown;
}

export interface UploadItemMetadata {
  original_filename?: string;
  upload_source?: string;
  file_id?: string;
  [key: string]: string | number | boolean | undefined;
}

export interface UploadItem {
  id: string;
  file: File | { name: string; size?: number; path?: string };
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error' | 'duplicate';
  progress: number;
  error?: string;
  result?: UploadResult;
  batchId?: string;
  startTime: number;
  completedTime?: number;
  metadata?: UploadItemMetadata;
  progressStage?: string;
  progressMessage?: string;
  sessionId?: string;
}

export interface UploadBatch {
  id: string;
  name: string;
  items: UploadItem[];
  status: 'active' | 'completed' | 'error' | 'partial' | 'duplicate';
  createdAt: number;
  totalFiles: number;
  completedFiles: number;
  errorFiles: number;
}

export interface UploadQueueState {
  batches: UploadBatch[];
  isVisible: boolean;
  isMinimized: boolean;
  activeUploads: number;
  totalProgress: number;
}

export type UploadQueueAction =
  | { type: 'ADD_BATCH'; payload: UploadBatch }
  | {
      type: 'UPDATE_ITEM_STATUS';
      payload: {
        itemId: string;
        status: UploadItem['status'];
        error?: string;
        result?: UploadResult;
      };
    }
  | {
      type: 'UPDATE_ITEM_PROGRESS';
      payload: { itemId: string; progress: number; stage?: string; message?: string };
    }
  | { type: 'REMOVE_BATCH'; payload: string }
  | { type: 'CLEAR_COMPLETED' }
  | { type: 'SET_VISIBILITY'; payload: boolean }
  | { type: 'SET_MINIMIZED'; payload: boolean }
  | { type: 'LOAD_PERSISTED_STATE'; payload: Partial<UploadQueueState> };

export interface UploadQueueContextType {
  state: UploadQueueState;
  dispatch: React.Dispatch<UploadQueueAction>;
  addBatch: (
    files: (File | { name: string; size?: number; path?: string })[],
    batchName?: string
  ) => { batchId: string; itemIds: string[] };
  updateItemStatus: (
    itemId: string,
    status: UploadItem['status'],
    error?: string,
    result?: UploadResult
  ) => void;
  updateItemProgress: (itemId: string, progress: number, stage?: string, message?: string) => void;
  removeBatch: (batchId: string) => void;
  clearCompleted: () => void;
  toggleVisibility: () => void;
  toggleMinimized: () => void;
  retryFailedUploads: (batchId?: string) => void;
  clearAllData: () => void;
  resetQueue: () => void;
}

export interface ProgressMetadata {
  status?: string;
  isDuplicate?: boolean;
  message?: string;
  document_id?: string;
  file_hash?: string;
  [key: string]: unknown;
}

export interface ProgressUpdate {
  file_id: string;
  stage: string;
  progress: number;
  message: string;
  timestamp: number;
  eta_seconds?: number;
  error?: string;
  metadata?: ProgressMetadata;
}

export interface WebSocketMessageData {
  file_id?: string;
  stage?: string;
  progress?: number;
  message?: string;
  timestamp?: number;
  eta_seconds?: number;
  error?: string;
  metadata?: ProgressMetadata;
  [key: string]: unknown;
}

export interface WebSocketMessage {
  type: string;
  data?: WebSocketMessageData | ProgressUpdate;
  id?: string;
  result?: {
    success?: boolean;
    error?: string;
    [key: string]: unknown;
  };
}

export interface ProgressTrackingSession {
  sessionId: string;
  fileId: string;
  websocket?: WebSocket;
  isConnected: boolean;
}
