/**
 * Timeline loading and error states
 */

import React from 'react';
import { AlertCircle, Calendar } from 'lucide-react';

export const LoadingState: React.FC = () => (
  <div className="flex items-center justify-center h-64">
    <div className="text-center">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
      <p className="mt-2 text-muted-foreground">Loading timeline...</p>
    </div>
  </div>
);

export const ErrorState: React.FC<{ error: string; onRetry: () => void }> = ({ error, onRetry }) => (
  <div className="flex items-center justify-center h-64">
    <div className="text-center">
      <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
      <p className="text-red-600 mb-4">{error}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
      >
        Retry
      </button>
    </div>
  </div>
);

export const EmptyState: React.FC = () => (
  <div className="flex items-center justify-center h-64">
    <div className="text-center">
      <Calendar className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
      <p className="text-lg font-medium mb-2">No documents yet</p>
      <p className="text-sm text-muted-foreground">
        Upload some documents to see your timeline
      </p>
    </div>
  </div>
);
