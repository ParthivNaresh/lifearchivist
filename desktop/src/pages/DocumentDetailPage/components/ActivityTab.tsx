import React from 'react';
import { Clock, FileSearch, Tag } from 'lucide-react';
import { DocumentAnalysis } from '../types';

interface ActivityTabProps {
  analysis: DocumentAnalysis | undefined;
  loading: boolean;
}

export const ActivityTab: React.FC<ActivityTabProps> = ({ analysis, loading }) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="mt-2 text-muted-foreground">Loading activity...</p>
        </div>
      </div>
    );
  }

  const metadata = analysis?.metadata || {};
  const provenance = metadata.provenance || [];

  return (
    <div className="space-y-6">
      <div className="glass-card p-6 rounded-lg">
        <h3 className="text-lg font-semibold mb-4">Document Activity</h3>
        
        <div className="space-y-4">
          {/* Upload Event */}
          <div className="flex items-start space-x-3">
            <div className="p-2 bg-green-100 rounded-full">
              <Clock className="h-4 w-4 text-green-600" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">Document Uploaded</p>
              <p className="text-xs text-muted-foreground">
                {(metadata.uploaded_at || metadata.created_at) ? new Date(metadata.uploaded_at || metadata.created_at).toLocaleString() : 'Unknown'}
              </p>
            </div>
          </div>

          {/* Processing Status */}
          {metadata.status && (
            <div className="flex items-start space-x-3">
              <div className="p-2 bg-blue-100 rounded-full">
                <FileSearch className="h-4 w-4 text-blue-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">Document Indexed</p>
                <p className="text-xs text-muted-foreground">
                  Status: {metadata.status}
                </p>
              </div>
            </div>
          )}

          {/* Enrichment Status */}
          {metadata.enrichment_status && (
            <div className="flex items-start space-x-3">
              <div className="p-2 bg-purple-100 rounded-full">
                <Tag className="h-4 w-4 text-purple-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">Enrichment</p>
                <p className="text-xs text-muted-foreground">
                  {metadata.enrichment_status === 'queued' ? 'Processing...' : 
                   metadata.enrichment_status === 'dates_extracted' ? 'Dates extracted' :
                   metadata.enrichment_status}
                </p>
              </div>
            </div>
          )}

          {/* Provenance entries */}
          {provenance.map((entry: any, index: number) => (
            <div key={index} className="flex items-start space-x-3">
              <div className="p-2 bg-gray-100 rounded-full">
                <Clock className="h-4 w-4 text-gray-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium capitalize">{entry.action}</p>
                <p className="text-xs text-muted-foreground">
                  {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : 'Unknown'}
                  {entry.tool && ` • Tool: ${entry.tool}`}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Processing Details */}
      {analysis?.processing_info && (
        <div className="glass-card p-6 rounded-lg">
          <h3 className="text-lg font-semibold mb-4">Processing Details</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Index Status:</span>
              <span className="font-medium">{analysis.status}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Processing Chunks:</span>
              <span className="font-medium">{analysis.processing_info.num_chunks}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Embedding Model:</span>
              <span className="font-medium text-xs">{analysis.processing_info.embedding_model}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};