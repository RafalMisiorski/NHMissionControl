/**
 * NH Mission Control - Frontend Types
 * ====================================
 *
 * Combined types from scaffold + existing NH types.
 * Keep in sync with backend schemas.
 */

// ==========================================================================
// Type Constants (using const objects instead of enums for erasableSyntaxOnly)
// ==========================================================================

export const UserRole = {
  ADMIN: 'admin',
  USER: 'user',
} as const;
export type UserRole = typeof UserRole[keyof typeof UserRole];

export const OpportunitySource = {
  UPWORK: 'upwork',
  USEME: 'useme',
  DIRECT: 'direct',
  REFERRAL: 'referral',
  OTHER: 'other',
} as const;
export type OpportunitySource = typeof OpportunitySource[keyof typeof OpportunitySource];

export const OpportunityStatus = {
  LEAD: 'lead',
  QUALIFIED: 'qualified',
  PROPOSAL: 'proposal',
  NEGOTIATING: 'negotiating',
  WON: 'won',
  DELIVERED: 'delivered',
  LOST: 'lost',
} as const;
export type OpportunityStatus = typeof OpportunityStatus[keyof typeof OpportunityStatus];

export const ProjectStatus = {
  NOT_STARTED: 'not_started',
  IN_PROGRESS: 'in_progress',
  REVIEW: 'review',
  COMPLETED: 'completed',
  ON_HOLD: 'on_hold',
  CANCELLED: 'cancelled',
} as const;
export type ProjectStatus = typeof ProjectStatus[keyof typeof ProjectStatus];

export const FinancialRecordType = {
  INCOME: 'income',
  EXPENSE: 'expense',
} as const;
export type FinancialRecordType = typeof FinancialRecordType[keyof typeof FinancialRecordType];

export const TaskMode = {
  YOLO: 'yolo',
  CHECKPOINTED: 'checkpointed',
  SUPERVISED: 'supervised',
} as const;
export type TaskMode = typeof TaskMode[keyof typeof TaskMode];

// ==========================================================================
// Auth Types
// ==========================================================================

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  email_verified: boolean;
  last_login: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  email: string;
  password: string;
  name: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface UserUpdate {
  name?: string;
  email?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// ==========================================================================
// NH Job Types (Mission Control specific)
// ==========================================================================

export type NHJobStatus = 'pending' | 'approved' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused' | 'needs_review' | 'spawned_retry';

export interface NHJob {
  id: string;
  type: string;
  project_path: string;
  description: string;
  full_description?: string;
  priority: 'low' | 'medium' | 'high';
  status: NHJobStatus;
  requires_approval: boolean;
  auto_approved_by_afk: boolean;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  output?: string;
  error?: string;
  evidence?: {
    item_count: number;
    is_sufficient: boolean;
  };
}

export interface NHJobSubmitRequest {
  project: string;
  description: string;
  task: string;
  priority?: 'low' | 'medium' | 'high';
}

export interface NHQueueStatus {
  total: number;
  total_jobs: number;
  pending: number;
  pending_jobs: number;
  running: number;
  running_jobs: number;
  completed: number;
  completed_jobs: number;
  failed: number;
  failed_jobs: number;
}

export interface NHAFKStatus {
  active: boolean;
  started_at?: string;
  duration_hours: number;
  remaining_hours: number;
  jobs_completed: number;
  jobs_failed: number;
  jobs_processed: number;
}

export interface NHAFKStartRequest {
  duration_hours: number;
}

export interface NHHealthStatus {
  status: 'ok' | 'degraded' | 'down';
  service: string;
  timestamp: string;
  governor?: string;
  queue_size?: number;
}

// ==========================================================================
// Dashboard Types
// ==========================================================================

export interface Project {
  id: string;
  name: string;
  path: string;
  status: 'active' | 'paused' | 'completed' | 'archived';
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface Alert {
  id: string;
  type: 'info' | 'warning' | 'error' | 'critical';
  severity: 'info' | 'warning' | 'error' | 'critical';
  title: string;
  message: string;
  created_at: string;
  acknowledged: boolean;
}

export interface Metric {
  name: string;
  value: number;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
}

export interface MetricsSummary {
  total_jobs: number;
  running_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  success_rate: number;
}

export interface DashboardData {
  metrics: MetricsSummary;
  projects: Project[];
  alerts: Alert[];
}

export interface PipelineStatus {
  running: number;
  queued: number;
  completed: number;
  failed: number;
}

export interface HealthCheck {
  status: 'ok' | 'degraded' | 'down';
  service: string;
  timestamp: string;
  version?: string;
}

// ==========================================================================
// Opportunity Types
// ==========================================================================

export interface Opportunity {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  external_url: string | null;
  source: OpportunitySource;
  status: OpportunityStatus;
  value: number | null;
  currency: string;
  probability: number;
  client_name: string | null;
  client_rating: number | null;
  client_total_spent: number | null;
  client_location: string | null;
  tech_stack: string[] | null;
  nh_score: number | null;
  nh_analysis: Record<string, unknown> | null;
  deadline: string | null;
  expected_close_date: string | null;
  notes: string | null;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface OpportunityCreate {
  title: string;
  description?: string;
  external_url?: string;
  source?: OpportunitySource;
  value?: number;
  currency?: string;
  probability?: number;
  client_name?: string;
  client_rating?: number;
  client_total_spent?: number;
  client_location?: string;
  tech_stack?: string[];
  deadline?: string;
  expected_close_date?: string;
  notes?: string;
}

export type OpportunityUpdate = Partial<OpportunityCreate>;

export interface OpportunityListResponse {
  items: Opportunity[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ==========================================================================
// Pipeline Stats Types
// ==========================================================================

export interface PipelineStageStats {
  status: OpportunityStatus;
  count: number;
  total_value: number;
  weighted_value: number;
}

export interface PipelineStatsExtended {
  stages: PipelineStageStats[];
  total_opportunities: number;
  total_value: number;
  weighted_pipeline_value: number;
  conversion_rate: number;
  avg_deal_size: number;
  opportunities_by_source: Record<string, number>;
}

// ==========================================================================
// NH Analysis Types
// ==========================================================================

export interface OpportunityAnalysis {
  opportunity_id: string;
  score: number;
  budget_fit_score: number;
  client_quality_score: number;
  technical_fit_score: number;
  timeline_fit_score: number;
  competition_score: number;
  strengths: string[];
  risks: string[];
  recommendations: string[];
  sw_difficulty_tier: number;
  recommended_mode: TaskMode;
  estimated_hours: number;
  estimated_sw_hours: number;
  suggested_price: number;
  analyzed_at: string;
}

export interface ProposalDraft {
  opportunity_id: string;
  subject: string;
  greeting: string;
  intro: string;
  approach: string;
  timeline: string;
  pricing: string;
  closing: string;
  word_count: number;
  estimated_reading_time_seconds: number;
  clarifying_questions: string[];
  generated_at: string;
}

export interface EffortEstimate {
  opportunity_id: string;
  total_hours: number;
  breakdown: {
    phase: string;
    hours: number;
    description: string;
  }[];
  confidence: number;
  assumptions: string[];
  risks: string[];
  recommended_timeline_days: number;
  estimated_at: string;
}

// ==========================================================================
// Financial Types
// ==========================================================================

export interface FinancialRecord {
  id: string;
  user_id: string;
  record_type: FinancialRecordType;
  category: string;
  amount: number;
  currency: string;
  source: string;
  description: string | null;
  record_date: string;
  project_id: string | null;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface FinancialSummary {
  period_start: string;
  period_end: string;
  total_income: number;
  income_by_source: Record<string, number>;
  income_by_category: Record<string, number>;
  total_expenses: number;
  expenses_by_category: Record<string, number>;
  net_income: number;
  previous_period_income: number | null;
  income_change_percent: number | null;
}

export const GoalStatus = {
  ACTIVE: 'active',
  PAUSED: 'paused',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
} as const;
export type GoalStatus = typeof GoalStatus[keyof typeof GoalStatus];

export interface FinancialGoal {
  id: string;
  user_id: string;
  name: string;
  target_amount: number;
  current_amount: number;
  currency: string;
  deadline: string | null;
  status: GoalStatus;
  is_north_star: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface FinancialGoalCreate {
  name: string;
  target_amount: number;
  current_amount?: number;
  currency?: string;
  deadline?: string;
  is_north_star?: boolean;
  notes?: string;
}

export interface FinancialGoalUpdate {
  name?: string;
  target_amount?: number;
  current_amount?: number;
  currency?: string;
  deadline?: string;
  status?: GoalStatus;
  is_north_star?: boolean;
  notes?: string;
}

export interface GoalProgress {
  goal_id: string;
  name: string;
  target_amount: number;
  current_amount: number;
  currency: string;
  progress_percent: number;
  remaining_amount: number;
  is_north_star: boolean;
  status: GoalStatus;
  days_remaining: number | null;
}

export interface QuickStats {
  mtd_income: number;
  mtd_expenses: number;
  mtd_net: number;
  ytd_income: number;
  ytd_expenses: number;
  ytd_net: number;
  income_change_percent: number | null;
  expense_change_percent: number | null;
}

export interface FinancialDashboard {
  quick_stats: QuickStats;
  north_star: GoalProgress | null;
  goals: GoalProgress[];
  recent_income: FinancialRecord[];
  recent_expenses: FinancialRecord[];
  income_by_source: Record<string, number>;
  expenses_by_category: Record<string, number>;
}

export interface FinancialRecordCreate {
  record_type: FinancialRecordType;
  category: string;
  amount: number;
  currency?: string;
  source: string;
  description?: string;
  record_date: string;
  project_id?: string;
}

// ==========================================================================
// Signal Factory Types (for SF components)
// ==========================================================================

export interface AgentStats {
  agent_name: string;
  total_actions: number;
  success_count: number;
  success_rate: number;
  avg_cost_per_action: number;
  common_failures: string[];
}

// ==========================================================================
// Memory Cortex Types
// ==========================================================================

export interface SessionLog {
  id: string;
  session_id: string;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  tasks_attempted: number;
  tasks_completed: number;
  tasks_failed: number;
  errors_total: number;
  errors_self_resolved: number;
  rollbacks: number;
  patterns_discovered: unknown[] | null;
  anti_patterns_discovered: unknown[] | null;
  claude_md_suggestions: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface PatternType {
  id: string;
  pattern_type: string;
  task_types: string[];
  description: string;
  recommendation: string;
  claude_md_snippet: string | null;
  evidence_count: number;
  confidence: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TaskClassificationType {
  id: string;
  task_type: string;
  recommended_mode: TaskMode;
  sample_count: number;
  success_rate: number;
  avg_time_seconds: number;
  human_intervention_rate: number;
  common_errors: string[] | null;
  created_at: string;
  updated_at: string;
}

// ==========================================================================
// API Response Types
// ==========================================================================

export interface MessageResponse {
  message: string;
  success: boolean;
}

export interface ErrorResponse {
  error: string;
  detail?: string;
  code?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  database: string;
  redis: string;
}

// ==========================================================================
// CC Session Types (EPOCH 8 - Visibility & Reliability)
// ==========================================================================

export const CCSessionStatus = {
  IDLE: 'idle',
  STARTING: 'starting',
  RUNNING: 'running',
  STUCK: 'stuck',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CRASHED: 'crashed',
  RESTARTING: 'restarting',
} as const;
export type CCSessionStatus = typeof CCSessionStatus[keyof typeof CCSessionStatus];

export interface CCSession {
  session_id: string;
  session_name: string;
  status: CCSessionStatus;
  platform: string;
  working_directory: string;
  pipeline_run_id: string | null;
  stage_id: string | null;
  task_prompt: string | null;
  dangerous_mode: boolean;
  started_at: string | null;
  runtime_seconds: number;
  output_lines: number;
  restart_count: number;
  max_restarts: number;
  max_runtime_minutes: number;
  attach_command: string;
}

export interface CCSessionCreateRequest {
  working_directory: string;
  pipeline_run_id?: string;
  stage_id?: string;
  max_runtime_minutes?: number;
  max_restarts?: number;
}

export interface CCSessionTaskRequest {
  task_prompt: string;
  dangerous_mode?: boolean;
}

export interface CCSessionOutput {
  session_id: string;
  lines: string[];
  total_lines: number;
}

export interface CCSessionScreen {
  session_id: string;
  content: string;
}

export interface CCSessionStreamMessage {
  type: 'output' | 'heartbeat' | 'status_change' | 'status' | 'error' | 'close';
  data: {
    session_id?: string;
    session_name?: string;
    status?: CCSessionStatus;
    old_status?: CCSessionStatus;
    new_status?: CCSessionStatus;
    line_number?: number;
    content?: string;
    timestamp?: string;
    runtime_seconds?: number;
    output_lines?: number;
    message?: string;
    reason?: string;
  };
}
