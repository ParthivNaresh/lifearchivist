/**
 * Constants for DocumentsPage
 */

import { type StatusOption } from './types';

// Cache configuration
export const CACHE_CONFIG = {
  DOCUMENTS_TTL: 2 * 60 * 1000, // 2 minutes
} as const;

// Status options for filter
export const STATUS_OPTIONS: StatusOption[] = [
  { value: 'all', label: 'All' },
  { value: 'ready', label: 'Ready' },
  { value: 'pending', label: 'Pending' },
  { value: 'failed', label: 'Failed' },
];

// Status colors and styles
export const STATUS_STYLES = {
  ready: {
    color: 'text-green-500',
    bgColor: 'bg-green-100 text-green-800',
  },
  pending: {
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-100 text-yellow-800',
  },
  failed: {
    color: 'text-red-500',
    bgColor: 'bg-red-100 text-red-800',
  },
  default: {
    color: 'text-gray-500',
    bgColor: 'bg-gray-100 text-gray-800',
  },
} as const;

// File type emoji mappings
export const FILE_TYPE_EMOJIS = {
  image: '🖼️',
  pdf: '📄',
  text: '📝',
  audio: '🎵',
  video: '🎬',
  default: '📁',
} as const;

// API configuration
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api',
} as const;

// UI text constants
export const UI_TEXT = {
  PAGE_TITLE: 'Documents',
  FILTER_LABEL: 'Filter by status:',
  NO_DOCUMENTS: 'No documents found',
  NO_DOCUMENTS_WITH_STATUS: (status: string) => `No documents with status "${status}"`,
  UPLOAD_PROMPT: 'Upload some files to get started',
  SHOWING_COUNT: (count: number) => `Showing ${count} document${count !== 1 ? 's' : ''}`,
  TAG_SEARCH_TITLE: (tag: string) => `Search documents with tag: ${tag}`,
  MORE_TAGS: (count: number) => `+${count} more`,
} as const;
