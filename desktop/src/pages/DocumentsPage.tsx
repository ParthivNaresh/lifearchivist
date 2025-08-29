import React, { useState, useCallback } from 'react';
import { FileText, Calendar, HardDrive, AlertCircle, CheckCircle, Clock, XCircle, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useCache, clearCacheKey } from '../hooks/useCache';
import { useUploadQueue } from '../contexts/UploadQueueContext';
import axios from 'axios';

interface Document {
  id: string;
  file_hash: string;
  original_path: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
  modified_at: string | null;
  ingested_at: string;
  status: string;
  error_message: string | null;
  word_count: number | null;
  language: string | null;
  extraction_method: string | null;
  text_preview: string | null;
  has_content: boolean;
  tags: string[];
  tag_count: number;
}

interface DocumentsResponse {
  documents: Document[];
  total: number;
  limit: number;
  offset: number;
}

const DocumentsPage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [clearing, setClearing] = useState(false);
  const { clearAllData: clearUploadQueueData } = useUploadQueue();

  const fetchDocuments = useCallback(async () => {
    const params = new URLSearchParams();
    if (selectedStatus && selectedStatus !== 'all') {
      params.append('status', selectedStatus);
    }
    
    const response = await axios.get<DocumentsResponse>(`http://localhost:8000/api/documents?${params}`);
    return response.data.documents;
  }, [selectedStatus]);

  const { data: documents, loading, error, refresh } = useCache(
    `documents-${selectedStatus}`,
    fetchDocuments,
    2 * 60 * 1000 // 2 minute cache
  );

  const clearAllDocuments = async () => {
    if (!confirm('Are you sure you want to clear all documents? This cannot be undone.')) {
      return;
    }

    try {
      setClearing(true);
      
      // Clear backend data (database, vault, LlamaIndex, Redis progress)
      await axios.delete('http://localhost:8000/api/documents');
      
      // Clear frontend upload queue localStorage
      clearUploadQueueData();
      
      // Clear cache and refresh
      clearCacheKey(`documents-${selectedStatus}`);
      clearCacheKey('vault-info');
      await refresh();
      
      console.log('✅ Complete Clear All operation finished successfully');
    } catch (err) {
      console.error('Failed to clear documents:', err);
    } finally {
      setClearing(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'pending':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'ready':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getMimeTypeIcon = (mimeType: string) => {
    if (mimeType.startsWith('image/')) {
      return '🖼️';
    } else if (mimeType.includes('pdf')) {
      return '📄';
    } else if (mimeType.includes('text')) {
      return '📝';
    } else if (mimeType.includes('audio')) {
      return '🎵';
    } else if (mimeType.includes('video')) {
      return '🎬';
    }
    return '📁';
  };

  const handleTagClick = (tag: string) => {
    // Navigate to search page with this tag selected
    navigate(`/search?tags=${encodeURIComponent(tag)}`);
  };

  const handleDocumentClick = (documentId: string) => {
    navigate(`/documents/${documentId}/details`);
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
            <p className="mt-2 text-muted-foreground">Loading documents...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertCircle className="h-8 w-8 text-red-500 mx-auto" />
            <p className="mt-2 text-red-600">{error}</p>
            <button 
              onClick={refresh}
              className="mt-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Documents</h1>
          
          <div className="flex items-center space-x-4">
            {/* Clear All Button */}
            <button
              onClick={clearAllDocuments}
              disabled={clearing || !documents || documents.length === 0}
              className="px-3 py-1 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              {clearing ? 'Clearing...' : 'Clear All'}
            </button>
            
            {/* Status Filter */}
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium">Filter by status:</label>
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="px-3 py-1 border border-input rounded-md bg-background text-foreground"
              >
                <option value="all">All</option>
                <option value="ready">Ready</option>
                <option value="pending">Pending</option>
                <option value="failed">Failed</option>
              </select>
            </div>
          </div>
        </div>

        {/* Document Count */}
        <div className="mb-4">
          <p className="text-sm text-muted-foreground">
            Showing {documents?.length || 0} document{(documents?.length || 0) !== 1 ? 's' : ''}
          </p>
        </div>

        {/* Documents List */}
        {(!documents || documents.length === 0) ? (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium text-muted-foreground">No documents found</h3>
            <p className="text-sm text-muted-foreground mt-2">
              {selectedStatus !== 'all' 
                ? `No documents with status "${selectedStatus}"`
                : 'Upload some files to get started'
              }
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {documents?.map((doc) => (
              <div 
                key={doc.id} 
                className="glass-card p-4 rounded-lg border border-border/30 hover:bg-muted/10 transition-colors cursor-pointer"
                onClick={() => handleDocumentClick(doc.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4 flex-1">
                    {/* File Icon */}
                    <div className="flex-shrink-0 text-2xl">
                      {getMimeTypeIcon(doc.mime_type)}
                    </div>
                    
                    {/* File Details */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        <h3 className="text-sm font-medium truncate">
                          {doc.original_path ? doc.original_path.split('/').pop() : 'Unknown File'}
                        </h3>
                        {getStatusIcon(doc.status)}
                      </div>
                      
                      {/* Key information */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1 text-xs text-muted-foreground">
                        <div className="flex items-center space-x-1">
                          <HardDrive className="h-3 w-3" />
                          <span>{formatFileSize(doc.size_bytes)}</span>
                        </div>
                        
                        <div className="flex items-center space-x-1">
                          <Calendar className="h-3 w-3" />
                          <span>Added {formatDate(doc.ingested_at)}</span>
                        </div>
                        
                        {/* Content information */}
                        {doc.has_content && doc.word_count && (
                          <div className="flex items-center space-x-1">
                            <FileText className="h-3 w-3" />
                            <span>{doc.word_count.toLocaleString()} words</span>
                          </div>
                        )}
                        
                        {doc.extraction_method && (
                          <div className="flex items-center space-x-1">
                            <span className="text-green-600">✓</span>
                            <span>Text extracted ({doc.extraction_method})</span>
                          </div>
                        )}
                      </div>
                      
                      {/* Text preview */}
                      {doc.text_preview && (
                        <div className="mt-3 p-2 bg-muted/30 rounded text-xs">
                          <div className="text-muted-foreground font-medium mb-1">Content Preview:</div>
                          <div className="text-foreground italic">"{doc.text_preview}"</div>
                        </div>
                      )}
                      
                      {/* Tags */}
                      {doc.tags && doc.tags.length > 0 && (
                        <div className="mt-3">
                          <div className="text-xs text-muted-foreground font-medium mb-2">Auto-generated Tags:</div>
                          <div className="flex flex-wrap gap-1">
                            {doc.tags.slice(0, 8).map((tag, index) => (
                              <button
                                key={index}
                                onClick={() => handleTagClick(tag)}
                                className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors cursor-pointer"
                                title={`Search documents with tag: ${tag}`}
                              >
                                {tag}
                              </button>
                            ))}
                            {doc.tags.length > 8 && (
                              <span className="text-xs text-muted-foreground">
                                +{doc.tags.length - 8} more
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                      
                      {/* Full path if different from filename */}
                      {doc.original_path && doc.original_path !== (doc.original_path.split('/').pop() || '') && (
                        <div className="mt-2 text-xs text-muted-foreground truncate">
                          <span className="font-mono">{doc.original_path}</span>
                        </div>
                      )}
                      
                      {/* Error message if failed */}
                      {doc.status === 'failed' && doc.error_message && (
                        <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                          <strong>Error:</strong> {doc.error_message}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Status Badge and Action */}
                  <div className="flex-shrink-0 ml-4 flex items-center space-x-2">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(doc.status)}`}>
                      {doc.status}
                    </span>
                    <ExternalLink className="h-4 w-4 text-muted-foreground" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentsPage;