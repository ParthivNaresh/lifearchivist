/**
 * DashboardHeader - Page header component
 * 
 * Displays page title, subtitle, and action buttons
 */

import React from 'react';
import { CompactUploadButton } from './CompactUploadButton';

interface DashboardHeaderProps {
  title?: string;
  subtitle?: string;
  onUploadFiles: () => void;
  onUploadFolder: () => void;
  onWatchFolder: () => void;
  onManageWatchedFolders?: () => void;
  uploadDisabled?: boolean;
  watchedFolderPath?: string | null;
  watchedFolderPending?: number;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  title = 'Dashboard',
  subtitle = 'Your personal knowledge archive',
  onUploadFiles,
  onUploadFolder,
  onWatchFolder,
  onManageWatchedFolders,
  uploadDisabled = false,
  watchedFolderPath = null,
  watchedFolderPending = 0,
}) => {
  return (
    <div className="mb-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">{title}</h1>
          <p className="text-muted-foreground">{subtitle}</p>
        </div>
        
        {/* Compact Upload Button */}
        <CompactUploadButton
          onUploadFiles={onUploadFiles}
          onUploadFolder={onUploadFolder}
          onWatchFolder={onWatchFolder}
          onManageWatchedFolders={onManageWatchedFolders}
          disabled={uploadDisabled}
          watchedFolderPath={watchedFolderPath}
          watchedFolderPending={watchedFolderPending}
        />
      </div>
    </div>
  );
};
