/**
 * useActivityFeed - Shared hook for activity feed with WebSocket updates
 *
 * Fetches activity events and subscribes to real-time updates via WebSocket.
 * Used by both InboxPage and ActivityPage for consistent behavior.
 */

import { useState, useEffect, useCallback } from 'react';
import apiClient from '../utils/api-client';

export type ActivityEventData = Record<string, string | number | boolean | null | undefined>;

export interface ActivityEvent {
  id: string;
  type: string;
  data: ActivityEventData;
  timestamp: string;
}

interface ApiResponse {
  events: ActivityEvent[];
  count: number;
}

interface WebSocketMessage {
  type: string;
  event?: ActivityEvent;
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
export const useActivityFeed = (options: UseActivityFeedOptions = {}): UseActivityFeedReturn => {
  const { limit = 50, autoFetch = true } = options;

  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [isLoading, setIsLoading] = useState(autoFetch);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  // Fetch events from API
  const fetchEvents = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await apiClient.get<ApiResponse>(`/api/activity/events?limit=${limit}`);

      if (data.events && Array.isArray(data.events)) {
        setEvents(data.events);
        setError(null);
      } else {
        setError('Invalid response format');
      }
    } catch (err) {
      if (err instanceof Error && !err.message.includes('Backend is not available')) {
        console.error('Failed to fetch activity events:', err);
        setError(err.message);
      } else {
        setError(null);
      }
    } finally {
      setIsLoading(false);
    }
  }, [limit]);

  // Initial fetch
  useEffect(() => {
    if (autoFetch) {
      void fetchEvents();
    }
  }, [autoFetch, fetchEvents]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout | null = null;
    let mounted = true;

    const connect = (): void => {
      if (!mounted) return;

      if (!apiClient.isReady()) {
        reconnectTimeout = setTimeout(() => {
          connect();
        }, 2000);
        return;
      }

      try {
        ws = new WebSocket(WS_ACTIVITY_FEED);

        ws.onopen = () => {
          if (!mounted) return;
          setIsConnected(true);
        };

        ws.onmessage = (event) => {
          if (!mounted) return;
          try {
            const message = JSON.parse(event.data as string) as WebSocketMessage;

            if (message.type === 'activity_event' && message.event) {
              const newEvent = message.event;
              setEvents((prev) => [newEvent, ...prev].slice(0, limit));
            }
          } catch (_err) {
            console.error('Failed to parse WebSocket message:', _err);
          }
        };

        ws.onerror = () => {
          if (!mounted) return;
          setIsConnected(false);
        };

        ws.onclose = () => {
          if (!mounted) return;
          setIsConnected(false);
          if (apiClient.isReady()) {
            reconnectTimeout = setTimeout(() => {
              connect();
            }, 5000);
          }
        };
      } catch (_err) {
        if (mounted) {
          setIsConnected(false);
          reconnectTimeout = setTimeout(() => {
            connect();
          }, 5000);
        }
      }
    };

    connect();

    return () => {
      mounted = false;
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
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
