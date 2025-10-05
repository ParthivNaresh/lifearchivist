import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  ArrowLeft,
  Download,
  Trash2,
  Share2,
  RefreshCw
} from 'lucide-react';
import { DocumentAnalysis } from '../types';
import { formatDate, formatFileSize, getFileIcon } from '../utils';

interface DocumentHeaderProps {
  analysis: DocumentAnalysis | undefined;
  documentId: string | undefined;
  onDownload: () => void;
  onDelete: () => void;
  onShare: () => void;
  onRefresh: () => void;
}

export const DocumentHeader: React.FC<DocumentHeaderProps> = ({
  analysis,
  documentId,
  onDownload,
  onDelete,
  onShare,
  onRefresh
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const metadata = analysis?.metadata || {};
  const fileName = metadata.title || metadata.original_path?.split('/').pop() || 'Unknown Document';

  const handleBack = () => {
    // Check if we came from vault with preserved state
    if (location.state?.from === 'vault' && location.state?.returnPath) {
      // Navigate back to the exact location in vault with preserved state
      navigate(location.state.returnPath, {
        state: location.state.returnState,
        replace: true
      });
    } else {
      // Use browser back as fallback
      navigate(-1);
    }
  };

  return (
    <div className="mb-6">
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-4">
          <button
            onClick={handleBack}
            className="p-2 hover:bg-muted rounded-md transition-colors mt-1"
            title="Go back"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div className="flex items-start space-x-3">
            <div className="p-2 bg-muted rounded-lg">
              {getFileIcon(metadata.mime_type)}
            </div>
            <div>
              <h1 className="text-2xl font-bold">{fileName}</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Uploaded {formatDate(metadata.uploaded_at || metadata.created_at)} • {formatFileSize(metadata.size_bytes || 0)}
              </p>
            </div>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={onDownload}
            className="p-2 hover:bg-muted rounded-md transition-colors"
            title="Download"
          >
            <Download className="h-4 w-4" />
          </button>
          <button
            onClick={onShare}
            className="p-2 hover:bg-muted rounded-md transition-colors"
            title="Share"
          >
            <Share2 className="h-4 w-4" />
          </button>
          <button
            onClick={onDelete}
            className="p-2 hover:bg-muted rounded-md transition-colors text-red-600 hover:text-red-700"
            title="Delete"
          >
            <Trash2 className="h-4 w-4" />
          </button>
          <div className="w-px h-6 bg-border mx-1" />
          <button
            onClick={onRefresh}
            className="p-2 hover:bg-muted rounded-md transition-colors"
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};