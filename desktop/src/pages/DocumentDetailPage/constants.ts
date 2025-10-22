/**
 * Constants and configuration for DocumentDetailPage
 */

// Cache durations
export const CACHE_DURATIONS = {
  ANALYSIS: 5 * 60 * 1000, // 5 minutes
  NEIGHBORS: 5 * 60 * 1000, // 5 minutes
  DOCUMENT_TEXT: 5 * 60 * 1000, // 5 minutes
} as const;

// Tab configuration
export const TAB_CONFIG = {
  OVERVIEW: 'overview',
  RELATED: 'related',
  ACTIVITY: 'activity',
} as const;
