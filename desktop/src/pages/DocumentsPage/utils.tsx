import React from 'react';
import { CheckCircle, Clock, XCircle, AlertCircle } from 'lucide-react';
import { STATUS_STYLES, FILE_TYPE_EMOJIS } from './constants';

/**
 * Format bytes into human-readable file size
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * Format date string into locale string
 */
export const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString();
};

/**
 * Get status icon component based on status
 */
export const getStatusIcon = (status: string): React.ReactNode => {
  switch (status) {
    case 'ready':
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    case 'pending':
      return <Clock className="h-5 w-5 text-yellow-500" />;
    case 'failed':
      return <XCircle className="h-5 w-5 text-red-500" />;
    default:
      return <AlertCircle className="h-5 w-5 text-gray-500" />;
  }
};

/**
 * Get status color classes
 */
export const getStatusColor = (status: string): string => {
  const style = STATUS_STYLES[status as keyof typeof STATUS_STYLES] || STATUS_STYLES.default;
  return style.bgColor;
};

/**
 * Get MIME type emoji icon
 */
export const getMimeTypeIcon = (mimeType: string | null | undefined): string => {
  if (!mimeType) {
    return FILE_TYPE_EMOJIS.default;
  }
  
  if (mimeType.startsWith('image/')) {
    return FILE_TYPE_EMOJIS.image;
  } else if (mimeType.includes('pdf')) {
    return FILE_TYPE_EMOJIS.pdf;
  } else if (mimeType.includes('text')) {
    return FILE_TYPE_EMOJIS.text;
  } else if (mimeType.includes('audio')) {
    return FILE_TYPE_EMOJIS.audio;
  } else if (mimeType.includes('video')) {
    return FILE_TYPE_EMOJIS.video;
  }
  
  return FILE_TYPE_EMOJIS.default;
};

/**
 * Extract filename from path
 */
export const getFileName = (path: string): string => {
  if (!path) return 'Unknown File';
  const parts = path.split('/');
  return parts[parts.length - 1] || 'Unknown File';
};