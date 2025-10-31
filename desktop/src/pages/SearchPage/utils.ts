/**
 * Utility functions for SearchPage
 */

import { FILE_SIZE_UNITS, MIME_TYPE_ICONS } from './constants';

/**
 * Format bytes into human-readable file size
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + FILE_SIZE_UNITS[i];
};

/**
 * Format date string into locale date
 */
export const formatDate = (dateString: string | null): string => {
  if (!dateString) return 'Unknown';
  return new Date(dateString).toLocaleDateString();
};

/**
 * Get emoji icon for MIME type
 */
export const getMimeTypeIcon = (mimeType: string | null | undefined): string => {
  const defaultIcon = MIME_TYPE_ICONS.default ?? '📄';
  if (!mimeType) return defaultIcon;

  if (mimeType.startsWith('text/')) {
    return MIME_TYPE_ICONS['text/'] ?? defaultIcon;
  }
  if (mimeType === 'application/pdf') {
    return MIME_TYPE_ICONS['application/pdf'] ?? defaultIcon;
  }
  if (mimeType.startsWith('image/')) {
    return MIME_TYPE_ICONS['image/'] ?? defaultIcon;
  }

  return defaultIcon;
};

/**
 * Parse tags from URL parameter string
 */
export const parseTagsFromUrl = (urlTags: string | null): string[] => {
  if (!urlTags) return [];
  return urlTags
    .split(',')
    .map((tag) => decodeURIComponent(tag.trim()))
    .filter((tag) => tag);
};

/**
 * Format score as percentage
 */
export const formatScore = (score: number): string => {
  return `${(score * 100).toFixed(0)}%`;
};

/**
 * Get file type from MIME type
 */
export const getFileType = (mimeType: string | null | undefined): string => {
  if (!mimeType) return 'unknown';
  const parts = mimeType.split('/');
  return parts[1] ?? 'unknown';
};
