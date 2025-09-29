/**
 * Constants and configuration for DocumentDetailPage
 */

// Cache durations
export const CACHE_DURATIONS = {
  ANALYSIS: 5 * 60 * 1000,    // 5 minutes
  NEIGHBORS: 5 * 60 * 1000,    // 5 minutes
  DOCUMENT_TEXT: 5 * 60 * 1000 // 5 minutes
} as const;

// Animation durations
export const ANIMATION_DURATIONS = {
  PAGE_TRANSITION: 300,
  TRANSITION_CLEANUP: 100
} as const;

// Tab configuration
export const TAB_CONFIG = {
  OVERVIEW: 'overview',
  RELATED: 'related',
  ACTIVITY: 'activity'
} as const;

// Document viewer settings
export const VIEWER_CONFIG = {
  HEIGHT: '800px',
  PDF_VIEWER_HEIGHT: '800px'
} as const;

// API configuration
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  NEIGHBORS_DEFAULT_COUNT: 10
} as const;

// File type messages
export const FILE_TYPE_MESSAGES = {
  WORD: 'Word Document',
  RTF: 'RTF Document',
  SPREADSHEET: 'Spreadsheet',
  PDF_NOT_AVAILABLE: 'PDF Preview Not Available',
  PDF_NO_SUPPORT: 'Your browser may not support inline PDF viewing',
  CANNOT_DISPLAY: 'This file type cannot be displayed in the browser',
  NO_DOCUMENT: 'No document available',
  FILE_NOT_LOADED: 'File could not be loaded'
} as const;