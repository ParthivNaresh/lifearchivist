/**
 * StatusBar component - displays document count and storage info
 */

import React from 'react';
import { HardDrive } from 'lucide-react';
import { CurrentStats, VaultInfo } from '../types';
import { formatFileSize } from '../utils';

interface StatusBarProps {
  currentPath: string[];
  currentStats: CurrentStats;
  documentsCount: number;
  vaultInfo: VaultInfo | undefined;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  currentPath,
  currentStats,
  documentsCount,
  vaultInfo
}) => {
  // Determine what to display based on the current level
  const getStatusText = () => {
    if (currentPath.length === 1) {
      // Root level - show themes
      return (
        <>
          <span>{currentStats.folders} themes</span>
          <span>{documentsCount} total documents</span>
        </>
      );
    } else if (currentStats.folders > 0 && currentStats.files === 0) {
      // Folder level - show subfolders and total documents within
      return (
        <>
          <span>{currentStats.folders} {currentStats.folders === 1 ? 'folder' : 'folders'}</span>
          <span>{currentStats.totalDocuments} {currentStats.totalDocuments === 1 ? 'document' : 'documents'}</span>
        </>
      );
    } else if (currentStats.files > 0) {
      // File level - show direct files
      return (
        <>
          <span>{currentStats.files} {currentStats.files === 1 ? 'document' : 'documents'}</span>
        </>
      );
    } else {
      // Empty folder
      return <span>Empty folder</span>;
    }
  };
  
  return (
    <div className="flex items-center justify-between text-sm text-muted-foreground">
      <div className="flex items-center space-x-4">
        {getStatusText()}
        <span>{formatFileSize(currentStats.totalSize)}</span>
      </div>
      {vaultInfo && (
        <div className="flex items-center space-x-2">
          <HardDrive className="h-3 w-3" />
          <span>
            {formatFileSize(vaultInfo.directories?.content?.total_size_bytes || 0)} total storage used
          </span>
        </div>
      )}
    </div>
  );
};