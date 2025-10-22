import {
  Clock,
  Upload,
  Loader2,
  CheckCircle2,
  XCircle,
  FileText,
  Image,
  Film,
  Music,
  Archive,
  RotateCcw,
  Copy,
} from 'lucide-react';
import { type UploadItem as UploadItemType } from '../../types/upload';

interface UploadItemProps {
  item: UploadItemType;
  onRetry?: () => void;
}

const getFileIcon = (fileName: string) => {
  const extension = fileName.split('.').pop()?.toLowerCase() ?? '';

  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(extension)) {
    return <Image className="w-4 h-4" />;
  }
  if (['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm'].includes(extension)) {
    return <Film className="w-4 h-4" />;
  }
  if (['mp3', 'wav', 'flac', 'aac', 'ogg'].includes(extension)) {
    return <Music className="w-4 h-4" />;
  }
  if (['zip', 'rar', '7z', 'tar', 'gz'].includes(extension)) {
    return <Archive className="w-4 h-4" />;
  }

  return <FileText className="w-4 h-4" />;
};

const getStatusIcon = (status: UploadItemType['status'], isDuplicate = false) => {
  switch (status) {
    case 'pending':
      return <Clock className="w-4 h-4 text-amber-400" />;
    case 'uploading':
      return <Upload className="w-4 h-4 text-blue-400 animate-pulse" />;
    case 'processing':
      return <Loader2 className="w-4 h-4 text-purple-400 animate-spin" />;
    case 'completed':
      return isDuplicate ? (
        <span title="File already exists">
          <Copy className="w-4 h-4 text-amber-400" />
        </span>
      ) : (
        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
      );
    case 'duplicate':
      return (
        <span title="Document already exists in archive">
          <Copy className="w-4 h-4 text-amber-400" />
        </span>
      );
    case 'error':
      return <XCircle className="w-4 h-4 text-red-400" />;
    default:
      return <Clock className="w-4 h-4 text-gray-400" />;
  }
};

const getStatusColor = (status: UploadItemType['status']) => {
  switch (status) {
    case 'pending':
      return 'border-amber-500/30 bg-amber-500/5';
    case 'uploading':
      return 'border-blue-500/30 bg-blue-500/5';
    case 'processing':
      return 'border-purple-500/30 bg-purple-500/5';
    case 'completed':
      return 'border-emerald-500/30 bg-emerald-500/5';
    case 'duplicate':
      return 'border-amber-500/30 bg-amber-500/10';
    case 'error':
      return 'border-red-500/30 bg-red-500/5';
    default:
      return 'border-gray-500/30 bg-gray-500/5';
  }
};

const formatFileSize = (bytes?: number): string => {
  if (!bytes) return '';

  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
};

const formatDuration = (startTime: number, endTime?: number): string => {
  const duration = (endTime ?? Date.now()) - startTime;
  const seconds = Math.floor(duration / 1000);

  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${seconds % 60}s`;
};

const getStageDisplayName = (stage?: string): string => {
  if (!stage) return '';

  const stageNames: Record<string, string> = {
    upload: 'UPLOAD',
    extract: 'EXTRACT',
    embed: 'EMBED',
    tag: 'TAGGING',
    index: 'INDEX',
    complete: 'DONE',
  };

  return stageNames[stage] ?? stage.toUpperCase();
};

const getDefaultProgressMessage = (status: UploadItemType['status'], stage?: string): string => {
  if (stage) {
    const messages: Record<string, string> = {
      upload: 'Uploading file...',
      extract: 'Extracting content...',
      embed: 'Generating embeddings...',
      tag: 'AI tagging and categorization...',
      index: 'Building search index...',
      complete: 'Processing complete!',
    };
    return messages[stage] ?? `Processing ${stage}...`;
  }

  switch (status) {
    case 'uploading':
      return 'Uploading...';
    case 'processing':
      return 'Processing...';
    default:
      return '';
  }
};

export const UploadItem: React.FC<UploadItemProps> = ({ item, onRetry }) => {
  const fileName = typeof item.file === 'object' ? item.file.name : 'Unknown file';
  const fileSize =
    typeof item.file === 'object' && 'size' in item.file ? item.file.size : undefined;
  const isDuplicate = item.result?.isDuplicate ?? false;
  const duplicateMessage = item.result?.message;

  return (
    <div
      className={`group relative p-3 rounded-lg upload-item-glass transition-all duration-200 ${getStatusColor(item.status)}`}
    >
      <div className="flex items-center space-x-3">
        {/* File Icon */}
        <div className="flex-shrink-0 p-2 rounded-lg bg-white/5 border border-white/10">
          {getFileIcon(fileName)}
        </div>

        {/* File Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-white/90 truncate">{fileName}</p>
            <div className="flex items-center space-x-2 ml-2">
              {getStatusIcon(item.status, isDuplicate)}
              {item.status === 'error' && onRetry && (
                <button
                  onClick={onRetry}
                  className="p-1 rounded-full hover:bg-white/10 transition-colors"
                  title="Retry upload"
                >
                  <RotateCcw className="w-3 h-3 text-white/60 hover:text-white/80" />
                </button>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between mt-1">
            <div className="flex items-center space-x-2 text-xs text-white/60">
              {fileSize && <span>{formatFileSize(fileSize)}</span>}
              <span>•</span>
              <span>{formatDuration(item.startTime, item.completedTime)}</span>
            </div>

            {(item.status === 'uploading' || item.status === 'processing') && (
              <span className="text-xs text-white/60">{Math.round(item.progress)}%</span>
            )}
          </div>

          {/* Progress Stage and Message */}
          {(item.status === 'uploading' || item.status === 'processing') && (
            <div className="mt-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-white/70 truncate">
                  {item.progressMessage ??
                    getDefaultProgressMessage(item.status, item.progressStage)}
                </span>
                {item.progressStage && (
                  <span className="text-white/50 uppercase tracking-wider text-[10px] ml-2 flex-shrink-0">
                    {getStageDisplayName(item.progressStage)}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Progress Bar */}
          {(item.status === 'uploading' || item.status === 'processing') && (
            <div className="mt-2">
              <div className="h-1 progress-glass">
                <div
                  className="h-full progress-fill transition-all duration-300 ease-out"
                  style={{ width: `${item.progress}%` }}
                />
              </div>
            </div>
          )}

          {/* Error Message */}
          {item.status === 'error' && item.error && (
            <p className="mt-1 text-xs text-red-400 truncate">{item.error}</p>
          )}

          {/* Duplicate Message */}
          {(isDuplicate || item.status === 'duplicate') &&
            (duplicateMessage ?? item.result?.message) && (
              <p className="mt-1 text-xs text-amber-400 break-words">
                {duplicateMessage ?? item.result?.message}
              </p>
            )}
        </div>
      </div>
    </div>
  );
};
