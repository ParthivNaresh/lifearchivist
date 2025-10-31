import { Upload } from 'lucide-react';
import { useUploadQueue } from '../../contexts/useUploadQueue';

const UploadQueueTrigger: React.FC = () => {
  const { state, toggleVisibility, toggleMinimized } = useUploadQueue();

  // Always show the floating button - let users control the queue
  if (!state.isVisible || state.isMinimized) {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        <button
          onClick={() => {
            if (!state.isVisible) {
              toggleVisibility();
            } else {
              toggleMinimized();
            }
          }}
          className="group relative w-14 h-14 floating-button-glass rounded-full transition-all duration-300"
          title={!state.isVisible ? 'Show upload queue' : 'Expand upload queue'}
        >
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/20 to-blue-500/20 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

          <div className="relative flex items-center justify-center">
            <Upload className="w-5 h-5 text-white/80 group-hover:text-white transition-colors" />

            {(state.activeUploads > 0 || state.batches.length > 0) && (
              <>
                <div className="absolute -top-1 -right-1 w-5 h-5 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center">
                  <span className="text-xs font-medium text-white">
                    {state.activeUploads > 0
                      ? state.activeUploads > 99
                        ? '99+'
                        : state.activeUploads
                      : state.batches.length > 99
                        ? '99+'
                        : state.batches.length}
                  </span>
                </div>

                {state.activeUploads > 0 && (
                  <div className="absolute inset-0 rounded-full border-2 border-purple-500/30">
                    <svg
                      className="w-full h-full -rotate-90"
                      viewBox="0 0 36 36"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <circle
                        cx="18"
                        cy="18"
                        r="16"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeDasharray={`${state.totalProgress * 100}, 100`}
                        className="text-purple-500 transition-all duration-300"
                      />
                    </svg>
                  </div>
                )}
              </>
            )}
          </div>
        </button>
      </div>
    );
  }

  return null;
};

export default UploadQueueTrigger;
