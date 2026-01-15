/**
 * NH Project Analyzer - Core Types
 * ==================================
 * 
 * Types for project analysis, execution tracking, and real-time monitoring.
 */

// ==========================================================================
// Project Analysis Types
// ==========================================================================

export type ProjectStatus = 
  | 'pending'
  | 'analyzing' 
  | 'planning'
  | 'executing'
  | 'paused'
  | 'completed'
  | 'failed';

export type PhaseStatus = 
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'skipped';

export type TaskStatus = 
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'skipped';

export type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'success';

// ==========================================================================
// Project Structure
// ==========================================================================

export interface ProjectFile {
  path: string;
  name: string;
  extension: string;
  size: number;
  lines?: number;
  type: 'component' | 'hook' | 'util' | 'style' | 'config' | 'test' | 'other';
  language: 'typescript' | 'javascript' | 'python' | 'css' | 'json' | 'other';
  imports?: string[];
  exports?: string[];
  complexity?: number;
  issues?: string[];
}

export interface ProjectDirectory {
  path: string;
  name: string;
  files: ProjectFile[];
  subdirectories: ProjectDirectory[];
  totalFiles: number;
  totalLines: number;
}

export interface TechStack {
  frontend: {
    framework: string;
    version: string;
    ui_libraries: string[];
    state_management: string[];
    build_tool: string;
  };
  backend: {
    framework: string;
    version: string;
    database: string;
    orm: string;
    auth: string;
  };
  ai_integration: string[];
  testing: string[];
  deployment: string[];
}

export interface ProjectAnalysis {
  id: string;
  project_path: string;
  project_name: string;
  analyzed_at: string;
  
  // Structure
  structure: ProjectDirectory;
  tech_stack: TechStack;
  
  // Metrics
  total_files: number;
  total_lines: number;
  total_components: number;
  total_hooks: number;
  total_api_endpoints: number;
  
  // Quality
  complexity_score: number;  // 0-100
  maintainability_score: number;  // 0-100
  scalability_score: number;  // 0-100
  
  // Issues
  critical_issues: Issue[];
  warnings: Issue[];
  suggestions: Issue[];
  
  // Dependencies
  dependencies: Dependency[];
  outdated_dependencies: Dependency[];
}

export interface Issue {
  id: string;
  severity: 'critical' | 'warning' | 'suggestion';
  category: string;
  file?: string;
  line?: number;
  message: string;
  recommendation: string;
}

export interface Dependency {
  name: string;
  current_version: string;
  latest_version?: string;
  is_outdated: boolean;
  is_dev: boolean;
}

// ==========================================================================
// Execution Plan Types
// ==========================================================================

export interface ExecutionPlan {
  id: string;
  project_id: string;
  name: string;
  description: string;
  created_at: string;
  status: ProjectStatus;
  
  // Phases
  phases: ExecutionPhase[];
  current_phase_index: number;
  
  // Progress
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  progress_percent: number;
  
  // Timing
  estimated_duration_minutes: number;
  actual_duration_minutes?: number;
  started_at?: string;
  completed_at?: string;
}

export interface ExecutionPhase {
  id: string;
  name: string;
  description: string;
  order: number;
  status: PhaseStatus;
  
  // Tasks
  tasks: ExecutionTask[];
  current_task_index: number;
  
  // Progress
  total_tasks: number;
  completed_tasks: number;
  progress_percent: number;
  
  // Timing
  estimated_duration_minutes: number;
  actual_duration_minutes?: number;
  started_at?: string;
  completed_at?: string;
}

export interface ExecutionTask {
  id: string;
  name: string;
  description: string;
  order: number;
  status: TaskStatus;
  
  // Details
  type: 'analyze' | 'generate' | 'modify' | 'create' | 'delete' | 'test' | 'validate';
  target_file?: string;
  
  // Progress (for long tasks)
  progress_percent: number;
  current_step?: string;
  
  // Timing
  estimated_duration_seconds: number;
  actual_duration_seconds?: number;
  started_at?: string;
  completed_at?: string;
  
  // Result
  output?: string;
  error?: string;
  artifacts?: string[];  // Created/modified files
}

// ==========================================================================
// Real-time Log Types
// ==========================================================================

export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  phase_id?: string;
  task_id?: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ExecutionState {
  plan: ExecutionPlan;
  logs: LogEntry[];
  is_running: boolean;
  can_pause: boolean;
  can_resume: boolean;
  can_cancel: boolean;
}

// ==========================================================================
// WebSocket Message Types
// ==========================================================================

export type WSMessageType = 
  | 'plan_update'
  | 'phase_start'
  | 'phase_complete'
  | 'task_start'
  | 'task_progress'
  | 'task_complete'
  | 'task_error'
  | 'log'
  | 'error'
  | 'completed';

export interface WSMessage {
  type: WSMessageType;
  timestamp: string;
  payload: unknown;
}

export interface WSPlanUpdate {
  plan: ExecutionPlan;
}

export interface WSPhaseEvent {
  phase_id: string;
  phase: ExecutionPhase;
}

export interface WSTaskEvent {
  phase_id: string;
  task_id: string;
  task: ExecutionTask;
}

export interface WSTaskProgress {
  phase_id: string;
  task_id: string;
  progress_percent: number;
  current_step: string;
}

export interface WSLogEvent {
  entry: LogEntry;
}

// ==========================================================================
// NH Recommendations
// ==========================================================================

export interface ArchitectureRecommendation {
  id: string;
  category: 'structure' | 'performance' | 'scalability' | 'maintainability' | 'adhd_ux';
  priority: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  current_state: string;
  recommended_state: string;
  rationale: string;
  implementation_steps: string[];
  estimated_effort_hours: number;
  impact_score: number;  // 0-100
}

export interface UIRecommendation {
  id: string;
  component: string;
  issue: string;
  recommendation: string;
  adhd_benefit: string;
  mockup_url?: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
}

export interface RefactoringPlan {
  id: string;
  project_analysis: ProjectAnalysis;
  target_architecture: string;  // e.g., "notion-level"
  
  // Recommendations
  architecture_recommendations: ArchitectureRecommendation[];
  ui_recommendations: UIRecommendation[];
  
  // Phases
  phases: RefactoringPhase[];
  
  // Metrics
  total_estimated_hours: number;
  complexity_reduction_percent: number;
  scalability_improvement_percent: number;
}

export interface RefactoringPhase {
  id: string;
  name: string;
  priority: 'P0' | 'P1' | 'P2' | 'P3' | 'P4';
  description: string;
  tasks: RefactoringTask[];
  dependencies: string[];  // Phase IDs
  estimated_hours: number;
}

export interface RefactoringTask {
  id: string;
  name: string;
  description: string;
  type: 'migration' | 'refactor' | 'new_feature' | 'optimization' | 'ui_redesign';
  files_affected: string[];
  estimated_hours: number;
  auto_executable: boolean;  // Can NH execute this automatically?
}
