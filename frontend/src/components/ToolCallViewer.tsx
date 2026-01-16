/**
 * ToolCallViewer Component (EPOCH 9)
 *
 * Displays parsed tool call events from interactive CC sessions.
 * Features:
 * - Expandable tool call details
 * - Color-coded event types
 * - Tool input/output display
 * - Duration tracking
 * - Error highlighting
 */

import { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  FileText,
  Terminal,
  Pencil,
  Search,
  AlertCircle,
  Clock,
  Brain,
  CheckCircle,
  XCircle,
} from 'lucide-react';

interface SessionEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  tool_name?: string;
  tool_input?: Record<string, unknown>;
  tool_output?: string;
  tool_duration_ms?: number;
  content?: string;
  is_error: boolean;
  error_type?: string;
  line_start?: number;
  line_end?: number;
}

interface ToolCallViewerProps {
  events: SessionEvent[];
  toolSummary: Record<string, number>;
  errorSummary: Record<string, number>;
  totalEvents: number;
}

// Tool icons mapping
const toolIcons: Record<string, React.ReactNode> = {
  Read: <FileText className="w-4 h-4 text-blue-400" />,
  Write: <Pencil className="w-4 h-4 text-green-400" />,
  Edit: <Pencil className="w-4 h-4 text-yellow-400" />,
  Bash: <Terminal className="w-4 h-4 text-purple-400" />,
  Grep: <Search className="w-4 h-4 text-cyan-400" />,
  Glob: <Search className="w-4 h-4 text-cyan-400" />,
  Task: <Brain className="w-4 h-4 text-pink-400" />,
};

// Event type colors
const eventTypeColors: Record<string, string> = {
  tool_call_start: 'border-l-blue-500 bg-blue-500/10',
  tool_call_end: 'border-l-green-500 bg-green-500/10',
  thinking: 'border-l-gray-500 bg-gray-500/10',
  decision: 'border-l-yellow-500 bg-yellow-500/10',
  error: 'border-l-red-500 bg-red-500/10',
  prompt_sent: 'border-l-purple-500 bg-purple-500/10',
  response_start: 'border-l-indigo-500 bg-indigo-500/10',
  response_end: 'border-l-indigo-500 bg-indigo-500/10',
  file_read: 'border-l-blue-400 bg-blue-400/10',
  file_write: 'border-l-green-400 bg-green-400/10',
  bash_command: 'border-l-purple-400 bg-purple-400/10',
};

function EventCard({ event, isExpanded, onToggle }: {
  event: SessionEvent;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const colorClass = eventTypeColors[event.event_type] || 'border-l-gray-500';
  const timestamp = new Date(event.timestamp).toLocaleTimeString();

  return (
    <div
      className={`border-l-4 rounded-r-lg mb-2 ${colorClass} ${
        event.is_error ? 'border-l-red-500 bg-red-500/10' : ''
      }`}
    >
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 text-left hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          )}

          {/* Tool/Event icon */}
          {event.tool_name ? (
            toolIcons[event.tool_name] || <Terminal className="w-4 h-4 text-gray-400" />
          ) : event.is_error ? (
            <AlertCircle className="w-4 h-4 text-red-400" />
          ) : event.event_type === 'thinking' ? (
            <Brain className="w-4 h-4 text-gray-400" />
          ) : (
            <CheckCircle className="w-4 h-4 text-gray-400" />
          )}

          {/* Title */}
          <div>
            <span className="font-medium text-gray-200">
              {event.tool_name || event.event_type.replace(/_/g, ' ')}
            </span>
            {event.tool_duration_ms && (
              <span className="ml-2 text-xs text-gray-500">
                <Clock className="inline w-3 h-3 mr-1" />
                {event.tool_duration_ms}ms
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {event.is_error && (
            <span className="text-xs text-red-400 bg-red-500/20 px-2 py-0.5 rounded">
              {event.error_type || 'Error'}
            </span>
          )}
          <span className="text-xs text-gray-500">{timestamp}</span>
        </div>
      </button>

      {/* Expanded details */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-3">
          {/* Tool input */}
          {event.tool_input && Object.keys(event.tool_input).length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-1">Input:</div>
              <pre className="text-xs bg-black/30 p-2 rounded overflow-x-auto max-h-40">
                {JSON.stringify(event.tool_input, null, 2)}
              </pre>
            </div>
          )}

          {/* Tool output */}
          {event.tool_output && (
            <div>
              <div className="text-xs text-gray-500 mb-1">Output:</div>
              <pre className="text-xs bg-black/30 p-2 rounded overflow-x-auto max-h-40 whitespace-pre-wrap">
                {event.tool_output}
              </pre>
            </div>
          )}

          {/* Content (for thinking/decision events) */}
          {event.content && !event.tool_output && (
            <div>
              <div className="text-xs text-gray-500 mb-1">Content:</div>
              <div className="text-sm text-gray-300 bg-black/30 p-2 rounded whitespace-pre-wrap">
                {event.content}
              </div>
            </div>
          )}

          {/* Line numbers */}
          {event.line_start !== undefined && (
            <div className="text-xs text-gray-500">
              Lines: {event.line_start}
              {event.line_end && event.line_end !== event.line_start
                ? ` - ${event.line_end}`
                : ''}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ToolCallViewer({
  events,
  toolSummary,
  errorSummary,
  totalEvents,
}: ToolCallViewerProps) {
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<string>('all');

  const toggleEvent = (eventId: string) => {
    setExpandedEvents((prev) => {
      const next = new Set(prev);
      if (next.has(eventId)) {
        next.delete(eventId);
      } else {
        next.add(eventId);
      }
      return next;
    });
  };

  // Filter events
  const filteredEvents = events.filter((event) => {
    if (filter === 'all') return true;
    if (filter === 'tools') return event.event_type.includes('tool_call');
    if (filter === 'errors') return event.is_error;
    if (filter === 'thinking') return event.event_type === 'thinking';
    return true;
  });

  return (
    <div className="flex flex-col h-full bg-[#1e1e2e] rounded-lg border border-gray-700">
      {/* Header with summary */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-200">Events</h3>
          <span className="text-sm text-gray-500">{totalEvents} total</span>
        </div>

        {/* Tool summary pills */}
        {Object.keys(toolSummary).length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {Object.entries(toolSummary).map(([tool, count]) => (
              <span
                key={tool}
                className="flex items-center gap-1 text-xs bg-gray-800 px-2 py-1 rounded"
              >
                {toolIcons[tool] || <Terminal className="w-3 h-3" />}
                <span className="text-gray-300">{tool}</span>
                <span className="text-gray-500">×{count}</span>
              </span>
            ))}
          </div>
        )}

        {/* Error summary */}
        {Object.keys(errorSummary).length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {Object.entries(errorSummary).map(([errorType, count]) => (
              <span
                key={errorType}
                className="flex items-center gap-1 text-xs bg-red-900/30 text-red-400 px-2 py-1 rounded"
              >
                <XCircle className="w-3 h-3" />
                <span>{errorType}</span>
                <span className="text-red-500">×{count}</span>
              </span>
            ))}
          </div>
        )}

        {/* Filter tabs */}
        <div className="flex gap-2">
          {['all', 'tools', 'thinking', 'errors'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-xs rounded transition-colors ${
                filter === f
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Events list */}
      <div className="flex-1 overflow-y-auto p-4">
        {filteredEvents.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <Brain className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No events to display</p>
            <p className="text-xs mt-1">Events will appear as CC processes your request</p>
          </div>
        ) : (
          filteredEvents.map((event) => (
            <EventCard
              key={event.event_id}
              event={event}
              isExpanded={expandedEvents.has(event.event_id)}
              onToggle={() => toggleEvent(event.event_id)}
            />
          ))
        )}
      </div>
    </div>
  );
}

export default ToolCallViewer;
