/**
 * Utility functions for InboxPage
 */

import { type ActivityEvent } from '../../hooks/useActivityFeed';

/**
 * Calculate the number of files uploaded in the last week
 *
 * @param events - Array of activity events
 * @returns Number of files uploaded in the last 7 days
 */
export const calculateWeekCount = (events: ActivityEvent[]): number => {
  const oneWeekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;

  let totalFiles = 0;

  events.forEach((event) => {
    const eventTime = new Date(event.timestamp).getTime();

    if (eventTime > oneWeekAgo) {
      if (event.type === 'files_uploaded') {
        // Each upload event can have multiple files
        totalFiles += (event.data.file_count as number) ?? 1;
      } else if (event.type === 'folder_watch_file_ingested') {
        // Folder watch events are per-file
        totalFiles += 1;
      }
    }
  });

  return totalFiles;
};

/**
 * Format a timestamp into a human-readable relative time string
 *
 * @param timestamp - ISO timestamp string
 * @returns Formatted string like "5m ago", "2h ago", or date
 */
export const formatTimestamp = (timestamp: string): string => {
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

/**
 * Format an activity event into a human-readable message
 *
 * @param event - Activity event object
 * @returns Formatted message string
 */
export const formatActivityMessage = (event: ActivityEvent): string => {
  const { type, data } = event;
  const fileNameRaw = data.file_name as string | undefined;
  const fileName = fileNameRaw ? (fileNameRaw.split('/').pop() ?? '') : '';

  switch (type) {
    case 'files_uploaded':
      return `Uploaded ${fileName || `${data.file_count} files`}`;

    case 'folder_watch_file_ingested':
      return `Ingested ${fileName} from watched folder`;

    case 'file_upload_failed':
      return `Failed to upload ${fileName}`;

    default:
      // Convert snake_case to readable format
      return type.replace(/_/g, ' ');
  }
};

/**
 * Format file size in bytes to human-readable format
 *
 * @param bytes - File size in bytes
 * @returns Formatted string like "1.5 MB"
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${units[i]}`;
};

/**
 * Format a timestamp into a relative time string
 *
 * @param timestamp - ISO timestamp string or null
 * @returns Formatted string like "5 minutes ago"
 */
export const formatRelativeTime = (timestamp: string | null): string => {
  if (!timestamp) return 'Unknown';

  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return 'just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;

  return date.toLocaleDateString();
};
