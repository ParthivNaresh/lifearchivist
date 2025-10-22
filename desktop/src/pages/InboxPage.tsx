/**
 * Inbox Page - Dashboard view with activity feed and quick actions
 *
 * Shows:
 * - Quick stats (document count, recent uploads)
 * - Recent activity feed
 * - Quick actions (upload, watch folder)
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import UploadProgress from '../components/upload/UploadProgress';
import {
  useFileUpload,
  useVaultInfo,
  useInboxActivityFeed,
  useFolderWatchStatus,
  DashboardHeader,
  QuickStats,
  RecentActivity,
  FolderWatchManager,
  DISPLAY_LIMITS,
} from './InboxPage/index';

const InboxPage: React.FC = () => {
  const navigate = useNavigate();
  const [showWatchManager, setShowWatchManager] = useState(false);

  // Custom hooks handle all data fetching and WebSocket connections
  const { vaultInfo, isLoading: vaultLoading } = useVaultInfo();
  const {
    recentActivity,
    weekCount,
    isLoading: activityLoading,
  } = useInboxActivityFeed(DISPLAY_LIMITS.RECENT_ACTIVITY_COUNT);
  const { watchStatus, refetch: refetchWatchStatus } = useFolderWatchStatus();

  const {
    hasActiveUploads,
    activeBatches,
    showUploadProgress,
    handleSelectFiles,
    handleSelectFolder,
    handleRetry,
    handleClearCompleted,
    handleCancelUploads,
  } = useFileUpload();

  // Navigation handlers
  const handleViewAllActivity = () => {
    navigate('/activity');
  };

  return (
    <div className="p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header with Upload Button */}
        <DashboardHeader
          onUploadFiles={() => void handleSelectFiles()}
          onUploadFolder={() => void handleSelectFolder()}
          onWatchFolder={() => setShowWatchManager(true)}
          onManageWatchedFolders={() => setShowWatchManager(true)}
          uploadDisabled={hasActiveUploads}
          watchedFolderPath={watchStatus?.enabled ? watchStatus.watched_path : null}
          watchedFolderPending={watchStatus?.pending_files ?? 0}
        />

        {/* Quick Stats */}
        <div className="mb-8">
          <QuickStats
            totalDocuments={vaultInfo?.directories?.content?.file_count ?? 0}
            weekCount={weekCount}
            storageBytes={vaultInfo?.total_size_bytes ?? 0}
            isLoading={vaultLoading}
          />
        </div>

        {/* Recent Activity */}
        <div className="mb-8">
          <RecentActivity
            events={recentActivity}
            isLoading={activityLoading}
            onViewAll={handleViewAllActivity}
          />
        </div>

        {/* Upload Progress - Shows when files are being uploaded */}
        {showUploadProgress && (
          <div className="mb-8">
            <UploadProgress
              batches={activeBatches}
              onRetry={handleRetry}
              onClearCompleted={handleClearCompleted}
              onCancel={hasActiveUploads ? handleCancelUploads : undefined}
            />
          </div>
        )}
      </div>

      {/* Folder Watch Manager Modal */}
      <FolderWatchManager
        isOpen={showWatchManager}
        onClose={() => setShowWatchManager(false)}
        onStatusChange={() => void refetchWatchStatus()}
      />
    </div>
  );
};

export default InboxPage;
