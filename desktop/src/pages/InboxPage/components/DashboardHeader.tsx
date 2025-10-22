/**
 * DashboardHeader - Page header component
 *
 * Displays page title, subtitle, search bar, and action buttons
 */

import { CompactUploadButton } from './CompactUploadButton';
import { SearchBar } from './SearchBar';

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
      {/* Top Row: Title, Search, Upload Button */}
      <div className="flex items-center justify-between gap-6 mb-2">
        <div className="flex-shrink-0">
          <h1 className="text-3xl font-bold">{title}</h1>
        </div>

        {/* Search Bar - Centered with flex-grow */}
        <div className="flex-1 max-w-2xl">
          <SearchBar placeholder="Quick search documents..." maxResults={5} />
        </div>

        {/* Compact Upload Button */}
        <div className="flex-shrink-0">
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

      {/* Subtitle */}
      <p className="text-muted-foreground">{subtitle}</p>
    </div>
  );
};
