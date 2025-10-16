/**
 * Inbox Page - Dashboard view with activity feed and quick actions
 * 
 * Shows:
 * - Quick stats (document count, recent uploads)
 * - Recent activity feed
 * - Theme/topic cards for browsing
 * - Quick actions (upload, watch folder, search)
 */

import React, { useState, useEffect } from 'react';
import { Activity, Upload, FolderOpen, Database, TrendingUp } from 'lucide-react';
import UploadProgress from '../components/upload/UploadProgress';
import { 
  useFileUpload,
  FolderWatcher
} from './InboxPage/index';

interface VaultInfo {
  success: boolean;
  total_files: number;
  total_size_bytes: number;
  total_size_mb: number;
  directories: {
    content: {
      file_count: number;
      total_size_bytes: number;
    };
  };
}

interface ActivityEvent {
  id: string;
  type: string;
  data: Record<string, any>;
  timestamp: string;
}

const InboxPage: React.FC = () => {
  const [vaultInfo, setVaultInfo] = useState<VaultInfo | null>(null);
  const [recentActivity, setRecentActivity] = useState<ActivityEvent[]>([]);
  const [weekCount, setWeekCount] = useState<number>(0);
  const [isLoadingStats, setIsLoadingStats] = useState(true);
  const [isLoadingActivity, setIsLoadingActivity] = useState(true);

  const {
    hasActiveUploads,
    activeBatches,
    showUploadProgress,
    handleFileDrop,
    handleSelectFiles,
    handleSelectFolder,
    handleRetry,
    handleClearCompleted,
    handleCancelUploads,
  } = useFileUpload();

  // Fetch vault info
  const fetchVaultInfo = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/vault/info');
      const data = await response.json();
      if (data.success) {
        setVaultInfo(data);
        setIsLoadingStats(false);
      }
    } catch (error) {
      console.error('Failed to fetch vault info:', error);
      setIsLoadingStats(false);
    }
  };

  // Calculate "This Week" count from activity
  const calculateWeekCount = (events: ActivityEvent[]) => {
    const oneWeekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
    
    // Count actual files uploaded, not events
    let totalFiles = 0;
    events.forEach(e => {
      if (new Date(e.timestamp).getTime() > oneWeekAgo) {
        if (e.type === 'files_uploaded') {
          // Each upload event can have multiple files
          totalFiles += e.data.file_count || 1;
        } else if (e.type === 'folder_watch_file_ingested') {
          // Folder watch events are per-file
          totalFiles += 1;
        }
      }
    });
    
    setWeekCount(totalFiles);
  };

  useEffect(() => {
    fetchVaultInfo();
    const interval = setInterval(fetchVaultInfo, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  // Fetch recent activity
  useEffect(() => {
    const fetchActivity = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/activity/events?limit=200');
        const data = await response.json();
        if (data.success) {
          setRecentActivity(data.events.slice(0, 5));
          calculateWeekCount(data.events);
          setIsLoadingActivity(false);
        }
      } catch (error) {
        console.error('Failed to fetch activity:', error);
        setIsLoadingActivity(false);
      }
    };

    fetchActivity();

    // WebSocket for real-time updates
    const ws = new WebSocket('ws://localhost:8000/ws/activity_feed');
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'activity_event' && message.event) {
          setRecentActivity(prev => {
            const updated = [message.event, ...prev].slice(0, 5);
            return updated;
          });
          
          // Refresh vault info when new uploads happen
          if (message.event.type === 'files_uploaded' || 
              message.event.type === 'folder_watch_file_ingested') {
            fetchVaultInfo();
            // Recalculate week count
            fetchActivity();
          }
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    return () => ws.close();
  }, []);

  // Format timestamp
  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  };

  // Format activity message
  const formatActivityMessage = (event: ActivityEvent): string => {
    const { type, data } = event;
    const fileName = data.file_name ? data.file_name.split('/').pop() : '';

    switch (type) {
      case 'files_uploaded':
        return `Uploaded ${fileName || `${data.file_count} files`}`;
      case 'folder_watch_file_ingested':
        return `Ingested ${fileName} from watched folder`;
      case 'file_upload_failed':
        return `Failed to upload ${fileName}`;
      default:
        return type.replace(/_/g, ' ');
    }
  };

  // Main dashboard view
  return (
    <div className="p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
            <p className="text-muted-foreground">
              Your personal knowledge archive
            </p>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="glass-card rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">Total Documents</span>
              <Database className="h-5 w-5 text-primary" />
            </div>
            <div className="text-3xl font-bold">
              {vaultInfo?.directories?.content?.file_count?.toLocaleString() || '0'}
            </div>
          </div>

          <div className="glass-card rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">This Week</span>
              <TrendingUp className="h-5 w-5 text-emerald-500" />
            </div>
            <div className="text-3xl font-bold">
              {weekCount}
            </div>
          </div>

          <div className="glass-card rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">Storage Used</span>
              <Database className="h-5 w-5 text-blue-500" />
            </div>
            <div className="text-3xl font-bold">
              {vaultInfo ? `${(vaultInfo.total_size_bytes / (1024 * 1024)).toFixed(0)} MB` : '0 MB'}
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="glass-card rounded-xl p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              Recent Activity
            </h2>
            <a
              href="/activity"
              className="text-sm text-primary hover:underline"
            >
              View all
            </a>
          </div>

          {recentActivity.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Activity className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No recent activity</p>
              <p className="text-sm mt-1">Upload documents to get started</p>
            </div>
          ) : (
            <div className="space-y-3">
              {recentActivity.map((event) => (
                <div
                  key={event.id}
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-accent/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-2 w-2 rounded-full bg-primary" />
                    <span className="text-sm">{formatActivityMessage(event)}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {formatTimestamp(event.timestamp)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="glass-card rounded-xl p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Upload Files */}
            <button
              onClick={handleSelectFiles}
              disabled={hasActiveUploads}
              className="flex flex-col items-center gap-3 p-6 rounded-lg border-2 border-dashed border-border hover:border-primary hover:bg-accent/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Upload className="h-8 w-8 text-primary" />
              <div className="text-center">
                <div className="font-medium">Upload Files</div>
                <div className="text-xs text-muted-foreground mt-1">
                  Add documents to your archive
                </div>
              </div>
            </button>

            {/* Select Folder */}
            <button
              onClick={handleSelectFolder}
              disabled={hasActiveUploads}
              className="flex flex-col items-center gap-3 p-6 rounded-lg border-2 border-dashed border-border hover:border-primary hover:bg-accent/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <FolderOpen className="h-8 w-8 text-primary" />
              <div className="text-center">
                <div className="font-medium">Select Folder</div>
                <div className="text-xs text-muted-foreground mt-1">
                  Upload multiple files at once
                </div>
              </div>
            </button>

            {/* Auto-Watch Folder - Integrated */}
            <div className="p-6 rounded-lg border-2 border-dashed border-border">
              <FolderWatcher />
            </div>
          </div>
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
    </div>
  );
};

export default InboxPage;
