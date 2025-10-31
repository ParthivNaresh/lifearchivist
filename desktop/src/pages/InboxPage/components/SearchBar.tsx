/**
 * SearchBar - Compact search bar with dropdown results and filters
 *
 * Features:
 * - Auto-search as user types (debounced)
 * - Dropdown with search results
 * - Advanced filters (document type, date range, theme)
 * - Click outside to close
 * - Navigate to full search page or document details
 * - Keyboard navigation support
 */

import { useRef, useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  FileText,
  Clock,
  ArrowRight,
  X,
  SlidersHorizontal,
  Calendar,
  FileType as FileTypeIcon,
  Tag,
} from 'lucide-react';
import { useSearch } from '@/hooks/useSearch.ts';
import { formatFileSize, formatRelativeTime } from '../utils';

interface SearchBarProps {
  placeholder?: string;
  maxResults?: number;
}

interface SearchFilters {
  mimeTypes: string[];
  dateRange: 'all' | 'today' | 'week' | 'month' | 'year';
  themes: string[];
}

const DOCUMENT_TYPES = [
  { value: 'application/pdf', label: 'PDF', icon: '📕' },
  {
    value: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    label: 'Word',
    icon: '📘',
  },
  {
    value: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    label: 'Excel',
    icon: '📗',
  },
  { value: 'text/plain', label: 'Text', icon: '📄' },
  { value: 'image/', label: 'Images', icon: '🖼️' },
];

const DATE_RANGES = [
  { value: 'all', label: 'All time' },
  { value: 'today', label: 'Today' },
  { value: 'week', label: 'Last 7 days' },
  { value: 'month', label: 'Last 30 days' },
  { value: 'year', label: 'Last year' },
] as const;

const THEMES = [
  'Financial',
  'Healthcare',
  'Legal',
  'Personal',
  'Education',
  'Business',
  'Real Estate',
  'Insurance',
];

export const SearchBar: React.FC<SearchBarProps> = ({
  placeholder = 'Search documents...',
  maxResults = 5,
}) => {
  const navigate = useNavigate();
  const searchRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const filterButtonRef = useRef<HTMLButtonElement>(null);

  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [showFilters, setShowFilters] = useState(false);

  const { query, results, isLoading, filters, setQuery, setFilters } = useSearch({
    debounceDelay: 300,
    defaultMode: 'hybrid',
    defaultLimit: maxResults,
    autoSearch: true,
    filters: {
      mimeTypes: [],
      dateRange: 'all',
      themes: [],
    },
  });

  // Calculate active filter count
  const activeFilterCount =
    (filters.mimeTypes?.length ?? 0) +
    (filters.themes?.length ?? 0) +
    (filters.dateRange === 'all' ? 0 : 1);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setSelectedIndex(-1);
        setShowFilters(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Derive isOpen state instead of setting it in effect
  const shouldBeOpen = useMemo(() => {
    return query.trim() && (results.length > 0 || isLoading);
  }, [query, results.length, isLoading]);

  // Use derived state for isOpen
  useEffect(() => {
    // Use requestAnimationFrame to defer state update
    const frame = requestAnimationFrame(() => {
      setIsOpen(Boolean(shouldBeOpen));
    });
    return () => cancelAnimationFrame(frame);
  }, [shouldBeOpen]);

  // Reset selected index when results change
  useEffect(() => {
    // Use requestAnimationFrame to defer state update
    const frame = requestAnimationFrame(() => {
      setSelectedIndex(-1);
    });
    return () => cancelAnimationFrame(frame);
  }, [results]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
  };

  const handleInputFocus = () => {
    // Close filters when focusing on search input
    setShowFilters(false);

    if (query.trim() && results.length > 0) {
      setIsOpen(true);
    }
  };

  const handleDocumentClick = (documentId: string) => {
    setIsOpen(false);
    setQuery('');
    navigate(`/vault/${documentId}/details`);
  };

  const handleClearSearch = () => {
    setQuery('');
    setIsOpen(false);
    inputRef.current?.focus();
  };

  const handleViewAllResults = () => {
    setIsOpen(false);
    navigate(`/search?q=${encodeURIComponent(query)}`);
  };

  const toggleFilters = () => {
    setShowFilters(!showFilters);
    // Don't close results dropdown - let them coexist
  };

  const toggleMimeType = (mimeType: string) => {
    const currentMimeTypes = filters.mimeTypes ?? [];
    setFilters({
      ...filters,
      mimeTypes: currentMimeTypes.includes(mimeType)
        ? currentMimeTypes.filter((t: string) => t !== mimeType)
        : [...currentMimeTypes, mimeType],
    });
  };

  const setDateRange = (range: SearchFilters['dateRange']) => {
    setFilters({ ...filters, dateRange: range });
  };

  const toggleTheme = (theme: string) => {
    const currentThemes = filters.themes ?? [];
    setFilters({
      ...filters,
      themes: currentThemes.includes(theme)
        ? currentThemes.filter((t: string) => t !== theme)
        : [...currentThemes, theme],
    });
  };

  const clearAllFilters = () => {
    setFilters({
      mimeTypes: [],
      dateRange: 'all',
      themes: [],
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen || results.length === 0) {
      if (e.key === 'Enter' && query.trim()) {
        handleViewAllResults();
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => (prev < results.length ? prev + 1 : prev));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => (prev > -1 ? prev - 1 : -1));
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex === -1 || selectedIndex === results.length) {
          handleViewAllResults();
        } else if (selectedIndex >= 0 && selectedIndex < results.length) {
          const selectedResult = results[selectedIndex];
          if (selectedResult) {
            handleDocumentClick(selectedResult.document_id);
          }
        }
        break;
      case 'Escape':
        setIsOpen(false);
        setSelectedIndex(-1);
        inputRef.current?.blur();
        break;
    }
  };

  const displayResults = results.slice(0, maxResults);
  const hasMoreResults = results.length > maxResults;

  // Extract dropdown content logic into a separate function for better readability
  const renderDropdownContent = () => {
    if (isLoading && results.length === 0) {
      return <div className="p-4 text-center text-sm text-muted-foreground">Searching...</div>;
    }

    if (results.length === 0) {
      return <div className="p-4 text-center text-sm text-muted-foreground">No results found</div>;
    }

    return (
      <>
        {/* Results List */}
        <div className="divide-y divide-border/50">
          {displayResults.map((result, index) => {
            const matchScore = (result.score ?? 0) * 100;
            const hasValidScore = matchScore > 0;

            // Determine score color based on match quality
            let scoreColor = 'bg-muted text-muted-foreground border-border/50';
            if (matchScore >= 80) {
              scoreColor =
                'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20';
            } else if (matchScore >= 60) {
              scoreColor = 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20';
            }

            return (
              <button
                key={result.document_id}
                onClick={() => handleDocumentClick(result.document_id)}
                className={`w-full px-4 py-3.5 text-left transition-all duration-150 ${
                  selectedIndex === index
                    ? 'bg-accent/70 shadow-sm'
                    : 'hover:bg-accent/50 hover:shadow-sm'
                }`}
              >
                <div className="flex items-start gap-3">
                  <FileText className="h-4 w-4 text-muted-foreground mt-1 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    {/* Title and Score Row */}
                    <div className="flex items-start justify-between gap-3 mb-1.5">
                      <h4 className="font-semibold text-sm text-foreground truncate flex-1">
                        {result.title}
                      </h4>
                      {hasValidScore && (
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border flex-shrink-0 ${scoreColor}`}
                        >
                          {matchScore.toFixed(0)}%
                        </span>
                      )}
                    </div>

                    {/* Snippet */}
                    <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed mb-2">
                      {result.snippet}
                    </p>

                    {/* Metadata Row */}
                    <div className="flex items-center gap-3 text-xs text-muted-foreground/80">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        <span>{formatRelativeTime(result.ingested_at)}</span>
                      </span>
                      {result.size_bytes > 0 && (
                        <span className="flex items-center gap-1">
                          <span>•</span>
                          <span>{formatFileSize(result.size_bytes)}</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* View All Results Button */}
        <div className="border-t border-border">
          <button
            onClick={handleViewAllResults}
            className={`w-full px-4 py-3 text-sm text-primary hover:bg-accent transition-colors flex items-center justify-between ${
              selectedIndex === results.length ? 'bg-accent' : ''
            }`}
          >
            <span>
              View all results
              {hasMoreResults && ` (${results.length} total)`}
            </span>
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </>
    );
  };

  return (
    <div ref={searchRef} className="relative w-full">
      {/* Search Input */}
      <div className="relative flex items-center gap-2">
        <div className="relative flex-1">
          {isLoading ? (
            <div className="absolute left-3 top-1/2 transform -translate-y-1/2">
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary border-t-transparent" />
            </div>
          ) : (
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          )}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={handleInputChange}
            onFocus={handleInputFocus}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="w-full pl-10 pr-10 py-2 text-sm border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-all"
          />
          {query && (
            <button
              onClick={handleClearSearch}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 p-0.5 rounded-full hover:bg-accent transition-colors"
              aria-label="Clear search"
            >
              <X className="h-4 w-4 text-muted-foreground hover:text-foreground" />
            </button>
          )}
        </div>

        {/* Filter Button */}
        <button
          ref={filterButtonRef}
          onClick={toggleFilters}
          className={`relative p-2 border border-input rounded-md hover:bg-accent transition-colors ${
            showFilters || activeFilterCount > 0 ? 'bg-accent' : ''
          }`}
          aria-label="Filters"
        >
          <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
          {activeFilterCount > 0 && (
            <span className="absolute -top-1 -right-1 h-4 w-4 bg-primary text-primary-foreground text-xs rounded-full flex items-center justify-center font-medium">
              {activeFilterCount}
            </span>
          )}
        </button>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-popover border border-border rounded-md shadow-lg z-50 p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold">Filters</h3>
            {activeFilterCount > 0 && (
              <button onClick={clearAllFilters} className="text-xs text-primary hover:underline">
                Clear all
              </button>
            )}
          </div>

          <div className="space-y-4">
            {/* Document Type */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <FileTypeIcon className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Document Type</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {DOCUMENT_TYPES.map((type) => (
                  <button
                    key={type.value}
                    onClick={() => toggleMimeType(type.value)}
                    className={`flex items-center gap-2 px-3 py-2 text-sm rounded-md border transition-colors ${
                      (filters.mimeTypes ?? []).includes(type.value)
                        ? 'bg-primary/10 border-primary text-primary'
                        : 'border-border hover:bg-accent'
                    }`}
                  >
                    <span>{type.icon}</span>
                    <span>{type.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Date Range */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Date Range</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {DATE_RANGES.map((range) => (
                  <button
                    key={range.value}
                    onClick={() => setDateRange(range.value)}
                    className={`px-3 py-2 text-sm rounded-md border transition-colors ${
                      filters.dateRange === range.value
                        ? 'bg-primary/10 border-primary text-primary'
                        : 'border-border hover:bg-accent'
                    }`}
                  >
                    {range.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Theme */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Tag className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Theme</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {THEMES.map((theme) => (
                  <button
                    key={theme}
                    onClick={() => toggleTheme(theme)}
                    className={`px-3 py-2 text-sm rounded-md border transition-colors ${
                      (filters.themes ?? []).includes(theme)
                        ? 'bg-primary/10 border-primary text-primary'
                        : 'border-border hover:bg-accent'
                    }`}
                  >
                    {theme}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Dropdown Results */}
      {isOpen && !showFilters && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-popover border border-border rounded-md shadow-lg z-50 max-h-96 overflow-y-auto">
          {renderDropdownContent()}
        </div>
      )}
    </div>
  );
};
