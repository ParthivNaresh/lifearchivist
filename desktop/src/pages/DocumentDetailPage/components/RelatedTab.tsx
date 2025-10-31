import { FileSearch, AlertCircle, Tag, ExternalLink } from 'lucide-react';
import { type DocumentNeighborsResponse } from '../types';

interface RelatedTabProps {
  neighbors: DocumentNeighborsResponse | undefined;
  loading: boolean;
  error: string | null;
  onNavigate: (documentId: string) => void;
  getFileIcon: (mimeType: string) => React.ReactNode;
  formatFileSize: (bytes: number) => string;
}

export const RelatedTab: React.FC<RelatedTabProps> = ({
  neighbors,
  loading,
  error,
  onNavigate,
  getFileIcon,
  formatFileSize,
}) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
          <p className="mt-2 text-muted-foreground">Finding related documents...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  if (!neighbors || neighbors.neighbors.length === 0) {
    return (
      <div className="text-center py-12">
        <FileSearch className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
        <p className="text-muted-foreground">No related documents found</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="glass-card p-6 rounded-lg">
        <h3 className="text-lg font-semibold mb-4">Similar Documents</h3>
        <p className="text-sm text-muted-foreground mb-6">
          These documents have similar content based on semantic analysis
        </p>

        <div className="space-y-3">
          {neighbors.neighbors.map((neighbor) => (
            <div
              key={neighbor.document_id}
              className="p-4 border border-border rounded-lg hover:bg-muted/50 transition-colors cursor-pointer"
              onClick={() => onNavigate(neighbor.document_id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3 flex-1">
                  <div className="p-2 bg-muted rounded">
                    {getFileIcon(neighbor.metadata.mime_type ?? 'application/octet-stream')}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <h4 className="font-medium text-sm">
                        {neighbor.metadata.title ?? 'Untitled Document'}
                      </h4>
                      <span className="px-2 py-0.5 bg-primary/10 text-primary rounded-full text-xs">
                        {(neighbor.score * 100).toFixed(0)}% match
                      </span>
                    </div>

                    <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                      {neighbor.text_preview}
                    </p>

                    <div className="flex items-center space-x-4 text-xs text-muted-foreground">
                      <span>{formatFileSize(neighbor.metadata.size_bytes ?? 0)}</span>
                      {neighbor.metadata.document_created_at && (
                        <span>
                          {new Date(neighbor.metadata.document_created_at).toLocaleDateString()}
                        </span>
                      )}
                      {neighbor.metadata.theme && (
                        <span className="px-2 py-0.5 bg-muted rounded text-xs">
                          {neighbor.metadata.theme}
                        </span>
                      )}
                      {neighbor.metadata.tags && neighbor.metadata.tags.length > 0 && (
                        <div className="flex items-center space-x-1">
                          <Tag className="h-3 w-3" />
                          <span>{neighbor.metadata.tags.slice(0, 3).join(', ')}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <button
                  className="ml-4 p-2 hover:bg-muted rounded-md transition-colors"
                  title="Open document"
                >
                  <ExternalLink className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
