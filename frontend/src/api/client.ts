import axios from 'axios';
import type {
  Project,
  Alert,
  Metric,
  MetricsSummary,
  DashboardData,
  PipelineStatus,
  HealthCheck,
  FinancialRecord,
  FinancialRecordCreate,
  FinancialGoal,
  FinancialGoalCreate,
  FinancialGoalUpdate,
  FinancialDashboard,
  QuickStats,
  FinancialRecordType,
  GoalStatus,
  MessageResponse,
} from '../types';

import type {
  NHJob,
  NHJobSubmitRequest,
  NHQueueStatus,
  NHAFKStatus,
  NHAFKStartRequest,
  NHHealthStatus,
} from '../types';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Health
export const getHealth = async (): Promise<HealthCheck> => {
  const { data } = await axios.get('/health');
  return data;
};

// Dashboard
export const getDashboard = async (): Promise<DashboardData> => {
  const { data } = await api.get('/dashboard/');
  return data;
};

export const getPipelineStatus = async (): Promise<PipelineStatus> => {
  const { data } = await api.get('/pipeline/status');
  return data;
};

// Projects
export const getProjects = async (): Promise<Project[]> => {
  const { data } = await api.get('/projects/');
  return data;
};

export const createProject = async (project: Omit<Project, 'id' | 'created_at' | 'updated_at'>): Promise<Project> => {
  const { data } = await api.post('/projects/', project);
  return data;
};

export const updateProject = async (id: number, project: Partial<Project>): Promise<Project> => {
  const { data } = await api.put(`/projects/${id}`, project);
  return data;
};

export const deleteProject = async (id: number): Promise<void> => {
  await api.delete(`/projects/${id}`);
};

// Alerts
export const getAlerts = async (): Promise<Alert[]> => {
  const { data } = await api.get('/alerts/');
  return data;
};

export const getActiveAlerts = async (): Promise<Alert[]> => {
  const { data } = await api.get('/alerts/active');
  return data;
};

export const createAlert = async (alert: Omit<Alert, 'id' | 'acknowledged' | 'acknowledged_at' | 'created_at' | 'updated_at'>): Promise<Alert> => {
  const { data } = await api.post('/alerts/', alert);
  return data;
};

export const acknowledgeAlert = async (id: string): Promise<Alert> => {
  const { data } = await api.put(`/alerts/${id}/acknowledge`);
  return data;
};

// Metrics
export const getMetrics = async (): Promise<Metric[]> => {
  const { data } = await api.get('/metrics/');
  return data;
};

export const getMetricsSummary = async (): Promise<MetricsSummary> => {
  const { data } = await api.get('/metrics/summary');
  return data;
};

export const createMetric = async (metric: Omit<Metric, 'id' | 'created_at' | 'updated_at'>): Promise<Metric> => {
  const { data } = await api.post('/metrics/', metric);
  return data;
};

// NH API - Neural Holding Integration
export const getNHHealth = async (): Promise<NHHealthStatus> => {
  const { data } = await api.get('/nh/health');
  return data;
};

export const getNHJobs = async (status?: string, limit = 50): Promise<NHJob[]> => {
  const params: Record<string, unknown> = { limit };
  if (status) params.status = status;
  const { data } = await api.get('/nh/jobs', { params });
  return data;
};

export const getNHPendingJobs = async (): Promise<NHJob[]> => {
  const { data } = await api.get('/nh/jobs/pending');
  return data;
};

export const getNHJob = async (jobId: string): Promise<NHJob> => {
  const { data } = await api.get(`/nh/jobs/${jobId}`);
  return data;
};

export const submitNHJob = async (job: NHJobSubmitRequest): Promise<NHJob> => {
  const { data } = await api.post('/nh/jobs/submit', job);
  return data;
};

export const approveNHJob = async (jobId: string): Promise<NHJob> => {
  const { data } = await api.post(`/nh/jobs/${jobId}/approve`);
  return data;
};

export const rejectNHJob = async (jobId: string, reason?: string): Promise<NHJob> => {
  const { data } = await api.post(`/nh/jobs/${jobId}/reject`, { reason });
  return data;
};

export const cancelNHJob = async (jobId: string): Promise<NHJob> => {
  const { data } = await api.post(`/nh/jobs/${jobId}/cancel`);
  return data;
};

export const getNHQueueStatus = async (): Promise<NHQueueStatus> => {
  const { data } = await api.get('/nh/queue/status');
  return data;
};

export const getNHAFKStatus = async (): Promise<NHAFKStatus> => {
  const { data } = await api.get('/nh/afk/status');
  return data;
};

export const startNHAFK = async (request: NHAFKStartRequest): Promise<NHAFKStatus> => {
  const { data } = await api.post('/nh/afk/start', request);
  return data;
};

export const stopNHAFK = async (): Promise<NHAFKStatus> => {
  const { data } = await api.post('/nh/afk/stop');
  return data;
};

export const getNHBriefing = async (): Promise<unknown> => {
  const { data } = await api.get('/nh/briefing');
  return data;
};

export const generateNHBriefing = async (): Promise<unknown> => {
  const { data } = await api.post('/nh/briefing/generate');
  return data;
};

export const getNHProjects = async (): Promise<unknown[]> => {
  const { data } = await api.get('/nh/projects');
  return data;
};

export const getNHStrategy = async (): Promise<unknown> => {
  const { data } = await api.get('/nh/strategy/master');
  return data;
};

export const getNHGaps = async (): Promise<unknown[]> => {
  const { data } = await api.get('/nh/gaps');
  return data;
};

// ==========================================================================
// Finance API
// ==========================================================================

// Financial Records
export const getFinancialRecords = async (params?: {
  record_type?: FinancialRecordType;
  start_date?: string;
  end_date?: string;
  category?: string;
  source?: string;
  limit?: number;
  offset?: number;
}): Promise<FinancialRecord[]> => {
  const { data } = await api.get('/finance/records', { params });
  return data;
};

export const createFinancialRecord = async (record: FinancialRecordCreate): Promise<FinancialRecord> => {
  const { data } = await api.post('/finance/records', record);
  return data;
};

export const getFinancialRecord = async (id: string): Promise<FinancialRecord> => {
  const { data } = await api.get(`/finance/records/${id}`);
  return data;
};

export const updateFinancialRecord = async (
  id: string,
  record: Partial<FinancialRecordCreate>
): Promise<FinancialRecord> => {
  const { data } = await api.patch(`/finance/records/${id}`, record);
  return data;
};

export const deleteFinancialRecord = async (id: string): Promise<MessageResponse> => {
  const { data } = await api.delete(`/finance/records/${id}`);
  return data;
};

// Financial Goals
export const getFinancialGoals = async (status?: GoalStatus): Promise<FinancialGoal[]> => {
  const params = status ? { status_filter: status } : undefined;
  const { data } = await api.get('/finance/goals', { params });
  return data;
};

export const createFinancialGoal = async (goal: FinancialGoalCreate): Promise<FinancialGoal> => {
  const { data } = await api.post('/finance/goals', goal);
  return data;
};

export const getFinancialGoal = async (id: string): Promise<FinancialGoal> => {
  const { data } = await api.get(`/finance/goals/${id}`);
  return data;
};

export const updateFinancialGoal = async (
  id: string,
  goal: FinancialGoalUpdate
): Promise<FinancialGoal> => {
  const { data } = await api.patch(`/finance/goals/${id}`, goal);
  return data;
};

export const deleteFinancialGoal = async (id: string): Promise<MessageResponse> => {
  const { data } = await api.delete(`/finance/goals/${id}`);
  return data;
};

export const setNorthStarGoal = async (id: string): Promise<FinancialGoal> => {
  const { data } = await api.post(`/finance/goals/${id}/set-north-star`);
  return data;
};

// Dashboard & Stats
export const getFinanceQuickStats = async (): Promise<QuickStats> => {
  const { data } = await api.get('/finance/quick-stats');
  return data;
};

export const getFinanceDashboard = async (): Promise<FinancialDashboard> => {
  const { data } = await api.get('/finance/dashboard');
  return data;
};

// ==========================================================================
// CC Session API (EPOCH 8 - Visibility & Reliability)
// ==========================================================================

import type {
  CCSession,
  CCSessionCreateRequest,
  CCSessionTaskRequest,
  CCSessionOutput,
  CCSessionScreen,
} from '../types';

export const getCCSessions = async (
  status?: string,
  pipeline_run_id?: string
): Promise<CCSession[]> => {
  const params: Record<string, unknown> = {};
  if (status) params.status_filter = status;
  if (pipeline_run_id) params.pipeline_run_id = pipeline_run_id;
  const { data } = await api.get('/cc-sessions', { params });
  return data;
};

export const createCCSession = async (
  request: CCSessionCreateRequest
): Promise<CCSession> => {
  const { data } = await api.post('/cc-sessions', request);
  return data;
};

export const getCCSession = async (sessionId: string): Promise<CCSession> => {
  const { data } = await api.get(`/cc-sessions/${sessionId}`);
  return data;
};

export const sendCCSessionTask = async (
  sessionId: string,
  request: CCSessionTaskRequest
): Promise<CCSession> => {
  const { data } = await api.post(`/cc-sessions/${sessionId}/task`, request);
  return data;
};

export const sendCCSessionCommand = async (
  sessionId: string,
  command: string
): Promise<{ status: string; command: string }> => {
  const { data } = await api.post(`/cc-sessions/${sessionId}/command`, { command });
  return data;
};

export const getCCSessionOutput = async (
  sessionId: string,
  tail = 100
): Promise<CCSessionOutput> => {
  const { data } = await api.get(`/cc-sessions/${sessionId}/output`, {
    params: { tail },
  });
  return data;
};

export const getCCSessionScreen = async (
  sessionId: string
): Promise<CCSessionScreen> => {
  const { data } = await api.get(`/cc-sessions/${sessionId}/screen`);
  return data;
};

export const restartCCSession = async (sessionId: string): Promise<CCSession> => {
  const { data } = await api.post(`/cc-sessions/${sessionId}/restart`);
  return data;
};

export const killCCSession = async (sessionId: string): Promise<void> => {
  await api.delete(`/cc-sessions/${sessionId}`);
};

export const getCCSessionStreamUrl = (sessionId: string): string => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/api/v1/cc-sessions/${sessionId}/stream`;
};

// ==========================================================================
// Interactive CC Session API (EPOCH 9)
// ==========================================================================

export interface InteractiveSessionResponse {
  session_id: string;
  session_name: string;
  status: string;
  mode: string;
  platform: string;
  working_directory: string;
  pipeline_run_id?: string;
  stage_id?: string;
  task_prompt?: string;
  dangerous_mode: boolean;
  started_at?: string;
  runtime_seconds: number;
  output_lines: number;
  prompt_count: number;
  event_count: number;
}

export interface SessionEvent {
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

export interface EventsResponse {
  session_id: string;
  events: SessionEvent[];
  total_events: number;
  tool_summary: Record<string, number>;
  error_summary: Record<string, number>;
}

export const createInteractiveSession = async (
  workingDirectory: string,
  pipelineRunId?: string,
  stageId?: string,
  dangerousMode = true
): Promise<InteractiveSessionResponse> => {
  const { data } = await api.post('/cc-sessions/interactive', {
    working_directory: workingDirectory,
    pipeline_run_id: pipelineRunId,
    stage_id: stageId,
    dangerous_mode: dangerousMode,
  });
  return data;
};

export const sendInteractivePrompt = async (
  sessionId: string,
  prompt: string
): Promise<InteractiveSessionResponse> => {
  const { data } = await api.post(`/cc-sessions/${sessionId}/prompt`, {
    prompt,
  });
  return data;
};

export const sendInteractiveInput = async (
  sessionId: string,
  text: string
): Promise<{ status: string; text: string }> => {
  const { data } = await api.post(`/cc-sessions/${sessionId}/input`, {
    text,
  });
  return data;
};

export const getCCSessionEvents = async (
  sessionId: string,
  eventType?: string,
  limit = 100
): Promise<EventsResponse> => {
  const params: Record<string, unknown> = { limit };
  if (eventType) params.event_type = eventType;
  const { data } = await api.get(`/cc-sessions/${sessionId}/events`, { params });
  return data;
};

export const stopInteractiveSession = async (
  sessionId: string
): Promise<{ status: string; session_id: string; final_status: string }> => {
  const { data } = await api.post(`/cc-sessions/${sessionId}/stop`);
  return data;
};

export default api;
