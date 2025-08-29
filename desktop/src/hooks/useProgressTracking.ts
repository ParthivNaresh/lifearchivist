import { useCallback, useEffect, useRef, useState } from 'react';
import { ProgressUpdate, WebSocketMessage, ProgressTrackingSession } from '../types/upload';

interface UseProgressTrackingOptions {
  onProgressUpdate?: (update: ProgressUpdate) => void;
  onError?: (error: string) => void;
  onConnectionChange?: (connected: boolean) => void;
}

interface UseProgressTrackingReturn {
  createSession: (fileId: string) => Promise<string>;
  isConnected: boolean;
  activeConnections: number;
  closeAllConnections: () => void;
}

export const useProgressTracking = (options: UseProgressTrackingOptions = {}): UseProgressTrackingReturn => {
  const { onProgressUpdate, onError, onConnectionChange } = options;
  
  const [isConnected, setIsConnected] = useState(false);
  const [activeConnections, setActiveConnections] = useState(0);
  const sessionsRef = useRef<Map<string, ProgressTrackingSession>>(new Map());
  const reconnectTimeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  const generateSessionId = useCallback((): string => {
    return `session_${Math.random().toString(36).substring(2)}_${Date.now()}`;
  }, []);

  const createWebSocketConnection = useCallback((sessionId: string, fileId: string): Promise<WebSocket> => {
    return new Promise((resolve, reject) => {
      const wsUrl = `ws://localhost:8000/ws/${sessionId}`;
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log(`🔌 WebSocket connected for session ${sessionId}`);
        setIsConnected(true);
        setActiveConnections(prev => prev + 1);
        onConnectionChange?.(true);
        resolve(ws);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          if (message.type === 'upload_progress' && message.data) {
            const progressUpdate = message.data as ProgressUpdate;
            
            // Verify this progress update is for the expected file
            if (progressUpdate.file_id === fileId) {
              onProgressUpdate?.(progressUpdate);
            }
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
          onError?.('Failed to parse progress update');
        }
      };

      ws.onerror = (error) => {
        console.error(`WebSocket error for session ${sessionId}:`, error);
        onError?.('WebSocket connection error');
        reject(new Error('WebSocket connection failed'));
      };

      ws.onclose = (event) => {
        console.log(`WebSocket closed for session ${sessionId}:`, event.code, event.reason);
        
        const session = sessionsRef.current.get(sessionId);
        if (session) {
          session.isConnected = false;
          sessionsRef.current.set(sessionId, session);
        }
        
        setActiveConnections(prev => Math.max(0, prev - 1));
        
        // Check if this was the last connection
        const hasActiveConnections = Array.from(sessionsRef.current.values())
          .some(s => s.isConnected);
        
        if (!hasActiveConnections) {
          setIsConnected(false);
          onConnectionChange?.(false);
        }

        // Attempt reconnection for unexpected closures (not manual close)
        if (event.code !== 1000 && event.code !== 1001) {
          const reconnectTimeout = setTimeout(() => {
            if (sessionsRef.current.has(sessionId)) {
              console.log(`Attempting to reconnect session ${sessionId}`);
              createWebSocketConnection(sessionId, fileId)
                .then(newWs => {
                  const session = sessionsRef.current.get(sessionId);
                  if (session) {
                    session.websocket = newWs;
                    session.isConnected = true;
                    sessionsRef.current.set(sessionId, session);
                  }
                })
                .catch(error => {
                  console.error(`Reconnection failed for session ${sessionId}:`, error);
                });
            }
          }, 3000); // Reconnect after 3 seconds
          
          reconnectTimeoutsRef.current.set(sessionId, reconnectTimeout);
        }
      };

      // Timeout after 10 seconds
      setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          ws.close();
          reject(new Error('WebSocket connection timeout'));
        }
      }, 10000);
    });
  }, [onProgressUpdate, onError, onConnectionChange]);

  const createSession = useCallback(async (fileId: string): Promise<string> => {
    const sessionId = generateSessionId();
    
    try {
      console.log(`🔗 Creating progress tracking session for file ${fileId} with session ${sessionId}`);
      
      const websocket = await createWebSocketConnection(sessionId, fileId);
      
      const session: ProgressTrackingSession = {
        sessionId,
        fileId,
        websocket,
        isConnected: true,
      };
      
      sessionsRef.current.set(sessionId, session);
      
      console.log(`✅ Progress tracking session created successfully: ${sessionId}`);
      return sessionId;
    } catch (error) {
      console.error(`❌ Failed to create session for file ${fileId}:`, error);
      onError?.(`Failed to establish progress tracking: ${error.message}`);
      throw error;
    }
  }, [generateSessionId, createWebSocketConnection, onError]);

  const closeSession = useCallback((sessionId: string) => {
    const session = sessionsRef.current.get(sessionId);
    if (session) {
      console.log(`Closing progress tracking session ${sessionId}`);
      
      // Clear any pending reconnection timeout
      const reconnectTimeout = reconnectTimeoutsRef.current.get(sessionId);
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeoutsRef.current.delete(sessionId);
      }
      
      // Close WebSocket connection
      if (session.websocket && session.websocket.readyState === WebSocket.OPEN) {
        session.websocket.close(1000, 'Session closed by client');
      }
      
      sessionsRef.current.delete(sessionId);
    }
  }, []);

  const closeAllConnections = useCallback(() => {
    console.log('Closing all progress tracking connections');
    
    // Clear all reconnection timeouts
    reconnectTimeoutsRef.current.forEach(timeout => clearTimeout(timeout));
    reconnectTimeoutsRef.current.clear();
    
    // Close all sessions
    sessionsRef.current.forEach((session, sessionId) => {
      if (session.websocket && session.websocket.readyState === WebSocket.OPEN) {
        session.websocket.close(1000, 'All sessions closed');
      }
    });
    
    sessionsRef.current.clear();
    setIsConnected(false);
    setActiveConnections(0);
    onConnectionChange?.(false);
  }, []); // Remove onConnectionChange dependency to prevent unnecessary recreation

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      console.log('🧹 useProgressTracking cleanup - closing all connections');
      
      // Clear all reconnection timeouts
      reconnectTimeoutsRef.current.forEach(timeout => clearTimeout(timeout));
      reconnectTimeoutsRef.current.clear();
      
      // Close all sessions
      sessionsRef.current.forEach((session, sessionId) => {
        if (session.websocket && session.websocket.readyState === WebSocket.OPEN) {
          session.websocket.close(1000, 'Component unmounting');
        }
      });
      
      sessionsRef.current.clear();
      setIsConnected(false);
      setActiveConnections(0);
      onConnectionChange?.(false);
    };
  }, []); // No dependencies to prevent unnecessary cleanup

  // Auto-cleanup completed sessions after 30 seconds
  useEffect(() => {
    const cleanupInterval = setInterval(() => {
      const now = Date.now();
      const sessionsToRemove: string[] = [];
      
      sessionsRef.current.forEach((session, sessionId) => {
        // Remove sessions that have been disconnected for more than 30 seconds
        if (!session.isConnected) {
          sessionsToRemove.push(sessionId);
        }
      });
      
      sessionsToRemove.forEach(sessionId => closeSession(sessionId));
    }, 30000);

    return () => clearInterval(cleanupInterval);
  }, [closeSession]);

  return {
    createSession,
    isConnected,
    activeConnections,
    closeAllConnections,
    closeSession,
  };
};