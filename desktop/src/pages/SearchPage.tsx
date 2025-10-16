import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  SearchHeader,
  SearchForm,
  SearchModeToggle,
  TagFilters,
  SearchResults,
  LoadingState,
  ErrorState,
  EmptyState,
} from './SearchPage/index';
import { searchDocuments, fetchTags } from './SearchPage/api';
import { SearchMode, SearchResult, Tag } from './SearchPage/types';

const SearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  
  // State
  const [query, setQuery] = useState(() => searchParams.get('q') || '');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [queryTime, setQueryTime] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchMode, setSearchMode] = useState<SearchMode>(() => (searchParams.get('mode') as SearchMode) || 'keyword');
  const [selectedTags, setSelectedTags] = useState<string[]>(() => {
    const urlTags = searchParams.get('tags');
    return urlTags ? urlTags.split(',').map(tag => decodeURIComponent(tag.trim())).filter(Boolean) : [];
  });
  const [availableTags, setAvailableTags] = useState<Tag[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [tagsLoading, setTagsLoading] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize from URL only once on mount
  useEffect(() => {
    setIsInitialized(true);
  }, []);

  // Fetch tags on mount
  useEffect(() => {
    const loadTags = async () => {
      setTagsLoading(true);
      try {
        const tags = await fetchTags();
        setAvailableTags(tags);
      } catch (err) {
        console.error('Failed to load tags:', err);
      } finally {
        setTagsLoading(false);
      }
    };
    loadTags();
  }, []);

  // Perform search when query/tags/mode change
  useEffect(() => {
    const performSearch = async () => {
      if (!query.trim() && selectedTags.length === 0) {
        setResults([]);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const startTime = performance.now();
        const response = await searchDocuments({
          q: query,
          mode: searchMode,
          limit: 20,
          tags: selectedTags.length > 0 ? selectedTags.join(',') : undefined,
        });
        const endTime = performance.now();

        setResults(response.results);
        setQueryTime(endTime - startTime);
      } catch (err: any) {
        setError(err.message || 'Search failed');
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    };

    // Debounce search
    const timer = setTimeout(performSearch, 300);
    return () => clearTimeout(timer);
  }, [query, selectedTags, searchMode]);

  // Update URL when search params change (only after initialization)
  useEffect(() => {
    if (!isInitialized) return;
    
    const params: Record<string, string> = {};
    
    if (query) params.q = query;
    if (searchMode !== 'keyword') params.mode = searchMode;
    if (selectedTags.length > 0) params.tags = selectedTags.join(',');
    
    setSearchParams(params, { replace: true });
  }, [query, searchMode, selectedTags, isInitialized, setSearchParams]);

  const toggleTag = useCallback((tag: string) => {
    setSelectedTags(prev =>
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
  }, []);

  const clearTags = useCallback(() => {
    setSelectedTags([]);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
  };

  const hasSearched = !!(query || selectedTags.length > 0);

  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <SearchHeader />
        
        <SearchForm
          query={query}
          isLoading={isLoading}
          showFilters={showFilters}
          selectedTagsCount={selectedTags.length}
          onQueryChange={setQuery}
          onToggleFilters={() => setShowFilters(!showFilters)}
          onSubmit={handleSubmit}
        />

        <SearchModeToggle
          searchMode={searchMode}
          onModeChange={setSearchMode}
        />

        <TagFilters
          showFilters={showFilters}
          tagsLoading={tagsLoading}
          availableTags={availableTags}
          selectedTags={selectedTags}
          onToggleTag={toggleTag}
          onClearTags={clearTags}
        />

        <SearchResults
          results={results}
          query={query}
          selectedTags={selectedTags}
          queryTime={queryTime}
          onToggleTag={toggleTag}
        />

        {isLoading && <LoadingState query={query} />}
        
        {!isLoading && error && <ErrorState error={error} />}
        
        {!isLoading && !error && results.length === 0 && hasSearched && (
          <EmptyState
            query={query}
            selectedTags={selectedTags}
            hasSearched={hasSearched}
          />
        )}
      </div>
    </div>
  );
};

export default SearchPage;