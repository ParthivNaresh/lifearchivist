/**
 * TagFilters component - tag selection filters
 */

import React from 'react';
import { Tag } from '../types';
import { UI_TEXT } from '../constants';

interface TagFiltersProps {
  showFilters: boolean;
  tagsLoading: boolean;
  availableTags: Tag[];
  selectedTags: string[];
  onToggleTag: (tag: string) => void;
  onClearTags: () => void;
}

export const TagFilters: React.FC<TagFiltersProps> = ({
  showFilters,
  tagsLoading,
  availableTags,
  selectedTags,
  onToggleTag,
  onClearTags,
}) => {
  if (!showFilters) return null;

  return (
    <div className="mb-6 p-4 border border-border rounded-lg bg-muted/30">
      <h3 className="text-sm font-medium mb-3">{UI_TEXT.FILTER_BY_TAGS}</h3>
      
      {tagsLoading ? (
        <div className="flex items-center space-x-2">
          <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary border-t-transparent"></div>
          <span className="text-sm text-muted-foreground">{UI_TEXT.LOADING_TAGS}</span>
        </div>
      ) : availableTags.length > 0 ? (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {availableTags.map((tag) => {
              const isSelected = selectedTags.includes(tag.name);
              return (
                <button
                  key={tag.id}
                  onClick={() => onToggleTag(tag.name)}
                  className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                    isSelected
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                  }`}
                >
                  {tag.name}
                  <span className="ml-1.5 text-xs opacity-75">({tag.document_count})</span>
                </button>
              );
            })}
          </div>
          
          {selectedTags.length > 0 && (
            <div className="flex items-center space-x-2">
              <span className="text-sm text-muted-foreground">{UI_TEXT.SELECTED_TAGS}</span>
              <div className="flex flex-wrap gap-1">
                {selectedTags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary text-primary-foreground"
                  >
                    {tag}
                    <button
                      onClick={() => onToggleTag(tag)}
                      className="ml-1 hover:bg-primary-foreground/20 rounded-full p-0.5"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <button
                onClick={onClearTags}
                className="text-xs text-muted-foreground hover:text-foreground underline"
              >
                {UI_TEXT.CLEAR_ALL}
              </button>
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">{UI_TEXT.NO_TAGS}</p>
      )}
    </div>
  );
};