/**
 * NH Nerve Center - Real-time Operations Dashboard
 * ==================================================
 * 
 * Full transparency into every operation NH performs.
 * Shows events at the most granular level in real-time.
 */

import { useState, useEffect, useRef } from 'react';
import {
  Activity,
  Brain,
  Cpu,
  Eye,
  EyeOff,
  FileCode,
  Filter,
  Layers,
  Loader2,
  Pause,
  Search,
  Zap,
  ChevronRight,
  ChevronDown,
  Clock,
  DollarSign,
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  Info,
  Bug,
  Database,
  Globe,
  User,
  Sparkles,
  Hash,
  Maximize2,
  Minimize2,
  Circle,
} from 'lucide-react';

// ==========================================================================
// Types
// ==========================================================================

type EventCategory = 'system' | 'agent' | 'file' | 'api' | 'database' | 'user' | 'analysis' | 'generation';
type Severity = 'debug' | 'info' | 'warning' | 'error' | 'critical' | 'success';

interface NHEvent {
  id: string;
  timestamp: string;
  category: EventCategory;
  event_type: string;
  severity: Severity;
  session_id?: string;
  task_id?: string;
  agent_id?: string;
  correlation_id?: string;
  message: string;
  details?: Record<string, any>;
  progress_current?: number;
  progress_total?: number;
  progress_percent?: number;
  duration_ms?: number;
  tokens_input?: number;
  tokens_output?: number;
  cost_usd?: number;
}

interface AgentState {
  id: string;
  name: string;
  role: string;
  status: 'idle' | 'thinking' | 'acting' | 'waiting' | 'error';
  current_thought?: string;
  current_action?: string;
  tasks_completed: number;
  tasks_failed: number;
  total_tokens: number;
  total_cost_usd: number;
}

interface TaskState {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress_percent: number;
  current_step?: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  error?: string;
  sub_tasks: TaskState[];
}

interface SessionState {
  id: string;
  name: string;
  status: 'initializing' | 'running' | 'paused' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  progress_percent: number;
  agents: Record<string, AgentState>;
  root_tasks: TaskState[];
  total_tokens_input: number;
  total_tokens_output: number;
  total_cost_usd: number;
  files_read: string[];
  files_written: string[];
  files_created: string[];
}

// ==========================================================================
// Constants
// ==========================================================================

const CATEGORY_ICONS: Record<EventCategory, React.ReactNode> = {
  system: <Cpu size={12} />,
  agent: <Brain size={12} />,
  file: <FileCode size={12} />,
  api: <Globe size={12} />,
  database: <Database size={12} />,
  user: <User size={12} />,
  analysis: <Search size={12} />,
  generation: <Sparkles size={12} />,
};

const CATEGORY_COLORS: Record<EventCategory, string> = {
  system: 'text-gray-400 bg-gray-400/10',
  agent: 'text-purple-400 bg-purple-400/10',
  file: 'text-blue-400 bg-blue-400/10',
  api: 'text-green-400 bg-green-400/10',
  database: 'text-yellow-400 bg-yellow-400/10',
  user: 'text-cyan-400 bg-cyan-400/10',
  analysis: 'text-orange-400 bg-orange-400/10',
  generation: 'text-pink-400 bg-pink-400/10',
};

const SEVERITY_ICONS: Record<Severity, React.ReactNode> = {
  debug: <Bug size={12} className="text-gray-500" />,
  info: <Info size={12} className="text-blue-400" />,
  warning: <AlertTriangle size={12} className="text-yellow-500" />,
  error: <AlertCircle size={12} className="text-red-500" />,
  critical: <AlertCircle size={12} className="text-red-600" />,
  success: <CheckCircle size={12} className="text-green-500" />,
};

const SEVERITY_COLORS: Record<Severity, string> = {
  debug: 'text-gray-500',
  info: 'text-gray-300',
  warning: 'text-yellow-400',
  error: 'text-red-400',
  critical: 'text-red-500 font-bold',
  success: 'text-green-400',
};

// ==========================================================================
// Agent Card Component
// ==========================================================================

interface AgentCardProps {
  agent: AgentState;
  isExpanded: boolean;
  onToggle: () => void;
}

function AgentCard({ agent, isExpanded, onToggle }: AgentCardProps) {
  const statusColors = {
    idle: 'bg-gray-500',
    thinking: 'bg-purple-500 animate-pulse',
    acting: 'bg-blue-500 animate-pulse',
    waiting: 'bg-yellow-500',
    error: 'bg-red-500',
  };

  return (
    <div className={`rounded-lg border ${
      agent.status === 'thinking' || agent.status === 'acting' 
        ? 'border-purple-500/50 bg-purple-500/5' 
        : 'border-gray-700 bg-gray-900'
    }`}>
      <div 
        className="flex items-center gap-3 p-3 cursor-pointer"
        onClick={onToggle}
      >
        {/* Status Indicator */}
        <div className={`w-2 h-2 rounded-full ${statusColors[agent.status]}`} />
        
        {/* Agent Icon */}
        <div className="p-2 rounded-lg bg-purple-500/20">
          <Brain size={16} className="text-purple-400" />
        </div>
        
        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-white">{agent.name}</span>
            <span className="text-xs text-gray-500">{agent.role}</span>
          </div>
          {(agent.current_thought || agent.current_action) && (
            <p className="text-xs text-gray-400 truncate mt-0.5">
              {agent.status === 'thinking' ? '💭 ' : '⚡ '}
              {agent.current_thought || agent.current_action}
            </p>
          )}
        </div>
        
        {/* Stats */}
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <CheckCircle size={12} className="text-green-500" />
            {agent.tasks_completed}
          </span>
          {agent.tasks_failed > 0 && (
            <span className="flex items-center gap-1 text-red-400">
              <AlertCircle size={12} />
              {agent.tasks_failed}
            </span>
          )}
          <span className="flex items-center gap-1">
            <Hash size={12} />
            {agent.total_tokens.toLocaleString()}
          </span>
        </div>
        
        {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </div>
      
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-gray-800 mt-2 pt-2">
          <div className="grid grid-cols-3 gap-4 text-xs">
            <div>
              <span className="text-gray-500">Status</span>
              <p className="text-white capitalize">{agent.status}</p>
            </div>
            <div>
              <span className="text-gray-500">Total Tokens</span>
              <p className="text-white">{agent.total_tokens.toLocaleString()}</p>
            </div>
            <div>
              <span className="text-gray-500">Cost</span>
              <p className="text-white">${agent.total_cost_usd.toFixed(4)}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ==========================================================================
// Task Tree Component
// ==========================================================================

interface TaskNodeProps {
  task: TaskState;
  depth: number;
}

function TaskNode({ task, depth }: TaskNodeProps) {
  const [expanded, setExpanded] = useState(task.status === 'running');
  
  const statusIcons = {
    pending: <Circle size={14} className="text-gray-500" />,
    running: <Loader2 size={14} className="text-blue-500 animate-spin" />,
    completed: <CheckCircle size={14} className="text-green-500" />,
    failed: <AlertCircle size={14} className="text-red-500" />,
  };

  return (
    <div className={`${depth > 0 ? 'ml-4 border-l border-gray-700 pl-3' : ''}`}>
      <div 
        className={`flex items-center gap-2 py-1.5 px-2 rounded cursor-pointer hover:bg-gray-800/50 ${
          task.status === 'running' ? 'bg-blue-500/10' : ''
        }`}
        onClick={() => setExpanded(!expanded)}
      >
        {task.sub_tasks.length > 0 && (
          expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />
        )}
        {statusIcons[task.status]}
        
        <span className={`text-sm flex-1 ${
          task.status === 'running' ? 'text-white font-medium' : 'text-gray-300'
        }`}>
          {task.name}
        </span>
        
        {task.status === 'running' && task.progress_percent > 0 && (
          <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-500 transition-all"
              style={{ width: `${task.progress_percent}%` }}
            />
          </div>
        )}
        
        {task.duration_ms && (
          <span className="text-xs text-gray-500">
            {(task.duration_ms / 1000).toFixed(1)}s
          </span>
        )}
      </div>
      
      {task.current_step && task.status === 'running' && (
        <div className="ml-8 text-xs text-gray-500 py-1">
          ↳ {task.current_step}
        </div>
      )}
      
      {expanded && task.sub_tasks.map(subtask => (
        <TaskNode key={subtask.id} task={subtask} depth={depth + 1} />
      ))}
    </div>
  );
}

// ==========================================================================
// Event Stream Component
// ==========================================================================

interface EventStreamProps {
  events: NHEvent[];
  filters: {
    categories: Set<EventCategory>;
    severities: Set<Severity>;
    searchQuery: string;
  };
  autoScroll: boolean;
  onToggleAutoScroll: () => void;
}

function EventStream({ events, filters, autoScroll, onToggleAutoScroll }: EventStreamProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Filter events
  const filteredEvents = events.filter(event => {
    if (filters.categories.size > 0 && !filters.categories.has(event.category)) {
      return false;
    }
    if (filters.severities.size > 0 && !filters.severities.has(event.severity)) {
      return false;
    }
    if (filters.searchQuery && !event.message.toLowerCase().includes(filters.searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  });
  
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [filteredEvents, autoScroll]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-900 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Activity size={14} className="text-green-400" />
          <span className="text-sm font-medium">Event Stream</span>
          <span className="text-xs text-gray-500">
            ({filteredEvents.length}/{events.length})
          </span>
        </div>
        <button
          onClick={onToggleAutoScroll}
          className={`p-1 rounded ${autoScroll ? 'text-green-400' : 'text-gray-500'}`}
          title={autoScroll ? 'Auto-scroll ON' : 'Auto-scroll OFF'}
        >
          {autoScroll ? <Eye size={14} /> : <EyeOff size={14} />}
        </button>
      </div>
      
      {/* Events */}
      <div 
        ref={containerRef}
        className="flex-1 overflow-y-auto font-mono text-xs"
      >
        {filteredEvents.map((event) => (
          <div 
            key={event.id}
            className="flex items-start gap-2 px-2 py-1 hover:bg-gray-800/50 border-b border-gray-800/50"
          >
            {/* Timestamp */}
            <span className="text-gray-600 whitespace-nowrap w-20 flex-shrink-0">
              {new Date(event.timestamp).toLocaleTimeString('en-US', { 
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                fractionalSecondDigits: 3
              })}
            </span>
            
            {/* Category Badge */}
            <span className={`px-1.5 py-0.5 rounded text-[10px] flex items-center gap-1 ${CATEGORY_COLORS[event.category]}`}>
              {CATEGORY_ICONS[event.category]}
              {event.category}
            </span>
            
            {/* Severity */}
            <span className="flex-shrink-0">
              {SEVERITY_ICONS[event.severity]}
            </span>
            
            {/* Message */}
            <span className={`flex-1 ${SEVERITY_COLORS[event.severity]}`}>
              {event.message}
            </span>
            
            {/* Extra info */}
            {event.tokens_output && (
              <span className="text-gray-500 flex items-center gap-1">
                <Hash size={10} />
                {event.tokens_output}
              </span>
            )}
            {event.duration_ms && (
              <span className="text-gray-500 flex items-center gap-1">
                <Clock size={10} />
                {event.duration_ms.toFixed(0)}ms
              </span>
            )}
            {event.cost_usd && (
              <span className="text-gray-500 flex items-center gap-1">
                <DollarSign size={10} />
                {event.cost_usd.toFixed(4)}
              </span>
            )}
          </div>
        ))}
        
        {filteredEvents.length === 0 && (
          <div className="flex items-center justify-center h-32 text-gray-500">
            No events match filters
          </div>
        )}
      </div>
    </div>
  );
}

// ==========================================================================
// Stats Panel Component
// ==========================================================================

interface StatsPanelProps {
  session: SessionState;
}

function StatsPanel({ session }: StatsPanelProps) {
  return (
    <div className="grid grid-cols-6 gap-2 p-3 bg-gray-900 border-b border-gray-800">
      {/* Status */}
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${
          session.status === 'running' ? 'bg-green-500 animate-pulse' :
          session.status === 'completed' ? 'bg-green-500' :
          session.status === 'failed' ? 'bg-red-500' :
          session.status === 'paused' ? 'bg-yellow-500' :
          'bg-gray-500'
        }`} />
        <div>
          <div className="text-xs text-gray-500">Status</div>
          <div className="text-sm font-medium capitalize">{session.status}</div>
        </div>
      </div>
      
      {/* Progress */}
      <div>
        <div className="text-xs text-gray-500">Progress</div>
        <div className="text-sm font-medium">
          {session.completed_tasks}/{session.total_tasks} tasks
        </div>
        <div className="w-full h-1 bg-gray-700 rounded-full mt-1">
          <div 
            className="h-full bg-blue-500 rounded-full transition-all"
            style={{ width: `${session.progress_percent}%` }}
          />
        </div>
      </div>
      
      {/* Tokens In */}
      <div>
        <div className="text-xs text-gray-500">Tokens In</div>
        <div className="text-sm font-medium text-blue-400">
          {session.total_tokens_input.toLocaleString()}
        </div>
      </div>
      
      {/* Tokens Out */}
      <div>
        <div className="text-xs text-gray-500">Tokens Out</div>
        <div className="text-sm font-medium text-green-400">
          {session.total_tokens_output.toLocaleString()}
        </div>
      </div>
      
      {/* Cost */}
      <div>
        <div className="text-xs text-gray-500">Cost</div>
        <div className="text-sm font-medium text-yellow-400">
          ${session.total_cost_usd.toFixed(4)}
        </div>
      </div>
      
      {/* Files */}
      <div>
        <div className="text-xs text-gray-500">Files</div>
        <div className="text-sm font-medium flex items-center gap-2">
          <span className="text-blue-400" title="Read">{session.files_read.length}R</span>
          <span className="text-yellow-400" title="Written">{session.files_written.length}W</span>
          <span className="text-green-400" title="Created">{session.files_created.length}C</span>
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// Filter Panel Component
// ==========================================================================

interface FilterPanelProps {
  filters: {
    categories: Set<EventCategory>;
    severities: Set<Severity>;
    searchQuery: string;
  };
  onUpdateFilters: (filters: any) => void;
}

function FilterPanel({ filters, onUpdateFilters }: FilterPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const toggleCategory = (cat: EventCategory) => {
    const newCats = new Set(filters.categories);
    if (newCats.has(cat)) {
      newCats.delete(cat);
    } else {
      newCats.add(cat);
    }
    onUpdateFilters({ ...filters, categories: newCats });
  };
  
  const toggleSeverity = (sev: Severity) => {
    const newSevs = new Set(filters.severities);
    if (newSevs.has(sev)) {
      newSevs.delete(sev);
    } else {
      newSevs.add(sev);
    }
    onUpdateFilters({ ...filters, severities: newSevs });
  };

  return (
    <div className="border-b border-gray-800">
      <div 
        className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-gray-800/50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <Filter size={14} />
        <span className="text-sm">Filters</span>
        {(filters.categories.size > 0 || filters.severities.size > 0 || filters.searchQuery) && (
          <span className="px-1.5 py-0.5 text-xs bg-blue-500/20 text-blue-400 rounded">
            Active
          </span>
        )}
        {isExpanded ? <ChevronDown size={14} className="ml-auto" /> : <ChevronRight size={14} className="ml-auto" />}
      </div>
      
      {isExpanded && (
        <div className="px-3 pb-3 space-y-3">
          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              placeholder="Search events..."
              value={filters.searchQuery}
              onChange={(e) => onUpdateFilters({ ...filters, searchQuery: e.target.value })}
              className="w-full pl-8 pr-3 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
            />
          </div>
          
          {/* Categories */}
          <div>
            <div className="text-xs text-gray-500 mb-1">Categories</div>
            <div className="flex flex-wrap gap-1">
              {(Object.keys(CATEGORY_ICONS) as EventCategory[]).map(cat => (
                <button
                  key={cat}
                  onClick={() => toggleCategory(cat)}
                  className={`px-2 py-1 text-xs rounded flex items-center gap-1 ${
                    filters.categories.size === 0 || filters.categories.has(cat)
                      ? CATEGORY_COLORS[cat]
                      : 'bg-gray-800 text-gray-500'
                  }`}
                >
                  {CATEGORY_ICONS[cat]}
                  {cat}
                </button>
              ))}
            </div>
          </div>
          
          {/* Severities */}
          <div>
            <div className="text-xs text-gray-500 mb-1">Severity</div>
            <div className="flex flex-wrap gap-1">
              {(['debug', 'info', 'warning', 'error', 'success'] as Severity[]).map(sev => (
                <button
                  key={sev}
                  onClick={() => toggleSeverity(sev)}
                  className={`px-2 py-1 text-xs rounded flex items-center gap-1 ${
                    filters.severities.size === 0 || filters.severities.has(sev)
                      ? `${SEVERITY_COLORS[sev]} bg-gray-800`
                      : 'bg-gray-800/50 text-gray-600'
                  }`}
                >
                  {SEVERITY_ICONS[sev]}
                  {sev}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ==========================================================================
// Main Nerve Center Component
// ==========================================================================

interface NerveCenterProps {
  sessionId?: string;
  wsUrl?: string;
}

export default function NerveCenter({ sessionId, wsUrl = 'ws://localhost:8000/api/v1/nerve-center/ws' }: NerveCenterProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [session, setSession] = useState<SessionState | null>(null);
  const [events, setEvents] = useState<NHEvent[]>([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [expandedAgents, setExpandedAgents] = useState<Set<string>>(new Set());
  const [filters, setFilters] = useState({
    categories: new Set<EventCategory>(),
    severities: new Set<Severity>(),
    searchQuery: '',
  });
  
  const wsRef = useRef<WebSocket | null>(null);
  
  // WebSocket connection
  useEffect(() => {
    const connect = () => {
      try {
        wsRef.current = new WebSocket(wsUrl);
        
        wsRef.current.onopen = () => {
          setIsConnected(true);
          // Subscribe to session if provided
          if (sessionId) {
            wsRef.current?.send(JSON.stringify({
              type: 'subscribe',
              payload: { session_id: sessionId }
            }));
          }
        };
        
        wsRef.current.onmessage = (event) => {
          const msg = JSON.parse(event.data);
          
          if (msg.type === 'event') {
            setEvents(prev => [...prev.slice(-999), msg.payload]);
          } else if (msg.type === 'state') {
            setSession(msg.payload);
          } else if (msg.type === 'connected') {
            console.log('Connected to Nerve Center:', msg.payload);
          }
        };
        
        wsRef.current.onclose = () => {
          setIsConnected(false);
          // Reconnect after delay
          setTimeout(connect, 3000);
        };
        
        wsRef.current.onerror = (error) => {
          console.error('WebSocket error:', error);
        };
        
      } catch (error) {
        console.error('Failed to connect:', error);
        setTimeout(connect, 3000);
      }
    };
    
    connect();
    
    return () => {
      wsRef.current?.close();
    };
  }, [wsUrl, sessionId]);
  
  // Auto-subscribe to system-status session when connected (no more demo data)
  useEffect(() => {
    if (isConnected && !sessionId && wsRef.current) {
      // Auto-subscribe to system status session
      wsRef.current.send(JSON.stringify({
        type: 'subscribe',
        payload: { session_id: 'system-status' }
      }));
    }
  }, [isConnected, sessionId]);

  // Fetch initial events from REST API when connected
  useEffect(() => {
    if (isConnected) {
      fetch('/api/v1/nerve-center/events?limit=50')
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data)) {
            setEvents(data.map((e: Record<string, unknown>) => ({
              id: e.id as string,
              timestamp: e.timestamp as string,
              category: e.category as EventCategory,
              event_type: e.event_type as string,
              severity: e.severity as Severity,
              message: e.message as string,
              session_id: e.session_id as string | undefined,
              agent_id: e.agent_id as string | undefined,
              details: e.details as Record<string, unknown> | undefined,
            })));
          }
        })
        .catch(err => console.error('Failed to fetch initial events:', err));
    }
  }, [isConnected]);

  return (
    <div className={`flex flex-col h-full bg-gray-950 text-white ${
      isFullscreen ? 'fixed inset-0 z-50' : ''
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-900 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gradient-to-r from-purple-500 to-pink-500">
            <Zap size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold flex items-center gap-2">
              NH Nerve Center
              <span className="text-xs px-2 py-0.5 bg-green-500/20 text-green-400 rounded-full">
                {isConnected ? 'LIVE' : 'CONNECTING...'}
              </span>
            </h1>
            <p className="text-xs text-gray-500">
              {session?.name || 'No active session'}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {session?.status === 'running' && (
            <button className="flex items-center gap-2 px-3 py-1.5 bg-yellow-600 rounded hover:bg-yellow-700">
              <Pause size={14} />
              Pause
            </button>
          )}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 rounded hover:bg-gray-800"
          >
            {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
        </div>
      </div>
      
      {/* Stats */}
      {session && <StatsPanel session={session} />}
      
      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Agents & Tasks */}
        <div className="w-80 border-r border-gray-800 flex flex-col overflow-hidden">
          {/* Agents */}
          <div className="p-3 border-b border-gray-800">
            <h3 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
              <Brain size={14} />
              Active Agents
            </h3>
            <div className="space-y-2">
              {session && Object.values(session.agents).map(agent => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  isExpanded={expandedAgents.has(agent.id)}
                  onToggle={() => {
                    const newExpanded = new Set(expandedAgents);
                    if (newExpanded.has(agent.id)) {
                      newExpanded.delete(agent.id);
                    } else {
                      newExpanded.add(agent.id);
                    }
                    setExpandedAgents(newExpanded);
                  }}
                />
              ))}
            </div>
          </div>
          
          {/* Tasks */}
          <div className="flex-1 overflow-y-auto p-3">
            <h3 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
              <Layers size={14} />
              Task Hierarchy
            </h3>
            {session?.root_tasks.map(task => (
              <TaskNode key={task.id} task={task} depth={0} />
            ))}
          </div>
        </div>
        
        {/* Right Panel - Event Stream */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <FilterPanel filters={filters} onUpdateFilters={setFilters} />
          <div className="flex-1 overflow-hidden bg-gray-950">
            <EventStream
              events={events}
              filters={filters}
              autoScroll={autoScroll}
              onToggleAutoScroll={() => setAutoScroll(!autoScroll)}
            />
          </div>
        </div>
      </div>
      
      {/* Footer */}
      <div className="px-4 py-2 bg-gray-900 border-t border-gray-800 flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            <Activity size={12} className="text-green-400" />
            {events.length} events
          </span>
          <span className="flex items-center gap-1">
            <Clock size={12} />
            {session?.started_at && `Started ${new Date(session.started_at).toLocaleTimeString()}`}
          </span>
        </div>
        <div>
          NH Mission Control • Full Transparency Mode
        </div>
      </div>
    </div>
  );
}
