import { useEffect, useRef, useState, useCallback } from 'react';
import type { NHJob } from '../types';

export type WSEventType =
  | 'job_started'
  | 'job_completed'
  | 'job_failed'
  | 'job_approved'
  | 'job_rejected'
  | 'circuit_break'
  | 'model_switched'
  | 'afk_started'
  | 'afk_stopped'
  | 'connected'
  | 'disconnected';

export interface WSEvent {
  event: WSEventType;
  data: {
    job_id?: string;
    job?: NHJob;
    message?: string;
    [key: string]: unknown;
  };
  timestamp: string;
}

export interface Toast {
  id: string;
  type: 'success' | 'warning' | 'error' | 'info';
  title: string;
  message: string;
  timestamp: Date;
}

interface UseWebSocketOptions {
  url: string;
  onEvent?: (event: WSEvent) => void;
  onJobUpdate?: (job: NHJob) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  lastEvent: WSEvent | null;
  toasts: Toast[];
  dismissToast: (id: string) => void;
  sendMessage: (data: string) => void;
}

export function useWebSocket({
  url,
  onEvent,
  onJobUpdate,
  reconnectInterval = 3000,
  maxReconnectAttempts = 5,
}: UseWebSocketOptions): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<WSEvent | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pingIntervalRef = useRef<number | null>(null);
  const wasConnectedRef = useRef(false);

  const addToast = useCallback((toast: Omit<Toast, 'id' | 'timestamp'>) => {
    const newToast: Toast = {
      ...toast,
      id: `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      timestamp: new Date(),
    };
    setToasts(prev => [newToast, ...prev].slice(0, 5));

    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== newToast.id));
    }, 5000);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        const wasDisconnected = wasConnectedRef.current && !isConnected;
        setIsConnected(true);
        wasConnectedRef.current = true;
        reconnectAttemptsRef.current = 0;
        console.log('[WS] Connected to NH');

        pingIntervalRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 25000);

        const event: WSEvent = {
          event: 'connected',
          data: { message: 'Connected to NH Mission Control' },
          timestamp: new Date().toISOString(),
        };
        setLastEvent(event);
        onEvent?.(event);

        // Only show toast if we were previously connected and reconnected
        if (wasDisconnected) {
          addToast({
            type: 'success',
            title: 'Reconnected',
            message: 'Real-time updates restored',
          });
        }
      };

      ws.onmessage = (event) => {
        if (event.data === 'pong') return;

        try {
          const wsEvent: WSEvent = JSON.parse(event.data);
          setLastEvent(wsEvent);
          onEvent?.(wsEvent);

          if (wsEvent.data.job && onJobUpdate) {
            onJobUpdate(wsEvent.data.job as NHJob);
          }

          // Only show toasts for critical events
          switch (wsEvent.event) {
            case 'job_completed':
              addToast({
                type: 'success',
                title: 'Job Completed',
                message: `Job ${wsEvent.data.job_id?.slice(0, 8)} finished`,
              });
              break;
            case 'job_failed':
              addToast({
                type: 'error',
                title: 'Job Failed',
                message: wsEvent.data.message || `Job ${wsEvent.data.job_id?.slice(0, 8)} failed`,
              });
              break;
            case 'circuit_break':
              addToast({
                type: 'error',
                title: 'STOP THE LINE',
                message: wsEvent.data.message || 'Circuit breaker triggered',
              });
              break;
          }
        } catch (e) {
          console.warn('[WS] Failed to parse message:', e);
        }
      };

      ws.onerror = () => {
        // Silent - errors are handled by onclose
      };

      ws.onclose = () => {
        setIsConnected(false);

        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        const event: WSEvent = {
          event: 'disconnected',
          data: { message: 'Disconnected from NH' },
          timestamp: new Date().toISOString(),
        };
        setLastEvent(event);
        onEvent?.(event);

        // Silent reconnection - no toasts
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = reconnectInterval * Math.pow(1.5, reconnectAttemptsRef.current);
          reconnectAttemptsRef.current++;
          console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`);
          reconnectTimeoutRef.current = window.setTimeout(connect, delay);
        }
        // No toast when max attempts reached - just stay in polling mode silently
        // The header indicator shows "Polling" which is sufficient feedback
      };
    } catch (e) {
      console.error('[WS] Failed to connect:', e);
    }
  }, [url, onEvent, onJobUpdate, reconnectInterval, maxReconnectAttempts, addToast, isConnected]);

  const sendMessage = useCallback((data: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    isConnected,
    lastEvent,
    toasts,
    dismissToast,
    sendMessage,
  };
}

export default useWebSocket;
