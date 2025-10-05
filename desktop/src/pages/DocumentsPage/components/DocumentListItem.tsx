import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Calendar, HardDrive, ExternalLink } from 'lucide-react';
import { Document } from '../types';
import { 
  formatFileSize, 
  formatDate, 
  getStatusIcon, 
  getStatusColor, 
  getMimeTypeIcon,
  getFileName 
} from '../utils';
import { UI_TEXT } from '../constants';

interface DocumentListItemProps {
  document: Document;
  onTagClick: (tag: string) => void;
}

export const DocumentListItem: React.FC<DocumentListItemProps> = ({ 
  document, 
  onTagClick 
}) => {
  const navigate = useNavigate();

  const handleDocumentClick = () => {
    navigate(`/vault/${document.id}/details`);
  };

  const handleTagClick = (e: React.MouseEvent, tag: string) => {
    e.stopPropagation();
    onTagClick(tag);
  };

  return (
    <div 
      className="glass-card p-4 rounded-lg border border-border/30 hover:bg-muted/10 transition-colors cursor-pointer"
      onClick={handleDocumentClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-4 flex-1">
          {/* File Icon */}
          <div className="flex-shrink-0 text-2xl">
            {getMimeTypeIcon(document.mime_type)}
          </div>
          
          {/* File Details */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-2">
              <h3 className="text-sm font-medium truncate">
                {getFileName(document.original_path)}
              </h3>
              {getStatusIcon(document.status)}
            </div>
            
            {/* Key information */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1 text-xs text-muted-foreground">
              <div className="flex items-center space-x-1">
                <HardDrive className="h-3 w-3" />
                <span>{formatFileSize(document.size_bytes)}</span>
              </div>
              
              <div className="flex items-center space-x-1">
                <Calendar className="h-3 w-3" />
                <span>Added {formatDate(document.ingested_at)}</span>
              </div>
              
              {/* Content information */}
              {document.has_content && document.word_count && (
                <div className="flex items-center space-x-1">
                  <FileText className="h-3 w-3" />
                  <span>{document.word_count.toLocaleString()} words</span>
                </div>
              )}
              
              {document.extraction_method && (
                <div className="flex items-center space-x-1">
                  <span className="text-green-600">✓</span>
                  <span>Text extracted ({document.extraction_method})</span>
                </div>
              )}
            </div>
            
            {/* Text preview */}
            {document.text_preview && (
              <div className="mt-3 p-2 bg-muted/30 rounded text-xs">
                <div className="text-muted-foreground font-medium mb-1">Content Preview:</div>
                <div className="text-foreground italic">"{document.text_preview}"</div>
              </div>
            )}
            
            {/* Tags */}
            {document.tags && document.tags.length > 0 && (
              <div className="mt-3">
                <div className="text-xs text-muted-foreground font-medium mb-2">Auto-generated Tags:</div>
                <div className="flex flex-wrap gap-1">
                  {document.tags.slice(0, 8).map((tag, index) => (
                    <button
                      key={index}
                      onClick={(e) => handleTagClick(e, tag)}
                      className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors cursor-pointer"
                      title={UI_TEXT.TAG_SEARCH_TITLE(tag)}
                    >
                      {tag}
                    </button>
                  ))}
                  {document.tags.length > 8 && (
                    <span className="text-xs text-muted-foreground">
                      {UI_TEXT.MORE_TAGS(document.tags.length - 8)}
                    </span>
                  )}
                </div>
              </div>
            )}
            
            {/* Full path if different from filename */}
            {document.original_path && document.original_path !== getFileName(document.original_path) && (
              <div className="mt-2 text-xs text-muted-foreground truncate">
                <span className="font-mono">{document.original_path}</span>
              </div>
            )}
            
            {/* Error message if failed */}
            {document.status === 'failed' && document.error_message && (
              <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                <strong>Error:</strong> {document.error_message}
              </div>
            )}
          </div>
        </div>
        
        {/* Status Badge and Action */}
        <div className="flex-shrink-0 ml-4 flex items-center space-x-2">
          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(document.status)}`}>
            {document.status}
          </span>
          <ExternalLink className="h-4 w-4 text-muted-foreground" />
        </div>
      </div>
    </div>
  );
};