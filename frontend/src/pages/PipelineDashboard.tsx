/**
 * Pipeline Orchestrator Dashboard
 * ================================
 *
 * Kanban-style view for pipeline runs with PO review integration.
 * Connects to /api/v1/pipeline/* and /api/v1/po-review/* endpoints.
 */

import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Zap,
  RefreshCw,
  Eye,
  ThumbsUp,
  ThumbsDown,
  MessageSquare,
  Shield,
  Server,
  Cpu,
  Activity,
  Loader2,
  GitBranch,
  ExternalLink,
} from 'lucide-react';

// ==========================================================================
// Types
// ==========================================================================

type PipelineStageType =
  | 'queued'
  | 'developing'
  | 'testing'
  | 'verifying'
  | 'po_review'
  | 'deploying'
  | 'completed'
  | 'failed'
  | 'cancelled';

type PipelineRunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused';
type EscalationLevel = 'codex' | 'sonnet' | 'opus' | 'human';

interface PipelineRun {
  id: string;
  task_id: string;
  task_title: string;
  project_name: string | null;
  current_stage: PipelineStageType;
  status: PipelineRunStatus;
  priority: 'critical' | 'high' | 'normal' | 'low';
  escalation_level: EscalationLevel;
  retry_count: number;
  max_retries: number;
  initial_trust_score: number | null;
  final_trust_score: number | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

interface POReviewItem {
  id: string;
  pipeline_run_id: string;
  task_id: string;
  task_title: string;
  project_name: string | null;
  priority: string;
  health_score: number;
  tests_passed: number;
  tests_failed: number;
  tests_skipped: number;
  coverage_percent: number | null;
  warnings: string[];
  blockers: string[];
  preview_url: string | null;
  status: string;
  created_at: string;
}

interface PortPoolStatus {
  range: string;
  total: number;
  allocated: number;
  available: number;
  allocated_ports: number[];
}

interface AllPortsStatus {
  frontend: PortPoolStatus;
  backend: PortPoolStatus;
  database: PortPoolStatus;
  redis: PortPoolStatus;
  test: PortPoolStatus;
}

// HandoffToken interface reserved for future use when displaying tokens in UI
export type HandoffToken = {
  id: string;
  pipeline_run_id: string;
  from_stage: PipelineStageType;
  to_stage: PipelineStageType;
  trust_score: number;
  is_valid: boolean;
  signature: string;
  created_at: string;
};

// ==========================================================================
// API Functions
// ==========================================================================

const API_BASE = '/api/v1';

async function fetchPipelineRuns(): Promise<PipelineRun[]> {
  const res = await fetch(`${API_BASE}/pipeline/runs?limit=50`);
  if (!res.ok) throw new Error('Failed to fetch pipeline runs');
  return res.json();
}

async function fetchPOReviewQueue(): Promise<POReviewItem[]> {
  const res = await fetch(`${API_BASE}/po-review/queue`);
  if (!res.ok) throw new Error('Failed to fetch PO review queue');
  return res.json();
}

async function fetchPortStatus(): Promise<AllPortsStatus> {
  const res = await fetch(`${API_BASE}/resources/ports`);
  if (!res.ok) throw new Error('Failed to fetch port status');
  return res.json();
}

async function approvePOReview(runId: string, feedback?: string): Promise<void> {
  const res = await fetch(`${API_BASE}/po-review/${runId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback, approved_by: 'PO Dashboard' }),
  });
  if (!res.ok) throw new Error('Failed to approve review');
}

async function requestChanges(runId: string, feedback: string): Promise<void> {
  const res = await fetch(`${API_BASE}/po-review/${runId}/request-changes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback, requested_by: 'PO Dashboard' }),
  });
  if (!res.ok) throw new Error('Failed to request changes');
}

async function rejectPOReview(runId: string, reason: string): Promise<void> {
  const res = await fetch(`${API_BASE}/po-review/${runId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason, rejected_by: 'PO Dashboard' }),
  });
  if (!res.ok) throw new Error('Failed to reject review');
}

async function retryPipelineRun(runId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/pipeline/runs/${runId}/retry`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to retry pipeline');
}

async function escalatePipelineRun(runId: string, reason: string): Promise<void> {
  const res = await fetch(`${API_BASE}/pipeline/runs/${runId}/escalate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) throw new Error('Failed to escalate pipeline');
}

// ==========================================================================
// Stage Configuration
// ==========================================================================

const STAGES: { key: PipelineStageType; label: string; icon: React.ReactNode; color: string }[] = [
  { key: 'queued', label: 'Queued', icon: <Clock size={14} />, color: 'gray' },
  { key: 'developing', label: 'Developing', icon: <Cpu size={14} />, color: 'blue' },
  { key: 'testing', label: 'Testing', icon: <Activity size={14} />, color: 'yellow' },
  { key: 'verifying', label: 'Verifying', icon: <Shield size={14} />, color: 'orange' },
  { key: 'po_review', label: 'PO Review', icon: <Eye size={14} />, color: 'purple' },
  { key: 'deploying', label: 'Deploying', icon: <Server size={14} />, color: 'cyan' },
  { key: 'completed', label: 'Completed', icon: <CheckCircle size={14} />, color: 'green' },
];

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/50',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/50',
  normal: 'bg-blue-500/20 text-blue-400 border-blue-500/50',
  low: 'bg-gray-500/20 text-gray-400 border-gray-500/50',
};

const ESCALATION_COLORS: Record<EscalationLevel, string> = {
  codex: 'text-green-400',
  sonnet: 'text-blue-400',
  opus: 'text-purple-400',
  human: 'text-red-400',
};

// ==========================================================================
// TaskCard Component
// ==========================================================================

interface TaskCardProps {
  run: PipelineRun;
  onRetry: (id: string) => void;
  onEscalate: (id: string, reason: string) => void;
}

function TaskCard({ run, onRetry, onEscalate }: TaskCardProps) {
  const [showActions, setShowActions] = useState(false);

  const trustScore = run.final_trust_score ?? run.initial_trust_score;
  const trustColor = trustScore
    ? trustScore >= 85 ? 'text-green-400' : trustScore >= 70 ? 'text-yellow-400' : 'text-red-400'
    : 'text-gray-500';

  return (
    <div
      className={`rounded-lg border bg-gray-900 p-3 mb-2 cursor-pointer hover:border-gray-600 transition-all ${
        run.status === 'running' ? 'border-blue-500/50 shadow-lg shadow-blue-500/10' : 'border-gray-700'
      }`}
      onClick={() => setShowActions(!showActions)}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className={`px-2 py-0.5 text-xs rounded border ${PRIORITY_COLORS[run.priority]}`}>
          {run.priority}
        </span>
        <span className={`text-xs ${ESCALATION_COLORS[run.escalation_level]}`}>
          {run.escalation_level.toUpperCase()}
        </span>
      </div>

      {/* Title */}
      <h4 className="text-sm font-medium text-white mb-1 truncate" title={run.task_title}>
        {run.task_title}
      </h4>

      {/* Project */}
      {run.project_name && (
        <div className="flex items-center gap-1 text-xs text-gray-500 mb-2">
          <GitBranch size={10} />
          {run.project_name}
        </div>
      )}

      {/* Stats Row */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          {/* Trust Score */}
          {trustScore !== null && (
            <span className={`flex items-center gap-1 ${trustColor}`}>
              <Shield size={12} />
              {trustScore.toFixed(0)}%
            </span>
          )}
          {/* Retries */}
          {run.retry_count > 0 && (
            <span className="text-orange-400 flex items-center gap-1">
              <RefreshCw size={10} />
              {run.retry_count}/{run.max_retries}
            </span>
          )}
        </div>
        {/* Status Indicator */}
        {run.status === 'running' && (
          <Loader2 size={14} className="text-blue-400 animate-spin" />
        )}
        {run.status === 'failed' && (
          <XCircle size={14} className="text-red-400" />
        )}
      </div>

      {/* Error Message */}
      {run.error_message && (
        <div className="mt-2 p-2 bg-red-500/10 rounded text-xs text-red-300 truncate" title={run.error_message}>
          {run.error_message}
        </div>
      )}

      {/* Actions */}
      {showActions && run.status === 'failed' && (
        <div className="mt-3 pt-3 border-t border-gray-700 flex gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); onRetry(run.id); }}
            className="flex-1 px-2 py-1.5 text-xs bg-blue-600 hover:bg-blue-500 rounded flex items-center justify-center gap-1"
          >
            <RefreshCw size={12} />
            Retry
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onEscalate(run.id, 'Manual escalation from dashboard'); }}
            className="flex-1 px-2 py-1.5 text-xs bg-orange-600 hover:bg-orange-500 rounded flex items-center justify-center gap-1"
          >
            <Zap size={12} />
            Escalate
          </button>
        </div>
      )}
    </div>
  );
}

// ==========================================================================
// PipelineStage Component (Kanban Column)
// ==========================================================================

interface PipelineStageProps {
  stage: typeof STAGES[number];
  runs: PipelineRun[];
  onRetry: (id: string) => void;
  onEscalate: (id: string, reason: string) => void;
}

function PipelineStage({ stage, runs, onRetry, onEscalate }: PipelineStageProps) {
  const stageColors: Record<string, string> = {
    gray: 'border-gray-600',
    blue: 'border-blue-500',
    yellow: 'border-yellow-500',
    orange: 'border-orange-500',
    purple: 'border-purple-500',
    cyan: 'border-cyan-500',
    green: 'border-green-500',
  };

  return (
    <div className="flex-1 min-w-[240px] max-w-[300px]">
      {/* Header */}
      <div className={`flex items-center gap-2 px-3 py-2 rounded-t-lg bg-gray-800 border-b-2 ${stageColors[stage.color]}`}>
        <span className={`text-${stage.color}-400`}>{stage.icon}</span>
        <span className="text-sm font-medium">{stage.label}</span>
        <span className="ml-auto px-2 py-0.5 text-xs bg-gray-700 rounded-full">
          {runs.length}
        </span>
      </div>

      {/* Cards */}
      <div className="p-2 bg-gray-850 rounded-b-lg min-h-[200px] max-h-[60vh] overflow-y-auto">
        {runs.map((run) => (
          <TaskCard
            key={run.id}
            run={run}
            onRetry={onRetry}
            onEscalate={onEscalate}
          />
        ))}
        {runs.length === 0 && (
          <div className="text-center text-gray-600 text-xs py-8">
            No tasks
          </div>
        )}
      </div>
    </div>
  );
}

// ==========================================================================
// POReviewCard Component
// ==========================================================================

interface POReviewCardProps {
  item: POReviewItem;
  onApprove: (id: string) => void;
  onRequestChanges: (id: string, feedback: string) => void;
  onReject: (id: string, reason: string) => void;
}

function POReviewCard({ item, onApprove, onRequestChanges, onReject }: POReviewCardProps) {
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);

  const healthColor = item.health_score >= 85 ? 'text-green-400' : item.health_score >= 70 ? 'text-yellow-400' : 'text-red-400';
  const hasBlockers = item.blockers.length > 0;

  return (
    <div className="rounded-lg border border-purple-500/30 bg-gray-900 p-4 mb-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-white">{item.task_title}</h4>
        <span className={`text-lg font-bold ${healthColor}`}>
          {item.health_score.toFixed(0)}%
        </span>
      </div>

      {/* Test Results */}
      <div className="flex items-center gap-4 text-xs mb-3">
        <span className="text-green-400 flex items-center gap-1">
          <CheckCircle size={12} />
          {item.tests_passed} passed
        </span>
        {item.tests_failed > 0 && (
          <span className="text-red-400 flex items-center gap-1">
            <XCircle size={12} />
            {item.tests_failed} failed
          </span>
        )}
        {item.coverage_percent !== null && (
          <span className="text-blue-400">
            {item.coverage_percent.toFixed(1)}% coverage
          </span>
        )}
      </div>

      {/* Warnings */}
      {item.warnings.length > 0 && (
        <div className="mb-3">
          {item.warnings.map((w, i) => (
            <div key={i} className="flex items-center gap-2 text-xs text-yellow-400 py-1">
              <AlertTriangle size={12} />
              {w}
            </div>
          ))}
        </div>
      )}

      {/* Blockers */}
      {item.blockers.length > 0 && (
        <div className="mb-3 p-2 bg-red-500/10 rounded">
          {item.blockers.map((b, i) => (
            <div key={i} className="flex items-center gap-2 text-xs text-red-400 py-1">
              <XCircle size={12} />
              {b}
            </div>
          ))}
        </div>
      )}

      {/* Preview Link */}
      {item.preview_url && (
        <a
          href={item.preview_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 mb-3"
        >
          <ExternalLink size={12} />
          Open Preview
        </a>
      )}

      {/* Feedback Input */}
      {showFeedback && (
        <div className="mb-3">
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Enter feedback..."
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-white placeholder-gray-500 resize-none"
            rows={2}
          />
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => onApprove(item.pipeline_run_id)}
          disabled={hasBlockers}
          className={`flex-1 px-3 py-2 text-xs rounded flex items-center justify-center gap-1 ${
            hasBlockers
              ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
              : 'bg-green-600 hover:bg-green-500 text-white'
          }`}
        >
          <ThumbsUp size={14} />
          Approve
        </button>
        <button
          onClick={() => {
            if (showFeedback && feedback) {
              onRequestChanges(item.pipeline_run_id, feedback);
            } else {
              setShowFeedback(true);
            }
          }}
          className="flex-1 px-3 py-2 text-xs bg-yellow-600 hover:bg-yellow-500 rounded flex items-center justify-center gap-1"
        >
          <MessageSquare size={14} />
          Changes
        </button>
        <button
          onClick={() => {
            if (showFeedback && feedback) {
              onReject(item.pipeline_run_id, feedback);
            } else {
              setShowFeedback(true);
            }
          }}
          className="flex-1 px-3 py-2 text-xs bg-red-600 hover:bg-red-500 rounded flex items-center justify-center gap-1"
        >
          <ThumbsDown size={14} />
          Reject
        </button>
      </div>
    </div>
  );
}

// ==========================================================================
// ResourcePanel Component
// ==========================================================================

interface ResourcePanelProps {
  ports: AllPortsStatus | null;
  isLoading: boolean;
}

function ResourcePanel({ ports, isLoading }: ResourcePanelProps) {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-700 rounded w-1/3" />
          <div className="h-2 bg-gray-700 rounded" />
          <div className="h-2 bg-gray-700 rounded" />
        </div>
      </div>
    );
  }

  if (!ports) return null;

  const pools = [
    { key: 'frontend', label: 'Frontend', data: ports.frontend, color: 'cyan' },
    { key: 'backend', label: 'Backend', data: ports.backend, color: 'blue' },
    { key: 'database', label: 'Database', data: ports.database, color: 'yellow' },
    { key: 'redis', label: 'Redis', data: ports.redis, color: 'red' },
    { key: 'test', label: 'Test', data: ports.test, color: 'green' },
  ];

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
        <Server size={14} />
        Port Pools
      </h3>
      <div className="space-y-3">
        {pools.map((pool) => {
          const usage = (pool.data.allocated / pool.data.total) * 100;
          return (
            <div key={pool.key}>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-gray-400">{pool.label}</span>
                <span className="text-gray-500">
                  {pool.data.allocated}/{pool.data.total}
                </span>
              </div>
              <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full bg-${pool.color}-500 transition-all`}
                  style={{ width: `${usage}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ==========================================================================
// Main PipelineDashboard Component
// ==========================================================================

export default function PipelineDashboard() {
  const queryClient = useQueryClient();

  // Queries
  const { data: runs = [], isLoading: runsLoading, refetch: refetchRuns } = useQuery({
    queryKey: ['pipelineRuns'],
    queryFn: fetchPipelineRuns,
    refetchInterval: 5000,
  });

  const { data: reviewQueue = [], isLoading: reviewLoading, refetch: refetchReview } = useQuery({
    queryKey: ['poReviewQueue'],
    queryFn: fetchPOReviewQueue,
    refetchInterval: 5000,
  });

  const { data: portStatus, isLoading: portsLoading } = useQuery({
    queryKey: ['portStatus'],
    queryFn: fetchPortStatus,
    refetchInterval: 10000,
  });

  // Mutations
  const retryMutation = useMutation({
    mutationFn: retryPipelineRun,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelineRuns'] });
    },
  });

  const escalateMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => escalatePipelineRun(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelineRuns'] });
    },
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, feedback }: { id: string; feedback?: string }) => approvePOReview(id, feedback),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['poReviewQueue'] });
      queryClient.invalidateQueries({ queryKey: ['pipelineRuns'] });
    },
  });

  const requestChangesMutation = useMutation({
    mutationFn: ({ id, feedback }: { id: string; feedback: string }) => requestChanges(id, feedback),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['poReviewQueue'] });
      queryClient.invalidateQueries({ queryKey: ['pipelineRuns'] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => rejectPOReview(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['poReviewQueue'] });
      queryClient.invalidateQueries({ queryKey: ['pipelineRuns'] });
    },
  });

  // Group runs by stage
  const runsByStage = STAGES.reduce((acc, stage) => {
    acc[stage.key] = runs.filter((r) => r.current_stage === stage.key);
    return acc;
  }, {} as Record<PipelineStageType, PipelineRun[]>);

  // Stats
  const totalRuns = runs.length;
  const runningCount = runs.filter((r) => r.status === 'running').length;
  const failedCount = runs.filter((r) => r.status === 'failed').length;
  const completedCount = runs.filter((r) => r.status === 'completed').length;

  const handleRefresh = useCallback(() => {
    refetchRuns();
    refetchReview();
  }, [refetchRuns, refetchReview]);

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="border-b border-gray-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gradient-to-r from-blue-500 to-purple-500">
              <Zap size={20} />
            </div>
            <div>
              <h1 className="text-lg font-bold">Pipeline Orchestrator</h1>
              <p className="text-xs text-gray-500">Taśmociąg - Autonomous Build Pipeline</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Stats */}
            <div className="flex items-center gap-4 text-sm">
              <span className="text-gray-400">
                Total: <span className="text-white font-medium">{totalRuns}</span>
              </span>
              <span className="text-blue-400">
                Running: <span className="font-medium">{runningCount}</span>
              </span>
              <span className="text-green-400">
                Completed: <span className="font-medium">{completedCount}</span>
              </span>
              {failedCount > 0 && (
                <span className="text-red-400">
                  Failed: <span className="font-medium">{failedCount}</span>
                </span>
              )}
            </div>

            <button
              onClick={handleRefresh}
              className="p-2 rounded hover:bg-gray-800 transition-colors"
              title="Refresh"
            >
              <RefreshCw size={16} className={runsLoading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex">
        {/* Kanban Board */}
        <div className="flex-1 p-4 overflow-x-auto">
          <div className="flex gap-3">
            {STAGES.map((stage) => (
              <PipelineStage
                key={stage.key}
                stage={stage}
                runs={runsByStage[stage.key] || []}
                onRetry={(id) => retryMutation.mutate(id)}
                onEscalate={(id, reason) => escalateMutation.mutate({ id, reason })}
              />
            ))}
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="w-80 border-l border-gray-800 p-4 space-y-4 overflow-y-auto max-h-[calc(100vh-80px)]">
          {/* PO Review Queue */}
          <div>
            <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
              <Eye size={14} className="text-purple-400" />
              PO Review Queue
              {reviewQueue.length > 0 && (
                <span className="px-2 py-0.5 text-xs bg-purple-500/20 text-purple-400 rounded-full">
                  {reviewQueue.length}
                </span>
              )}
            </h3>

            {reviewLoading ? (
              <div className="animate-pulse space-y-3">
                <div className="h-24 bg-gray-800 rounded" />
                <div className="h-24 bg-gray-800 rounded" />
              </div>
            ) : reviewQueue.length > 0 ? (
              reviewQueue.map((item) => (
                <POReviewCard
                  key={item.id}
                  item={item}
                  onApprove={(id) => approveMutation.mutate({ id })}
                  onRequestChanges={(id, feedback) => requestChangesMutation.mutate({ id, feedback })}
                  onReject={(id, reason) => rejectMutation.mutate({ id, reason })}
                />
              ))
            ) : (
              <div className="text-center text-gray-600 text-xs py-8">
                No items awaiting review
              </div>
            )}
          </div>

          {/* Resource Panel */}
          <ResourcePanel ports={portStatus ?? null} isLoading={portsLoading} />
        </div>
      </div>
    </div>
  );
}
