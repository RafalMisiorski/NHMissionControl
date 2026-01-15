import { useState, useMemo } from 'react';
import {
  Play,
  CheckCircle,
  XCircle,
  Clock,
  Loader,
  ChevronDown,
  ChevronUp,
  Terminal,
  GitBranch,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import type { NHJob, NHJobStatus } from '../types';

interface LiveJobStreamProps {
  jobs: NHJob[];
  onApprove?: (jobId: string) => void;
  onReject?: (jobId: string) => void;
  onCancel?: (jobId: string) => void;
  isConnected?: boolean;
  isLoading?: boolean;
}

const statusConfig: Record<NHJobStatus, { icon: React.ReactNode; color: string; bg: string; label: string }> = {
  pending: {
    icon: <Clock className="w-4 h-4" />,
    color: 'text-orange-400',
    bg: 'bg-orange-500/20 border-orange-500/30',
    label: 'PENDING',
  },
  approved: {
    icon: <ThumbsUp className="w-4 h-4" />,
    color: 'text-blue-400',
    bg: 'bg-blue-500/20 border-blue-500/30',
    label: 'APPROVED',
  },
  running: {
    icon: <Loader className="w-4 h-4 animate-spin" />,
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/20 border-cyan-500/30',
    label: 'RUNNING',
  },
  paused: {
    icon: <Clock className="w-4 h-4" />,
    color: 'text-yellow-400',
    bg: 'bg-yellow-500/20 border-yellow-500/30',
    label: 'PAUSED',
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
  cancelled: {
    icon: <XCircle className="w-4 h-4" />,
    color: 'text-gray-400',
    bg: 'bg-gray-500/20 border-gray-500/30',
    label: 'CANCELLED',
  },
  spawned_retry: {
    icon: <GitBranch className="w-4 h-4" />,
    color: 'text-purple-400',
    bg: 'bg-purple-500/20 border-purple-500/30',
    label: 'RETRY',
  },
  needs_review: {
    icon: <Clock className="w-4 h-4" />,
    color: 'text-amber-400',
    bg: 'bg-amber-500/20 border-amber-500/30',
    label: 'REVIEW',
  },
};

interface JobCardProps {
  job: NHJob;
  onApprove?: (jobId: string) => void;
  onReject?: (jobId: string) => void;
  onCancel?: (jobId: string) => void;
}

function JobCard({ job, onApprove, onReject, onCancel }: JobCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const config = statusConfig[job.status] || statusConfig.pending;

  // Calculate relative time
  const timeAgo = useMemo(() => {
    const date = new Date(job.created_at);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) return `${diffDays}d ago`;
    if (diffHours > 0) return `${diffHours}h ago`;
    if (diffMins > 0) return `${diffMins}m ago`;
    return 'just now';
  }, [job.created_at]);

  // Calculate duration for completed/failed jobs
  const duration = useMemo(() => {
    if (!job.started_at || !job.completed_at) return null;
    const start = new Date(job.started_at);
    const end = new Date(job.completed_at);
    const diffMs = end.getTime() - start.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const mins = Math.floor(diffSecs / 60);
    const secs = diffSecs % 60;
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  }, [job.started_at, job.completed_at]);

  // Stale detection for running jobs (>15 min is stale)
  const isStale = useMemo(() => {
    if (job.status !== 'running' || !job.started_at) return false;
    const start = new Date(job.started_at);
    const now = new Date();
    const diffMs = now.getTime() - start.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    return diffMins > 15; // Stale after 15 minutes
  }, [job.status, job.started_at]);

  // Running duration for active jobs
  const runningFor = useMemo(() => {
    if (job.status !== 'running' || !job.started_at) return null;
    const start = new Date(job.started_at);
    const now = new Date();
    const diffMs = now.getTime() - start.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours > 0) return `${diffHours}h ${diffMins % 60}m`;
    return `${diffMins}m`;
  }, [job.status, job.started_at]);

  // Extract project name from path
  const projectName = job.project_path.split(/[/\\]/).pop() || job.project_path;

  return (
    <div
      className={`
        border rounded-lg p-4 transition-all duration-300 ease-in-out
        hover:shadow-lg hover:shadow-cyan-500/5
        ${config.bg}
        animate-fade-in
      `}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <span className={`${config.color}`}>{config.icon}</span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-mono text-gray-400">
                {job.id.slice(0, 8)}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded ${config.bg} ${config.color} border`}>
                {config.label}
              </span>
              {isStale && (
                <span className="text-xs px-2 py-0.5 rounded bg-red-500/30 text-red-400 border border-red-500/50 animate-pulse">
                  STALE
                </span>
              )}
              {runningFor && !isStale && (
                <span className="text-xs text-cyan-400/70">
                  {runningFor}
                </span>
              )}
              {runningFor && isStale && (
                <span className="text-xs text-red-400">
                  {runningFor}
                </span>
              )}
              <span className="text-xs text-gray-500">{projectName}</span>
            </div>
            <p className="text-sm text-white truncate mt-1">{job.description}</p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-xs text-gray-500">{timeAgo}</span>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-gray-400 hover:text-white transition-colors p-1"
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Progress bar for running jobs */}
      {job.status === 'running' && (
        <div className="mt-3">
          <div className="h-1 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full animate-pulse"
              style={{ width: '100%' }}
            />
          </div>
        </div>
      )}

      {/* Action buttons for pending jobs */}
      {job.status === 'pending' && job.requires_approval && (
        <div className="mt-3 flex items-center gap-2">
          {onApprove && (
            <button
              onClick={() => onApprove(job.id)}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-green-600 hover:bg-green-500 rounded transition-colors"
            >
              <ThumbsUp className="w-3 h-3" />
              Approve
            </button>
          )}
          {onReject && (
            <button
              onClick={() => onReject(job.id)}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-red-600 hover:bg-red-500 rounded transition-colors"
            >
              <ThumbsDown className="w-3 h-3" />
              Reject
            </button>
          )}
        </div>
      )}

      {/* Cancel button for running jobs */}
      {job.status === 'running' && onCancel && (
        <div className="mt-3">
          <button
            onClick={() => onCancel(job.id)}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded transition-colors"
          >
            <XCircle className="w-3 h-3" />
            Cancel
          </button>
        </div>
      )}

      {/* Expanded content */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-700/50 space-y-3 animate-slide-down">
          {/* Full description */}
          {job.full_description && (
            <div>
              <p className="text-xs text-gray-500 mb-1">Full Description</p>
              <p className="text-sm text-gray-300">{job.full_description}</p>
            </div>
          )}

          {/* Duration */}
          {duration && (
            <div className="flex items-center gap-2 text-sm">
              <Clock className="w-4 h-4 text-gray-500" />
              <span className="text-gray-400">Duration: {duration}</span>
            </div>
          )}

          {/* Output preview */}
          {job.output && (
            <div>
              <p className="text-xs text-gray-500 mb-1 flex items-center gap-1">
                <Terminal className="w-3 h-3" />
                Output
              </p>
              <pre className="text-xs text-gray-400 bg-gray-900/50 p-2 rounded overflow-x-auto max-h-32">
                {job.output.slice(0, 500)}
                {job.output.length > 500 && '...'}
              </pre>
            </div>
          )}

          {/* Error */}
          {job.error && (
            <div>
              <p className="text-xs text-red-400 mb-1">Error</p>
              <pre className="text-xs text-red-300 bg-red-900/20 p-2 rounded overflow-x-auto">
                {job.error}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

type FilterStatus = 'all' | 'active' | 'completed' | 'failed' | 'pending';

export function LiveJobStream({
  jobs,
  onApprove,
  onReject,
  onCancel,
  isConnected = false,
  isLoading = false,
}: LiveJobStreamProps) {
  const [filter, setFilter] = useState<FilterStatus>('all');

  const filteredJobs = useMemo(() => {
    let filtered = [...jobs];

    switch (filter) {
      case 'active':
        filtered = filtered.filter(j => j.status === 'running' || j.status === 'approved');
        break;
      case 'completed':
        filtered = filtered.filter(j => j.status === 'completed');
        break;
      case 'failed':
        filtered = filtered.filter(j => j.status === 'failed' || j.status === 'cancelled');
        break;
      case 'pending':
        filtered = filtered.filter(j => j.status === 'pending' || j.status === 'needs_review');
        break;
    }

    // Sort by created_at descending (newest first)
    return filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [jobs, filter]);

  const pendingCount = jobs.filter(j => j.status === 'pending').length;
  const runningCount = jobs.filter(j => j.status === 'running').length;

  return (
    <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-700/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Play className="w-5 h-5 text-cyan-400" />
            <h2 className="text-lg font-semibold text-white">Live Job Stream</h2>
            {isConnected ? (
              <span className="flex items-center gap-1 text-xs text-green-400">
                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                Live
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs text-yellow-400">
                <span className="w-2 h-2 bg-yellow-400 rounded-full" />
                Polling
              </span>
            )}
          </div>

          {/* Status badges */}
          <div className="flex items-center gap-2">
            {pendingCount > 0 && (
              <span className="px-2 py-1 text-xs font-medium text-orange-400 bg-orange-500/20 rounded-full animate-pulse">
                {pendingCount} pending
              </span>
            )}
            {runningCount > 0 && (
              <span className="px-2 py-1 text-xs font-medium text-cyan-400 bg-cyan-500/20 rounded-full">
                {runningCount} running
              </span>
            )}
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 mt-3">
          {(['all', 'active', 'pending', 'completed', 'failed'] as FilterStatus[]).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`
                px-3 py-1 text-xs font-medium rounded transition-colors
                ${filter === f
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
                }
              `}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Jobs list */}
      <div className="p-4 space-y-3 max-h-[500px] overflow-y-auto">
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="border border-gray-700/50 rounded-lg p-4 animate-pulse">
                <div className="flex items-center gap-3">
                  <div className="w-4 h-4 bg-gray-700 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <div className="h-3 bg-gray-700 rounded w-1/3" />
                    <div className="h-4 bg-gray-700/50 rounded w-2/3" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No jobs match the current filter</p>
          </div>
        ) : (
          filteredJobs.map(job => (
            <JobCard
              key={job.id}
              job={job}
              onApprove={onApprove}
              onReject={onReject}
              onCancel={onCancel}
            />
          ))
        )}
      </div>
    </div>
  );
}

export default LiveJobStream;
