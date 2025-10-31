/**
 * SearchResultItem component - individual search result
 */

import { FileText, Calendar, HardDrive } from 'lucide-react';
import { type SearchResult } from '../types';
import { formatFileSize, formatDate, getMimeTypeIcon, formatScore, getFileType } from '../utils';
import { useSearchNavigation } from '../hooks';
import { UI_TEXT, SEARCH_CONFIG } from '../constants';

interface SearchResultItemProps {
  result: SearchResult;
  selectedTags: string[];
  onToggleTag: (tag: string) => void;
}

export const SearchResultItem: React.FC<SearchResultItemProps> = ({
  result,
  selectedTags,
  onToggleTag,
}) => {
  const { handleDocumentClick } = useSearchNavigation();

  return (
    <div
      onClick={() => handleDocumentClick(result.document_id)}
      className="p-4 glass-card rounded-lg border border-border/30 hover:bg-accent/50 cursor-pointer transition-colors"
    >
      <div className="flex items-start space-x-3">
        <div className="text-2xl mt-1 flex-shrink-0">{getMimeTypeIcon(result.mime_type)}</div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium text-foreground truncate">{result.title}</h3>
            <span className="text-sm text-muted-foreground ml-2">
              {UI_TEXT.SCORE} {formatScore(result.score)}
            </span>
          </div>

          <p className="text-sm text-muted-foreground mb-3 line-clamp-3">{result.snippet}</p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs text-muted-foreground mb-2">
            <div className="flex items-center space-x-1">
              <HardDrive className="h-3 w-3" />
              <span>{formatFileSize(result.size_bytes)}</span>
            </div>

            {result.word_count && (
              <div className="flex items-center space-x-1">
                <FileText className="h-3 w-3" />
                <span>{UI_TEXT.WORDS(result.word_count)}</span>
              </div>
            )}

            <div className="flex items-center space-x-1">
              <Calendar className="h-3 w-3" />
              <span>
                {UI_TEXT.ADDED} {formatDate(result.ingested_at)}
              </span>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex space-x-2">
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">
                  {result.match_type}
                </span>
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-secondary text-secondary-foreground">
                  {getFileType(result.mime_type)}
                </span>
              </div>
            </div>

            {/* Document Tags */}
            {result.tags && result.tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {result.tags.slice(0, SEARCH_CONFIG.MAX_TAGS_DISPLAY).map((tag) => {
                  const isSelected = selectedTags.includes(tag);
                  return (
                    <button
                      key={tag}
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleTag(tag);
                      }}
                      className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium transition-colors ${
                        isSelected
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 hover:bg-green-200 dark:hover:bg-green-800'
                          : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 hover:bg-blue-200 dark:hover:bg-blue-800'
                      }`}
                      title={isSelected ? UI_TEXT.REMOVE_FILTER(tag) : UI_TEXT.ADD_FILTER(tag)}
                    >
                      {tag}
                    </button>
                  );
                })}
                {result.tags.length > SEARCH_CONFIG.MAX_TAGS_DISPLAY && (
                  <span className="text-xs text-muted-foreground px-2 py-1">
                    {UI_TEXT.MORE_TAGS(result.tags.length - SEARCH_CONFIG.MAX_TAGS_DISPLAY)}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
