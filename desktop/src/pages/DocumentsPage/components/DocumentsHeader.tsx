/**
 * DocumentsHeader component - displays page title and filter controls
 */

import { type DocumentStatus } from '../types';
import { StatusFilter } from './StatusFilter';
import { UI_TEXT } from '../constants';

interface DocumentsHeaderProps {
  selectedStatus: DocumentStatus;
  onStatusChange: (status: DocumentStatus) => void;
}

export const DocumentsHeader: React.FC<DocumentsHeaderProps> = ({
  selectedStatus,
  onStatusChange,
}) => {
  return (
    <div className="flex items-center justify-between mb-6">
      <h1 className="text-2xl font-bold">{UI_TEXT.PAGE_TITLE}</h1>

      <div className="flex items-center space-x-4">
        <StatusFilter selectedStatus={selectedStatus} onStatusChange={onStatusChange} />
      </div>
    </div>
  );
};
