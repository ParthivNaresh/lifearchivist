import { useEffect, useRef, useCallback, useState } from 'react';
import type {
  WSIncomingMessage,
  WSOutgoingMessage,
  WSMessageStatusUpdate,
} from '@/pages/ConversationsPage';

interface UseConversationWebSocketOptions {
  conversationId: string | null;
  onMessageStatusUpdate?: (update: WSMessageStatusUpdate) => void;
  onError?: (error: string) => void;
  enabled?: boolean;
}

interface UseConversationWebSocketReturn {
  isConnected: boolean;
  subscribe: (conversationId: string) => void;
  unsubscribe: () => void;
}

const WS_URL = 'ws://localhost:8000/ws';
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 5;

export function useConversationWebSocket({
  conversationId,
  onMessageStatusUpdate,
  onError,
  enabled = true,
}: UseConversationWebSocketOptions): UseConversationWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const subscribedConversationRef = useRef<string | null>(null);
  const isConnectingRef = useRef(false);
  const [isConnected, setIsConnected] = useState(false);

  const onMessageStatusUpdateRef = useRef(onMessageStatusUpdate);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onMessageStatusUpdateRef.current = onMessageStatusUpdate;
    onErrorRef.current = onError;
  }, [onMessageStatusUpdate, onError]);

  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    subscribedConversationRef.current = null;
    isConnectingRef.current = false;
    reconnectAttemptsRef.current = 0;
    setIsConnected(false);
  }, []);

  const sendMessage = useCallback((message: WSOutgoingMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  const subscribe = useCallback(
    (convId: string) => {
      if (subscribedConversationRef.current === convId) {
        return;
      }

      subscribedConversationRef.current = convId;

      sendMessage({
        type: 'conversation_subscribe',
        conversation_id: convId,
      });
    },
    [sendMessage]
  );

  const unsubscribe = useCallback(() => {
    subscribedConversationRef.current = null;
  }, []);

  const connectToWebSocketRef = useRef<() => void>();

  const connectToWebSocket = useCallback(() => {
    if (!enabled) return;

    if (isConnectingRef.current || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    isConnectingRef.current = true;

    try {
      const sessionId = `session-${Date.now()}-${Math.random().toString(36).substring(7)}`;
      const ws = new WebSocket(`${WS_URL}/${sessionId}`);

      ws.onopen = () => {
        isConnectingRef.current = false;
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;

        if (subscribedConversationRef.current && ws.readyState === WebSocket.OPEN) {
          ws.send(
            JSON.stringify({
              type: 'conversation_subscribe',
              conversation_id: subscribedConversationRef.current,
            })
          );
        }
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const data: unknown = JSON.parse(event.data as string);
          const message = data as WSIncomingMessage;

          switch (message.type) {
            case 'subscription_confirmed':
              break;

            case 'message_status':
              onMessageStatusUpdateRef.current?.(message);
              break;

            case 'error':
              onErrorRef.current?.(message.error);
              break;
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        isConnectingRef.current = false;
      };

      ws.onclose = () => {
        isConnectingRef.current = false;
        setIsConnected(false);
        wsRef.current = null;

        if (enabled && reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            connectToWebSocketRef.current?.();
          }, RECONNECT_DELAY);
        }
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('Failed to create WebSocket connection:', err);
      isConnectingRef.current = false;
      onErrorRef.current?.('Failed to establish WebSocket connection');
    }
  }, [enabled]);

  useEffect(() => {
    connectToWebSocketRef.current = connectToWebSocket;
  }, [connectToWebSocket]);

  useEffect(() => {
    connectToWebSocket();

    return () => {
      cleanup();
    };
  }, [connectToWebSocket, cleanup]);

  useEffect(() => {
    if (conversationId && isConnected) {
      subscribe(conversationId);
    }
  }, [conversationId, isConnected, subscribe]);

  return {
    isConnected,
    subscribe,
    unsubscribe,
  };
}
