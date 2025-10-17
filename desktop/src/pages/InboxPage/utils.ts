/**
 * Utility functions for InboxPage
 */

import { ActivityEvent } from './types';

/**
 * Calculate the number of files uploaded in the last week
 * 
 * @param events - Array of activity events
 * @returns Number of files uploaded in the last 7 days
 */
export const calculateWeekCount = (events: ActivityEvent[]): number => {
  const oneWeekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  
  let totalFiles = 0;
  
  events.forEach(event => {
    const eventTime = new Date(event.timestamp).getTime();
    
    if (eventTime > oneWeekAgo) {
      if (event.type === 'files_uploaded') {
        // Each upload event can have multiple files
        totalFiles += event.data.file_count || 1;
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
  const fileName = data.file_name ? data.file_name.split('/').pop() : '';

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
