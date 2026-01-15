/**
 * Pipeline WebSocket Hook
 * =======================
 *
 * Subscribes to real-time pipeline events from Nerve Center.
 * Events: stage_started, stage_completed, handoff_created, escalation, guardrail violations
 */

import { useEffect, useRef, useState, useCallback } from 'react';

// ==========================================================================
// Types
// ==========================================================================

export type PipelineEventType =
  | 'stage_started'
  | 'stage_completed'
  | 'stage_failed'
  | 'handoff_created'
  | 'handoff_rejected'
  | 'escalation_triggered'
  | 'neural_ralph_attempt'
  | 'neural_ralph_success'
  | 'neural_ralph_failed'
  | 'po_review_required'
  | 'po_approved'
  | 'po_rejected'
  | 'po_changes_requested'
  | 'guardrail_violation'
  | 'resource_allocated'
  | 'resource_released'
  | 'pipeline_started'
  | 'pipeline_completed'
  | 'pipeline_failed'
  | 'health_check_passed'
  | 'health_check_failed'
  | 'connected'
  | 'disconnected';

export interface PipelineEvent {
  id: string;
  timestamp: string;
  category: 'pipeline';
  event_type: PipelineEventType;
  severity: 'debug' | 'info' | 'warning' | 'error' | 'critical' | 'success';
  message: string;
  session_id?: string;
  pipeline_run_id?: string;
  task_id?: string;
  details?: {
    stage?: string;
    from_stage?: string;
    to_stage?: string;
    trust_score?: number;
    escalation_level?: string;
    error?: string;
    rule_name?: string;
    resource_type?: string;
    port?: number;
    [key: string]: unknown;
  };
}

export interface PipelineToast {
  id: string;
  type: 'success' | 'warning' | 'error' | 'info';
  title: string;
  message: string;
  timestamp: Date;
}

interface UsePipelineSocketOptions {
  wsUrl?: string;
  onEvent?: (event: PipelineEvent) => void;
  onStageChange?: (runId: string, stage: string) => void;
  onEscalation?: (runId: string, level: string) => void;
  onPOReviewRequired?: (runId: string) => void;
  onGuardrailViolation?: (violation: PipelineEvent) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

interface UsePipelineSocketReturn {
  isConnected: boolean;
  lastEvent: PipelineEvent | null;
  events: PipelineEvent[];
  toasts: PipelineToast[];
  dismissToast: (id: string) => void;
  clearEvents: () => void;
}

// ==========================================================================
// Hook Implementation
// ==========================================================================

export function usePipelineSocket({
  wsUrl = 'ws://localhost:8000/api/v1/nerve-center/ws',
  onEvent,
  onStageChange,
  onEscalation,
  onPOReviewRequired,
  onGuardrailViolation,
  reconnectInterval = 3000,
  maxReconnectAttempts = 10,
}: UsePipelineSocketOptions = {}): UsePipelineSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<PipelineEvent | null>(null);
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [toasts, setToasts] = useState<PipelineToast[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pingIntervalRef = useRef<number | null>(null);

  // Add toast notification
  const addToast = useCallback((toast: Omit<PipelineToast, 'id' | 'timestamp'>) => {
    const newToast: PipelineToast = {
      ...toast,
      id: `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      timestamp: new Date(),
    };
    setToasts((prev) => [newToast, ...prev].slice(0, 5));

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== newToast.id));
    }, 5000);
  }, []);

  // Dismiss toast manually
  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Clear all events
  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  // Process incoming event
  const processEvent = useCallback(
    (event: PipelineEvent) => {
      // Update state
      setLastEvent(event);
      setEvents((prev) => [...prev.slice(-99), event]);

      // Call general event handler
      onEvent?.(event);

      // Handle specific event types
      switch (event.event_type) {
        case 'stage_started':
        case 'stage_completed':
          if (event.pipeline_run_id && event.details?.stage) {
            onStageChange?.(event.pipeline_run_id, event.details.stage);
          }
          break;

        case 'escalation_triggered':
          if (event.pipeline_run_id && event.details?.escalation_level) {
            onEscalation?.(event.pipeline_run_id, event.details.escalation_level);
            addToast({
              type: 'warning',
              title: 'Escalation Triggered',
              message: `Pipeline escalated to ${event.details.escalation_level}`,
            });
          }
          break;

        case 'po_review_required':
          if (event.pipeline_run_id) {
            onPOReviewRequired?.(event.pipeline_run_id);
            addToast({
              type: 'info',
              title: 'PO Review Required',
              message: event.message || 'A task requires PO review',
            });
          }
          break;

        case 'guardrail_violation':
          onGuardrailViolation?.(event);
          addToast({
            type: 'error',
            title: 'Guardrail Violation',
            message: event.details?.rule_name || 'A guardrail rule was violated',
          });
          break;

        case 'pipeline_completed':
          addToast({
            type: 'success',
            title: 'Pipeline Completed',
            message: event.message || 'Pipeline run completed successfully',
          });
          break;

        case 'pipeline_failed':
          addToast({
            type: 'error',
            title: 'Pipeline Failed',
            message: event.details?.error || 'Pipeline run failed',
          });
          break;

        case 'neural_ralph_success':
          addToast({
            type: 'success',
            title: 'Auto-Correction Success',
            message: 'Neural Ralph fixed the issue automatically',
          });
          break;

        case 'neural_ralph_failed':
          addToast({
            type: 'warning',
            title: 'Auto-Correction Failed',
            message: 'Neural Ralph could not fix the issue',
          });
          break;
      }
    },
    [onEvent, onStageChange, onEscalation, onPOReviewRequired, onGuardrailViolation, addToast]
  );

  // WebSocket connection
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        console.log('[PipelineSocket] Connected to Nerve Center');

        // Subscribe to pipeline events
        ws.send(
          JSON.stringify({
            type: 'subscribe',
            payload: {
              categories: ['pipeline'],
            },
          })
        );

        // Ping to keep connection alive
        pingIntervalRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 25000);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === 'pong') return;

          if (msg.type === 'event' && msg.payload?.category === 'pipeline') {
            processEvent(msg.payload as PipelineEvent);
          }
        } catch (e) {
          console.warn('[PipelineSocket] Failed to parse message:', e);
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

        // Reconnect with exponential backoff
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = reconnectInterval * Math.pow(1.5, reconnectAttemptsRef.current);
          reconnectAttemptsRef.current++;
          console.log(
            `[PipelineSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`
          );
          reconnectTimeoutRef.current = window.setTimeout(connect, delay);
        }
      };
    } catch (e) {
      console.error('[PipelineSocket] Failed to connect:', e);
    }
  }, [wsUrl, processEvent, reconnectInterval, maxReconnectAttempts]);

  // Connect on mount
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
    events,
    toasts,
    dismissToast,
    clearEvents,
  };
}

export default usePipelineSocket;
