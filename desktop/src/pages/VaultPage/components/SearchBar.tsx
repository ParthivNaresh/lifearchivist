/**
 * SearchBar component - search input with toggle
 */

import React from 'react';
import { Search, X } from 'lucide-react';

interface SearchBarProps {
  searchTerm: string;
  isSearching: boolean;
  onSearchTermChange: (term: string) => void;
  onSearchingChange: (searching: boolean) => void;
  placeholder?: string;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  searchTerm,
  isSearching,
  onSearchTermChange,
  onSearchingChange,
  placeholder = 'Search in current folder...'
}) => {
  if (isSearching) {
    return (
      <div className="flex items-center space-x-2 bg-background/50 px-3 py-1.5 rounded-md border border-border">
        <Search className="h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => onSearchTermChange(e.target.value)}
          placeholder={placeholder}
          className="bg-transparent outline-none text-sm w-48"
          autoFocus
        />
        <button
          onClick={() => {
            onSearchingChange(false);
            onSearchTermChange('');
          }}
          className="hover:text-foreground"
        >
          <X className="h-3 w-3" />
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => onSearchingChange(true)}
      className="p-2 hover:bg-muted rounded-md transition-colors"
      title="Search"
    >
      <Search className="h-4 w-4" />
    </button>
  );
};