import React, { useMemo } from 'react';
import { 
  FileText, 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  Copy,
  AlertCircle,
  Clock,
  FileSpreadsheet,
  Image,
  FileCode,
  File,
  RotateCcw,
  X
} from 'lucide-react';
import { UploadItem as UploadItemType, UploadBatch } from '../../types/upload';

interface UploadProgressProps {
  batches: UploadBatch[];
  onRetry: (itemId: string) => void;
  onCancel?: () => void;
  onClearCompleted?: () => void;
}

const getFileIcon = (fileName: string): React.ReactNode => {
  const ext = fileName.split('.').pop()?.toLowerCase() || '';
  
  if (['pdf'].includes(ext)) {
    return <FileText className="h-5 w-5 text-red-500" />;
  }
  if (['xlsx', 'xls', 'csv', 'tsv'].includes(ext)) {
    return <FileSpreadsheet className="h-5 w-5 text-green-500" />;
  }
  if (['doc', 'docx'].includes(ext)) {
    return <FileText className="h-5 w-5 text-blue-500" />;
  }
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) {
    return <Image className="h-5 w-5 text-purple-500" />;
  }
  if (['txt', 'md', 'rtf'].includes(ext)) {
    return <FileCode className="h-5 w-5 text-gray-500" />;
  }
  
  return <File className="h-5 w-5 text-gray-400" />;
};

const getStatusIcon = (status: UploadItemType['status']) => {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-5 w-5 text-emerald-500" />;
    case 'duplicate':
      return <Copy className="h-5 w-5 text-amber-500" />;
    case 'error':
      return <XCircle className="h-5 w-5 text-red-500" />;
    case 'uploading':
    case 'processing':
      return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
    case 'pending':
      return <Clock className="h-5 w-5 text-gray-400" />;
    default:
      return null;
  }
};

const getStatusText = (status: UploadItemType['status'], progressStage?: string) => {
  switch (status) {
    case 'completed':
      return 'Complete';
    case 'duplicate':
      return 'Duplicate';
    case 'error':
      return 'Failed';
    case 'uploading':
      return progressStage || 'Uploading...';
    case 'processing':
      return progressStage || 'Processing...';
    case 'pending':
      return 'Waiting...';
    default:
      return '';
  }
};

const UploadProgress: React.FC<UploadProgressProps> = ({ 
  batches, 
  onRetry, 
  onCancel,
  onClearCompleted 
}) => {
  // Calculate overall statistics
  const stats = useMemo(() => {
    const allItems = batches.flatMap(b => b.items);
    const total = allItems.length;
    const completed = allItems.filter(i => i.status === 'completed').length;
    const duplicates = allItems.filter(i => i.status === 'duplicate').length;
    const errors = allItems.filter(i => i.status === 'error').length;
    const processing = allItems.filter(i => 
      i.status === 'uploading' || i.status === 'processing'
    ).length;
    const pending = allItems.filter(i => i.status === 'pending').length;
    
    const overallProgress = total > 0 
      ? ((completed + duplicates) / total) * 100 
      : 0;
    
    return {
      total,
      completed,
      duplicates,
      errors,
      processing,
      pending,
      overallProgress
    };
  }, [batches]);

  // Get all items sorted by status (active first, then errors, then completed)
  const sortedItems = useMemo(() => {
    const allItems = batches.flatMap(b => b.items);
    
    return allItems.sort((a, b) => {
      const statusOrder = {
        'uploading': 0,
        'processing': 1,
        'pending': 2,
        'error': 3,
        'duplicate': 4,
        'completed': 5
      };
      
      return (statusOrder[a.status] || 6) - (statusOrder[b.status] || 6);
    });
  }, [batches]);

  const hasActiveUploads = stats.processing > 0 || stats.pending > 0;
  const hasErrors = stats.errors > 0;
  const allComplete = stats.total > 0 && 
    (stats.completed + stats.duplicates + stats.errors) === stats.total;

  return (
    <div className="w-full">
      {/* Header with overall progress */}
      <div className="glass-card rounded-xl p-6 mb-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            {hasActiveUploads ? (
              <div className="relative">
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <Loader2 className="h-6 w-6 text-primary animate-spin" />
                </div>
                {/* Progress ring */}
                <svg className="absolute inset-0 w-12 h-12 -rotate-90">
                  <circle
                    cx="24"
                    cy="24"
                    r="20"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    className="text-gray-200 dark:text-gray-700"
                  />
                  <circle
                    cx="24"
                    cy="24"
                    r="20"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    strokeDasharray={`${stats.overallProgress * 1.26} 126`}
                    className="text-primary transition-all duration-500"
                  />
                </svg>
              </div>
            ) : allComplete ? (
              <div className="w-12 h-12 rounded-full bg-emerald-500/10 flex items-center justify-center">
                <CheckCircle2 className="h-6 w-6 text-emerald-500" />
              </div>
            ) : (
              <div className="w-12 h-12 rounded-full bg-amber-500/10 flex items-center justify-center">
                <AlertCircle className="h-6 w-6 text-amber-500" />
              </div>
            )}
            
            <div>
              <h3 className="text-lg font-semibold">
                {hasActiveUploads 
                  ? `Processing ${stats.total} ${stats.total === 1 ? 'file' : 'files'}...`
                  : allComplete 
                    ? 'Upload Complete'
                    : 'Upload Paused'
                }
              </h3>
              <p className="text-sm text-muted-foreground">
                {stats.completed > 0 && (
                  <span className="text-emerald-600 dark:text-emerald-400">
                    {stats.completed} complete
                  </span>
                )}
                {stats.duplicates > 0 && (
                  <span className="text-amber-600 dark:text-amber-400 ml-2">
                    • {stats.duplicates} {stats.duplicates === 1 ? 'duplicate' : 'duplicates'}
                  </span>
                )}
                {stats.errors > 0 && (
                  <span className="text-red-600 dark:text-red-400 ml-2">
                    • {stats.errors} failed
                  </span>
                )}
                {stats.pending > 0 && (
                  <span className="text-gray-600 dark:text-gray-400 ml-2">
                    • {stats.pending} waiting
                  </span>
                )}
              </p>
            </div>
          </div>
          
          {/* Action buttons */}
          <div className="flex items-center space-x-2">
            {hasErrors && (
              <button
                onClick={() => sortedItems.filter(i => i.status === 'error').forEach(i => onRetry(i.id))}
                className="px-3 py-1.5 text-sm bg-amber-500/10 text-amber-600 dark:text-amber-400 rounded-lg hover:bg-amber-500/20 transition-colors flex items-center space-x-1"
              >
                <RotateCcw className="h-4 w-4" />
                <span>Retry Failed</span>
              </button>
            )}
            
            {allComplete && onClearCompleted && (
              <button
                onClick={onClearCompleted}
                className="px-3 py-1.5 text-sm bg-gray-500/10 text-gray-600 dark:text-gray-400 rounded-lg hover:bg-gray-500/20 transition-colors"
              >
                Clear
              </button>
            )}
            
            {onCancel && hasActiveUploads && (
              <button
                onClick={onCancel}
                className="p-1.5 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
                title="Cancel uploads"
              >
                <X className="h-5 w-5" />
              </button>
            )}
          </div>
        </div>
        
        {/* Overall progress bar */}
        <div className="w-full">
          <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-primary to-primary/80 transition-all duration-500 ease-out"
              style={{ width: `${stats.overallProgress}%` }}
            />
          </div>
          <div className="flex justify-between items-center mt-2">
            <span className="text-xs text-muted-foreground">
              {Math.round(stats.overallProgress)}% complete
            </span>
            <span className="text-xs text-muted-foreground">
              {stats.completed + stats.duplicates} of {stats.total} files
            </span>
          </div>
        </div>
      </div>

      {/* File list */}
      <div className="glass-card rounded-xl p-4 max-h-96 overflow-y-auto">
        <div className="space-y-2">
          {sortedItems.map((item) => (
            <div 
              key={item.id}
              className={`flex items-center justify-between p-3 rounded-lg transition-all ${
                item.status === 'error' 
                  ? 'bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800' 
                  : item.status === 'duplicate'
                    ? 'bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800'
                    : item.status === 'completed'
                      ? 'bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800'
                      : 'bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700'
              }`}
            >
              <div className="flex items-center space-x-3 flex-1 min-w-0">
                {/* File icon */}
                <div className="flex-shrink-0">
                  {getFileIcon(item.file.name)}
                </div>
                
                {/* File info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {item.file.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {item.file.size ? `${(item.file.size / 1024 / 1024).toFixed(2)} MB` : 'Unknown size'}
                    {item.progressMessage && ` • ${item.progressMessage}`}
                  </p>
                  
                  {/* Progress bar for active uploads */}
                  {(item.status === 'uploading' || item.status === 'processing') && (
                    <div className="mt-1 h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-primary transition-all duration-300"
                        style={{ width: `${item.progress}%` }}
                      />
                    </div>
                  )}
                </div>
              </div>
              
              {/* Status and actions */}
              <div className="flex items-center space-x-3 ml-3">
                <span className="text-xs text-muted-foreground">
                  {getStatusText(item.status, item.progressStage)}
                </span>
                
                {item.status === 'error' ? (
                  <button
                    onClick={() => onRetry(item.id)}
                    className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                    title="Retry upload"
                  >
                    <RotateCcw className="h-4 w-4 text-amber-600" />
                  </button>
                ) : (
                  getStatusIcon(item.status)
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default UploadProgress;