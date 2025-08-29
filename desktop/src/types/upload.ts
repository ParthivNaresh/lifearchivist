export interface UploadItem {
  id: string;
  file: File | { name: string; size?: number; path?: string };
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error' | 'duplicate';
  progress: number;
  error?: string;
  result?: any;
  batchId?: string;
  startTime: number;
  completedTime?: number;
  metadata?: Record<string, any>;
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
  | { type: 'UPDATE_ITEM_STATUS'; payload: { itemId: string; status: UploadItem['status']; error?: string; result?: any } }
  | { type: 'UPDATE_ITEM_PROGRESS'; payload: { itemId: string; progress: number; stage?: string; message?: string } }
  | { type: 'REMOVE_BATCH'; payload: string }
  | { type: 'CLEAR_COMPLETED' }
  | { type: 'SET_VISIBILITY'; payload: boolean }
  | { type: 'SET_MINIMIZED'; payload: boolean }
  | { type: 'LOAD_PERSISTED_STATE'; payload: Partial<UploadQueueState> };

export interface UploadQueueContextType {
  state: UploadQueueState;
  dispatch: React.Dispatch<UploadQueueAction>;
  addBatch: (files: (File | { name: string; size?: number; path?: string })[], batchName?: string) => { batchId: string; itemIds: string[] };
  updateItemStatus: (itemId: string, status: UploadItem['status'], error?: string, result?: any) => void;
  updateItemProgress: (itemId: string, progress: number, stage?: string, message?: string) => void;
  removeBatch: (batchId: string) => void;
  clearCompleted: () => void;
  toggleVisibility: () => void;
  toggleMinimized: () => void;
  retryFailedUploads: (batchId?: string) => void;
  clearAllData: () => void;
  resetQueue: () => void;
}

export interface ProgressUpdate {
  file_id: string;
  stage: string;
  progress: number;
  message: string;
  timestamp: number;
  eta_seconds?: number;
  error?: string;
  metadata?: Record<string, any>;
}

export interface WebSocketMessage {
  type: string;
  data?: any;
  id?: string;
  result?: any;
}

export interface ProgressTrackingSession {
  sessionId: string;
  fileId: string;
  websocket?: WebSocket;
  isConnected: boolean;
}