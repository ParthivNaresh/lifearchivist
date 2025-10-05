import React, { useCallback } from 'react';
import { useCache } from '../hooks/useCache';
import { 
  fetchDocuments,
  useDocumentFilter,
  useTagNavigation,
  LoadingState,
  ErrorState,
  DocumentsHeader,
  DocumentCount,
  DocumentsList,
  CACHE_CONFIG
} from './DocumentsPage/index';

const DocumentsPage: React.FC = () => {
  // Use custom hooks
  const { selectedStatus, setSelectedStatus } = useDocumentFilter();
  const handleTagClick = useTagNavigation();

  // Fetch documents callback
  const fetchDocumentsCallback = useCallback(async () => {
    const response = await fetchDocuments(selectedStatus);
    return response.documents;
  }, [selectedStatus]);

  // Use cache hook
  const { data: documents, loading, error, refresh } = useCache(
    `documents-${selectedStatus}`,
    fetchDocumentsCallback,
    CACHE_CONFIG.DOCUMENTS_TTL
  );

  // Render loading state
  if (loading) {
    return (
      <div className="p-6">
        <LoadingState />
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="p-6">
        <ErrorState error={error} onRetry={refresh} />
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="max-w-6xl mx-auto">
        <DocumentsHeader
          selectedStatus={selectedStatus}
          onStatusChange={setSelectedStatus}
        />

        <DocumentCount count={documents?.length || 0} />

        <DocumentsList
          documents={documents}
          selectedStatus={selectedStatus}
          onTagClick={handleTagClick}
        />
      </div>
    </div>
  );
};

export default DocumentsPage;