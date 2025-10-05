/**
 * SearchModeToggle component - toggle between search modes
 */

import React from 'react';
import { SearchMode } from '../types';
import { SEARCH_MODES } from '../constants';

interface SearchModeToggleProps {
  searchMode: SearchMode;
  onModeChange: (mode: SearchMode) => void;
}

export const SearchModeToggle: React.FC<SearchModeToggleProps> = ({
  searchMode,
  onModeChange,
}) => {
  const currentMode = SEARCH_MODES.find(mode => mode.value === searchMode);

  return (
    <div className="mb-6">
      <div className="flex items-center space-x-1 bg-muted rounded-lg p-1">
        {SEARCH_MODES.map((mode) => (
          <button
            key={mode.value}
            onClick={() => onModeChange(mode.value)}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors capitalize ${
              searchMode === mode.value
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {mode.label}
          </button>
        ))}
      </div>
      {currentMode && (
        <div className="mt-2 text-xs text-muted-foreground">
          {currentMode.description}
        </div>
      )}
    </div>
  );
};