import React from 'react';
import UploadProgress from '../components/upload/UploadProgress';
import { 
  useFileUpload,
  useTopicNavigation,
  DropZone,
  SupportedFormats,
  InboxHeader,
  TopicLandscape,
  FolderWatcher
} from './InboxPage/index';

const InboxPage: React.FC = () => {
  const {
    hasActiveUploads,
    activeBatches,
    showUploadProgress,
    handleFileDrop,
    handleSelectFiles,
    handleSelectFolder,
    handleRetry,
    handleClearCompleted,
    handleCancelUploads,
  } = useFileUpload();

  const handleTopicClick = useTopicNavigation();

  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <InboxHeader />
        
        {/* Upload Progress or Drop Zone */}
        {showUploadProgress ? (
          <UploadProgress 
            batches={activeBatches}
            onRetry={handleRetry}
            onClearCompleted={handleClearCompleted}
            onCancel={hasActiveUploads ? handleCancelUploads : undefined}
          />
        ) : (
          <DropZone
            onDrop={handleFileDrop}
            onSelectFiles={handleSelectFiles}
            onSelectFolder={handleSelectFolder}
            disabled={hasActiveUploads}
          />
        )}

        {/* Folder Watcher */}
        <div className="mt-6">
          <FolderWatcher />
        </div>

        {/* Supported Formats Info */}
        <SupportedFormats />

        {/* Knowledge Landscape */}
        <div className="mt-8">
          <TopicLandscape onTopicClick={handleTopicClick} />
        </div>
      </div>
    </div>
  );
};

export default InboxPage;