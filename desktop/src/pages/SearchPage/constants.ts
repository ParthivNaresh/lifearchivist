/**
 * Constants for SearchPage
 */

export const API_BASE_URL = 'http://localhost:8000';

export const API_ENDPOINTS = {
  SEARCH: '/api/search',
  TAGS: '/api/tags',
} as const;

export const SEARCH_CONFIG = {
  DEBOUNCE_DELAY: 300,
  DEFAULT_LIMIT: 20,
  MAX_TAGS_DISPLAY: 6,
} as const;

export const SEARCH_MODES: Array<{ value: SearchMode; label: string; description: string }> = [
  {
    value: 'keyword',
    label: 'Keyword',
    description: 'Search using exact text matches and keywords',
  },
  {
    value: 'semantic',
    label: 'Semantic',
    description: 'Search using AI to understand meaning and context',
  },
  {
    value: 'hybrid',
    label: 'Hybrid',
    description: 'Combine keyword and semantic search for best results',
  },
];

export const FILE_SIZE_UNITS = ['B', 'KB', 'MB', 'GB'] as const;

export const MIME_TYPE_ICONS: Record<string, string> = {
  'text/': '📄',
  'application/pdf': '📕',
  'image/': '🖼️',
  'default': '📄',
} as const;

export const UI_TEXT = {
  PAGE_TITLE: 'Search Documents',
  SEARCH_PLACEHOLDER: 'Search your documents...',
  SEARCH_BUTTON: 'Search',
  SEARCHING: 'Searching...',
  FILTER_BY_TAGS: 'Filter by Tags',
  LOADING_TAGS: 'Loading tags...',
  NO_TAGS: 'No tags available yet. Upload and process some documents to see tags.',
  SELECTED_TAGS: 'Selected:',
  CLEAR_ALL: 'Clear all',
  NO_RESULTS: 'No results found',
  NO_RESULTS_DESCRIPTION: {
    WITH_QUERY_AND_TAGS: 'Try adjusting your search terms or tag filters.',
    WITH_QUERY: 'Try adjusting your search terms or check your spelling.',
    WITH_TAGS: 'No documents found with the selected tags.',
  },
  SEARCH_ERROR: 'Search Error',
  RESULTS_FOUND: (count: number) => `${count} result${count !== 1 ? 's' : ''} found`,
  SHOWING_RESULTS: {
    WITH_QUERY_AND_TAGS: (query: string, tags: string[]) => 
      `Showing results for "${query}" with tags: ${tags.join(', ')}`,
    WITH_QUERY: (query: string) => `Showing results for "${query}"`,
    WITH_TAGS: (tags: string[]) => `Showing results with tags: ${tags.join(', ')}`,
  },
  SCORE: 'Score:',
  WORDS: (count: number) => `${count.toLocaleString()} words`,
  ADDED: 'Added',
  MORE_TAGS: (count: number) => `+${count} more`,
  ADD_FILTER: (tag: string) => `Add filter: ${tag}`,
  REMOVE_FILTER: (tag: string) => `Remove filter: ${tag}`,
} as const;

import { SearchMode } from './types';