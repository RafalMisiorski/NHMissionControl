"""
NH Project Analyzer - Analysis Engine
======================================

Analyzes project structure, generates refactoring plans,
and executes transformations with real-time progress tracking.
"""

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
import re

# ==========================================================================
# Enums & Types
# ==========================================================================

class TaskType(str, Enum):
    ANALYZE = "analyze"
    GENERATE = "generate"
    MODIFY = "modify"
    CREATE = "create"
    DELETE = "delete"
    TEST = "test"
    VALIDATE = "validate"


class PhaseStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    SUCCESS = "success"


# ==========================================================================
# Data Classes
# ==========================================================================

@dataclass
class ProjectFile:
    path: str
    name: str
    extension: str
    size: int
    lines: int = 0
    file_type: str = "other"
    language: str = "other"
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    complexity: int = 0
    issues: List[str] = field(default_factory=list)


@dataclass
class TechStack:
    frontend_framework: str = ""
    frontend_version: str = ""
    ui_libraries: List[str] = field(default_factory=list)
    state_management: List[str] = field(default_factory=list)
    build_tool: str = ""
    backend_framework: str = ""
    backend_version: str = ""
    database: str = ""
    orm: str = ""
    auth: str = ""
    ai_integration: List[str] = field(default_factory=list)
    testing: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    project_path: str
    project_name: str
    analyzed_at: str
    total_files: int = 0
    total_lines: int = 0
    total_components: int = 0
    total_hooks: int = 0
    total_api_endpoints: int = 0
    tech_stack: TechStack = field(default_factory=TechStack)
    complexity_score: int = 0
    maintainability_score: int = 0
    scalability_score: int = 0
    files: List[ProjectFile] = field(default_factory=list)
    issues: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ExecutionTask:
    id: str
    name: str
    description: str
    order: int
    task_type: TaskType
    target_file: Optional[str] = None
    status: PhaseStatus = PhaseStatus.PENDING
    progress_percent: float = 0
    current_step: Optional[str] = None
    estimated_duration_seconds: float = 10
    actual_duration_seconds: Optional[float] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    
    # Execution function
    execute_fn: Optional[Callable] = None


@dataclass
class ExecutionPhase:
    id: str
    name: str
    description: str
    order: int
    tasks: List[ExecutionTask] = field(default_factory=list)
    status: PhaseStatus = PhaseStatus.PENDING
    current_task_index: int = 0
    estimated_duration_minutes: float = 5
    actual_duration_minutes: Optional[float] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    @property
    def total_tasks(self) -> int:
        return len(self.tasks)
    
    @property
    def completed_tasks(self) -> int:
        return sum(1 for t in self.tasks if t.status == PhaseStatus.COMPLETED)
    
    @property
    def progress_percent(self) -> float:
        if not self.tasks:
            return 0
        return (self.completed_tasks / self.total_tasks) * 100


@dataclass
class ExecutionPlan:
    id: str
    project_path: str
    name: str
    description: str
    phases: List[ExecutionPhase] = field(default_factory=list)
    status: PhaseStatus = PhaseStatus.PENDING
    current_phase_index: int = 0
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    estimated_duration_minutes: float = 30
    actual_duration_minutes: Optional[float] = None
    
    @property
    def total_tasks(self) -> int:
        return sum(p.total_tasks for p in self.phases)
    
    @property
    def completed_tasks(self) -> int:
        return sum(p.completed_tasks for p in self.phases)
    
    @property
    def failed_tasks(self) -> int:
        return sum(1 for p in self.phases for t in p.tasks if t.status == PhaseStatus.FAILED)
    
    @property
    def progress_percent(self) -> float:
        if not self.total_tasks:
            return 0
        return (self.completed_tasks / self.total_tasks) * 100


@dataclass
class LogEntry:
    id: str
    timestamp: str
    level: LogLevel
    message: str
    phase_id: Optional[str] = None
    task_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# ==========================================================================
# Project Analyzer Engine
# ==========================================================================

class ProjectAnalyzer:
    """
    Analyzes project structure and generates refactoring plans.
    """
    
    IGNORE_DIRS = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv',
        'dist', 'build', '.next', '.cache', 'coverage', '.pytest_cache'
    }
    
    IGNORE_FILES = {
        '.DS_Store', 'Thumbs.db', '.gitignore', '.env', '.env.local'
    }
    
    CODE_EXTENSIONS = {
        '.py': 'python',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.css': 'css',
        '.scss': 'css',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.md': 'markdown',
        '.html': 'html',
    }
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.result = AnalysisResult(
            project_path=str(self.project_path),
            project_name=self.project_path.name,
            analyzed_at=datetime.utcnow().isoformat()
        )
        self.logs: List[LogEntry] = []
        self._log_callback: Optional[Callable[[LogEntry], None]] = None
    
    def set_log_callback(self, callback: Callable[[LogEntry], None]):
        """Set callback for real-time log streaming."""
        self._log_callback = callback
    
    def _log(self, level: LogLevel, message: str, phase_id: str = None, task_id: str = None, **details):
        """Create and emit log entry."""
        entry = LogEntry(
            id=str(uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            level=level,
            message=message,
            phase_id=phase_id,
            task_id=task_id,
            details=details if details else None
        )
        self.logs.append(entry)
        if self._log_callback:
            self._log_callback(entry)
        return entry
    
    async def analyze(self) -> AnalysisResult:
        """Run full project analysis."""
        self._log(LogLevel.INFO, f"Starting analysis of {self.project_path}")
        
        # Scan files
        await self._scan_files()
        
        # Detect tech stack
        await self._detect_tech_stack()
        
        # Analyze patterns
        await self._analyze_patterns()
        
        # Calculate scores
        self._calculate_scores()
        
        # Generate recommendations
        self._generate_recommendations()
        
        self._log(LogLevel.SUCCESS, f"Analysis complete. Found {self.result.total_files} files, {self.result.total_lines} lines")
        
        return self.result
    
    async def _scan_files(self):
        """Scan all files in project."""
        self._log(LogLevel.INFO, "Scanning file structure...")
        
        for root, dirs, files in os.walk(self.project_path):
            # Filter ignored directories
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]
            
            rel_root = Path(root).relative_to(self.project_path)
            
            for filename in files:
                if filename in self.IGNORE_FILES:
                    continue
                
                filepath = Path(root) / filename
                rel_path = str(rel_root / filename)
                ext = filepath.suffix.lower()
                
                try:
                    stat = filepath.stat()
                    lines = 0
                    
                    if ext in self.CODE_EXTENSIONS:
                        try:
                            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                lines = sum(1 for _ in f)
                        except:
                            pass
                    
                    file_type = self._detect_file_type(rel_path, ext)
                    
                    pf = ProjectFile(
                        path=rel_path,
                        name=filename,
                        extension=ext,
                        size=stat.st_size,
                        lines=lines,
                        file_type=file_type,
                        language=self.CODE_EXTENSIONS.get(ext, 'other')
                    )
                    
                    self.result.files.append(pf)
                    self.result.total_files += 1
                    self.result.total_lines += lines
                    
                    if file_type == 'component':
                        self.result.total_components += 1
                    elif file_type == 'hook':
                        self.result.total_hooks += 1
                    
                except Exception as e:
                    self._log(LogLevel.WARN, f"Error scanning {rel_path}: {e}")
        
        self._log(LogLevel.SUCCESS, f"Scanned {self.result.total_files} files")
    
    def _detect_file_type(self, path: str, ext: str) -> str:
        """Detect file type based on path and extension."""
        path_lower = path.lower()
        
        if ext in ['.tsx', '.jsx']:
            if 'hook' in path_lower or path_lower.startswith('use'):
                return 'hook'
            if 'component' in path_lower or 'pages' in path_lower:
                return 'component'
        
        if ext == '.py':
            if 'router' in path_lower or 'api' in path_lower:
                return 'api'
            if 'model' in path_lower:
                return 'model'
            if 'service' in path_lower:
                return 'service'
        
        if 'test' in path_lower or 'spec' in path_lower:
            return 'test'
        
        if ext in ['.css', '.scss', '.sass']:
            return 'style'
        
        if ext == '.json' or 'config' in path_lower:
            return 'config'
        
        return 'other'
    
    async def _detect_tech_stack(self):
        """Detect technology stack from project files."""
        self._log(LogLevel.INFO, "Detecting tech stack...")
        
        # Check package.json
        pkg_json_path = self.project_path / 'frontend' / 'package.json'
        if not pkg_json_path.exists():
            pkg_json_path = self.project_path / 'package.json'
        
        if pkg_json_path.exists():
            try:
                with open(pkg_json_path) as f:
                    pkg = json.load(f)
                
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                
                # Frontend
                if 'react' in deps:
                    self.result.tech_stack.frontend_framework = 'React'
                    self.result.tech_stack.frontend_version = deps.get('react', '')
                elif 'vue' in deps:
                    self.result.tech_stack.frontend_framework = 'Vue'
                    self.result.tech_stack.frontend_version = deps.get('vue', '')
                
                # UI Libraries
                ui_libs = ['react-big-calendar', 'react-beautiful-dnd', '@mui/material', 'tailwindcss', 'antd']
                self.result.tech_stack.ui_libraries = [lib for lib in ui_libs if lib in deps]
                
                # State Management
                state_libs = ['zustand', 'redux', 'recoil', 'jotai', 'mobx']
                self.result.tech_stack.state_management = [lib for lib in state_libs if lib in deps]
                
                # Build Tool
                if 'vite' in deps:
                    self.result.tech_stack.build_tool = 'Vite'
                elif 'next' in deps:
                    self.result.tech_stack.build_tool = 'Next.js'
                elif 'webpack' in deps:
                    self.result.tech_stack.build_tool = 'Webpack'
                
                # Testing
                test_libs = ['jest', 'vitest', 'cypress', 'playwright', '@testing-library/react']
                self.result.tech_stack.testing = [lib for lib in test_libs if lib in deps]
                
                self._log(LogLevel.SUCCESS, f"Frontend: {self.result.tech_stack.frontend_framework}")
                
            except Exception as e:
                self._log(LogLevel.WARN, f"Error parsing package.json: {e}")
        
        # Check requirements.txt for Python
        req_path = self.project_path / 'backend' / 'requirements.txt'
        if not req_path.exists():
            req_path = self.project_path / 'requirements.txt'
        
        if req_path.exists():
            try:
                with open(req_path) as f:
                    reqs = f.read().lower()
                
                if 'fastapi' in reqs:
                    self.result.tech_stack.backend_framework = 'FastAPI'
                elif 'django' in reqs:
                    self.result.tech_stack.backend_framework = 'Django'
                elif 'flask' in reqs:
                    self.result.tech_stack.backend_framework = 'Flask'
                
                if 'sqlalchemy' in reqs:
                    self.result.tech_stack.orm = 'SQLAlchemy'
                elif 'django' in reqs:
                    self.result.tech_stack.orm = 'Django ORM'
                
                if 'google-generativeai' in reqs or 'gemini' in reqs:
                    self.result.tech_stack.ai_integration.append('Gemini')
                if 'openai' in reqs:
                    self.result.tech_stack.ai_integration.append('OpenAI')
                if 'anthropic' in reqs:
                    self.result.tech_stack.ai_integration.append('Claude')
                
                self._log(LogLevel.SUCCESS, f"Backend: {self.result.tech_stack.backend_framework}")
                
            except Exception as e:
                self._log(LogLevel.WARN, f"Error parsing requirements.txt: {e}")
    
    async def _analyze_patterns(self):
        """Analyze code patterns and detect issues."""
        self._log(LogLevel.INFO, "Analyzing code patterns...")
        
        # Count API endpoints
        for pf in self.result.files:
            if pf.file_type == 'api' and pf.language == 'python':
                filepath = self.project_path / pf.path
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Count route decorators
                    routes = len(re.findall(r'@router\.(get|post|put|patch|delete)', content))
                    self.result.total_api_endpoints += routes
                    
                except:
                    pass
        
        self._log(LogLevel.INFO, f"Found {self.result.total_api_endpoints} API endpoints")
    
    def _calculate_scores(self):
        """Calculate quality scores."""
        # Simple heuristics for demo
        
        # Complexity based on file count and LOC
        if self.result.total_lines > 50000:
            self.result.complexity_score = 30
        elif self.result.total_lines > 20000:
            self.result.complexity_score = 50
        elif self.result.total_lines > 5000:
            self.result.complexity_score = 70
        else:
            self.result.complexity_score = 85
        
        # Maintainability based on structure
        has_tests = any(f.file_type == 'test' for f in self.result.files)
        has_types = self.result.tech_stack.frontend_framework and 'typescript' in [f.language for f in self.result.files]
        
        self.result.maintainability_score = 50
        if has_tests:
            self.result.maintainability_score += 20
        if has_types:
            self.result.maintainability_score += 20
        if self.result.tech_stack.orm:
            self.result.maintainability_score += 10
        
        # Scalability
        self.result.scalability_score = 40
        if self.result.tech_stack.state_management:
            self.result.scalability_score += 15
        if 'SQLAlchemy' in self.result.tech_stack.orm:
            self.result.scalability_score += 15
        if self.result.tech_stack.ai_integration:
            self.result.scalability_score += 10
    
    def _generate_recommendations(self):
        """Generate improvement recommendations."""
        
        # ADHD-specific recommendations
        self.result.recommendations.append({
            'id': str(uuid4()),
            'category': 'adhd_ux',
            'priority': 'high',
            'title': 'Add Focus Mode',
            'current_state': 'Multiple UI elements visible at once',
            'recommended_state': 'Single-task focus mode with distractions hidden',
            'rationale': 'Reduces cognitive load for ADHD users',
            'effort_hours': 8,
        })
        
        self.result.recommendations.append({
            'id': str(uuid4()),
            'category': 'adhd_ux',
            'priority': 'high',
            'title': 'Visual Time Estimation',
            'current_state': 'Text-based time estimates',
            'recommended_state': 'Visual countdown timers with color-coded urgency',
            'rationale': 'Compensates for time blindness common in ADHD',
            'effort_hours': 6,
        })
        
        # Architecture recommendations
        if not self.result.tech_stack.state_management:
            self.result.recommendations.append({
                'id': str(uuid4()),
                'category': 'scalability',
                'priority': 'critical',
                'title': 'Add State Management',
                'current_state': 'React Context only',
                'recommended_state': 'Zustand + Immer for scalable state',
                'rationale': 'Context re-renders entire tree, Zustand is more performant',
                'effort_hours': 4,
            })
        
        self.result.recommendations.append({
            'id': str(uuid4()),
            'category': 'scalability',
            'priority': 'critical',
            'title': 'Block-Based Architecture',
            'current_state': 'Fixed Task model',
            'recommended_state': 'Generic Block model (like Notion)',
            'rationale': 'Enables infinite nesting and flexible content types',
            'effort_hours': 20,
        })
        
        self.result.recommendations.append({
            'id': str(uuid4()),
            'category': 'performance',
            'priority': 'high',
            'title': 'Real-time Sync',
            'current_state': 'REST API with polling',
            'recommended_state': 'WebSocket + Event Sourcing',
            'rationale': 'Enables instant updates and offline support',
            'effort_hours': 16,
        })
        
        self._log(LogLevel.INFO, f"Generated {len(self.result.recommendations)} recommendations")


# ==========================================================================
# Execution Engine
# ==========================================================================

class ExecutionEngine:
    """
    Executes refactoring plans with real-time progress tracking.
    """
    
    def __init__(self, plan: ExecutionPlan, project_path: str):
        self.plan = plan
        self.project_path = Path(project_path)
        self.logs: List[LogEntry] = []
        self._log_callback: Optional[Callable[[LogEntry], None]] = None
        self._progress_callback: Optional[Callable[[ExecutionPlan], None]] = None
        self._is_running = False
        self._is_paused = False
        self._should_cancel = False
    
    def set_callbacks(
        self,
        log_callback: Callable[[LogEntry], None] = None,
        progress_callback: Callable[[ExecutionPlan], None] = None
    ):
        """Set callbacks for real-time updates."""
        self._log_callback = log_callback
        self._progress_callback = progress_callback
    
    def _log(self, level: LogLevel, message: str, phase_id: str = None, task_id: str = None):
        """Emit log entry."""
        entry = LogEntry(
            id=str(uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            level=level,
            message=message,
            phase_id=phase_id,
            task_id=task_id
        )
        self.logs.append(entry)
        if self._log_callback:
            self._log_callback(entry)
    
    def _emit_progress(self):
        """Emit progress update."""
        if self._progress_callback:
            self._progress_callback(self.plan)
    
    async def execute(self) -> ExecutionPlan:
        """Execute the plan."""
        self._is_running = True
        self._should_cancel = False
        
        self.plan.status = PhaseStatus.RUNNING
        self.plan.started_at = datetime.utcnow().isoformat()
        self._log(LogLevel.INFO, f"Starting execution: {self.plan.name}")
        self._emit_progress()
        
        start_time = datetime.utcnow()
        
        try:
            for phase_idx, phase in enumerate(self.plan.phases):
                if self._should_cancel:
                    break
                
                self.plan.current_phase_index = phase_idx
                await self._execute_phase(phase)
                
                if phase.status == PhaseStatus.FAILED:
                    self.plan.status = PhaseStatus.FAILED
                    break
            
            if not self._should_cancel and self.plan.status != PhaseStatus.FAILED:
                self.plan.status = PhaseStatus.COMPLETED
                self.plan.completed_at = datetime.utcnow().isoformat()
                
        except Exception as e:
            self._log(LogLevel.ERROR, f"Execution failed: {e}")
            self.plan.status = PhaseStatus.FAILED
        
        finally:
            self._is_running = False
            duration = (datetime.utcnow() - start_time).total_seconds() / 60
            self.plan.actual_duration_minutes = duration
            self._emit_progress()
        
        return self.plan
    
    async def _execute_phase(self, phase: ExecutionPhase):
        """Execute a single phase."""
        phase.status = PhaseStatus.RUNNING
        phase.started_at = datetime.utcnow().isoformat()
        self._log(LogLevel.INFO, f"Starting phase: {phase.name}", phase_id=phase.id)
        self._emit_progress()
        
        start_time = datetime.utcnow()
        
        for task_idx, task in enumerate(phase.tasks):
            if self._should_cancel:
                break
            
            while self._is_paused:
                await asyncio.sleep(0.1)
            
            phase.current_task_index = task_idx
            await self._execute_task(task, phase.id)
            self._emit_progress()
            
            if task.status == PhaseStatus.FAILED:
                phase.status = PhaseStatus.FAILED
                break
        
        if not self._should_cancel and phase.status != PhaseStatus.FAILED:
            phase.status = PhaseStatus.COMPLETED
            phase.completed_at = datetime.utcnow().isoformat()
            self._log(LogLevel.SUCCESS, f"Phase complete: {phase.name}", phase_id=phase.id)
        
        duration = (datetime.utcnow() - start_time).total_seconds() / 60
        phase.actual_duration_minutes = duration
    
    async def _execute_task(self, task: ExecutionTask, phase_id: str):
        """Execute a single task."""
        task.status = PhaseStatus.RUNNING
        task.started_at = datetime.utcnow().isoformat()
        self._log(LogLevel.INFO, f"Starting: {task.name}", phase_id=phase_id, task_id=task.id)
        
        start_time = datetime.utcnow()
        
        try:
            # Simulate task execution with progress updates
            steps = 10
            for i in range(steps):
                if self._should_cancel:
                    break
                
                while self._is_paused:
                    await asyncio.sleep(0.1)
                
                task.progress_percent = ((i + 1) / steps) * 100
                task.current_step = f"Step {i + 1}/{steps}"
                self._emit_progress()
                
                # Simulate work
                await asyncio.sleep(task.estimated_duration_seconds / steps)
            
            if not self._should_cancel:
                task.status = PhaseStatus.COMPLETED
                task.completed_at = datetime.utcnow().isoformat()
                task.progress_percent = 100
                self._log(LogLevel.SUCCESS, f"Completed: {task.name}", phase_id=phase_id, task_id=task.id)
            
        except Exception as e:
            task.status = PhaseStatus.FAILED
            task.error = str(e)
            self._log(LogLevel.ERROR, f"Failed: {task.name} - {e}", phase_id=phase_id, task_id=task.id)
        
        finally:
            duration = (datetime.utcnow() - start_time).total_seconds()
            task.actual_duration_seconds = duration
    
    def pause(self):
        """Pause execution."""
        self._is_paused = True
        self.plan.status = PhaseStatus.PENDING  # Using PENDING as "paused"
        self._log(LogLevel.WARN, "Execution paused")
        self._emit_progress()
    
    def resume(self):
        """Resume execution."""
        self._is_paused = False
        self.plan.status = PhaseStatus.RUNNING
        self._log(LogLevel.INFO, "Execution resumed")
        self._emit_progress()
    
    def cancel(self):
        """Cancel execution."""
        self._should_cancel = True
        self._is_paused = False
        self._log(LogLevel.WARN, "Execution cancelled")


# ==========================================================================
# Plan Generator
# ==========================================================================

def generate_refactoring_plan(
    analysis: AnalysisResult,
    target: str = "notion-level"
) -> ExecutionPlan:
    """
    Generate execution plan based on analysis results.
    """
    
    plan = ExecutionPlan(
        id=str(uuid4()),
        project_path=analysis.project_path,
        name=f"{analysis.project_name} → {target.title()} Refactoring",
        description=f"Complete refactoring with Block Engine, Real-time Sync, and ADHD optimizations",
        created_at=datetime.utcnow().isoformat(),
        estimated_duration_minutes=45
    )
    
    # Phase 1: Discovery
    plan.phases.append(ExecutionPhase(
        id=str(uuid4()),
        name="Phase 1: Discovery",
        description="Analyze current codebase structure and dependencies",
        order=0,
        estimated_duration_minutes=5,
        tasks=[
            ExecutionTask(id=str(uuid4()), name="Scan file structure", description="", order=0, task_type=TaskType.ANALYZE, estimated_duration_seconds=2),
            ExecutionTask(id=str(uuid4()), name="Parse dependencies", description="", order=1, task_type=TaskType.ANALYZE, target_file="package.json", estimated_duration_seconds=1),
            ExecutionTask(id=str(uuid4()), name="Identify tech stack", description="", order=2, task_type=TaskType.ANALYZE, estimated_duration_seconds=1),
            ExecutionTask(id=str(uuid4()), name="Map component hierarchy", description="", order=3, task_type=TaskType.ANALYZE, estimated_duration_seconds=5),
            ExecutionTask(id=str(uuid4()), name="Extract existing features", description="", order=4, task_type=TaskType.ANALYZE, estimated_duration_seconds=3),
        ]
    ))
    
    # Phase 2: Architecture Analysis
    plan.phases.append(ExecutionPhase(
        id=str(uuid4()),
        name="Phase 2: Architecture Analysis",
        description="Evaluate patterns and generate improvement recommendations",
        order=1,
        estimated_duration_minutes=8,
        tasks=[
            ExecutionTask(id=str(uuid4()), name="Evaluate current patterns", description="", order=0, task_type=TaskType.ANALYZE, estimated_duration_seconds=10),
            ExecutionTask(id=str(uuid4()), name="Identify scalability bottlenecks", description="", order=1, task_type=TaskType.ANALYZE, estimated_duration_seconds=15),
            ExecutionTask(id=str(uuid4()), name="Generate improvement recommendations", description="", order=2, task_type=TaskType.GENERATE, estimated_duration_seconds=30),
            ExecutionTask(id=str(uuid4()), name="Compare with Notion architecture", description="", order=3, task_type=TaskType.ANALYZE, estimated_duration_seconds=20),
            ExecutionTask(id=str(uuid4()), name="Propose new system design", description="", order=4, task_type=TaskType.GENERATE, estimated_duration_seconds=45),
        ]
    ))
    
    # Phase 3: UI/UX Redesign
    plan.phases.append(ExecutionPhase(
        id=str(uuid4()),
        name="Phase 3: UI/UX Redesign",
        description="Create ADHD-optimized design system and mockups",
        order=2,
        estimated_duration_minutes=12,
        tasks=[
            ExecutionTask(id=str(uuid4()), name="Analyze current UI patterns", description="", order=0, task_type=TaskType.ANALYZE, estimated_duration_seconds=20),
            ExecutionTask(id=str(uuid4()), name="Generate ADHD-optimized design system", description="", order=1, task_type=TaskType.GENERATE, estimated_duration_seconds=60),
            ExecutionTask(id=str(uuid4()), name="Create component mockups", description="", order=2, task_type=TaskType.GENERATE, estimated_duration_seconds=120),
            ExecutionTask(id=str(uuid4()), name="Build interactive prototype", description="", order=3, task_type=TaskType.CREATE, estimated_duration_seconds=180),
        ]
    ))
    
    # Phase 4: Block Engine Core (P0)
    plan.phases.append(ExecutionPhase(
        id=str(uuid4()),
        name="Phase 4: Block Engine Core (P0)",
        description="Implement base Block model and editor",
        order=3,
        estimated_duration_minutes=10,
        tasks=[
            ExecutionTask(id=str(uuid4()), name="Create Block model schema", description="", order=0, task_type=TaskType.CREATE, target_file="backend/models/block.py", estimated_duration_seconds=30),
            ExecutionTask(id=str(uuid4()), name="Create Block API endpoints", description="", order=1, task_type=TaskType.CREATE, target_file="backend/routers/blocks.py", estimated_duration_seconds=60),
            ExecutionTask(id=str(uuid4()), name="Create BlockEditor component", description="", order=2, task_type=TaskType.CREATE, target_file="frontend/components/BlockEditor.tsx", estimated_duration_seconds=120),
            ExecutionTask(id=str(uuid4()), name="Implement block types", description="", order=3, task_type=TaskType.CREATE, estimated_duration_seconds=90),
            ExecutionTask(id=str(uuid4()), name="Add nested blocks support", description="", order=4, task_type=TaskType.MODIFY, estimated_duration_seconds=60),
        ]
    ))
    
    # Phase 5: Real-time Sync (P1)
    plan.phases.append(ExecutionPhase(
        id=str(uuid4()),
        name="Phase 5: Real-time Sync (P1)",
        description="Implement WebSocket sync and CRDT",
        order=4,
        estimated_duration_minutes=10,
        tasks=[
            ExecutionTask(id=str(uuid4()), name="Setup WebSocket endpoint", description="", order=0, task_type=TaskType.CREATE, target_file="backend/routers/sync.py", estimated_duration_seconds=30),
            ExecutionTask(id=str(uuid4()), name="Implement event broadcast", description="", order=1, task_type=TaskType.CREATE, estimated_duration_seconds=45),
            ExecutionTask(id=str(uuid4()), name="Create useSync hook", description="", order=2, task_type=TaskType.CREATE, target_file="frontend/hooks/useSync.ts", estimated_duration_seconds=60),
            ExecutionTask(id=str(uuid4()), name="Implement optimistic updates", description="", order=3, task_type=TaskType.MODIFY, estimated_duration_seconds=90),
            ExecutionTask(id=str(uuid4()), name="Add conflict resolution", description="", order=4, task_type=TaskType.CREATE, estimated_duration_seconds=120),
        ]
    ))
    
    return plan
