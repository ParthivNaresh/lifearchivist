import { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Folder,
  Files,
  Clock,
  CheckCircle2,
  XCircle,
  Trash2,
  RotateCcw,
  Copy,
  CheckCircle,
} from 'lucide-react';
import { type UploadBatch as UploadBatchType } from '../../types/upload';
import { UploadItem } from './UploadItem';

interface UploadBatchProps {
  batch: UploadBatchType;
  onRemove: () => void;
  onRetryBatch: () => void;
  onRetryItem: (itemId: string) => void;
}

const getBatchIcon = (batchName: string) => {
  if (batchName.toLowerCase().includes('folder') || batchName.includes('/')) {
    return <Folder className="w-4 h-4" />;
  }
  return <Files className="w-4 h-4" />;
};

const getBatchStatusIcon = (status: UploadBatchType['status']) => {
  switch (status) {
    case 'active':
      return <Clock className="w-4 h-4 text-amber-400 animate-pulse" />;
    case 'completed':
      return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
    case 'duplicate':
      return <Copy className="w-4 h-4 text-amber-400" />;
    case 'partial':
      return <CheckCircle className="w-4 h-4 text-blue-400" />;
    case 'error':
      return <XCircle className="w-4 h-4 text-red-400" />;
    default:
      return <Clock className="w-4 h-4 text-gray-400" />;
  }
};

const getBatchStatusColor = (status: UploadBatchType['status']) => {
  switch (status) {
    case 'active':
      return 'border-amber-500/20 bg-gradient-to-br from-amber-500/10 to-amber-600/5';
    case 'completed':
      return 'border-emerald-500/20 bg-gradient-to-br from-emerald-500/10 to-emerald-600/5';
    case 'duplicate':
      return 'border-amber-500/20 bg-gradient-to-br from-amber-500/15 to-amber-600/10';
    case 'partial':
      return 'border-blue-500/20 bg-gradient-to-br from-blue-500/10 to-blue-600/5';
    case 'error':
      return 'border-red-500/20 bg-gradient-to-br from-red-500/10 to-red-600/5';
    default:
      return 'border-gray-500/20 bg-gradient-to-br from-gray-500/10 to-gray-600/5';
  }
};

const calculateBatchProgress = (batch: UploadBatchType): number => {
  if (batch.items.length === 0) return 0;

  const totalProgress = batch.items.reduce((acc, item) => {
    if (item.status === 'completed') return acc + 100;
    if (item.status === 'error') return acc + 0;
    return acc + item.progress;
  }, 0);

  return totalProgress / batch.items.length;
};

const formatTimeAgo = (timestamp: number): string => {
  const now = Date.now();
  const diff = now - timestamp;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return new Date(timestamp).toLocaleDateString();
};

export const UploadBatch: React.FC<UploadBatchProps> = ({
  batch,
  onRemove,
  onRetryBatch,
  onRetryItem,
}) => {
  const [isExpanded, setIsExpanded] = useState(batch.status === 'active');

  const progress = calculateBatchProgress(batch);
  const hasFailedItems = batch.errorFiles > 0;
  const isActive = batch.status === 'active';

  return (
    <div
      className={`rounded-xl upload-item-glass transition-all duration-300 ${getBatchStatusColor(batch.status)}`}
    >
      {/* Batch Header */}
      <div className="p-4">
        <div className="flex items-center justify-between">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center space-x-3 flex-1 text-left group"
          >
            <div className="flex items-center space-x-2">
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-white/60 group-hover:text-white/80" />
              ) : (
                <ChevronRight className="w-4 h-4 text-white/60 group-hover:text-white/80" />
              )}
              <div className="p-2 rounded-lg bg-white/5 border border-white/10">
                {getBatchIcon(batch.name)}
              </div>
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-white/90 truncate">{batch.name}</h3>
                <div className="flex items-center space-x-2 ml-2">
                  {getBatchStatusIcon(batch.status)}
                </div>
              </div>

              <div className="flex items-center justify-between mt-1">
                <p className="text-sm text-white/60">
                  {batch.completedFiles}/{batch.totalFiles} files
                  {batch.errorFiles > 0 && (
                    <span className="text-red-400 ml-2">• {batch.errorFiles} failed</span>
                  )}
                </p>
                <span className="text-xs text-white/50">{formatTimeAgo(batch.createdAt)}</span>
              </div>
            </div>
          </button>

          {/* Batch Actions */}
          <div className="flex items-center space-x-1 ml-2">
            {hasFailedItems && (
              <button
                onClick={onRetryBatch}
                className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                title="Retry failed uploads"
              >
                <RotateCcw className="w-4 h-4 text-white/60 hover:text-white/80" />
              </button>
            )}

            {!isActive && (
              <button
                onClick={onRemove}
                className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                title="Remove batch"
              >
                <Trash2 className="w-4 h-4 text-white/60 hover:text-red-400" />
              </button>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        {isActive && (
          <div className="mt-3">
            <div className="h-2 progress-glass">
              <div
                className="h-full progress-fill transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex justify-between items-center mt-1">
              <span className="text-xs text-white/60">{Math.round(progress)}% complete</span>
              {batch.status === 'active' && (
                <span className="text-xs text-white/60">Processing...</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Batch Items */}
      {isExpanded && (
        <div className="border-t border-white/10">
          <div className="p-4 space-y-2 max-h-64 overflow-y-auto">
            {batch.items.map((item) => (
              <UploadItem key={item.id} item={item} onRetry={() => onRetryItem(item.id)} />
            ))}
          </div>
        </div>
      )}

      {/* Success Animation Overlay */}
      {batch.status === 'completed' && (
        <div className="absolute inset-0 pointer-events-none rounded-xl overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/20 via-transparent to-emerald-500/20 animate-pulse" />
        </div>
      )}
    </div>
  );
};
