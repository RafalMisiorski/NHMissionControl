/**
 * NH Project Analyzer - Main Dashboard
 * ======================================
 * 
 * Real-time project analysis and execution tracking with granular visibility.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Play,
  Pause,
  Square,
  RotateCcw,
  ChevronRight,
  ChevronDown,
  Check,
  X,
  Loader2,
  AlertCircle,
  AlertTriangle,
  Info,
  FolderTree,
  Cpu,
  Clock,
  Terminal,
  Eye,
  EyeOff,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import type {
  ExecutionPlan,
  ExecutionPhase,
  ExecutionTask,
  LogEntry,
  LogLevel,
  PhaseStatus,
  TaskStatus,
} from '../types/analyzer';

// ==========================================================================
// Status Indicator Components
// ==========================================================================

const STATUS_ICONS: Record<PhaseStatus | TaskStatus, React.ReactNode> = {
  pending: <div className="w-3 h-3 rounded-full bg-gray-300 dark:bg-gray-600" />,
  running: <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />,
  completed: <Check className="w-4 h-4 text-green-500" />,
  failed: <X className="w-4 h-4 text-red-500" />,
  skipped: <div className="w-3 h-3 rounded-full bg-gray-400 dark:bg-gray-500" />,
};

const LOG_ICONS: Record<LogLevel, React.ReactNode> = {
  debug: <Terminal className="w-3 h-3 text-gray-400" />,
  info: <Info className="w-3 h-3 text-blue-400" />,
  warn: <AlertTriangle className="w-3 h-3 text-yellow-500" />,
  error: <AlertCircle className="w-3 h-3 text-red-500" />,
  success: <Check className="w-3 h-3 text-green-500" />,
};

const LOG_COLORS: Record<LogLevel, string> = {
  debug: 'text-gray-500',
  info: 'text-gray-300',
  warn: 'text-yellow-400',
  error: 'text-red-400',
  success: 'text-green-400',
};

// ==========================================================================
// Progress Bar Component
// ==========================================================================

interface ProgressBarProps {
  percent: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  animated?: boolean;
  color?: 'blue' | 'green' | 'purple' | 'gradient';
}

function ProgressBar({ 
  percent, 
  size = 'md', 
  showLabel = false, 
  animated = true,
  color = 'blue' 
}: ProgressBarProps) {
  const heights = { sm: 'h-1', md: 'h-2', lg: 'h-3' };
  const colors = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    purple: 'bg-purple-500',
    gradient: 'bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500',
  };

  return (
    <div className="flex items-center gap-2 w-full">
      <div className={`flex-1 ${heights[size]} bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden`}>
        <div
          className={`h-full ${colors[color]} rounded-full transition-all duration-300 ${
            animated && percent < 100 ? 'animate-pulse' : ''
          }`}
          style={{ width: `${Math.min(100, percent)}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs text-gray-500 w-10 text-right">
          {percent.toFixed(0)}%
        </span>
      )}
    </div>
  );
}

// ==========================================================================
// Task Row Component
// ==========================================================================

interface TaskRowProps {
  task: ExecutionTask;
  isActive: boolean;
}

function TaskRow({ task, isActive }: TaskRowProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`border-l-2 ${
      isActive ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-900/10' : 
      task.status === 'completed' ? 'border-green-500' :
      task.status === 'failed' ? 'border-red-500' :
      'border-gray-200 dark:border-gray-700'
    }`}>
      <div 
        className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Expand Icon */}
        {(task.output || task.error) ? (
          expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />
        ) : (
          <div className="w-[14px]" />
        )}

        {/* Status */}
        <div className="flex-shrink-0">
          {STATUS_ICONS[task.status]}
        </div>

        {/* Task Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-sm ${isActive ? 'font-medium' : ''}`}>
              {task.name}
            </span>
            {task.target_file && (
              <code className="text-xs text-gray-500 bg-gray-100 dark:bg-gray-800 px-1 rounded truncate max-w-[200px]">
                {task.target_file}
              </code>
            )}
          </div>
          
          {/* Progress for running tasks */}
          {task.status === 'running' && task.progress_percent > 0 && (
            <div className="mt-1 flex items-center gap-2">
              <ProgressBar percent={task.progress_percent} size="sm" />
              {task.current_step && (
                <span className="text-xs text-gray-500 truncate">
                  {task.current_step}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Duration */}
        <div className="text-xs text-gray-500 flex items-center gap-1">
          <Clock size={12} />
          {task.actual_duration_seconds 
            ? `${task.actual_duration_seconds.toFixed(1)}s`
            : task.status === 'running' 
              ? '...'
              : `~${task.estimated_duration_seconds}s`
          }
        </div>
      </div>

      {/* Expanded Content */}
      {expanded && (task.output || task.error) && (
        <div className="px-4 py-2 bg-gray-900 text-gray-100 text-xs font-mono overflow-x-auto">
          {task.error && (
            <div className="text-red-400 mb-2">
              <span className="font-bold">Error:</span> {task.error}
            </div>
          )}
          {task.output && (
            <pre className="whitespace-pre-wrap">{task.output}</pre>
          )}
          {task.artifacts && task.artifacts.length > 0 && (
            <div className="mt-2 pt-2 border-t border-gray-700">
              <span className="text-gray-500">Artifacts:</span>
              {task.artifacts.map((a, i) => (
                <div key={i} className="text-green-400">+ {a}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ==========================================================================
// Phase Card Component
// ==========================================================================

interface PhaseCardProps {
  phase: ExecutionPhase;
  isActive: boolean;
  defaultExpanded?: boolean;
}

function PhaseCard({ phase, isActive, defaultExpanded = false }: PhaseCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded || isActive);

  useEffect(() => {
    if (isActive) setExpanded(true);
  }, [isActive]);

  return (
    <div className={`rounded-lg border ${
      isActive ? 'border-blue-500 shadow-lg shadow-blue-500/10' :
      phase.status === 'completed' ? 'border-green-500/50' :
      phase.status === 'failed' ? 'border-red-500/50' :
      'border-gray-200 dark:border-gray-700'
    } bg-white dark:bg-gray-900 overflow-hidden`}>
      {/* Phase Header */}
      <div 
        className={`flex items-center gap-3 p-4 cursor-pointer ${
          isActive ? 'bg-blue-50 dark:bg-blue-900/20' : ''
        }`}
        onClick={() => setExpanded(!expanded)}
      >
        {/* Expand Icon */}
        {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}

        {/* Status */}
        <div className="flex-shrink-0">
          {STATUS_ICONS[phase.status]}
        </div>

        {/* Phase Info */}
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold">{phase.name}</span>
            {isActive && (
              <span className="px-2 py-0.5 text-xs bg-blue-500 text-white rounded-full">
                ACTIVE
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 mt-0.5">{phase.description}</p>
        </div>

        {/* Progress */}
        <div className="w-32">
          <ProgressBar 
            percent={phase.progress_percent} 
            showLabel 
            color={phase.status === 'completed' ? 'green' : 'blue'}
          />
        </div>

        {/* Task Count */}
        <div className="text-sm text-gray-500">
          {phase.completed_tasks}/{phase.total_tasks}
        </div>

        {/* Duration */}
        <div className="text-sm text-gray-500 flex items-center gap-1">
          <Clock size={14} />
          {phase.actual_duration_minutes 
            ? `${phase.actual_duration_minutes.toFixed(1)}m`
            : `~${phase.estimated_duration_minutes}m`
          }
        </div>
      </div>

      {/* Tasks List */}
      {expanded && (
        <div className="border-t dark:border-gray-800">
          {phase.tasks.map((task, idx) => (
            <TaskRow 
              key={task.id} 
              task={task} 
              isActive={isActive && idx === phase.current_task_index}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ==========================================================================
// Live Log Component
// ==========================================================================

interface LiveLogProps {
  logs: LogEntry[];
  maxHeight?: string;
  autoScroll?: boolean;
  filter?: LogLevel[];
}

function LiveLog({ 
  logs, 
  maxHeight = '300px', 
  autoScroll = true,
  filter 
}: LiveLogProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isAutoScrolling, setIsAutoScrolling] = useState(autoScroll);
  const [levelFilter, setLevelFilter] = useState<LogLevel[]>(filter || ['info', 'warn', 'error', 'success']);

  const filteredLogs = logs.filter(log => levelFilter.includes(log.level));

  useEffect(() => {
    if (isAutoScrolling && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [filteredLogs, isAutoScrolling]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setIsAutoScrolling(isAtBottom);
  };

  const toggleLevel = (level: LogLevel) => {
    setLevelFilter(prev => 
      prev.includes(level) 
        ? prev.filter(l => l !== level)
        : [...prev, level]
    );
  };

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-950 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-900 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Terminal size={14} className="text-gray-400" />
          <span className="text-sm text-gray-300">Live Log</span>
          <span className="text-xs text-gray-500">({filteredLogs.length})</span>
        </div>
        
        {/* Filter Toggles */}
        <div className="flex items-center gap-1">
          {(['debug', 'info', 'warn', 'error', 'success'] as LogLevel[]).map(level => (
            <button
              key={level}
              onClick={() => toggleLevel(level)}
              className={`p-1 rounded ${
                levelFilter.includes(level) 
                  ? 'bg-gray-700' 
                  : 'opacity-30 hover:opacity-60'
              }`}
              title={level}
            >
              {LOG_ICONS[level]}
            </button>
          ))}
        </div>

        {/* Auto-scroll indicator */}
        <button
          onClick={() => setIsAutoScrolling(!isAutoScrolling)}
          className={`p-1 rounded ${isAutoScrolling ? 'text-green-400' : 'text-gray-500'}`}
          title={isAutoScrolling ? 'Auto-scroll ON' : 'Auto-scroll OFF'}
        >
          {isAutoScrolling ? <Eye size={14} /> : <EyeOff size={14} />}
        </button>
      </div>

      {/* Log Content */}
      <div 
        ref={containerRef}
        className="overflow-y-auto font-mono text-xs"
        style={{ maxHeight }}
        onScroll={handleScroll}
      >
        {filteredLogs.length === 0 ? (
          <div className="p-4 text-gray-500 text-center">
            No logs yet...
          </div>
        ) : (
          <table className="w-full">
            <tbody>
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-800/50">
                  <td className="px-2 py-1 text-gray-600 whitespace-nowrap">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="px-1 py-1">
                    {LOG_ICONS[log.level]}
                  </td>
                  <td className={`px-2 py-1 ${LOG_COLORS[log.level]}`}>
                    {log.message}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ==========================================================================
// Main Project Analyzer Component
// ==========================================================================

interface ProjectAnalyzerProps {
  projectPath?: string;
  plan?: ExecutionPlan;
  logs?: LogEntry[];
  onStart?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  onCancel?: () => void;
  onReset?: () => void;
}

export default function ProjectAnalyzer({
  projectPath = 'D:\\Projects\\time-organization-app',
  plan: initialPlan,
  logs: initialLogs = [],
  onStart,
  onPause,
  onResume,
  onCancel,
  onReset,
}: ProjectAnalyzerProps) {
  const [plan, setPlan] = useState<ExecutionPlan | null>(initialPlan || null);
  const [logs, _setLogs] = useState<LogEntry[]>(initialLogs);
  const [isConnected, setIsConnected] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Demo: Generate mock plan for visualization
  useEffect(() => {
    if (!plan) {
      setPlan(generateMockPlan());
    }
  }, []);

  // WebSocket connection (would connect to real backend)
  const connectWS = useCallback(() => {
    // Mock connection for demo
    setIsConnected(true);
    
    // In real implementation:
    // wsRef.current = new WebSocket('ws://localhost:8000/api/v1/analyzer/ws');
    // wsRef.current.onmessage = (event) => {
    //   const msg: WSMessage = JSON.parse(event.data);
    //   handleWSMessage(msg);
    // };
  }, []);

  useEffect(() => {
    connectWS();
    return () => {
      wsRef.current?.close();
    };
  }, [connectWS]);

  const currentPhaseIndex = plan?.current_phase_index ?? 0;
  const isRunning = plan?.status === 'executing';
  const isPaused = plan?.status === 'paused';
  const isCompleted = plan?.status === 'completed';

  return (
    <div className={`flex flex-col h-full ${isFullscreen ? 'fixed inset-0 z-50 bg-white dark:bg-gray-950' : ''}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b dark:border-gray-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gradient-to-r from-blue-500 to-purple-500">
            <Cpu className="text-white" size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold">NH Project Analyzer</h1>
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <FolderTree size={14} />
              <span className="font-mono">{projectPath}</span>
              {isConnected && (
                <span className="flex items-center gap-1 text-green-500">
                  <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  Live
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          {!isRunning && !isPaused && !isCompleted && (
            <button
              onClick={onStart}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              <Play size={18} />
              Start Execution
            </button>
          )}
          
          {isRunning && (
            <button
              onClick={onPause}
              className="flex items-center gap-2 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700"
            >
              <Pause size={18} />
              Pause
            </button>
          )}
          
          {isPaused && (
            <button
              onClick={onResume}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Play size={18} />
              Resume
            </button>
          )}
          
          {(isRunning || isPaused) && (
            <button
              onClick={onCancel}
              className="flex items-center gap-2 px-3 py-2 border border-red-500 text-red-500 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20"
            >
              <Square size={18} />
              Cancel
            </button>
          )}
          
          {isCompleted && (
            <button
              onClick={onReset}
              className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
            >
              <RotateCcw size={18} />
              New Analysis
            </button>
          )}

          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 rounded-lg border dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
          </button>
        </div>
      </div>

      {/* Overall Progress */}
      {plan && (
        <div className="px-4 py-3 bg-gray-50 dark:bg-gray-900/50 border-b dark:border-gray-800">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-4">
              <span className="font-medium">{plan.name}</span>
              <span className={`px-2 py-0.5 text-xs rounded-full ${
                plan.status === 'executing' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
                plan.status === 'completed' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                plan.status === 'failed' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                plan.status === 'paused' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
              }`}>
                {plan.status.toUpperCase()}
              </span>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span>{plan.completed_tasks}/{plan.total_tasks} tasks</span>
              <span className="flex items-center gap-1">
                <Clock size={14} />
                {plan.actual_duration_minutes 
                  ? `${plan.actual_duration_minutes.toFixed(1)}m`
                  : `~${plan.estimated_duration_minutes}m`
                }
              </span>
            </div>
          </div>
          <ProgressBar 
            percent={plan.progress_percent} 
            size="lg"
            color="gradient"
            animated={isRunning}
          />
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 overflow-hidden flex">
        {/* Phases Panel */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {plan?.phases.map((phase, idx) => (
            <PhaseCard
              key={phase.id}
              phase={phase}
              isActive={idx === currentPhaseIndex && isRunning}
              defaultExpanded={idx === currentPhaseIndex}
            />
          ))}
        </div>

        {/* Live Log Panel */}
        <div className="w-[400px] border-l dark:border-gray-800 p-4">
          <LiveLog 
            logs={logs} 
            maxHeight="calc(100vh - 250px)"
            autoScroll
          />
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// Mock Data Generator (for demo)
// ==========================================================================

function generateMockPlan(): ExecutionPlan {
  return {
    id: 'plan-1',
    project_id: 'proj-1',
    name: 'Time Organization App → Notion-Level Refactoring',
    description: 'Complete refactoring with Block Engine, Real-time Sync, and ADHD optimizations',
    created_at: new Date().toISOString(),
    status: 'pending',
    current_phase_index: 0,
    total_tasks: 24,
    completed_tasks: 0,
    failed_tasks: 0,
    progress_percent: 0,
    estimated_duration_minutes: 45,
    phases: [
      {
        id: 'phase-1',
        name: 'Phase 1: Discovery',
        description: 'Analyze current codebase structure and dependencies',
        order: 0,
        status: 'pending',
        current_task_index: 0,
        total_tasks: 5,
        completed_tasks: 0,
        progress_percent: 0,
        estimated_duration_minutes: 5,
        tasks: [
          { id: 't1', name: 'Scan file structure', description: '', order: 0, status: 'pending', type: 'analyze', progress_percent: 0, estimated_duration_seconds: 2 },
          { id: 't2', name: 'Parse package.json dependencies', description: '', order: 1, status: 'pending', type: 'analyze', progress_percent: 0, estimated_duration_seconds: 1, target_file: 'package.json' },
          { id: 't3', name: 'Identify tech stack', description: '', order: 2, status: 'pending', type: 'analyze', progress_percent: 0, estimated_duration_seconds: 1 },
          { id: 't4', name: 'Map component hierarchy', description: '', order: 3, status: 'pending', type: 'analyze', progress_percent: 0, estimated_duration_seconds: 5 },
          { id: 't5', name: 'Extract existing features', description: '', order: 4, status: 'pending', type: 'analyze', progress_percent: 0, estimated_duration_seconds: 3 },
        ],
      },
      {
        id: 'phase-2',
        name: 'Phase 2: Architecture Analysis',
        description: 'Evaluate patterns and generate improvement recommendations',
        order: 1,
        status: 'pending',
        current_task_index: 0,
        total_tasks: 5,
        completed_tasks: 0,
        progress_percent: 0,
        estimated_duration_minutes: 8,
        tasks: [
          { id: 't6', name: 'Evaluate current patterns', description: '', order: 0, status: 'pending', type: 'analyze', progress_percent: 0, estimated_duration_seconds: 10 },
          { id: 't7', name: 'Identify scalability bottlenecks', description: '', order: 1, status: 'pending', type: 'analyze', progress_percent: 0, estimated_duration_seconds: 15 },
          { id: 't8', name: 'Generate improvement recommendations', description: '', order: 2, status: 'pending', type: 'generate', progress_percent: 0, estimated_duration_seconds: 30 },
          { id: 't9', name: 'Compare with Notion architecture', description: '', order: 3, status: 'pending', type: 'analyze', progress_percent: 0, estimated_duration_seconds: 20 },
          { id: 't10', name: 'Propose new system design', description: '', order: 4, status: 'pending', type: 'generate', progress_percent: 0, estimated_duration_seconds: 45 },
        ],
      },
      {
        id: 'phase-3',
        name: 'Phase 3: UI/UX Redesign',
        description: 'Create ADHD-optimized design system and mockups',
        order: 2,
        status: 'pending',
        current_task_index: 0,
        total_tasks: 4,
        completed_tasks: 0,
        progress_percent: 0,
        estimated_duration_minutes: 12,
        tasks: [
          { id: 't11', name: 'Analyze current UI patterns', description: '', order: 0, status: 'pending', type: 'analyze', progress_percent: 0, estimated_duration_seconds: 20 },
          { id: 't12', name: 'Generate ADHD-optimized design system', description: '', order: 1, status: 'pending', type: 'generate', progress_percent: 0, estimated_duration_seconds: 60 },
          { id: 't13', name: 'Create component mockups', description: '', order: 2, status: 'pending', type: 'generate', progress_percent: 0, estimated_duration_seconds: 120 },
          { id: 't14', name: 'Build interactive prototype', description: '', order: 3, status: 'pending', type: 'create', progress_percent: 0, estimated_duration_seconds: 180 },
        ],
      },
      {
        id: 'phase-4',
        name: 'Phase 4: Block Engine Core (P0)',
        description: 'Implement base Block model and editor',
        order: 3,
        status: 'pending',
        current_task_index: 0,
        total_tasks: 5,
        completed_tasks: 0,
        progress_percent: 0,
        estimated_duration_minutes: 10,
        tasks: [
          { id: 't15', name: 'Create Block model schema', description: '', order: 0, status: 'pending', type: 'create', progress_percent: 0, estimated_duration_seconds: 30, target_file: 'backend/models/block.py' },
          { id: 't16', name: 'Create Block API endpoints', description: '', order: 1, status: 'pending', type: 'create', progress_percent: 0, estimated_duration_seconds: 60, target_file: 'backend/routers/blocks.py' },
          { id: 't17', name: 'Create BlockEditor component', description: '', order: 2, status: 'pending', type: 'create', progress_percent: 0, estimated_duration_seconds: 120, target_file: 'frontend/components/BlockEditor.tsx' },
          { id: 't18', name: 'Implement block types (text, task, page)', description: '', order: 3, status: 'pending', type: 'create', progress_percent: 0, estimated_duration_seconds: 90 },
          { id: 't19', name: 'Add nested blocks support', description: '', order: 4, status: 'pending', type: 'modify', progress_percent: 0, estimated_duration_seconds: 60 },
        ],
      },
      {
        id: 'phase-5',
        name: 'Phase 5: Real-time Sync (P1)',
        description: 'Implement WebSocket sync and CRDT',
        order: 4,
        status: 'pending',
        current_task_index: 0,
        total_tasks: 5,
        completed_tasks: 0,
        progress_percent: 0,
        estimated_duration_minutes: 10,
        tasks: [
          { id: 't20', name: 'Setup WebSocket endpoint', description: '', order: 0, status: 'pending', type: 'create', progress_percent: 0, estimated_duration_seconds: 30, target_file: 'backend/routers/sync.py' },
          { id: 't21', name: 'Implement event broadcast', description: '', order: 1, status: 'pending', type: 'create', progress_percent: 0, estimated_duration_seconds: 45 },
          { id: 't22', name: 'Create useSync hook', description: '', order: 2, status: 'pending', type: 'create', progress_percent: 0, estimated_duration_seconds: 60, target_file: 'frontend/hooks/useSync.ts' },
          { id: 't23', name: 'Implement optimistic updates', description: '', order: 3, status: 'pending', type: 'modify', progress_percent: 0, estimated_duration_seconds: 90 },
          { id: 't24', name: 'Add conflict resolution', description: '', order: 4, status: 'pending', type: 'create', progress_percent: 0, estimated_duration_seconds: 120 },
        ],
      },
    ],
  };
}
