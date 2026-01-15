import { useState, useCallback, useMemo } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  Zap,
  AlertTriangle,
  Cpu,
  Users,
  Clock,
  WifiOff,
  RefreshCw,
} from 'lucide-react';
import { Header, StatusCard, AlertsPanel, PipelineChart, LiveJobStream, ToastContainer, ErrorBoundary } from './components';
import Sidebar from './components/Sidebar';
import { useWebSocket } from './hooks/useWebSocket';
import * as api from './api/client';
import type { HealthCheck, PipelineStatus, Alert, NHQueueStatus, NHAFKStatus, NHJob } from './types';
import { Opportunities, Finance, NerveCenter, Assets, SystemOverview, PipelineDashboard, GuardrailsMonitor, CCSessions } from './pages';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchInterval: 30000,
      retry: 1,
    },
  },
});

const getWSUrl = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/ws/alerts`;
};

function Dashboard() {
  const qc = useQueryClient();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const { isConnected, toasts, dismissToast } = useWebSocket({
    url: getWSUrl(),
    onEvent: (event) => {
      if (event.event.startsWith('job_')) {
        qc.invalidateQueries({ queryKey: ['nhJobs'] });
        qc.invalidateQueries({ queryKey: ['nhQueueStatus'] });
      }
      if (event.event === 'afk_started' || event.event === 'afk_stopped') {
        qc.invalidateQueries({ queryKey: ['nhAFKStatus'] });
      }
    },
  });

  const { data: health, isLoading: healthLoading } = useQuery<HealthCheck>({
    queryKey: ['health'],
    queryFn: api.getHealth,
    retry: 1,
    retryDelay: 1000,
  });

  const { data: nhQueueStatus, isLoading: queueLoading, isError: queueError } = useQuery<NHQueueStatus>({
    queryKey: ['nhQueueStatus'],
    queryFn: api.getNHQueueStatus,
    retry: 1,
    retryDelay: 1000,
  });

  const { data: nhJobs = [], isLoading: jobsLoading, isError: jobsError } = useQuery<NHJob[]>({
    queryKey: ['nhJobs'],
    queryFn: () => api.getNHJobs(undefined, 100),
    retry: 1,
    retryDelay: 1000,
  });

  const { data: nhAFKStatus } = useQuery<NHAFKStatus>({
    queryKey: ['nhAFKStatus'],
    queryFn: api.getNHAFKStatus,
    retry: 1,
    retryDelay: 1000,
  });

  const { data: alerts = [], isLoading: alertsLoading } = useQuery<Alert[]>({
    queryKey: ['alerts'],
    queryFn: api.getAlerts,
    retry: 1,
    retryDelay: 1000,
  });

  // Determine if NH API is unavailable
  const nhUnavailable = queueError || jobsError;
  const isInitialLoading = healthLoading || queueLoading || jobsLoading || alertsLoading;

  const approveMutation = useMutation({
    mutationFn: api.approveNHJob,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['nhJobs'] });
      qc.invalidateQueries({ queryKey: ['nhQueueStatus'] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (jobId: string) => api.rejectNHJob(jobId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['nhJobs'] });
      qc.invalidateQueries({ queryKey: ['nhQueueStatus'] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: api.cancelNHJob,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['nhJobs'] });
      qc.invalidateQueries({ queryKey: ['nhQueueStatus'] });
    },
  });

  const acknowledgeMutation = useMutation({
    mutationFn: api.acknowledgeAlert,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const pipelineStatus: PipelineStatus = useMemo(() => {
    if (nhQueueStatus) {
      return {
        running: nhQueueStatus.running_jobs,
        queued: nhQueueStatus.pending_jobs,
        completed: nhQueueStatus.completed_jobs,
        failed: nhQueueStatus.failed_jobs,
      };
    }
    const running = nhJobs.filter(j => j.status === 'running').length;
    const queued = nhJobs.filter(j => j.status === 'pending' || j.status === 'approved').length;
    const completed = nhJobs.filter(j => j.status === 'completed').length;
    const failed = nhJobs.filter(j => j.status === 'failed').length;
    return { running, queued, completed, failed };
  }, [nhQueueStatus, nhJobs]);

  const uniqueProjects = useMemo(() => {
    const projectPaths = new Set(nhJobs.map(j => j.project_path));
    return projectPaths.size;
  }, [nhJobs]);

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    await Promise.all([
      qc.invalidateQueries({ queryKey: ['health'] }),
      qc.invalidateQueries({ queryKey: ['nhQueueStatus'] }),
      qc.invalidateQueries({ queryKey: ['nhJobs'] }),
      qc.invalidateQueries({ queryKey: ['nhAFKStatus'] }),
      qc.invalidateQueries({ queryKey: ['alerts'] }),
    ]);
    setIsRefreshing(false);
  }, [qc]);

  const activeAlerts = alerts.filter((a) => !a.acknowledged);
  const totalJobs = nhQueueStatus?.total_jobs ?? nhJobs.length;
  const afkActive = nhAFKStatus?.active ?? false;

  const systemHealth = useMemo(() => {
    if (totalJobs === 0) return 100;
    const failedCount = pipelineStatus.failed;
    const successRate = Math.round(((totalJobs - failedCount) / totalJobs) * 100);
    return Math.max(0, successRate);
  }, [totalJobs, pipelineStatus.failed]);

  return (
    <>
      <Header
        health={health || null}
        isLoading={isRefreshing}
        onRefresh={handleRefresh}
        afkActive={afkActive}
        isConnected={isConnected}
      />

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* NH API Unavailable Banner */}
        {nhUnavailable && !isInitialLoading && (
          <div className="mb-6 p-4 bg-red-900/30 border border-red-500/50 rounded-xl flex items-center gap-4 animate-fade-in">
            <WifiOff className="w-6 h-6 text-red-400 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-red-400">NH API Unavailable</h3>
              <p className="text-xs text-red-300/70">Unable to connect to Neural Holding. Some features may be limited.</p>
            </div>
            <button
              onClick={handleRefresh}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-red-600 hover:bg-red-500 rounded transition-colors"
            >
              <RefreshCw className={"w-3 h-3 " + (isRefreshing ? "animate-spin" : "")} />
              Retry
            </button>
          </div>
        )}

        {/* Loading Skeleton */}
        {isInitialLoading && (
          <div className="mb-6 p-4 bg-slate-800/50 border border-slate-700/50 rounded-xl flex items-center gap-3 animate-pulse">
            <div className="w-6 h-6 bg-slate-700 rounded-full" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-slate-700 rounded w-1/4" />
              <div className="h-3 bg-slate-700/50 rounded w-1/3" />
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatusCard
            title="Total Jobs"
            value={totalJobs}
            icon={<Activity className="w-8 h-8" />}
            color="blue"
          />
          <StatusCard
            title="Running Jobs"
            value={pipelineStatus.running}
            icon={<Zap className="w-8 h-8" />}
            color="green"
          />
          <StatusCard
            title="Queued Jobs"
            value={pipelineStatus.queued}
            icon={<Clock className="w-8 h-8" />}
            color="yellow"
          />
          <StatusCard
            title="System Health"
            value={`${systemHealth}%`}
            icon={<Cpu className="w-8 h-8" />}
            color={systemHealth >= 90 ? 'green' : systemHealth >= 70 ? 'yellow' : 'red'}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <StatusCard
            title="Projects"
            value={uniqueProjects}
            icon={<Users className="w-8 h-8" />}
            color="cyan"
          />
          <StatusCard
            title="Completed"
            value={pipelineStatus.completed}
            icon={<Activity className="w-8 h-8" />}
            color="blue"
          />
          <StatusCard
            title="Active Alerts"
            value={activeAlerts.length}
            icon={<AlertTriangle className="w-8 h-8" />}
            color={activeAlerts.length > 0 ? 'red' : 'green'}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <PipelineChart status={pipelineStatus} />
            <LiveJobStream
              jobs={nhJobs}
              onApprove={(id) => approveMutation.mutate(id)}
              onReject={(id) => rejectMutation.mutate(id)}
              onCancel={(id) => cancelMutation.mutate(id)}
              isConnected={isConnected}
              isLoading={jobsLoading}
            />
          </div>

          <div>
            <AlertsPanel
              alerts={alerts}
              onAcknowledge={(id) => acknowledgeMutation.mutate(id)}
            />
          </div>
        </div>
      </main>

      <footer className="border-t border-slate-700/50 mt-12">
        <div className="max-w-7xl mx-auto px-6 py-4 text-center text-gray-500 text-sm">
          NH Mission Control v2.0 - Neural Holding Operations
          {nhAFKStatus?.active && (
            <span className="ml-4 text-cyan-400">
              AFK Mode Active ({nhAFKStatus.jobs_processed} jobs processed)
            </span>
          )}
          {isConnected && (
            <span className="ml-4 text-green-400">
              Real-time Connected
            </span>
          )}
        </div>
      </footer>

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </>
  );
}

function AppContent() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 min-h-screen">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/pipeline" element={<PipelineDashboard />} />
          <Route path="/cc-sessions" element={<CCSessions />} />
          <Route path="/opportunities" element={<Opportunities />} />
          <Route path="/finance" element={<Finance />} />
          <Route path="/nerve-center" element={<NerveCenter />} />
          <Route path="/nerve-center/:sessionId" element={<NerveCenter />} />
          <Route path="/assets" element={<Assets />} />
          <Route path="/guardrails" element={<GuardrailsMonitor />} />
          <Route path="/system" element={<SystemOverview />} />
        </Routes>
      </div>
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
