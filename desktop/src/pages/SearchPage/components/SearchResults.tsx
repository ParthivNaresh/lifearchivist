/**
 * SearchResults component - displays search results
 */

import React from 'react';
import { SearchResult } from '../types';
import { SearchResultItem } from './SearchResultItem';
import { UI_TEXT } from '../constants';

interface SearchResultsProps {
  results: SearchResult[];
  query: string;
  selectedTags: string[];
  queryTime: number | null;
  onToggleTag: (tag: string) => void;
}

export const SearchResults: React.FC<SearchResultsProps> = ({
  results,
  query,
  selectedTags,
  queryTime,
  onToggleTag,
}) => {
  if (results.length === 0) return null;

  const getResultsDescription = () => {
    if (query && selectedTags.length > 0) {
      return UI_TEXT.SHOWING_RESULTS.WITH_QUERY_AND_TAGS(query, selectedTags);
    }
    if (query) {
      return UI_TEXT.SHOWING_RESULTS.WITH_QUERY(query);
    }
    return UI_TEXT.SHOWING_RESULTS.WITH_TAGS(selectedTags);
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">
          {UI_TEXT.RESULTS_FOUND(results.length)}
        </h2>
        <div className="text-sm text-muted-foreground">
          <span>{getResultsDescription()}</span>
          {queryTime && <span className="ml-2">({queryTime}ms)</span>}
        </div>
      </div>
      
      <div className="space-y-4">
        {results.map((result) => (
          <SearchResultItem
            key={result.document_id}
            result={result}
            selectedTags={selectedTags}
            onToggleTag={onToggleTag}
          />
        ))}
      </div>
    </div>
  );
};