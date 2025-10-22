/**
 * DocumentsList component - renders list of documents
 */

import { type Document, type DocumentStatus } from '../types';
import { DocumentListItem } from './DocumentListItem';
import { EmptyState } from './DocumentStates';

interface DocumentsListProps {
  documents: Document[] | undefined;
  selectedStatus: DocumentStatus;
  onTagClick: (tag: string) => void;
}

export const DocumentsList: React.FC<DocumentsListProps> = ({
  documents,
  selectedStatus,
  onTagClick,
}) => {
  if (!documents || documents.length === 0) {
    return <EmptyState selectedStatus={selectedStatus} />;
  }

  return (
    <div className="space-y-4">
      {documents.map((doc) => (
        <DocumentListItem key={doc.id} document={doc} onTagClick={onTagClick} />
      ))}
    </div>
  );
};
