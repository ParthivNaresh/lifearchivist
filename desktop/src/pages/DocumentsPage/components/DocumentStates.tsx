import React from 'react';
import { FileText, AlertCircle } from 'lucide-react';
import { UI_TEXT } from '../constants';

interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ 
  message = 'Loading documents...' 
}) => (
  <div className="flex items-center justify-center h-64">
    <div className="text-center">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
      <p className="mt-2 text-muted-foreground">{message}</p>
    </div>
  </div>
);

interface ErrorStateProps {
  error: string;
  onRetry: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({ error, onRetry }) => (
  <div className="flex items-center justify-center h-64">
    <div className="text-center">
      <AlertCircle className="h-8 w-8 text-red-500 mx-auto" />
      <p className="mt-2 text-red-600">{error}</p>
      <button 
        onClick={onRetry}
        className="mt-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
      >
        Retry
      </button>
    </div>
  </div>
);

interface EmptyStateProps {
  selectedStatus: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ selectedStatus }) => (
  <div className="text-center py-12">
    <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
    <h3 className="text-lg font-medium text-muted-foreground">
      {UI_TEXT.NO_DOCUMENTS}
    </h3>
    <p className="text-sm text-muted-foreground mt-2">
      {selectedStatus !== 'all' 
        ? UI_TEXT.NO_DOCUMENTS_WITH_STATUS(selectedStatus)
        : UI_TEXT.UPLOAD_PROMPT
      }
    </p>
  </div>
);