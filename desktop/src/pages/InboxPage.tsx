import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Loader2 } from 'lucide-react';
import { cn } from '../utils/cn';
import { FolderFilesResult } from '../types/electron';
import { useUploadManager } from '../hooks/useUploadManager';
import { useUploadQueue } from '../contexts/UploadQueueContext';
import { TopicLandscape } from '../components/topics/TopicLandscape';
import axios from 'axios';


const InboxPage: React.FC = () => {
  const { uploadFiles, uploadFolder } = useUploadManager();
  const { state: uploadQueueState } = useUploadQueue();

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    // Use the upload queue system
    const batchName = acceptedFiles.length === 1 
      ? acceptedFiles[0].name 
      : `${acceptedFiles.length} Files`;
    
    try {
      await uploadFiles(acceptedFiles, { batchName });
    } catch (error) {
      console.error('Upload failed:', error);
    }
  }, [uploadFiles]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
  });

  const handleSelectFiles = async () => {
    if (window.electronAPI) {
      try {
        const filePaths = await window.electronAPI.selectFiles();
        if (filePaths.length === 0) return;
        
        // Convert file paths to File objects for the upload queue
        // Note: This is a simplified conversion - in a real implementation you'd want to 
        // read the actual file data or handle this differently
        const files = filePaths.map(filePath => {
          const fileName = filePath.split('/').pop() || filePath;
          return { name: fileName, path: filePath } as File;
        });
        
        const batchName = files.length === 1 
          ? files[0].name 
          : `${files.length} Selected Files`;
        
        try {
          await uploadFiles(files, { batchName });
        } catch (error) {
          console.error('Upload failed:', error);
        }
      } catch (error) {
        console.error('Error selecting files:', error);
      }
    }
  };

  const handleSelectFolder = async () => {
    if (window.electronAPI && typeof window.electronAPI.selectFolderFiles === 'function') {
      try {
        const folderResult: FolderFilesResult | null = await window.electronAPI.selectFolderFiles();
        
        if (!folderResult || !folderResult.files || folderResult.files.length === 0) {
          return;
        }
        
        // Convert file paths to File objects for the upload queue
        const files = folderResult.files.map(filePath => {
          const fileName = filePath.split('/').pop() || filePath;
          return { name: fileName, path: filePath } as File;
        });
        
        const folderName = folderResult.folderPath.split('/').pop() || 'Selected Folder';
        
        try {
          await uploadFolder(files, folderName);
        } catch (error) {
          console.error('Folder upload failed:', error);
        }
      } catch (error) {
        console.error('Error selecting folder:', error);
      }
    }
  };


  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Document Inbox</h1>
        
        {/* Drop Zone */}
        <div
          {...getRootProps()}
          className={cn(
            'glass-dropzone rounded-xl p-12 text-center cursor-pointer',
            isDragActive && 'border-primary/60 bg-primary/10'
          )}
        >
          <input {...getInputProps()} />
          
          <div className="flex flex-col items-center space-y-4">
            {uploadQueueState.activeUploads > 0 ? (
              <Loader2 className="h-12 w-12 text-primary animate-spin" />
            ) : (
              <Upload className="h-12 w-12 text-muted-foreground" />
            )}
            
            {uploadQueueState.activeUploads > 0 ? (
              <div className="text-center">
                <p className="text-lg">Processing {uploadQueueState.activeUploads} files...</p>
                <p className="text-sm text-muted-foreground">
                  {Math.round(uploadQueueState.totalProgress)}% complete
                </p>
              </div>
            ) : isDragActive ? (
              <p className="text-lg">Drop files here...</p>
            ) : (
              <>
                <p className="text-lg">Drag & drop files here, or click to select</p>
                <p className="text-sm text-muted-foreground">
                  Supports PDF, Word docs, images, audio, video, and more
                </p>
              </>
            )}
            
            <div className="flex space-x-3">
              <button
                onClick={handleSelectFiles}
                disabled={uploadQueueState.activeUploads > 0}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {uploadQueueState.activeUploads > 0 ? 'Processing...' : 'Choose Files'}
              </button>
              
              <button
                onClick={handleSelectFolder}
                disabled={uploadQueueState.activeUploads > 0}
                className="px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {uploadQueueState.activeUploads > 0 ? 'Processing...' : 'Select Folder'}
              </button>
            </div>
          </div>
        </div>


        {/* Knowledge Landscape */}
        <div className="mt-8">
          <TopicLandscape 
            onTopicClick={(topic) => {
              // Navigate to documents page with topic filter
              window.location.href = `/documents?tag=${encodeURIComponent(topic.name)}`;
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default InboxPage;