/**
 * CC Session Viewer Component (EPOCH 8 + EPOCH 9)
 * ================================================
 *
 * Real-time terminal output viewer for Claude Code sessions.
 *
 * Features (EPOCH 8):
 * - Real-time output streaming via WebSocket
 * - Session status indicators
 * - Manual intervention controls (send commands, restart, kill)
 * - Runtime and health metrics
 *
 * Features (EPOCH 9):
 * - Interactive mode toggle
 * - xterm.js terminal for interactive sessions
 * - Tool call viewer with granular event tracking
 * - Prompt input for multi-turn conversations
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Terminal,
  Square,
  RotateCcw,
  Send,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader,
  Copy,
  Maximize2,
  Minimize2,
  Zap,
  Heart,
  Play,
  PanelRightClose,
  PanelRightOpen,
  Sparkles,
} from 'lucide-react';
import type { CCSession, CCSessionStatus, CCSessionStreamMessage } from '../types';
import * as api from '../api/client';
import { InteractiveTerminal } from './InteractiveTerminal';
import { ToolCallViewer } from './ToolCallViewer';

// ==========================================================================
// Status Configuration
// ==========================================================================

const statusConfig: Record<CCSessionStatus, {
  icon: React.ReactNode;
  color: string;
  bg: string;
  label: string;
}> = {
  idle: {
    icon: <Clock className="w-4 h-4" />,
    color: 'text-gray-400',
    bg: 'bg-gray-500/20 border-gray-500/30',
    label: 'IDLE',
  },
  starting: {
    icon: <Loader className="w-4 h-4 animate-spin" />,
    color: 'text-blue-400',
    bg: 'bg-blue-500/20 border-blue-500/30',
    label: 'STARTING',
  },
  running: {
    icon: <Zap className="w-4 h-4" />,
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/20 border-cyan-500/30',
    label: 'RUNNING',
  },
  awaiting_input: {
    icon: <Sparkles className="w-4 h-4 animate-pulse" />,
    color: 'text-yellow-400',
    bg: 'bg-yellow-500/20 border-yellow-500/30',
    label: 'AWAITING INPUT',
  },
  stuck: {
    icon: <AlertTriangle className="w-4 h-4" />,
    color: 'text-orange-400',
    bg: 'bg-orange-500/20 border-orange-500/30',
    label: 'STUCK',
  },
  completed: {
    icon: <CheckCircle className="w-4 h-4" />,
    color: 'text-green-400',
    bg: 'bg-green-500/20 border-green-500/30',
    label: 'COMPLETED',
  },
  failed: {
    icon: <XCircle className="w-4 h-4" />,
    color: 'text-red-400',
    bg: 'bg-red-500/20 border-red-500/30',
    label: 'FAILED',
  },
  crashed: {
    icon: <XCircle className="w-4 h-4" />,
    color: 'text-red-400',
    bg: 'bg-red-500/20 border-red-500/30',
    label: 'CRASHED',
  },
  restarting: {
    icon: <RotateCcw className="w-4 h-4 animate-spin" />,
    color: 'text-purple-400',
    bg: 'bg-purple-500/20 border-purple-500/30',
    label: 'RESTARTING',
  },
};

// ==========================================================================
// Session Card Component
// ==========================================================================

interface SessionCardProps {
  session: CCSession;
  isSelected: boolean;
  onSelect: () => void;
  onRestart: () => void;
  onKill: () => void;
}

function SessionCard({ session, isSelected, onSelect, onRestart, onKill }: SessionCardProps) {
  const config = statusConfig[session.status] || statusConfig.idle;

  const runtimeDisplay = useMemo(() => {
    const mins = Math.floor(session.runtime_seconds / 60);
    const secs = Math.floor(session.runtime_seconds % 60);
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  }, [session.runtime_seconds]);

  const runtimePercent = useMemo(() => {
    return Math.min(100, (session.runtime_seconds / 60 / session.max_runtime_minutes) * 100);
  }, [session.runtime_seconds, session.max_runtime_minutes]);

  return (
    <div
      onClick={onSelect}
      className={`
        border rounded-lg p-4 cursor-pointer transition-all duration-200
        ${isSelected
          ? 'border-cyan-500/50 bg-cyan-500/10'
          : 'border-gray-700/50 bg-gray-800/30 hover:bg-gray-800/50'
        }
      `}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={config.color}>{config.icon}</span>
          <span className="font-mono text-sm text-gray-300">{session.session_name}</span>
          <span className={`text-xs px-2 py-0.5 rounded border ${config.bg} ${config.color}`}>
            {config.label}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {session.status === 'running' && (
            <button
              onClick={(e) => { e.stopPropagation(); onRestart(); }}
              className="p-1 text-gray-400 hover:text-yellow-400 transition-colors"
              title="Restart session"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          )}
          {session.status !== 'completed' && session.status !== 'failed' && (
            <button
              onClick={(e) => { e.stopPropagation(); onKill(); }}
              className="p-1 text-gray-400 hover:text-red-400 transition-colors"
              title="Kill session"
            >
              <Square className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Info */}
      <div className="space-y-2 text-xs text-gray-500">
        <div className="flex items-center gap-2">
          <Terminal className="w-3 h-3" />
          <span className="truncate">{session.working_directory}</span>
        </div>

        {session.status === 'running' && (
          <>
            <div className="flex items-center gap-2">
              <Clock className="w-3 h-3" />
              <span>{runtimeDisplay}</span>
              <span className="text-gray-600">/ {session.max_runtime_minutes}m</span>
            </div>
            {/* Runtime progress bar */}
            <div className="h-1 bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-1000 ${
                  runtimePercent > 80 ? 'bg-orange-500' : 'bg-cyan-500'
                }`}
                style={{ width: `${runtimePercent}%` }}
              />
            </div>
          </>
        )}

        <div className="flex items-center justify-between">
          <span>{session.output_lines} output lines</span>
          {session.restart_count > 0 && (
            <span className="text-orange-400">
              Restarts: {session.restart_count}/{session.max_restarts}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// Terminal Output Component
// ==========================================================================

interface TerminalOutputProps {
  sessionId: string;
  isStreaming: boolean;
}

function TerminalOutput({ sessionId, isStreaming }: TerminalOutputProps) {
  const [lines, setLines] = useState<Array<{ num: number; content: string; isError: boolean }>>([]);
  const [isExpanded, setIsExpanded] = useState(false);
  const outputRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');

  // Initial output fetch
  const { data: initialOutput } = useQuery({
    queryKey: ['ccSessionOutput', sessionId],
    queryFn: () => api.getCCSessionOutput(sessionId, 200),
    enabled: !!sessionId,
  });

  // Set initial lines
  useEffect(() => {
    if (initialOutput?.lines) {
      setLines(initialOutput.lines.map((content, idx) => ({
        num: idx + 1,
        content,
        isError: /error|fail|exception/i.test(content),
      })));
    }
  }, [initialOutput]);

  // WebSocket streaming
  useEffect(() => {
    if (!isStreaming || !sessionId) return;

    const url = api.getCCSessionStreamUrl(sessionId);
    setConnectionStatus('connecting');

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('connected');
    };

    ws.onmessage = (event) => {
      try {
        const msg: CCSessionStreamMessage = JSON.parse(event.data);

        if (msg.type === 'output' && msg.data.content !== undefined) {
          setLines(prev => [...prev, {
            num: msg.data.line_number || prev.length + 1,
            content: msg.data.content || '',
            isError: /error|fail|exception/i.test(msg.data.content || ''),
          }]);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
    };

    ws.onerror = () => {
      setConnectionStatus('disconnected');
    };

    return () => {
      ws.close();
    };
  }, [isStreaming, sessionId]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [lines]);

  const copyOutput = useCallback(() => {
    const text = lines.map(l => l.content).join('\n');
    navigator.clipboard.writeText(text);
  }, [lines]);

  return (
    <div className={`bg-gray-900 rounded-lg border border-gray-700/50 overflow-hidden transition-all duration-300 ${
      isExpanded ? 'fixed inset-4 z-50' : ''
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700/50 bg-gray-800/50">
        <div className="flex items-center gap-3">
          <Terminal className="w-4 h-4 text-cyan-400" />
          <span className="text-sm font-medium text-gray-300">Terminal Output</span>
          <span className="text-xs text-gray-500">{lines.length} lines</span>
          {connectionStatus === 'connected' && (
            <span className="flex items-center gap-1 text-xs text-green-400">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              Live
            </span>
          )}
          {connectionStatus === 'connecting' && (
            <span className="flex items-center gap-1 text-xs text-yellow-400">
              <Loader className="w-3 h-3 animate-spin" />
              Connecting
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={copyOutput}
            className="p-1 text-gray-400 hover:text-white transition-colors"
            title="Copy output"
          >
            <Copy className="w-4 h-4" />
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 text-gray-400 hover:text-white transition-colors"
            title={isExpanded ? 'Minimize' : 'Maximize'}
          >
            {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Output */}
      <div
        ref={outputRef}
        className={`p-4 font-mono text-xs overflow-y-auto ${isExpanded ? 'h-[calc(100%-48px)]' : 'h-80'}`}
      >
        {lines.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            Waiting for output...
          </div>
        ) : (
          lines.map((line, idx) => (
            <div
              key={idx}
              className={`flex gap-3 py-0.5 hover:bg-gray-800/50 ${
                line.isError ? 'text-red-400' : 'text-gray-300'
              }`}
            >
              <span className="text-gray-600 select-none w-8 text-right flex-shrink-0">
                {line.num}
              </span>
              <span className="whitespace-pre-wrap break-all">{line.content}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ==========================================================================
// Command Input Component
// ==========================================================================

interface CommandInputProps {
  sessionId: string;
  disabled: boolean;
}

function CommandInput({ sessionId, disabled }: CommandInputProps) {
  const [command, setCommand] = useState('');
  const queryClient = useQueryClient();

  const sendCommandMutation = useMutation({
    mutationFn: (cmd: string) => api.sendCCSessionCommand(sessionId, cmd),
    onSuccess: () => {
      setCommand('');
      queryClient.invalidateQueries({ queryKey: ['ccSessionOutput', sessionId] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (command.trim()) {
      sendCommandMutation.mutate(command.trim());
    }
  };

  const quickCommands = ['continue', 'yes', 'no', 'exit'];

  return (
    <div className="space-y-2">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          placeholder="Type a command..."
          disabled={disabled}
          className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || !command.trim() || sendCommandMutation.isPending}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
        >
          <Send className="w-4 h-4" />
          Send
        </button>
      </form>

      {/* Quick commands */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500">Quick:</span>
        {quickCommands.map((cmd) => (
          <button
            key={cmd}
            onClick={() => sendCommandMutation.mutate(cmd)}
            disabled={disabled}
            className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-gray-300 rounded transition-colors"
          >
            {cmd}
          </button>
        ))}
      </div>
    </div>
  );
}

// ==========================================================================
// Main CC Session Viewer Component
// ==========================================================================

interface CCSessionViewerProps {
  pipelineRunId?: string;
}

export function CCSessionViewer({ pipelineRunId }: CCSessionViewerProps) {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [showEventsPanel, setShowEventsPanel] = useState(false);
  const [isCreatingInteractive, setIsCreatingInteractive] = useState(false);
  const queryClient = useQueryClient();

  // Fetch sessions
  const { data: sessions = [], isLoading } = useQuery({
    queryKey: ['ccSessions', pipelineRunId],
    queryFn: () => api.getCCSessions(undefined, pipelineRunId),
    refetchInterval: 5000,
  });

  // Fetch events for selected interactive session
  const { data: sessionEvents } = useQuery({
    queryKey: ['ccSessionEvents', selectedSessionId],
    queryFn: () => selectedSessionId ? api.getCCSessionEvents(selectedSessionId) : null,
    enabled: !!selectedSessionId && showEventsPanel,
    refetchInterval: 2000,
  });

  // Mutations
  const restartMutation = useMutation({
    mutationFn: api.restartCCSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ccSessions'] });
    },
  });

  const killMutation = useMutation({
    mutationFn: api.killCCSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ccSessions'] });
    },
  });

  // Create interactive session mutation
  const createInteractiveMutation = useMutation({
    mutationFn: (workingDirectory: string) => api.createInteractiveSession(workingDirectory),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['ccSessions'] });
      setSelectedSessionId(data.session_id);
      setIsCreatingInteractive(false);
    },
    onError: () => {
      setIsCreatingInteractive(false);
    },
  });

  // Send prompt to interactive session
  const sendPromptMutation = useMutation({
    mutationFn: ({ sessionId, prompt }: { sessionId: string; prompt: string }) =>
      api.sendInteractivePrompt(sessionId, prompt),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ccSessions'] });
    },
  });

  // Stop interactive session
  const stopInteractiveMutation = useMutation({
    mutationFn: (sessionId: string) => api.stopInteractiveSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ccSessions'] });
    },
  });

  // Get selected session
  const selectedSession = useMemo(() => {
    return sessions.find(s => s.session_id === selectedSessionId);
  }, [sessions, selectedSessionId]);

  // Auto-select first running session
  useEffect(() => {
    if (!selectedSessionId && sessions.length > 0) {
      const runningSession = sessions.find(s => s.status === 'running');
      setSelectedSessionId(runningSession?.session_id || sessions[0].session_id);
    }
  }, [sessions, selectedSessionId]);

  // Stats
  const stats = useMemo(() => ({
    running: sessions.filter(s => s.status === 'running').length,
    completed: sessions.filter(s => s.status === 'completed').length,
    failed: sessions.filter(s => s.status === 'failed' || s.status === 'crashed').length,
  }), [sessions]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader className="w-8 h-8 text-cyan-400 animate-spin" />
      </div>
    );
  }

  // Check if selected session is interactive
  const isInteractiveSession = selectedSession && (selectedSession as any).mode === 'interactive';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Terminal className="w-6 h-6 text-cyan-400" />
          <h2 className="text-xl font-semibold text-white">CC Sessions</h2>
          <span className="text-sm text-gray-500">EPOCH 9</span>
        </div>
        <div className="flex items-center gap-4">
          {/* New Interactive Session Button */}
          <button
            onClick={() => setIsCreatingInteractive(true)}
            className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Play className="w-4 h-4" />
            New Interactive
          </button>
          <div className="flex items-center gap-2">
            <Heart className="w-4 h-4 text-green-400" />
            <span className="text-sm text-gray-400">{stats.running} running</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-400" />
            <span className="text-sm text-gray-400">{stats.completed} completed</span>
          </div>
          {stats.failed > 0 && (
            <div className="flex items-center gap-2">
              <XCircle className="w-4 h-4 text-red-400" />
              <span className="text-sm text-red-400">{stats.failed} failed</span>
            </div>
          )}
        </div>
      </div>

      {/* Create Interactive Session Modal */}
      {isCreatingInteractive && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">New Interactive Session</h3>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const formData = new FormData(e.currentTarget);
                const dir = formData.get('workingDirectory') as string;
                if (dir) createInteractiveMutation.mutate(dir);
              }}
            >
              <div className="mb-4">
                <label className="block text-sm text-gray-400 mb-2">Working Directory</label>
                <input
                  type="text"
                  name="workingDirectory"
                  defaultValue="D:\\Projects"
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                  placeholder="Enter working directory"
                />
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsCreatingInteractive(false)}
                  className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createInteractiveMutation.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-600 text-white font-medium rounded-lg transition-colors"
                >
                  {createInteractiveMutation.isPending && (
                    <Loader className="w-4 h-4 animate-spin" />
                  )}
                  Create Session
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {sessions.length === 0 ? (
        <div className="text-center py-12 bg-gray-800/30 rounded-xl border border-gray-700/50">
          <Terminal className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400">No CC sessions active</p>
          <p className="text-sm text-gray-500 mt-2">
            Sessions will appear here when the pipeline orchestrator spawns Claude Code agents
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sessions List */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
              Active Sessions
            </h3>
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
              {sessions.map((session) => (
                <SessionCard
                  key={session.session_id}
                  session={session}
                  isSelected={session.session_id === selectedSessionId}
                  onSelect={() => setSelectedSessionId(session.session_id)}
                  onRestart={() => restartMutation.mutate(session.session_id)}
                  onKill={() => killMutation.mutate(session.session_id)}
                />
              ))}
            </div>
          </div>

          {/* Terminal & Controls */}
          <div className={`${showEventsPanel ? 'lg:col-span-1' : 'lg:col-span-2'} space-y-4`}>
            {selectedSession ? (
              <>
                {/* Session info header */}
                <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-lg font-medium text-white">
                          {selectedSession.session_name}
                        </h3>
                        {isInteractiveSession && (
                          <span className="text-xs px-2 py-0.5 bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded">
                            INTERACTIVE
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-400 font-mono mt-1">
                        {selectedSession.working_directory}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {/* Events panel toggle */}
                      <button
                        onClick={() => setShowEventsPanel(!showEventsPanel)}
                        className={`p-2 rounded-lg transition-colors ${
                          showEventsPanel
                            ? 'bg-cyan-500/20 text-cyan-400'
                            : 'bg-gray-700 text-gray-400 hover:text-white'
                        }`}
                        title={showEventsPanel ? 'Hide Events' : 'Show Events'}
                      >
                        {showEventsPanel ? (
                          <PanelRightClose className="w-5 h-5" />
                        ) : (
                          <PanelRightOpen className="w-5 h-5" />
                        )}
                      </button>
                      {!isInteractiveSession && (
                        <div className="text-right">
                          <p className="text-sm text-gray-500">Attach:</p>
                          <code className="text-xs text-cyan-400 bg-gray-900 px-2 py-1 rounded">
                            {selectedSession.attach_command}
                          </code>
                        </div>
                      )}
                    </div>
                  </div>

                  {selectedSession.task_prompt && (
                    <div className="mt-4 pt-4 border-t border-gray-700/50">
                      <p className="text-xs text-gray-500 mb-1">Task Prompt:</p>
                      <p className="text-sm text-gray-300 line-clamp-3">
                        {selectedSession.task_prompt}
                      </p>
                    </div>
                  )}
                </div>

                {/* Interactive Terminal (EPOCH 9) or Headless Output (EPOCH 8) */}
                {isInteractiveSession ? (
                  <div className="h-96">
                    <InteractiveTerminal
                      sessionId={selectedSession.session_id}
                      status={selectedSession.status}
                      onSendPrompt={(prompt) =>
                        sendPromptMutation.mutate({
                          sessionId: selectedSession.session_id,
                          prompt,
                        })
                      }
                      onSendInput={(text) =>
                        api.sendInteractiveInput(selectedSession.session_id, text)
                      }
                      onStop={() => stopInteractiveMutation.mutate(selectedSession.session_id)}
                      onKill={() => killMutation.mutate(selectedSession.session_id)}
                    />
                  </div>
                ) : (
                  <>
                    {/* Headless terminal output */}
                    <TerminalOutput
                      sessionId={selectedSession.session_id}
                      isStreaming={selectedSession.status === 'running'}
                    />

                    {/* Command input for headless */}
                    {selectedSession.status === 'running' && (
                      <CommandInput
                        sessionId={selectedSession.session_id}
                        disabled={selectedSession.status !== 'running'}
                      />
                    )}
                  </>
                )}
              </>
            ) : (
              <div className="flex items-center justify-center h-64 bg-gray-800/30 rounded-xl border border-gray-700/50">
                <p className="text-gray-500">Select a session to view details</p>
              </div>
            )}
          </div>

          {/* Events Panel (EPOCH 9) */}
          {showEventsPanel && selectedSession && (
            <div className="h-[600px]">
              <ToolCallViewer
                events={sessionEvents?.events || []}
                toolSummary={sessionEvents?.tool_summary || {}}
                errorSummary={sessionEvents?.error_summary || {}}
                totalEvents={sessionEvents?.total_events || 0}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default CCSessionViewer;
