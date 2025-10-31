import { useCallback, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AlertCircle, Trash2, X, CheckCircle, Info } from 'lucide-react';
import { useCache } from '../hooks/useCache';
import {
  formatFileSize,
  formatDate,
  getFileIcon,
  getFileTypeName,
  fetchDocumentAnalysis,
  fetchDocumentNeighbors,
  deleteDocument,
  useDocumentTags,
  useDocumentDownload,
  useDocumentShare,
  usePageTransition,
  useSyncTags,
  useNotification,
  CACHE_DURATIONS,
  TAB_CONFIG,
  DocumentHeader,
  TabNavigation,
  OverviewTab,
  RelatedTab,
  ActivityTab,
  type TabType,
} from './DocumentDetailPage/index';

const DocumentDetailPage: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>(TAB_CONFIG.OVERVIEW);
  const [prevDocumentId, setPrevDocumentId] = useState<string | undefined>(documentId);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Reset to Overview tab when document changes
  if (documentId !== prevDocumentId) {
    setPrevDocumentId(documentId);
    if (activeTab !== TAB_CONFIG.OVERVIEW) {
      setActiveTab(TAB_CONFIG.OVERVIEW);
    }
  }

  // Use custom hooks for cleaner state management
  const {
    tags,
    setTags,
    isAddingTag,
    setIsAddingTag,
    newTag,
    setNewTag,
    handleAddTag,
    handleRemoveTag,
  } = useDocumentTags();

  const { isTransitioning, navigateWithTransition } = usePageTransition();
  const { notification, showNotification, clearNotification } = useNotification();

  // API fetch callbacks
  const fetchAnalysis = useCallback(async () => {
    if (!documentId) throw new Error('Document ID required');
    return fetchDocumentAnalysis(documentId);
  }, [documentId]);

  const fetchNeighbors = useCallback(async () => {
    if (!documentId) throw new Error('Document ID required');
    return fetchDocumentNeighbors(documentId);
  }, [documentId]);

  // Use cache hooks with constants
  const {
    data: analysis,
    loading: analysisLoading,
    error: analysisError,
    refresh: refreshAnalysis,
  } = useCache(`document-analysis-${documentId}`, fetchAnalysis, CACHE_DURATIONS.ANALYSIS);

  const {
    data: neighbors,
    loading: neighborsLoading,
    error: neighborsError,
  } = useCache(`document-neighbors-${documentId}`, fetchNeighbors, CACHE_DURATIONS.NEIGHBORS);

  // Sync tags from analysis metadata
  useSyncTags(analysis, setTags);

  // Use custom hooks for document actions with notification callbacks
  const handleDownload = useDocumentDownload(
    analysis,
    (error) => showNotification('error', error),
    (success) => showNotification('success', success)
  );

  const handleShare = useDocumentShare(
    analysis,
    (success) => showNotification('info', success),
    (error) => showNotification('error', error)
  );

  // Handle document deletion
  const handleDelete = useCallback(() => {
    setShowDeleteConfirm(true);
    setDeleteError(null);
  }, []);

  const confirmDelete = useCallback(async () => {
    if (!documentId) return;

    setIsDeleting(true);
    setDeleteError(null);

    try {
      await deleteDocument(documentId);
      console.log('Document deleted successfully:', documentId);
      navigate('/vault', { replace: true });
    } catch (error) {
      console.error('Failed to delete document:', error);
      const errorMessage =
        error instanceof Error ? error.message : 'Failed to delete document. Please try again.';
      setDeleteError(errorMessage);
      setIsDeleting(false);
    }
  }, [documentId, navigate]);

  const cancelDelete = useCallback(() => {
    setShowDeleteConfirm(false);
    setDeleteError(null);
    setIsDeleting(false);
  }, []);

  // Handle navigation to related documents
  const handleNavigateToRelated = useCallback(
    (docId: string) => {
      void navigateWithTransition(`/vault/${docId}/details`);
    },
    [navigateWithTransition]
  );

  if (!documentId) {
    return (
      <div className="p-6">
        <div className="text-center">
          <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
          <p className="text-red-600">Document ID is required</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 relative">
      {/* Notification Toast */}
      {notification && (
        <div className="fixed top-4 right-4 z-50 animate-in slide-in-from-top-2 fade-in duration-300">
          <div
            className={`flex items-start gap-3 p-4 rounded-lg shadow-lg border ${
              notification.type === 'error'
                ? 'bg-destructive/10 border-destructive/20 text-destructive'
                : notification.type === 'success'
                  ? 'bg-green-500/10 border-green-500/20 text-green-600 dark:text-green-400'
                  : 'bg-blue-500/10 border-blue-500/20 text-blue-600 dark:text-blue-400'
            }`}
          >
            {notification.type === 'error' && (
              <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
            )}
            {notification.type === 'success' && (
              <CheckCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
            )}
            {notification.type === 'info' && <Info className="h-5 w-5 flex-shrink-0 mt-0.5" />}
            <div className="flex-1">
              <p className="text-sm font-medium">{notification.message}</p>
            </div>
            <button
              onClick={clearNotification}
              className="p-1 hover:bg-background/20 rounded transition-colors"
              aria-label="Dismiss"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-destructive/10 rounded-full">
                <Trash2 className="h-6 w-6 text-destructive" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold mb-2">Delete Document</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Are you sure you want to delete this document? This action cannot be undone.
                </p>

                {deleteError && (
                  <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded-md">
                    <p className="text-sm text-destructive">{deleteError}</p>
                  </div>
                )}

                <div className="flex gap-3 justify-end">
                  <button
                    onClick={cancelDelete}
                    disabled={isDeleting}
                    className="px-4 py-2 text-sm border border-border rounded-md hover:bg-accent transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => void confirmDelete()}
                    disabled={isDeleting}
                    className="px-4 py-2 text-sm bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90 transition-colors disabled:opacity-50 flex items-center gap-2"
                  >
                    {isDeleting ? (
                      <>
                        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-current" />
                        Deleting...
                      </>
                    ) : (
                      'Delete'
                    )}
                  </button>
                </div>
              </div>
              {!isDeleting && (
                <button
                  onClick={cancelDelete}
                  className="p-1 hover:bg-accent rounded-md transition-colors"
                  aria-label="Close"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Transition Overlay */}
      {isTransitioning && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
            <p className="text-sm text-muted-foreground">Loading document...</p>
          </div>
        </div>
      )}

      <div
        className={`max-w-6xl mx-auto transition-all duration-300 ${isTransitioning ? 'opacity-50 scale-98' : 'opacity-100 scale-100'}`}
      >
        {/* Document Header */}
        <DocumentHeader
          analysis={analysis}
          onDownload={() => void handleDownload()}
          onDelete={() => void handleDelete()}
          onShare={() => void handleShare()}
          onRefresh={() => void refreshAnalysis()}
        />

        {/* Tabs */}
        <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />

        {/* Tab Content */}
        {activeTab === TAB_CONFIG.OVERVIEW && (
          <OverviewTab
            analysis={analysis}
            loading={analysisLoading}
            error={analysisError}
            tags={tags}
            isAddingTag={isAddingTag}
            setIsAddingTag={setIsAddingTag}
            newTag={newTag}
            setNewTag={setNewTag}
            handleAddTag={handleAddTag}
            handleRemoveTag={handleRemoveTag}
            handleDownload={() => void handleDownload()}
            handleDelete={handleDelete}
            handleShare={() => void handleShare()}
            formatFileSize={formatFileSize}
            formatDate={formatDate}
            getFileTypeName={getFileTypeName}
          />
        )}

        {activeTab === TAB_CONFIG.RELATED && (
          <RelatedTab
            neighbors={neighbors}
            loading={neighborsLoading}
            error={neighborsError}
            onNavigate={handleNavigateToRelated}
            getFileIcon={getFileIcon}
            formatFileSize={formatFileSize}
          />
        )}

        {activeTab === TAB_CONFIG.ACTIVITY && (
          <ActivityTab analysis={analysis} loading={analysisLoading} />
        )}
      </div>
    </div>
  );
};

export default DocumentDetailPage;
