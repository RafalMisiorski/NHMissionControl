import {
  Briefcase,
  Play,
  Pause,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  RotateCcw,
  Eye,
} from 'lucide-react';
import type { NHJob, NHJobStatus } from '../types';

interface JobsListProps {
  jobs: NHJob[];
}

const statusConfig: Record<NHJobStatus, { icon: typeof Play; color: string; bg: string }> = {
  pending: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
  approved: { icon: CheckCircle, color: 'text-blue-400', bg: 'bg-blue-500/20' },
  running: { icon: Play, color: 'text-green-400', bg: 'bg-green-500/20' },
  paused: { icon: Pause, color: 'text-orange-400', bg: 'bg-orange-500/20' },
  completed: { icon: CheckCircle, color: 'text-cyan-400', bg: 'bg-cyan-500/20' },
  failed: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/20' },
  cancelled: { icon: XCircle, color: 'text-gray-400', bg: 'bg-gray-500/20' },
  spawned_retry: { icon: RotateCcw, color: 'text-purple-400', bg: 'bg-purple-500/20' },
  needs_review: { icon: Eye, color: 'text-amber-400', bg: 'bg-amber-500/20' },
};

const priorityColors: Record<string, string> = {
  critical: 'text-red-400 bg-red-500/20 border-red-500/30',
  high: 'text-orange-400 bg-orange-500/20 border-orange-500/30',
  normal: 'text-blue-400 bg-blue-500/20 border-blue-500/30',
  low: 'text-gray-400 bg-gray-500/20 border-gray-500/30',
  background: 'text-slate-400 bg-slate-500/20 border-slate-500/30',
};

function getProjectName(projectPath: string): string {
  const parts = projectPath.split(/[/\\]/);
  return parts[parts.length - 1] || projectPath;
}

function formatTime(dateString: string | undefined): string {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function JobsList({ jobs }: JobsListProps) {
  // Sort jobs: running first, then pending, then by created_at descending
  const sortedJobs = [...jobs].sort((a, b) => {
    const statusOrder: Record<string, number> = {
      running: 0,
      pending: 1,
      approved: 2,
      needs_review: 3,
      paused: 4,
      spawned_retry: 5,
      completed: 6,
      failed: 7,
      cancelled: 8,
    };
    const orderA = statusOrder[a.status] ?? 10;
    const orderB = statusOrder[b.status] ?? 10;
    if (orderA !== orderB) return orderA - orderB;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  // Limit to 20 most relevant jobs
  const displayJobs = sortedJobs.slice(0, 20);

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <Briefcase className="w-5 h-5" />
        Jobs
        <span className="text-gray-400 text-sm font-normal">({jobs.length})</span>
      </h2>
      {jobs.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          <Briefcase className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No jobs found</p>
          <p className="text-sm mt-1">Jobs from the NH API will appear here</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {displayJobs.map((job) => {
            const config = statusConfig[job.status] || statusConfig.pending;
            const Icon = config.icon;
            const priorityClass = priorityColors[job.priority] || priorityColors.normal;

            return (
              <div
                key={job.id}
                className="flex items-center justify-between p-3 rounded-lg bg-slate-700/30 hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <div className={`p-2 rounded-lg ${config.bg} flex-shrink-0`}>
                    <Icon className={`w-4 h-4 ${config.color}`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-white truncate">
                        {job.description || `${job.type} job`}
                      </h3>
                      <span className={`text-xs px-2 py-0.5 rounded border ${priorityClass} flex-shrink-0`}>
                        {job.priority}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-sm text-gray-400 truncate">
                        {getProjectName(job.project_path)}
                      </span>
                      <span className="text-xs text-gray-500">
                        {job.type}
                      </span>
                      {job.requires_approval && !job.auto_approved_by_afk && (
                        <span title="Requires approval">
                          <AlertTriangle className="w-3 h-3 text-yellow-400" />
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0 ml-2">
                  <span className="text-xs text-gray-500">
                    {formatTime(job.started_at || job.created_at)}
                  </span>
                  <span className={`text-xs ${config.color} uppercase font-medium min-w-[70px] text-right`}>
                    {job.status.replace('_', ' ')}
                  </span>
                </div>
              </div>
            );
          })}
          {jobs.length > 20 && (
            <div className="text-center py-2 text-gray-500 text-sm">
              Showing 20 of {jobs.length} jobs
            </div>
          )}
        </div>
      )}
    </div>
  );
}
