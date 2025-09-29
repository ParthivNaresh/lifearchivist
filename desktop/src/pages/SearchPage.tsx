import React from 'react';
import {
  useSearchState,
  useTagFilters,
  useUrlParams,
  useFetchTags,
  useSearch,
  SearchHeader,
  SearchForm,
  SearchModeToggle,
  TagFilters,
  SearchResults,
  LoadingState,
  ErrorState,
  EmptyState,
} from './SearchPage/index';

const SearchPage: React.FC = () => {
  // Use custom hooks for state management
  const {
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
  } = useSearchState();

  const {
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
  } = useTagFilters();

  // Initialize from URL parameters
  useUrlParams(setQuery, setSelectedTags);

  // Fetch available tags on mount
  useFetchTags(setAvailableTags, setTagsLoading);

  // Perform search with debouncing
  useSearch(
    query,
    selectedTags,
    searchMode,
    setResults,
    setQueryTime,
    setError,
    setIsLoading
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Search is handled automatically by useSearch hook
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

        <LoadingState query={query} />
        
        <ErrorState error={!isLoading ? error : null} />
        
        <EmptyState
          query={query}
          selectedTags={selectedTags}
          hasSearched={!isLoading && !error && results.length === 0 && hasSearched}
        />
      </div>
    </div>
  );
};

export default SearchPage;