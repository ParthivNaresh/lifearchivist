import { useState } from 'react';
import { AlertCircle, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';
import type { Message } from '../types';
import { getErrorMetadata } from '../utils/metadata';

interface ErrorMessageProps {
  message: Message;
  onRetry?: () => void;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({ message, onRetry }) => {
  const [showDetails, setShowDetails] = useState(false);

  const errorMeta = getErrorMetadata(message.metadata);

  if (!errorMeta) {
    return null;
  }

  return (
    <div className="max-w-[70%] rounded-lg border-2 border-destructive/30 bg-destructive/5 p-4">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          <AlertCircle className="h-5 w-5 text-destructive" />
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-destructive mb-1">Error</p>
          <p className="text-sm text-foreground whitespace-pre-wrap break-words">
            {message.content}
          </p>

          <div className="mt-3 flex items-center gap-2 flex-wrap">
            {errorMeta.retryable && onRetry && (
              <button
                onClick={onRetry}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
              >
                <RefreshCw className="h-3 w-3" />
                Retry
              </button>
            )}

            {errorMeta.raw_error && (
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-border rounded-md hover:bg-accent transition-colors"
              >
                {showDetails ? (
                  <>
                    <ChevronUp className="h-3 w-3" />
                    Hide Details
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-3 w-3" />
                    Show Details
                  </>
                )}
              </button>
            )}
          </div>

          {showDetails && errorMeta.raw_error && (
            <div className="mt-3 p-3 bg-muted/50 rounded-md border border-border">
              <p className="text-xs font-medium text-muted-foreground mb-2">Technical Details</p>
              <div className="space-y-1 text-xs font-mono text-muted-foreground">
                <div>
                  <span className="font-semibold">Type:</span> {errorMeta.error_type}
                </div>
                <div>
                  <span className="font-semibold">Provider:</span> {errorMeta.provider_id}
                </div>
                <div>
                  <span className="font-semibold">Model:</span> {errorMeta.model}
                </div>
                <div className="mt-2 pt-2 border-t border-border">
                  <span className="font-semibold">Raw Error:</span>
                  <pre className="mt-1 whitespace-pre-wrap break-all">{errorMeta.raw_error}</pre>
                </div>
              </div>
            </div>
          )}

          <div className="mt-3 flex items-center gap-3 text-xs text-muted-foreground">
            <span>{new Date(message.created_at).toLocaleTimeString()}</span>
            {message.latency_ms && <span>{message.latency_ms}ms</span>}
          </div>
        </div>
      </div>
    </div>
  );
};
