import React from 'react';
import {
  FileText,
  Download,
  FileType,
  HardDrive,
  Calendar,
  Tag,
  Plus,
  X,
  AlertCircle,
  ExternalLink
} from 'lucide-react';
import { formatFileSize, formatDate, formatDateOnly, getFileTypeName, willFileDownload } from '../utils';
import { DocumentAnalysis } from '../types';

interface OverviewTabProps {
  analysis: DocumentAnalysis | undefined;
  loading: boolean;
  error: string | null;
  tags: string[];
  isAddingTag: boolean;
  setIsAddingTag: (value: boolean) => void;
  newTag: string;
  setNewTag: (value: string) => void;
  handleAddTag: () => void;
  handleRemoveTag: (tag: string) => void;
  handleDownload: () => void;
  handleDelete: () => void;
  handleShare: () => void;
  formatFileSize: (bytes: number) => string;
  formatDate: (date: string) => string;
  getFileTypeName: (mimeType: string) => string;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({ 
  analysis, 
  loading, 
  error, 
  tags,
  isAddingTag,
  setIsAddingTag,
  newTag,
  setNewTag,
  handleAddTag,
  handleRemoveTag,
  handleDownload,
  handleDelete,
  handleShare,
  formatFileSize,
  formatDate,
  getFileTypeName
}) => {
  // Create a stable timestamp that only changes when the file hash changes
  const [pdfTimestamp] = React.useState(() => Date.now());
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="mt-2 text-muted-foreground">Loading document details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
        <p className="text-red-600 mb-4">{error}</p>
      </div>
    );
  }

  const metadata = analysis?.metadata || {};
  const classifications = metadata?.classifications || {};
  const fileHash = metadata?.file_hash;
  const mimeType = metadata?.mime_type || '';
  
  // Files that will definitely download when clicked
  const willDownload = willFileDownload(mimeType);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Document Viewer - Takes 2 columns on large screens */}
      <div className="lg:col-span-2 bg-white/25 dark:bg-gray-900/25 backdrop-blur-xl border border-white/50 dark:border-gray-700/50 shadow-lg rounded-lg overflow-hidden">
        <div className="p-6 border-b border-border/50">
          <h3 className="text-lg font-semibold">Document</h3>
        </div>
        <div className="relative">
          {fileHash ? (
            // Show original file based on type
            <div className="w-full h-[800px] bg-gray-50 dark:bg-gray-900">
              {willDownload ? (
                // For Word/Excel/RTF files that will download
                <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                  <FileText className="h-12 w-12 mb-4 opacity-50" />
                  <p className="text-lg font-medium mb-2">
                    {mimeType.includes('word') ? 'Word Document' : 
                     mimeType.includes('rtf') ? 'RTF Document' :
                     'Spreadsheet'}
                  </p>
                  <p className="text-sm mb-4">This file type cannot be displayed in the browser</p>
                  <a 
                    href={`http://localhost:8000/api/vault/file/${fileHash}`}
                    download
                    className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 flex items-center"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download Original File
                  </a>
                </div>
              ) : mimeType.includes('pdf') ? (
                // Use object tag for PDFs - more reliable than iframe
                // Use stable timestamp to prevent reloading on every render
                <object
                  data={`http://localhost:8000/api/vault/file/${fileHash}?t=${pdfTimestamp}`}
                  type="application/pdf"
                  className="w-full h-full"
                  aria-label="PDF Document"
                >
                  <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                    <FileText className="h-12 w-12 mb-4 opacity-50" />
                    <p className="text-lg font-medium mb-2">PDF Preview Not Available</p>
                    <p className="text-sm mb-4">Your browser may not support inline PDF viewing</p>
                    <a 
                      href={`http://localhost:8000/api/vault/file/${fileHash}?t=${pdfTimestamp}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline flex items-center"
                    >
                      Open PDF in new tab
                      <ExternalLink className="h-3 w-3 ml-1" />
                    </a>
                  </div>
                </object>
              ) : (
                // Use iframe for images and text files
                <iframe
                  src={`http://localhost:8000/api/vault/file/${fileHash}`}
                  className="w-full h-full border-0"
                  title="Original Document"
                />
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <div className="p-4 bg-muted/30 rounded-full mb-4">
                <FileText className="h-12 w-12" />
              </div>
              <p className="text-sm font-medium">No document available</p>
              <p className="text-xs mt-1">File could not be loaded</p>
            </div>
          )}
        </div>
      </div>

      {/* Right column - Information and Tags */}
      <div className="space-y-6">
        {/* Document Information */}
        <div className="bg-white/25 dark:bg-gray-900/25 backdrop-blur-xl border border-white/50 dark:border-gray-700/50 shadow-lg p-6 rounded-lg">
          <h3 className="text-lg font-semibold mb-4">Information</h3>
          <div className="space-y-4">
            <div>
              <div className="flex items-center text-xs text-muted-foreground mb-1">
                <FileType className="h-3 w-3 mr-1.5" />
                Theme
              </div>
              <p className="text-sm font-medium">
                {classifications.theme || 'Not detected'}
                {classifications.confidence && (
                  <span className="text-xs text-muted-foreground ml-1">
                    ({(classifications.confidence * 100).toFixed(0)}%)
                  </span>
                )}
              </p>
              {classifications.confidence_level && (
                <p className="text-xs text-muted-foreground mt-0.5">
                  Confidence: {classifications.confidence_level}
                </p>
              )}
            </div>
            
            {classifications.primary_subtheme && (
              <div>
                <div className="flex items-center text-xs text-muted-foreground mb-1">
                  <FileType className="h-3 w-3 mr-1.5" />
                  Category
                </div>
                <p className="text-sm font-medium">
                  {classifications.primary_subtheme}
                </p>
              </div>
            )}
            
            {classifications.primary_subclassification && (
              <div>
                <div className="flex items-center text-xs text-muted-foreground mb-1">
                  <FileType className="h-3 w-3 mr-1.5" />
                  Document Type
                </div>
                <p className="text-sm font-medium">
                  {classifications.primary_subclassification}
                  {classifications.subclassification_confidence && (
                    <span className="text-xs text-muted-foreground ml-1">
                      ({(classifications.subclassification_confidence * 100).toFixed(0)}%)
                    </span>
                  )}
                </p>
                {classifications.subclassification_method && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Match: {classifications.subclassification_method}
                  </p>
                )}
              </div>
            )}
            
            <div>
              <div className="flex items-center text-xs text-muted-foreground mb-1">
                <FileType className="h-3 w-3 mr-1.5" />
                Format
              </div>
              <p className="text-sm font-medium">{getFileTypeName(metadata.mime_type)}</p>
            </div>
            
            <div>
              <div className="flex items-center text-xs text-muted-foreground mb-1">
                <HardDrive className="h-3 w-3 mr-1.5" />
                Size
              </div>
              <p className="text-sm font-medium">{formatFileSize(metadata.size_bytes || 0)}</p>
            </div>
            
            <div>
              <div className="flex items-center text-xs text-muted-foreground mb-1">
                <Calendar className="h-3 w-3 mr-1.5" />
                Added
              </div>
              <p className="text-sm font-medium">{formatDate(metadata.uploaded_at || metadata.created_at)}</p>
            </div>
            
            <div>
              <div className="flex items-center text-xs text-muted-foreground mb-1">
                <Calendar className="h-3 w-3 mr-1.5" />
                Document Created
              </div>
              <p className="text-sm font-medium">
                {metadata.document_created_at 
                  ? formatDateOnly(metadata.document_created_at)
                  : 'Not detected'}
              </p>
            </div>
          </div>
        </div>

        {/* Tags */}
        <div className="bg-white/25 dark:bg-gray-900/25 backdrop-blur-xl border border-white/50 dark:border-gray-700/50 shadow-lg p-6 rounded-lg">
          <h3 className="text-lg font-semibold mb-4">Tags</h3>
          <div className="flex flex-wrap gap-2">
            {tags.map(tag => (
              <span 
                key={tag} 
                className="inline-flex items-center px-3 py-1 bg-primary/10 text-primary rounded-full text-sm group"
              >
                <Tag className="h-3 w-3 mr-1" />
                {tag}
                <button
                  onClick={() => handleRemoveTag(tag)}
                  className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
            
            {isAddingTag ? (
              <div className="inline-flex items-center">
                <input
                  type="text"
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddTag()}
                  onBlur={handleAddTag}
                  className="px-3 py-1 border border-border rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background text-foreground placeholder:text-muted-foreground"
                  placeholder="Enter tag..."
                  autoFocus
                />
              </div>
            ) : (
              <button
                onClick={() => setIsAddingTag(true)}
                className="inline-flex items-center px-3 py-1 border border-border rounded-full text-sm hover:bg-muted transition-colors"
              >
                <Plus className="h-3 w-3 mr-1" />
                Add Tag
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};