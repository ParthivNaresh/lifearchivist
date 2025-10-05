/**
 * SearchStates component - loading, error, and empty states
 */

import React from 'react';
import { Search } from 'lucide-react';
import { UI_TEXT } from '../constants';

interface LoadingStateProps {
  query: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ query }) => {
  if (!query) return null;
  
  return (
    <div className="text-center py-12">
      <div className="flex items-center justify-center mb-4">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent"></div>
      </div>
      <p className="text-muted-foreground">{UI_TEXT.SEARCHING}</p>
    </div>
  );
};

interface ErrorStateProps {
  error: string | null;
}

export const ErrorState: React.FC<ErrorStateProps> = ({ error }) => {
  if (!error) return null;
  
  return (
    <div className="text-center py-12">
      <div className="text-red-500 mb-2">⚠️</div>
      <h3 className="text-lg font-medium mb-2 text-red-600">{UI_TEXT.SEARCH_ERROR}</h3>
      <p className="text-muted-foreground">{error}</p>
    </div>
  );
};

interface EmptyStateProps {
  query: string;
  selectedTags: string[];
  hasSearched: boolean;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ query, selectedTags, hasSearched }) => {
  if (!hasSearched) return null;
  
  const getDescription = () => {
    if (query && selectedTags.length > 0) {
      return UI_TEXT.NO_RESULTS_DESCRIPTION.WITH_QUERY_AND_TAGS;
    }
    if (query) {
      return UI_TEXT.NO_RESULTS_DESCRIPTION.WITH_QUERY;
    }
    if (selectedTags.length > 0) {
      return UI_TEXT.NO_RESULTS_DESCRIPTION.WITH_TAGS;
    }
    return '';
  };
  
  return (
    <div className="text-center py-12">
      <Search className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
      <h3 className="text-lg font-medium mb-2">{UI_TEXT.NO_RESULTS}</h3>
      <p className="text-muted-foreground">{getDescription()}</p>
    </div>
  );
};