/**
 * Activity Page - System activity feed
 * 
 * Displays recent system events with real-time WebSocket updates.
 * Shows folder watch events, uploads, deletions, Q&A queries, etc.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Activity, 
  FolderOpen, 
  Upload, 
  Trash2, 
  MessageCircle, 
  Search, 
  AlertCircle,
  CheckCircle2,
  Clock,
  RefreshCw,
  XCircle,
  Filter
} from 'lucide-react';
import { cn } from '../utils/cn';

interface ActivityEvent {
  id: string;
  type: string;
  data: Record<string, any>;
  timestamp: string;
}

type FilterType = 'all' | 'uploads' | 'folder_watch' | 'errors' | 'other';

const ActivityPage: React.FC = () => {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [activeFilter, setActiveFilter] = useState<FilterType>('all');

  // Fetch initial events
  const fetchEvents = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/activity/events?limit=50');
      const data = await response.json();
      
      if (data.success) {
        setEvents(data.events);
        setError(null);
      } else {
        setError(data.error || 'Failed to load activity events');
      }
    } catch (err) {
      console.error('Failed to fetch activity events:', err);
      setError('Failed to connect to server');
    } finally {
      setLoading(false);
    }
  }, []);

  // WebSocket connection for real-time updates
  useEffect(() => {
    fetchEvents();

    // Connect to WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws/activity_feed');

    ws.onopen = () => {
      console.log('🔌 Activity feed WebSocket connected');
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'activity_event' && message.event) {
          // Add new event to the top of the list
          setEvents(prev => [message.event, ...prev].slice(0, 50));
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('Activity feed WebSocket error:', error);
      setWsConnected(false);
    };

    ws.onclose = () => {
      console.log('Activity feed WebSocket disconnected');
      setWsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [fetchEvents]);

  // Format timestamp
  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 60) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString();
  };

  // Get event icon and color
  const getEventIcon = (eventType: string) => {
    if (eventType.startsWith('folder_watch_')) {
      if (eventType.includes('ingested')) {
        return { icon: CheckCircle2, color: 'text-emerald-500' };
      }
      if (eventType.includes('failed')) {
        return { icon: XCircle, color: 'text-red-500' };
      }
      if (eventType.includes('duplicate')) {
        return { icon: AlertCircle, color: 'text-amber-500' };
      }
      return { icon: FolderOpen, color: 'text-blue-500' };
    }
    if (eventType.includes('upload')) {
      return { icon: Upload, color: 'text-purple-500' };
    }
    if (eventType.includes('delete')) {
      return { icon: Trash2, color: 'text-red-500' };
    }
    if (eventType.includes('qa_query')) {
      return { icon: MessageCircle, color: 'text-indigo-500' };
    }
    if (eventType.includes('search')) {
      return { icon: Search, color: 'text-cyan-500' };
    }
    return { icon: Activity, color: 'text-gray-500' };
  };

  // Format event message
  const formatEventMessage = (event: ActivityEvent): string => {
    const { type, data } = event;

    switch (type) {
      case 'folder_watch_file_ingested':
        return `Ingested ${data.file_name} from watched folder`;
      case 'folder_watch_file_failed':
        return `Failed to ingest ${data.file_name}: ${data.error}`;
      case 'folder_watch_file_detected':
        return `Detected ${data.file_name} in watched folder`;
      case 'folder_watch_duplicate_skipped':
        return `Skipped duplicate file: ${data.file_name}`;
      case 'file_upload_failed':
        return `Failed to upload ${data.file_name}: ${data.error}`;
      case 'files_uploaded':
        if (data.file_name) {
          return `Uploaded ${data.file_name}`;
        }
        return `Uploaded ${data.file_count} file${data.file_count !== 1 ? 's' : ''}`;
      case 'document_deleted':
        return `Deleted ${data.file_name}`;
      case 'qa_query':
        return `Asked: "${data.question}"`;
      case 'search_performed':
        return `Searched for "${data.query}" (${data.results_count} results)`;
      case 'vault_reconciliation':
        return `Vault reconciliation: ${data.cleaned} cleaned, ${data.errors} errors`;
      default:
        return type.replace(/_/g, ' ');
    }
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Get file name from path
  const getFileName = (path: string): string => {
    const parts = path.split('/');
    return parts[parts.length - 1] || path;
  };

  // Filter events based on active filter
  const filteredEvents = useMemo(() => {
    if (activeFilter === 'all') return events;

    return events.filter(event => {
      switch (activeFilter) {
        case 'uploads':
          return event.type === 'files_uploaded';
        case 'folder_watch':
          return event.type.startsWith('folder_watch_');
        case 'errors':
          return event.type.includes('failed') || event.type.includes('error');
        case 'other':
          return !event.type.startsWith('folder_watch_') && 
                 event.type !== 'files_uploaded' &&
                 !event.type.includes('failed') &&
                 !event.type.includes('error');
        default:
          return true;
      }
    });
  }, [events, activeFilter]);

  // Get count for each filter
  const filterCounts = useMemo(() => {
    return {
      all: events.length,
      uploads: events.filter(e => e.type === 'files_uploaded').length,
      folder_watch: events.filter(e => e.type.startsWith('folder_watch_')).length,
      errors: events.filter(e => e.type.includes('failed') || e.type.includes('error')).length,
      other: events.filter(e => 
        !e.type.startsWith('folder_watch_') && 
        e.type !== 'files_uploaded' &&
        !e.type.includes('failed') &&
        !e.type.includes('error')
      ).length,
    };
  }, [events]);

  if (loading && events.length === 0) {
    return (
      <div className="p-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-primary/20 to-purple-500/20 blur-xl" />
              <Activity className="h-8 w-8 text-primary relative z-10" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">Activity</h1>
              <p className="text-sm text-muted-foreground">
                Recent system events and actions
              </p>
            </div>
          </div>

          {/* Refresh Button */}
          <div className="flex items-center space-x-4">
            <button
              onClick={fetchEvents}
              disabled={loading}
              className="p-2 hover:bg-secondary rounded-lg transition-colors disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw className={cn("h-5 w-5", loading && "animate-spin")} />
            </button>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="mb-6 flex items-center gap-2 overflow-x-auto pb-2">
          <button
            onClick={() => setActiveFilter('all')}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap",
              activeFilter === 'all'
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
            )}
          >
            All
            {filterCounts.all > 0 && (
              <span className="ml-2 opacity-70">({filterCounts.all})</span>
            )}
          </button>

          <button
            onClick={() => setActiveFilter('uploads')}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap flex items-center gap-2",
              activeFilter === 'uploads'
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
            )}
          >
            <Upload className="h-4 w-4" />
            Uploads
            {filterCounts.uploads > 0 && (
              <span className="opacity-70">({filterCounts.uploads})</span>
            )}
          </button>

          <button
            onClick={() => setActiveFilter('folder_watch')}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap flex items-center gap-2",
              activeFilter === 'folder_watch'
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
            )}
          >
            <FolderOpen className="h-4 w-4" />
            Folder Watch
            {filterCounts.folder_watch > 0 && (
              <span className="opacity-70">({filterCounts.folder_watch})</span>
            )}
          </button>

          <button
            onClick={() => setActiveFilter('errors')}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap flex items-center gap-2",
              activeFilter === 'errors'
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
            )}
          >
            <XCircle className="h-4 w-4" />
            Errors
            {filterCounts.errors > 0 && (
              <span className="opacity-70">({filterCounts.errors})</span>
            )}
          </button>

          {filterCounts.other > 0 && (
            <button
              onClick={() => setActiveFilter('other')}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap flex items-center gap-2",
                activeFilter === 'other'
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
              )}
            >
              <Activity className="h-4 w-4" />
              Other
              <span className="opacity-70">({filterCounts.other})</span>
            </button>
          )}
        </div>

        {/* Error State */}
        {error && (
          <div className="mb-6 flex items-start space-x-3 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
            <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-destructive">Error loading activity</p>
              <p className="text-sm text-destructive/80 mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Events List */}
        {filteredEvents.length === 0 ? (
          <div className="glass-card rounded-xl p-12 text-center">
            <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">
              {events.length === 0 ? 'No activity yet' : 'No matching events'}
            </h3>
            <p className="text-sm text-muted-foreground">
              {events.length === 0 
                ? 'System events will appear here as they happen'
                : 'Try selecting a different filter'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredEvents.map((event) => {
              const { icon: Icon, color } = getEventIcon(event.type);
              const { type, data } = event;
              const timestamp = formatTimestamp(event.timestamp);

              // Render upload/folder watch events with detailed card
              if (type === 'files_uploaded' || type === 'folder_watch_file_ingested') {
                const fileName = getFileName(data.file_name || '');
                const fullPath = data.file_name || '';
                const fileSize = data.file_size ? formatFileSize(data.file_size) : null;
                const source = type === 'folder_watch_file_ingested' ? 'Watched Folder' : 'Manual Upload';

                return (
                  <div
                    key={event.id}
                    className="glass-card rounded-lg p-4 hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-start space-x-3">
                      {/* Icon */}
                      <div className={cn("flex-shrink-0 mt-1", color)}>
                        <Icon className="h-5 w-5" />
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        {/* File name */}
                        <div className="flex items-start justify-between gap-3 mb-1">
                          <h4 className="text-sm font-semibold break-words">{fileName}</h4>
                          <span className="text-xs text-muted-foreground whitespace-nowrap flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {timestamp}
                          </span>
                        </div>

                        {/* Full path */}
                        <p className="text-xs text-muted-foreground break-all mb-2 font-mono">
                          {fullPath}
                        </p>

                        {/* Metadata row */}
                        <div className="flex items-center gap-3 text-xs">
                          <span className="text-muted-foreground">
                            {source}
                          </span>
                          {fileSize && (
                            <>
                              <span className="text-muted-foreground">•</span>
                              <span className="text-muted-foreground font-medium">
                                {fileSize}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              }

              // Render other event types with simple layout
              const message = formatEventMessage(event);

              return (
                <div
                  key={event.id}
                  className="glass-card rounded-lg p-4 hover:bg-accent/50 transition-colors"
                >
                  <div className="flex items-start space-x-3">
                    {/* Icon */}
                    <div className={cn("flex-shrink-0 mt-0.5", color)}>
                      <Icon className="h-5 w-5" />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium break-words">{message}</p>
                    </div>

                    {/* Timestamp */}
                    <div className="flex items-center space-x-1 text-xs text-muted-foreground flex-shrink-0">
                      <Clock className="h-3 w-3" />
                      <span>{timestamp}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Footer Info */}
        {events.length > 0 && (
          <div className="mt-6 text-center text-sm text-muted-foreground">
            Showing {events.length} recent event{events.length !== 1 ? 's' : ''}
          </div>
        )}
      </div>
    </div>
  );
};

export default ActivityPage;
