/**
 * useActivityFeed - Shared hook for activity feed with WebSocket updates
 * 
 * Fetches activity events and subscribes to real-time updates via WebSocket.
 * Used by both InboxPage and ActivityPage for consistent behavior.
 */

import { useState, useEffect, useCallback } from 'react';

export interface ActivityEvent {
  id: string;
  type: string;
  data: Record<string, any>;
  timestamp: string;
}

interface UseActivityFeedOptions {
  limit?: number;
  autoFetch?: boolean;
}

interface UseActivityFeedReturn {
  events: ActivityEvent[];
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  isConnected: boolean;
}

const API_BASE_URL = 'http://localhost:8000';
const WS_ACTIVITY_FEED = 'ws://localhost:8000/ws/activity_feed';

/**
 * Hook for managing activity feed with real-time WebSocket updates
 * 
 * @param options.limit - Maximum number of events to fetch (default: 50)
 * @param options.autoFetch - Whether to fetch on mount (default: true)
 * 
 * @example
 * // In InboxPage - show last 5 events
 * const { events } = useActivityFeed({ limit: 5 });
 * 
 * @example
 * // In ActivityPage - show last 50 events
 * const { events, isLoading, refetch } = useActivityFeed({ limit: 50 });
 */
export const useActivityFeed = (
  options: UseActivityFeedOptions = {}
): UseActivityFeedReturn => {
  const { limit = 50, autoFetch = true } = options;

  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [isLoading, setIsLoading] = useState(autoFetch);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  // Fetch events from API
  const fetchEvents = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/activity/events?limit=${limit}`);
      const data = await response.json();

      if (data.success && Array.isArray(data.events)) {
        setEvents(data.events);
        setError(null);
      } else {
        setError(data.error || 'Failed to load activity events');
      }
    } catch (err) {
      console.error('Failed to fetch activity events:', err);
      setError('Failed to connect to server');
    } finally {
      setIsLoading(false);
    }
  }, [limit]);

  // Initial fetch
  useEffect(() => {
    if (autoFetch) {
      fetchEvents();
    }
  }, [autoFetch, fetchEvents]);

  // WebSocket connection for real-time updates
  useEffect(() => {
    let ws: WebSocket | null = null;

    const connect = () => {
      try {
        ws = new WebSocket(WS_ACTIVITY_FEED);

        ws.onopen = () => {
          console.log('Activity feed WebSocket connected');
          setIsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);

            if (message.type === 'activity_event' && message.event) {
              // Add new event to the top of the list, maintain limit
              setEvents((prev) => [message.event, ...prev].slice(0, limit));
            }
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
          }
        };

        ws.onerror = () => {
          // Don't log error - it's expected when server is down
          setIsConnected(false);
        };

        ws.onclose = () => {
          console.log('Activity feed WebSocket disconnected');
          setIsConnected(false);
        };
      } catch (err) {
        console.error('Failed to create WebSocket:', err);
        setIsConnected(false);
      }
    };

    connect();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [limit]);

  return {
    events,
    isLoading,
    error,
    refetch: fetchEvents,
    isConnected,
  };
};
