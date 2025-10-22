/**
 * Shared search hook for document search functionality
 *
 * Provides debounced search with loading states and error handling.
 * Can be used across multiple components (SearchPage, InboxPage, etc.)
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { searchDocuments } from '../pages/SearchPage/api';
import { type SearchResult, type SearchMode, type SearchParams } from '../pages/SearchPage/types';
import { SEARCH_CONFIG } from '../pages/SearchPage/constants';

interface SearchFilters {
  mimeTypes?: string[];
  dateRange?: 'all' | 'today' | 'week' | 'month' | 'year';
  themes?: string[];
}

interface UseSearchOptions {
  debounceDelay?: number;
  defaultMode?: SearchMode;
  defaultLimit?: number;
  autoSearch?: boolean; // Whether to search automatically on query change
  filters?: SearchFilters;
}

interface UseSearchReturn {
  query: string;
  results: SearchResult[];
  isLoading: boolean;
  error: string | null;
  queryTime: number | null;
  searchMode: SearchMode;
  filters: SearchFilters;
  setQuery: (query: string) => void;
  setSearchMode: (mode: SearchMode) => void;
  setFilters: (filters: SearchFilters) => void;
  performSearch: () => Promise<void>;
  clearResults: () => void;
}

/**
 * Hook for managing document search with debouncing
 */
export const useSearch = (options: UseSearchOptions = {}): UseSearchReturn => {
  const {
    debounceDelay = SEARCH_CONFIG.DEBOUNCE_DELAY,
    defaultMode = 'keyword',
    defaultLimit = SEARCH_CONFIG.DEFAULT_LIMIT,
    autoSearch = true,
  } = options;

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [queryTime, setQueryTime] = useState<number | null>(null);
  const [searchMode, setSearchMode] = useState<SearchMode>(defaultMode);
  const [filters, setFilters] = useState<SearchFilters>(options.filters ?? {});

  // Track if component is mounted to prevent state updates after unmount
  const isMountedRef = useRef(true);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      // Cancel any pending requests on unmount
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const performSearch = useCallback(async () => {
    const trimmedQuery = query.trim();

    if (!trimmedQuery) {
      setResults([]);
      setQueryTime(null);
      setError(null);
      return;
    }

    // Cancel previous request if still pending
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    setIsLoading(true);
    setError(null);

    try {
      const startTime = performance.now();

      // Build search params with filters
      const searchParams: SearchParams = {
        q: trimmedQuery,
        mode: searchMode,
        limit: defaultLimit,
      };

      // Add mime type filter (backend expects single mime_type, we send first one)
      if (filters.mimeTypes && filters.mimeTypes.length > 0) {
        searchParams.mime_type = filters.mimeTypes[0];
      }

      // Add theme filter as tags (backend uses tags parameter)
      if (filters.themes && filters.themes.length > 0) {
        searchParams.tags = filters.themes.join(',');
      }

      // Date range filtering would need backend support for date parameters
      // For now, we'll filter client-side after getting results

      const response = await searchDocuments(searchParams);
      const endTime = performance.now();

      // Client-side date filtering if date range is set
      let filteredResults = response.results;
      if (filters.dateRange && filters.dateRange !== 'all') {
        const now = new Date();
        const cutoffDate = new Date();

        switch (filters.dateRange) {
          case 'today':
            cutoffDate.setHours(0, 0, 0, 0);
            break;
          case 'week':
            cutoffDate.setDate(now.getDate() - 7);
            break;
          case 'month':
            cutoffDate.setDate(now.getDate() - 30);
            break;
          case 'year':
            cutoffDate.setFullYear(now.getFullYear() - 1);
            break;
        }

        filteredResults = response.results.filter((result) => {
          const resultDate = new Date(result.ingested_at ?? result.created_at ?? '');
          return resultDate >= cutoffDate;
        });
      }

      // Only update state if component is still mounted
      if (isMountedRef.current) {
        setResults(filteredResults);
        setQueryTime(endTime - startTime);
      }
    } catch (err) {
      // Ignore abort errors
      const error = err as Error;
      if (error.name === 'AbortError' || error.message?.includes('abort')) {
        return;
      }

      if (isMountedRef.current) {
        setError(error.message || 'Search failed');
        setResults([]);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
      abortControllerRef.current = null;
    }
  }, [query, searchMode, defaultLimit, filters]);

  const clearResults = useCallback(() => {
    setResults([]);
    setQueryTime(null);
    setError(null);
    setQuery('');
  }, []);

  // Auto-search with debouncing when query, mode, or filters change
  useEffect(() => {
    if (!autoSearch) return;

    const timer = setTimeout(() => {
      void performSearch();
    }, debounceDelay);

    return () => clearTimeout(timer);
  }, [query, searchMode, filters, debounceDelay, autoSearch, performSearch]);

  return {
    query,
    results,
    isLoading,
    error,
    queryTime,
    searchMode,
    filters,
    setQuery,
    setSearchMode,
    setFilters,
    performSearch,
    clearResults,
  };
};
