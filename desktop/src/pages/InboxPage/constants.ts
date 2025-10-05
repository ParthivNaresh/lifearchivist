/**
 * Constants for InboxPage
 */

import { AcceptedFileTypes, FileFormat } from './types';

// Accepted file types for dropzone
export const ACCEPTED_FILE_TYPES: AcceptedFileTypes = {
  // Documents
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'application/msword': ['.doc'],
  'text/plain': ['.txt', '.text'],
  'text/markdown': ['.md', '.markdown'],
  'text/rtf': ['.rtf'],
  
  // Spreadsheets
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/vnd.ms-excel': ['.xls'],
  'text/csv': ['.csv'],
  'text/tab-separated-values': ['.tsv'],
  
  // Images
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'image/gif': ['.gif'],
  'image/webp': ['.webp'],
  'image/svg+xml': ['.svg'],
  
  // Audio
  'audio/mpeg': ['.mp3'],
  'audio/wav': ['.wav'],
  'audio/ogg': ['.ogg'],
  'audio/mp4': ['.m4a'],
  
  // Video
  'video/mp4': ['.mp4'],
  'video/quicktime': ['.mov'],
  'video/x-msvideo': ['.avi'],
  'video/webm': ['.webm'],
};

// Supported file formats for display
export const SUPPORTED_FORMATS: FileFormat[] = [
  {
    category: 'Documents',
    categoryIcon: '📄',
    categoryColor: 'text-primary',
    formats: [
      { name: 'PDF', extensions: '.pdf' },
      { name: 'Word', extensions: '.docx, .doc' },
      { name: 'Text', extensions: '.txt, .text' },
      { name: 'Markdown', extensions: '.md' },
      { name: 'Rich Text', extensions: '.rtf' },
    ],
  },
  {
    category: 'Spreadsheets',
    categoryIcon: '📊',
    categoryColor: 'text-green-600 dark:text-green-400',
    formats: [
      { name: 'Excel', extensions: '.xlsx, .xls', isNew: true },
      { name: 'CSV', extensions: '.csv', isNew: true },
      { name: 'TSV', extensions: '.tsv', isNew: true },
    ],
  },
  {
    category: 'Media',
    categoryIcon: '🎨',
    categoryColor: 'text-purple-600 dark:text-purple-400',
    formats: [
      { name: 'Images', extensions: '.jpg, .png, .gif, .webp' },
      { name: 'Audio', extensions: '.mp3, .wav, .ogg, .m4a' },
      { name: 'Video', extensions: '.mp4, .mov, .avi, .webm' },
    ],
  },
];

// UI Text constants
export const UI_TEXT = {
  PAGE_TITLE: 'Document Inbox',
  DROP_ZONE: {
    DRAG_ACTIVE: 'Drop files here...',
    DRAG_ACTIVE_SUBTITLE: 'Release to start uploading',
    DEFAULT: 'Drag & drop files here',
    DEFAULT_SUBTITLE: 'or use the buttons below to select files',
    SUPPORTED_FILES: 'Supports PDF, Word, Excel, CSV, images, and more',
  },
  BUTTONS: {
    CHOOSE_FILES: 'Choose Files',
    SELECT_FOLDER: 'Select Folder',
    VIEW_FORMATS: 'View all supported formats',
    CANCEL_UPLOADS: 'Cancel all active uploads?',
  },
  FORMATS: {
    TITLE: 'Supported File Formats',
    NEW_FEATURE: '✨ New:',
    NEW_FEATURE_DESC: 'Excel and CSV files are now fully supported with intelligent data extraction, including automatic detection of headers, currency formatting, and date parsing.',
  },
} as const;

// Timing constants
export const TIMING = {
  RECENT_BATCH_DURATION: 60000, // Show recent batches for 1 minute
  NAVIGATION_DELAY: 500, // Delay before navigation after clearing
} as const;