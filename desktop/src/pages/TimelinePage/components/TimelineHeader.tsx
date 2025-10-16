/**
 * Timeline page header
 */

import React from 'react';
import { Calendar, ChevronDown, ChevronRight } from 'lucide-react';
import { SearchBar } from './SearchBar';

interface TimelineHeaderProps {
  dateRange: string;
  totalDocuments: number;
  allExpanded: boolean;
  onToggleAll: () => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onSearchClear: () => void;
  searchResultCount?: number;
}

export const TimelineHeader: React.FC<TimelineHeaderProps> = ({ 
  dateRange, 
  totalDocuments,
  allExpanded,
  onToggleAll,
  searchQuery,
  onSearchChange,
  onSearchClear,
  searchResultCount,
}) => {
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-4xl font-bold flex items-center gap-3 mb-2">
            <Calendar className="h-9 w-9 text-primary" />
            Timeline
          </h1>
          <p className="text-base text-muted-foreground">
            {totalDocuments} {totalDocuments === 1 ? 'document' : 'documents'} • {dateRange}
          </p>
        </div>
        
        {/* Collapse/Expand All Button */}
        <button
          onClick={onToggleAll}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-background hover:bg-accent transition-colors text-sm font-medium"
        >
          {allExpanded ? (
            <>
              <ChevronRight className="h-4 w-4" />
              Collapse All
            </>
          ) : (
            <>
              <ChevronDown className="h-4 w-4" />
              Expand All
            </>
          )}
        </button>
      </div>
      
      {/* Search Bar */}
      <div className="mb-4">
        <SearchBar
          value={searchQuery}
          onChange={onSearchChange}
          onClear={onSearchClear}
          resultCount={searchResultCount}
          totalCount={totalDocuments}
        />
      </div>
      
      {/* Subtle divider */}
      <div className="mt-6 h-px bg-gradient-to-r from-border via-border/50 to-transparent" />
    </div>
  );
};
