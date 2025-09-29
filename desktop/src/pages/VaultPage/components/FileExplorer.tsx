/**
 * FileExplorer component - main container for file display
 */

import React from 'react';
import { FileSystemItem, ViewMode, Document } from '../types';
import { EmptyStates } from './EmptyStates';
import { GridView } from './GridView';
import { ListView } from './ListView';

interface FileExplorerProps {
  documentsLoading: boolean;
  documents: Document[] | undefined;
  filteredItems: FileSystemItem[];
  viewMode: ViewMode;
  searchTerm: string;
  isTransitioning: boolean;
  onItemClick: (item: FileSystemItem, viewMode: ViewMode, searchTerm: string) => void;
}

export const FileExplorer: React.FC<FileExplorerProps> = ({
  documentsLoading,
  documents,
  filteredItems,
  viewMode,
  searchTerm,
  isTransitioning,
  onItemClick
}) => {
  return (
    <div className="flex-1 glass-card rounded-lg overflow-hidden">
      <div className={`h-full overflow-y-auto p-6 transition-all duration-300 ${
        isTransitioning ? 'opacity-50 scale-98' : 'opacity-100 scale-100'
      }`}>
        {documentsLoading ? (
          <EmptyStates type="loading" />
        ) : !documents || documents.length === 0 ? (
          <EmptyStates type="no-documents" />
        ) : filteredItems.length === 0 ? (
          <EmptyStates type="no-matches" />
        ) : viewMode === 'grid' ? (
          <GridView
            items={filteredItems}
            viewMode={viewMode}
            searchTerm={searchTerm}
            onItemClick={onItemClick}
          />
        ) : (
          <ListView
            items={filteredItems}
            viewMode={viewMode}
            searchTerm={searchTerm}
            onItemClick={onItemClick}
          />
        )}
      </div>
    </div>
  );
};