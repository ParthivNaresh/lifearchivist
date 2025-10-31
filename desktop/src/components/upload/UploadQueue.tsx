import {
  X,
  Minimize2,
  Upload,
  Trash2,
  RotateCcw,
  CheckCircle2,
  CheckCircle,
  Clock,
  AlertCircle,
  Copy,
} from 'lucide-react';
import { useState } from 'react';
import { useUploadQueue } from '../../contexts/useUploadQueue';
import { useUploadManager } from '../../hooks/useUploadManager';
import { UploadBatch } from './UploadBatch';

const UploadQueue: React.FC = () => {
  const {
    state,
    toggleVisibility,
    toggleMinimized,
    clearCompleted,
    removeBatch,
    updateItemStatus,
    resetQueue,
  } = useUploadQueue();

  const { uploadFile } = useUploadManager();
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  if (!state.isVisible || state.isMinimized) return null;

  const activeBatches = state.batches.filter((batch) => batch.status === 'active');
  const completedBatches = state.batches.filter((batch) => batch.status === 'completed');
  const duplicateBatches = state.batches.filter((batch) => batch.status === 'duplicate');
  const partialBatches = state.batches.filter((batch) => batch.status === 'partial');
  const errorBatches = state.batches.filter((batch) => batch.status === 'error');

  const totalFiles = state.batches.reduce((acc, batch) => acc + batch.totalFiles, 0);
  const completedFiles = state.batches.reduce((acc, batch) => acc + batch.completedFiles, 0);
  const duplicateFiles = state.batches.reduce(
    (acc, batch) => acc + batch.items.filter((item) => item.status === 'duplicate').length,
    0
  );
  const errorFiles = state.batches.reduce((acc, batch) => acc + batch.errorFiles, 0);

  const handleRetryItem = async (itemId: string) => {
    console.log(`🔄 Retrying item ${itemId}`);

    // Find the item in the batches
    let itemToRetry = null;
    for (const batch of state.batches) {
      const item = batch.items.find((i) => i.id === itemId);
      if (item) {
        itemToRetry = item;
        break;
      }
    }

    if (!itemToRetry) {
      console.error(`❌ Item ${itemId} not found for retry`);
      return;
    }

    console.log(`✅ Found item to retry:`, {
      id: itemId,
      fileName: itemToRetry.file instanceof File ? itemToRetry.file.name : itemToRetry.file.name,
      hasPath: 'path' in itemToRetry.file && itemToRetry.file.path,
      status: itemToRetry.status,
    });

    // Reset the item status to pending
    updateItemStatus(itemId, 'pending');

    // Actually retry the upload using the upload manager
    try {
      console.log(`📤 Calling uploadFile for item ${itemId}`);
      const result = await uploadFile(itemToRetry.file, itemId);
      console.log(`✅ Upload completed for item ${itemId}:`, result);
    } catch (error) {
      console.error(`❌ Failed to retry upload for item ${itemId}:`, error);
      updateItemStatus(itemId, 'error', 'Retry failed');
    }
  };

  const handleRetryBatch = async (batchId: string) => {
    const batch = state.batches.find((b) => b.id === batchId);
    if (!batch) {
      console.error(`Batch ${batchId} not found for retry`);
      return;
    }

    // Find all failed items in the batch
    const failedItems = batch.items.filter((item) => item.status === 'error');

    // Retry items concurrently with same limit as initial uploads (6)
    const concurrencyLimit = 6;
    for (let i = 0; i < failedItems.length; i += concurrencyLimit) {
      const batchItems = failedItems.slice(i, i + concurrencyLimit);
      await Promise.all(batchItems.map((item) => handleRetryItem(item.id)));
    }
  };

  const handleRetryAll = async () => {
    console.log('🔄 Retry All clicked');

    // Find all failed items across all batches
    const failedItems = state.batches.flatMap((batch) =>
      batch.items.filter((item) => item.status === 'error')
    );

    console.log(
      `📊 Found ${failedItems.length} failed items to retry:`,
      failedItems.map((item) => ({
        id: item.id,
        fileName: item.file instanceof File ? item.file.name : item.file.name,
        status: item.status,
      }))
    );

    if (failedItems.length === 0) {
      console.warn('⚠️ No failed items found to retry');
      return;
    }

    // Retry items concurrently with same limit as initial uploads (6)
    // This matches the browser WebSocket connection limit
    const concurrencyLimit = 6;
    for (let i = 0; i < failedItems.length; i += concurrencyLimit) {
      const batchItems = failedItems.slice(i, i + concurrencyLimit);
      console.log(
        `📦 Processing batch ${Math.floor(i / concurrencyLimit) + 1}: ${batchItems.length} items`
      );
      await Promise.all(batchItems.map((item) => handleRetryItem(item.id)));
    }

    console.log('✅ Retry All completed');
  };

  return (
    <div className="fixed bottom-6 right-6 w-96 max-h-[70vh] z-50">
      <div className="upload-queue-glass rounded-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-white/10 bg-gradient-to-r from-slate-900/40 to-slate-800/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500/20 to-blue-500/20 border border-white/10">
                <Upload className="w-5 h-5 text-white/80" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white/90">Upload Queue</h2>
                <p className="text-sm text-white/60">
                  {totalFiles > 0 ? (
                    <>
                      {completedFiles + duplicateFiles}/{totalFiles} files
                      {duplicateFiles > 0 && (
                        <span className="text-amber-400 ml-1">• {duplicateFiles} duplicates</span>
                      )}
                      {errorFiles > 0 && (
                        <span className="text-red-400 ml-1">• {errorFiles} failed</span>
                      )}
                    </>
                  ) : (
                    'No uploads'
                  )}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-1">
              {/* Overall Progress */}
              {state.activeUploads > 0 && (
                <div className="mr-2">
                  <div className="w-8 h-8 relative">
                    <svg className="w-8 h-8 -rotate-90" viewBox="0 0 36 36">
                      <circle
                        cx="18"
                        cy="18"
                        r="14"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        className="text-white/20"
                      />
                      <circle
                        cx="18"
                        cy="18"
                        r="14"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeDasharray={`${(state.totalProgress * 88) / 100}, 88`}
                        className="text-purple-400 transition-all duration-300"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-xs font-medium text-white/80">
                        {Math.round(state.totalProgress)}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              <button
                onClick={toggleMinimized}
                className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                title="Minimize"
              >
                <Minimize2 className="w-4 h-4 text-white/60 hover:text-white/80" />
              </button>

              <button
                onClick={toggleVisibility}
                className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                title="Close"
              >
                <X className="w-4 h-4 text-white/60 hover:text-white/80" />
              </button>
            </div>
          </div>

          {/* Quick Actions */}
          {state.batches.length > 0 && (
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/10">
              <div className="flex items-center space-x-4 text-sm text-white/60">
                {activeBatches.length > 0 && (
                  <div className="flex items-center space-x-1">
                    <Clock className="w-4 h-4" />
                    <span>{activeBatches.length} active</span>
                  </div>
                )}
                {completedBatches.length > 0 && (
                  <div className="flex items-center space-x-1">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>{completedBatches.length} done</span>
                  </div>
                )}
                {duplicateBatches.length > 0 && (
                  <div className="flex items-center space-x-1">
                    <Copy className="w-4 h-4 text-amber-400" />
                    <span>{duplicateBatches.length} all duplicates</span>
                  </div>
                )}
                {partialBatches.length > 0 && (
                  <div className="flex items-center space-x-1">
                    <CheckCircle className="w-4 h-4 text-blue-400" />
                    <span>{partialBatches.length} mixed</span>
                  </div>
                )}
                {duplicateFiles > 0 &&
                  duplicateBatches.length === 0 &&
                  partialBatches.length === 0 && (
                    <div className="flex items-center space-x-1">
                      <Copy className="w-4 h-4 text-amber-400" />
                      <span>{duplicateFiles} duplicates</span>
                    </div>
                  )}
                {errorBatches.length > 0 && (
                  <div className="flex items-center space-x-1">
                    <AlertCircle className="w-4 h-4 text-red-400" />
                    <span>{errorBatches.length} failed</span>
                  </div>
                )}
              </div>

              <div className="flex items-center space-x-1">
                {errorFiles > 0 && (
                  <button
                    onClick={() => void handleRetryAll()}
                    className="px-3 py-1 text-xs bg-amber-500/20 text-amber-300 rounded-lg hover:bg-amber-500/30 transition-colors flex items-center space-x-1"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>Retry All</span>
                  </button>
                )}

                {(completedBatches.length > 0 ||
                  duplicateBatches.length > 0 ||
                  partialBatches.length > 0) && (
                  <button
                    onClick={clearCompleted}
                    className="px-3 py-1 text-xs bg-white/10 text-white/60 rounded-lg hover:bg-white/20 hover:text-white/80 transition-colors flex items-center space-x-1"
                  >
                    <Trash2 className="w-3 h-3" />
                    <span>Clear</span>
                  </button>
                )}

                {state.batches.length > 0 && (
                  <button
                    onClick={() => setShowResetConfirm(true)}
                    className="px-3 py-1 text-xs bg-red-500/20 text-red-300 rounded-lg hover:bg-red-500/30 transition-colors flex items-center space-x-1"
                    title="Reset entire upload queue"
                  >
                    <X className="w-3 h-3" />
                    <span>Reset</span>
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-96">
          {state.batches.length === 0 ? (
            <div className="p-8 text-center">
              <div className="w-16 h-16 mx-auto mb-4 p-4 rounded-2xl bg-gradient-to-br from-purple-500/20 to-blue-500/20 border border-white/10">
                <Upload className="w-8 h-8 text-white/40" />
              </div>
              <h3 className="text-lg font-medium text-white/70 mb-2">No uploads yet</h3>
              <p className="text-sm text-white/50">
                Drag & drop files or use the upload button to get started
              </p>
            </div>
          ) : (
            <div className="p-4 space-y-3">
              {/* Active Batches First */}
              {activeBatches.map((batch) => (
                <UploadBatch
                  key={batch.id}
                  batch={batch}
                  onRemove={() => removeBatch(batch.id)}
                  onRetryBatch={() => void handleRetryBatch(batch.id)}
                  onRetryItem={(itemId) => void handleRetryItem(itemId)}
                />
              ))}

              {/* Then Error Batches */}
              {errorBatches.map((batch) => (
                <UploadBatch
                  key={batch.id}
                  batch={batch}
                  onRemove={() => removeBatch(batch.id)}
                  onRetryBatch={() => void handleRetryBatch(batch.id)}
                  onRetryItem={(itemId) => void handleRetryItem(itemId)}
                />
              ))}

              {/* Finally Completed Batches */}
              {completedBatches.map((batch) => (
                <UploadBatch
                  key={batch.id}
                  batch={batch}
                  onRemove={() => removeBatch(batch.id)}
                  onRetryBatch={() => void handleRetryBatch(batch.id)}
                  onRetryItem={(itemId) => void handleRetryItem(itemId)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Reset Confirmation Modal */}
      {showResetConfirm && (
        <>
          <div
            className="fixed inset-0 bg-black/60 z-[60]"
            onClick={() => setShowResetConfirm(false)}
          />
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-white/10 rounded-lg shadow-xl w-full max-w-md">
              <div className="p-6">
                <h3 className="text-lg font-semibold text-white mb-2">Reset Upload Queue?</h3>
                <p className="text-sm text-white/60 mb-6">
                  This will clear all upload history. This action cannot be undone.
                </p>
                <div className="flex justify-end gap-3">
                  <button
                    onClick={() => setShowResetConfirm(false)}
                    className="px-4 py-2 text-sm font-medium text-white/60 rounded-lg hover:bg-white/10 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => {
                      resetQueue();
                      setShowResetConfirm(false);
                    }}
                    className="px-4 py-2 text-sm font-medium bg-red-500/20 text-red-300 rounded-lg hover:bg-red-500/30 transition-colors"
                  >
                    Reset Queue
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default UploadQueue;
