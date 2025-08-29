import React, { useState, useEffect, useCallback } from 'react';
import { Search, Filter, FileText, Calendar, HardDrive } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';

interface SearchResult {
  document_id: string;
  title: string;
  snippet: string;
  score: number;
  created_at: string | null;
  ingested_at: string | null;
  mime_type: string;
  size_bytes: number;
  word_count: number | null;
  match_type: string;
  tags?: string[];
  matched_tags?: string[];
}

interface Tag {
  id: number;
  name: string;
  category: string | null;
  document_count: number;
}

interface SearchResponse {
  results: SearchResult[];
  total: number;
  query_time_ms: number;
}

const SearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [queryTime, setQueryTime] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [availableTags, setAvailableTags] = useState<Tag[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [tagsLoading, setTagsLoading] = useState(false);
  const [searchMode, setSearchMode] = useState<'keyword' | 'semantic' | 'hybrid'>('keyword');

  // Fetch available tags
  const fetchTags = useCallback(async () => {
    try {
      setTagsLoading(true);
      const response = await axios.get('http://localhost:8000/api/tags');
      setAvailableTags(response.data.tags || []);
    } catch (err) {
      console.error('Failed to fetch tags:', err);
    } finally {
      setTagsLoading(false);
    }
  }, []);

  // Load tags on component mount and read URL parameters
  useEffect(() => {
    fetchTags();
    
    // Read initial state from URL parameters
    const urlTags = searchParams.get('tags');
    const urlQuery = searchParams.get('q') || '';
    
    if (urlTags) {
      const tagList = urlTags.split(',').map(tag => decodeURIComponent(tag.trim())).filter(tag => tag);
      setSelectedTags(tagList);
      // Keep filters closed by default - user can open them if needed
    }
    
    if (urlQuery) {
      setQuery(urlQuery);
    }
  }, [fetchTags, searchParams]);

  // Debounced search function
  const performSearch = useCallback(async (searchQuery: string, tagFilters: string[] = []) => {
    // Allow search with tags even if query is empty
    if (!searchQuery.trim() && tagFilters.length === 0) {
      setResults([]);
      setQueryTime(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    try {
      const params: any = {
        mode: searchMode,
        limit: 20
      };
      
      // Only add query if it's not empty
      if (searchQuery.trim()) {
        params.q = searchQuery.trim();
      }
      
      if (tagFilters.length > 0) {
        params.tags = tagFilters.join(',');
      }
      
      const response = await axios.get<SearchResponse>('http://localhost:8000/api/search', {
        params
      });
      
      setResults(response.data.results);
      setQueryTime(response.data.query_time_ms);
      setError(null);
      
    } catch (err) {
      console.error('Search failed:', err);
      setError('Search failed. Please try again.');
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, [searchMode]);

  // Debounce search while typing or when tags change
  useEffect(() => {
    // Start loading immediately when query changes or tags change
    if (query.trim() || selectedTags.length > 0) {
      setIsLoading(true);
      setError(null);
    }

    const timer = setTimeout(() => {
      performSearch(query, selectedTags);
    }, 300); // 300ms delay

    return () => clearTimeout(timer);
  }, [query, selectedTags, performSearch]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    // Search is now handled automatically by useEffect
    // This just prevents the form from refreshing the page
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'Unknown';
    return new Date(dateString).toLocaleDateString();
  };

  const getMimeTypeIcon = (mimeType: string) => {
    if (mimeType.startsWith('text/')) return '📄';
    if (mimeType === 'application/pdf') return '📕';
    if (mimeType.startsWith('image/')) return '🖼️';
    return '📄';
  };

  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Search Documents</h1>
        
        {/* Search Form */}
        <form onSubmit={handleSearch} className="mb-8">
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
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search your documents..."
                className="w-full pl-10 pr-4 py-2 border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className={`px-3 py-2 border border-input rounded-md hover:bg-accent transition-colors ${
                showFilters || selectedTags.length > 0 ? 'bg-accent' : ''
              }`}
            >
              <Filter className="h-5 w-5" />
              {selectedTags.length > 0 && (
                <span className="ml-1 text-xs bg-primary text-primary-foreground rounded-full px-1.5 py-0.5">
                  {selectedTags.length}
                </span>
              )}
            </button>
            
            <button
              type="submit"
              disabled={isLoading}
              className="px-6 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Searching...' : 'Search'}
            </button>
          </div>
        </form>

        {/* Search Mode Toggle */}
        <div className="mb-6">
          <div className="flex items-center space-x-1 bg-muted rounded-lg p-1">
            {(['keyword', 'semantic', 'hybrid'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setSearchMode(mode)}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors capitalize ${
                  searchMode === mode
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
          <div className="mt-2 text-xs text-muted-foreground">
            {searchMode === 'keyword' && 'Search using exact text matches and keywords'}
            {searchMode === 'semantic' && 'Search using AI to understand meaning and context'}
            {searchMode === 'hybrid' && 'Combine keyword and semantic search for best results'}
          </div>
        </div>

        {/* Tag Filters */}
        {showFilters && (
          <div className="mb-6 p-4 border border-border rounded-lg bg-muted/30">
            <h3 className="text-sm font-medium mb-3">Filter by Tags</h3>
            
            {tagsLoading ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary border-t-transparent"></div>
                <span className="text-sm text-muted-foreground">Loading tags...</span>
              </div>
            ) : availableTags.length > 0 ? (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  {availableTags.map((tag) => {
                    const isSelected = selectedTags.includes(tag.name);
                    return (
                      <button
                        key={tag.id}
                        onClick={() => {
                          if (isSelected) {
                            setSelectedTags(selectedTags.filter(t => t !== tag.name));
                          } else {
                            setSelectedTags([...selectedTags, tag.name]);
                          }
                        }}
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
                    <span className="text-sm text-muted-foreground">Selected:</span>
                    <div className="flex flex-wrap gap-1">
                      {selectedTags.map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary text-primary-foreground"
                        >
                          {tag}
                          <button
                            onClick={() => setSelectedTags(selectedTags.filter(t => t !== tag))}
                            className="ml-1 hover:bg-primary-foreground/20 rounded-full p-0.5"
                          >
                            ×
                          </button>
                        </span>
                      ))}
                    </div>
                    <button
                      onClick={() => setSelectedTags([])}
                      className="text-xs text-muted-foreground hover:text-foreground underline"
                    >
                      Clear all
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No tags available yet. Upload and process some documents to see tags.</p>
            )}
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold">
                {results.length} result{results.length !== 1 ? 's' : ''} found
              </h2>
              <div className="text-sm text-muted-foreground">
                <span>
                  {query && selectedTags.length > 0
                    ? `Showing results for "${query}" with tags: ${selectedTags.join(', ')}`
                    : query
                    ? `Showing results for "${query}"`
                    : `Showing results with tags: ${selectedTags.join(', ')}`
                  }
                </span>
                {queryTime && <span className="ml-2">({queryTime}ms)</span>}
              </div>
            </div>
            
            <div className="space-y-4">
              {results.map((result) => (
                <div
                  key={result.document_id}
                  className="p-4 glass-card rounded-lg border border-border/30 hover:bg-accent/50 cursor-pointer transition-colors"
                >
                  <div className="flex items-start space-x-3">
                    <div className="text-2xl mt-1 flex-shrink-0">
                      {getMimeTypeIcon(result.mime_type)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-medium text-foreground truncate">{result.title}</h3>
                        <span className="text-sm text-muted-foreground ml-2">
                          Score: {(result.score * 100).toFixed(0)}%
                        </span>
                      </div>
                      
                      <p className="text-sm text-muted-foreground mb-3 line-clamp-3">
                        {result.snippet}
                      </p>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs text-muted-foreground mb-2">
                        <div className="flex items-center space-x-1">
                          <HardDrive className="h-3 w-3" />
                          <span>{formatFileSize(result.size_bytes)}</span>
                        </div>
                        
                        {result.word_count && (
                          <div className="flex items-center space-x-1">
                            <FileText className="h-3 w-3" />
                            <span>{result.word_count.toLocaleString()} words</span>
                          </div>
                        )}
                        
                        <div className="flex items-center space-x-1">
                          <Calendar className="h-3 w-3" />
                          <span>Added {formatDate(result.ingested_at)}</span>
                        </div>
                      </div>
                      
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex space-x-2">
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">
                              {result.match_type}
                            </span>
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-secondary text-secondary-foreground">
                              {result.mime_type.split('/')[1]}
                            </span>
                          </div>
                        </div>
                        
                        {/* Document Tags */}
                        {result.tags && result.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {result.tags.slice(0, 6).map((tag) => {
                              const isMatched = result.matched_tags?.includes(tag);
                              const isSelected = selectedTags.includes(tag);
                              return (
                                <button
                                  key={tag}
                                  onClick={() => {
                                    if (isSelected) {
                                      // Remove tag if already selected
                                      setSelectedTags(selectedTags.filter(t => t !== tag));
                                    } else {
                                      // Add tag if not selected
                                      setSelectedTags([...selectedTags, tag]);
                                    }
                                  }}
                                  className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium transition-colors ${
                                    isSelected
                                      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 hover:bg-green-200 dark:hover:bg-green-800'
                                      : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 hover:bg-blue-200 dark:hover:bg-blue-800'
                                  }`}
                                  title={isSelected ? `Remove filter: ${tag}` : `Add filter: ${tag}`}
                                >
                                  {tag}
                                </button>
                              );
                            })}
                            {result.tags.length > 6 && (
                              <span className="text-xs text-muted-foreground px-2 py-1">
                                +{result.tags.length - 6} more
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && query && (
          <div className="text-center py-12">
            <div className="flex items-center justify-center mb-4">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent"></div>
            </div>
            <p className="text-muted-foreground">Searching...</p>
          </div>
        )}

        {/* Error State */}
        {!isLoading && error && (
          <div className="text-center py-12">
            <div className="text-red-500 mb-2">⚠️</div>
            <h3 className="text-lg font-medium mb-2 text-red-600">Search Error</h3>
            <p className="text-muted-foreground">{error}</p>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && results.length === 0 && (query || selectedTags.length > 0) && (
          <div className="text-center py-12">
            <Search className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">No results found</h3>
            <p className="text-muted-foreground">
              {query && selectedTags.length > 0
                ? 'Try adjusting your search terms or tag filters.'
                : query
                ? 'Try adjusting your search terms or check your spelling.'
                : 'No documents found with the selected tags.'
              }
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchPage;