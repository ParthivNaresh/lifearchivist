import React, { useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';
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
  CACHE_DURATIONS,
  TAB_CONFIG,
  DocumentHeader,
  TabNavigation,
  OverviewTab,
  RelatedTab,
  ActivityTab
} from './DocumentDetailPage/index';

const DocumentDetailPage: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = React.useState(TAB_CONFIG.OVERVIEW);
  
  // Use custom hooks for cleaner state management
  const {
    tags,
    setTags,
    isAddingTag,
    setIsAddingTag,
    newTag,
    setNewTag,
    handleAddTag,
    handleRemoveTag
  } = useDocumentTags();
  
  const { isTransitioning, navigateWithTransition } = usePageTransition();

  // API fetch callbacks
  const fetchAnalysis = useCallback(async () => {
    if (!documentId) throw new Error('Document ID required');
    return fetchDocumentAnalysis(documentId);
  }, [documentId]);

  const fetchNeighbors = useCallback(async () => {
    if (!documentId) throw new Error('Document ID required');
    return fetchDocumentNeighbors(documentId);
  }, [documentId]);

  // Removed: Debug text endpoint doesn't exist
  // const fetchText = useCallback(async () => {
  //   if (!documentId) throw new Error('Document ID required');
  //   return fetchDocumentText(documentId);
  // }, [documentId]);

  // Use cache hooks with constants
  const { data: analysis, loading: analysisLoading, error: analysisError, refresh: refreshAnalysis } = useCache(
    `document-analysis-${documentId}`,
    fetchAnalysis,
    CACHE_DURATIONS.ANALYSIS
  );

  const { data: neighbors, loading: neighborsLoading, error: neighborsError } = useCache(
    `document-neighbors-${documentId}`,
    fetchNeighbors,
    CACHE_DURATIONS.NEIGHBORS
  );

  // Removed: Debug text endpoint doesn't exist
  // const { data: documentText } = useCache(
  //   `document-text-${documentId}`,
  //   fetchText,
  //   CACHE_DURATIONS.DOCUMENT_TEXT
  // );

  // Sync tags from analysis metadata
  useSyncTags(analysis, setTags);

  // Use custom hooks for document actions
  const handleDownload = useDocumentDownload(analysis);
  const handleShare = useDocumentShare(analysis);

  // Handle document deletion
  const handleDelete = useCallback(async () => {
    if (!documentId) return;
    
    if (window.confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
      try {
        await deleteDocument(documentId);
        console.log('Document deleted successfully:', documentId);
        navigate('/vault', { replace: true });
      } catch (error) {
        console.error('Failed to delete document:', error);
        alert('Failed to delete document. Please try again.');
      }
    }
  }, [documentId, navigate]);

  // Handle navigation to related documents
  const handleNavigateToRelated = useCallback((docId: string) => {
    navigateWithTransition(`/vault/${docId}/details`);
  }, [navigateWithTransition]);

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
      {/* Transition Overlay */}
      {isTransitioning && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-sm text-muted-foreground">Loading document...</p>
          </div>
        </div>
      )}
      
      <div className={`max-w-6xl mx-auto transition-all duration-300 ${isTransitioning ? 'opacity-50 scale-98' : 'opacity-100 scale-100'}`}>
        {/* Document Header */}
        <DocumentHeader
          analysis={analysis}
          documentId={documentId}
          onDownload={handleDownload}
          onDelete={handleDelete}
          onShare={handleShare}
          onRefresh={refreshAnalysis}
        />

        {/* Tabs */}
        <TabNavigation
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />

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
            handleDownload={handleDownload}
            handleDelete={handleDelete}
            handleShare={handleShare}
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
          <ActivityTab 
            analysis={analysis}
            loading={analysisLoading}
          />
        )}
      </div>
    </div>
  );
};

export default DocumentDetailPage;