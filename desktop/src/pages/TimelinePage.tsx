/**
 * Timeline page - Browse documents by creation date
 */

import React, { useCallback, useState, useMemo, useRef, useEffect } from 'react';
import { useCache } from '../hooks/useCache';
import {
  fetchTimelineData,
  TimelineHeader,
  TimelineBar,
  LoadingState,
  ErrorState,
  EmptyState,
  VirtualizedTimeline,
  TimelineLoadingSkeleton,
  SearchLoadingIndicator,
  CACHE_CONFIG,
  formatDateRange,
  sortYears,
  filterTimelineBySearch,
  debounce,
  flattenTimelineData,
  initializeVirtualizationState,
  toggleYearExpansion,
  setAllYearsExpanded,
  VirtualizationState,
} from './TimelinePage/index';

const TimelinePage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const scrollPositionRef = useRef<number>(0);
  const [virtualizationState, setVirtualizationState] = useState<VirtualizationState>({
    expandedYears: new Set(),
  });

  // Fetch timeline data
  const fetchCallback = useCallback(async () => {
    return await fetchTimelineData();
  }, []);

  const { data: timelineData, loading, error, refresh } = useCache(
    'timeline-data',
    fetchCallback,
    CACHE_CONFIG.TIMELINE_TTL
  );

  // Debounced search handler
  const debouncedSetSearch = useMemo(
    () => debounce((query: string) => {
      setDebouncedSearchQuery(query);
    }, 300),
    []
  );

  // Handle search input change
  const handleSearchChange = useCallback((query: string) => {
    setSearchQuery(query);
    debouncedSetSearch(query);
  }, [debouncedSetSearch]);

  // Handle search clear
  const handleSearchClear = useCallback(() => {
    setSearchQuery('');
    setDebouncedSearchQuery('');
    
    // Restore scroll position after clearing
    setTimeout(() => {
      const scrollContainer = document.querySelector('main');
      if (scrollContainer && scrollPositionRef.current) {
        scrollContainer.scrollTop = scrollPositionRef.current;
      }
    }, 0);
  }, []);

  // Save scroll position before filtering
  useEffect(() => {
    const scrollContainer = document.querySelector('main');
    if (scrollContainer && !debouncedSearchQuery) {
      scrollPositionRef.current = scrollContainer.scrollTop;
    }
  }, [debouncedSearchQuery]);

  // Filter timeline data based on search
  const { filteredData, resultCount } = useMemo(() => {
    if (!timelineData) return { filteredData: null, resultCount: 0 };
    return filterTimelineBySearch(timelineData, debouncedSearchQuery);
  }, [timelineData, debouncedSearchQuery]);

  // Use filtered data for display
  const displayData = filteredData || timelineData;
  const isSearching = debouncedSearchQuery.trim().length > 0;
  
  // Show loading indicator while search is debouncing
  const isSearchDebouncing = searchQuery !== debouncedSearchQuery;

  // Initialize virtualization state when data loads
  useEffect(() => {
    if (displayData) {
      setVirtualizationState(initializeVirtualizationState(displayData, true));
    }
  }, [displayData]);

  // Handle toggle all years
  const handleToggleAll = useCallback(() => {
    if (!displayData) return;
    
    const allExpanded = virtualizationState.expandedYears.size === Object.keys(displayData.by_year).length;
    setVirtualizationState(setAllYearsExpanded(displayData, !allExpanded));
  }, [displayData, virtualizationState]);

  // Handle toggle individual year
  const handleToggleYear = useCallback((year: string) => {
    setVirtualizationState(prev => toggleYearExpansion(year, prev));
  }, []);

  // Flatten timeline data for virtualization
  const flattenedItems = useMemo(() => {
    if (!displayData) return [];
    return flattenTimelineData(displayData, virtualizationState);
  }, [displayData, virtualizationState]);

  // Check if all years are expanded for header button
  const allExpanded = displayData 
    ? virtualizationState.expandedYears.size === Object.keys(displayData.by_year).length
    : true;

  // Render loading state
  if (loading) {
    return (
      <div className="p-6">
        <LoadingState />
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="p-6">
        <ErrorState error={error} onRetry={refresh} />
      </div>
    );
  }

  // Render empty state
  if (!timelineData || timelineData.total_documents === 0) {
    return (
      <div className="p-6">
        <EmptyState />
      </div>
    );
  }

  const years = sortYears(Object.keys(displayData.by_year));
  const dateRange = formatDateRange(
    displayData.date_range.earliest,
    displayData.date_range.latest
  );

  const handleJumpToSection = (year: string, month?: string) => {
    // Callback for timeline bar clicks (already handled by scroll)
  };

  // Show empty search state if searching with no results
  const showEmptySearch = isSearching && resultCount === 0;

  return (
    <>
      {/* Timeline visualization bar (desktop only) */}
      <TimelineBar 
        timelineData={displayData} 
        onJumpToSection={handleJumpToSection}
      />

      {/* Main content with left margin for timeline bar on desktop */}
      <div className="min-h-screen p-6 lg:ml-32">
        <div className="max-w-5xl mx-auto">
          <TimelineHeader
            dateRange={dateRange}
            totalDocuments={timelineData.total_documents}
            allExpanded={allExpanded}
            onToggleAll={handleToggleAll}
            searchQuery={searchQuery}
            onSearchChange={handleSearchChange}
            onSearchClear={handleSearchClear}
            searchResultCount={isSearching ? resultCount : undefined}
          />

          {isSearchDebouncing ? (
            <SearchLoadingIndicator />
          ) : showEmptySearch ? (
            <div className="flex flex-col items-center justify-center py-20">
              <div className="text-center">
                <div className="text-6xl mb-4">🔍</div>
                <h3 className="text-xl font-semibold mb-2">No documents found</h3>
                <p className="text-muted-foreground mb-4">
                  Try a different search term
                </p>
                <button
                  onClick={handleSearchClear}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                >
                  Clear Search
                </button>
              </div>
            </div>
          ) : (
            <div className="mt-8 h-[calc(100vh-300px)]">
              <VirtualizedTimeline
                items={flattenedItems}
                onToggleYear={handleToggleYear}
              />
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default TimelinePage;
