/**
 * Custom hooks for SearchPage
 */

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { SearchResult, Tag, SearchMode, SearchParams } from './types';
import { searchDocuments, fetchTags } from './api';
import { parseTagsFromUrl } from './utils';
import { SEARCH_CONFIG } from './constants';

/**
 * Hook to manage search state
 */
export const useSearchState = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [queryTime, setQueryTime] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchMode, setSearchMode] = useState<SearchMode>('keyword');

  return {
    query,
    setQuery,
    results,
    setResults,
    isLoading,
    setIsLoading,
    queryTime,
    setQueryTime,
    error,
    setError,
    searchMode,
    setSearchMode,
  };
};

/**
 * Hook to manage tag filters
 */
export const useTagFilters = () => {
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [availableTags, setAvailableTags] = useState<Tag[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [tagsLoading, setTagsLoading] = useState(false);

  const toggleTag = useCallback((tag: string) => {
    setSelectedTags(prev => 
      prev.includes(tag) 
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    );
  }, []);

  const clearTags = useCallback(() => {
    setSelectedTags([]);
  }, []);

  return {
    selectedTags,
    setSelectedTags,
    availableTags,
    setAvailableTags,
    showFilters,
    setShowFilters,
    tagsLoading,
    setTagsLoading,
    toggleTag,
    clearTags,
  };
};

/**
 * Hook to manage URL parameters
 */
export const useUrlParams = (
  setQuery: (query: string) => void,
  setSelectedTags: (tags: string[]) => void
) => {
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const urlTags = searchParams.get('tags');
    const urlQuery = searchParams.get('q') || '';
    
    if (urlTags) {
      const tagList = parseTagsFromUrl(urlTags);
      setSelectedTags(tagList);
    }
    
    if (urlQuery) {
      setQuery(urlQuery);
    }
  }, [searchParams, setQuery, setSelectedTags]);
};

/**
 * Hook to fetch tags on mount
 */
export const useFetchTags = (
  setAvailableTags: (tags: Tag[]) => void,
  setTagsLoading: (loading: boolean) => void
) => {
  useEffect(() => {
    const loadTags = async () => {
      try {
        setTagsLoading(true);
        const tags = await fetchTags();
        setAvailableTags(tags);
      } catch (err) {
        console.error('Failed to fetch tags:', err);
      } finally {
        setTagsLoading(false);
      }
    };

    loadTags();
  }, [setAvailableTags, setTagsLoading]);
};

/**
 * Hook to perform search with debouncing
 */
export const useSearch = (
  query: string,
  selectedTags: string[],
  searchMode: SearchMode,
  setResults: (results: SearchResult[]) => void,
  setQueryTime: (time: number | null) => void,
  setError: (error: string | null) => void,
  setIsLoading: (loading: boolean) => void
) => {
  const performSearch = useCallback(async (searchQuery: string, tagFilters: string[] = []) => {
    // Allow search with tags even if query is empty
    if (!searchQuery.trim() && tagFilters.length === 0) {
      setResults([]);
      setQueryTime(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    try {
      const params: SearchParams = {
        mode: searchMode,
        limit: SEARCH_CONFIG.DEFAULT_LIMIT,
      };
      
      // Only add query if it's not empty
      if (searchQuery.trim()) {
        params.q = searchQuery.trim();
      }
      
      if (tagFilters.length > 0) {
        params.tags = tagFilters.join(',');
      }
      
      const response = await searchDocuments(params);
      
      setResults(response.results);
      setQueryTime(response.query_time_ms);
      setError(null);
      
    } catch (err) {
      console.error('Search failed:', err);
      setError('Search failed. Please try again.');
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, [searchMode, setResults, setQueryTime, setError, setIsLoading]);

  useEffect(() => {
    // Start loading immediately when query changes or tags change
    if (query.trim() || selectedTags.length > 0) {
      setIsLoading(true);
      setError(null);
    }

    const timer = setTimeout(() => {
      performSearch(query, selectedTags);
    }, SEARCH_CONFIG.DEBOUNCE_DELAY);

    return () => clearTimeout(timer);
  }, [query, selectedTags, performSearch, setIsLoading, setError]);

  return { performSearch };
};