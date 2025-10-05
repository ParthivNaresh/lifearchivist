/**
 * SearchForm component - search input and filter button
 */

import React from 'react';
import { Search, Filter } from 'lucide-react';
import { UI_TEXT } from '../constants';

interface SearchFormProps {
  query: string;
  isLoading: boolean;
  showFilters: boolean;
  selectedTagsCount: number;
  onQueryChange: (query: string) => void;
  onToggleFilters: () => void;
  onSubmit: (e: React.FormEvent) => void;
}

export const SearchForm: React.FC<SearchFormProps> = ({
  query,
  isLoading,
  showFilters,
  selectedTagsCount,
  onQueryChange,
  onToggleFilters,
  onSubmit,
}) => {
  return (
    <form onSubmit={onSubmit} className="mb-8">
      <div className="flex space-x-4">
        <div className="flex-1 relative">
          {isLoading ? (
            <div className="absolute left-3 top-1/2 transform -translate-y-1/2">
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary border-t-transparent"></div>
            </div>
          ) : (
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-muted-foreground" />
          )}
          <input
            type="text"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder={UI_TEXT.SEARCH_PLACEHOLDER}
            className="w-full pl-10 pr-4 py-2 border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        
        <button
          type="button"
          onClick={onToggleFilters}
          className={`px-3 py-2 border border-input rounded-md hover:bg-accent transition-colors ${
            showFilters || selectedTagsCount > 0 ? 'bg-accent' : ''
          }`}
        >
          <Filter className="h-5 w-5" />
          {selectedTagsCount > 0 && (
            <span className="ml-1 text-xs bg-primary text-primary-foreground rounded-full px-1.5 py-0.5">
              {selectedTagsCount}
            </span>
          )}
        </button>
        
        <button
          type="submit"
          disabled={isLoading}
          className="px-6 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          {isLoading ? UI_TEXT.SEARCHING : UI_TEXT.SEARCH_BUTTON}
        </button>
      </div>
    </form>
  );
};