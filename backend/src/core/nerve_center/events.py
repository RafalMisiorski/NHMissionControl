"""
NH Nerve Center - Event System
===============================

Core event types and structures for real-time transparency.
Every operation in NH emits events that can be tracked.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field, asdict
from uuid import uuid4
import json


# ==========================================================================
# Event Categories
# ==========================================================================

class EventCategory(str, Enum):
    """Top-level event categories"""
    SYSTEM = "system"           # NH system events
    AGENT = "agent"             # AI agent operations
    FILE = "file"               # File system operations
    API = "api"                 # External API calls
    DATABASE = "database"       # Database operations
    USER = "user"               # User-initiated actions
    ANALYSIS = "analysis"       # Code/project analysis
    GENERATION = "generation"   # Code/content generation
    NOTIFICATION = "notification"  # SyncWave notifications
    PIPELINE = "pipeline"       # Pipeline orchestrator (EPOCH 7)
    CC_SESSION = "cc_session"   # Claude Code sessions (EPOCH 8)


class EventType(str, Enum):
    """Specific event types"""
    # System
    SYSTEM_START = "system.start"
    SYSTEM_READY = "system.ready"
    SYSTEM_ERROR = "system.error"
    SYSTEM_SHUTDOWN = "system.shutdown"
    
    # Agent
    AGENT_SPAWN = "agent.spawn"
    AGENT_THINKING = "agent.thinking"
    AGENT_DECISION = "agent.decision"
    AGENT_ACTION = "agent.action"
    AGENT_COMPLETE = "agent.complete"
    AGENT_ERROR = "agent.error"
    
    # Task
    TASK_QUEUE = "task.queue"
    TASK_START = "task.start"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETE = "task.complete"
    TASK_FAIL = "task.fail"
    TASK_CANCEL = "task.cancel"
    
    # File
    FILE_READ = "file.read"
    FILE_WRITE = "file.write"
    FILE_CREATE = "file.create"
    FILE_DELETE = "file.delete"
    FILE_MOVE = "file.move"
    FILE_SCAN = "file.scan"
    
    # API (LLM calls)
    LLM_REQUEST = "llm.request"
    LLM_STREAM = "llm.stream"
    LLM_COMPLETE = "llm.complete"
    LLM_ERROR = "llm.error"
    LLM_TOKENS = "llm.tokens"
    
    # Analysis
    ANALYSIS_START = "analysis.start"
    ANALYSIS_PROGRESS = "analysis.progress"
    ANALYSIS_FINDING = "analysis.finding"
    ANALYSIS_COMPLETE = "analysis.complete"
    
    # Generation
    GEN_PLAN = "gen.plan"
    GEN_CODE = "gen.code"
    GEN_TEST = "gen.test"
    GEN_DOC = "gen.doc"
    
    # Notification (SyncWave)
    NOTIF_TASK_START = "notif.task_start"
    NOTIF_TASK_COMPLETE = "notif.task_complete"
    NOTIF_TASK_FAIL = "notif.task_fail"
    NOTIF_PROGRESS = "notif.progress"
    NOTIF_BLOCKER = "notif.blocker"
    NOTIF_GITHUB = "notif.github"

    # Pipeline Orchestrator (EPOCH 7 - Taśmociąg)
    PIPELINE_CREATED = "pipeline.created"
    PIPELINE_STARTED = "pipeline.started"
    PIPELINE_COMPLETED = "pipeline.completed"
    PIPELINE_FAILED = "pipeline.failed"
    PIPELINE_PAUSED = "pipeline.paused"
    PIPELINE_RESUMED = "pipeline.resumed"
    PIPELINE_CANCELLED = "pipeline.cancelled"

    # Pipeline Stages
    STAGE_STARTED = "pipeline.stage.started"
    STAGE_COMPLETED = "pipeline.stage.completed"
    STAGE_FAILED = "pipeline.stage.failed"
    STAGE_SKIPPED = "pipeline.stage.skipped"

    # Handoff Tokens (Gate Verification)
    HANDOFF_CREATED = "pipeline.handoff.created"
    HANDOFF_VALIDATED = "pipeline.handoff.validated"
    HANDOFF_REJECTED = "pipeline.handoff.rejected"

    # Neural Ralph (Auto-Correction)
    NEURAL_RALPH_ATTEMPT = "pipeline.neural_ralph.attempt"
    NEURAL_RALPH_DIAGNOSIS = "pipeline.neural_ralph.diagnosis"
    NEURAL_RALPH_SUCCESS = "pipeline.neural_ralph.success"
    NEURAL_RALPH_FAILED = "pipeline.neural_ralph.failed"

    # Escalation
    ESCALATION_TRIGGERED = "pipeline.escalation.triggered"
    ESCALATION_AGENT_CHANGED = "pipeline.escalation.agent_changed"
    ESCALATION_HUMAN_REQUIRED = "pipeline.escalation.human_required"

    # PO Review
    PO_REVIEW_REQUIRED = "pipeline.po.review_required"
    PO_APPROVED = "pipeline.po.approved"
    PO_CHANGES_REQUESTED = "pipeline.po.changes_requested"
    PO_REJECTED = "pipeline.po.rejected"

    # Guardrails
    GUARDRAIL_CHECK = "pipeline.guardrail.check"
    GUARDRAIL_PASSED = "pipeline.guardrail.passed"
    GUARDRAIL_VIOLATION = "pipeline.guardrail.violation"
    GUARDRAIL_OVERRIDE = "pipeline.guardrail.override"

    # Resources
    RESOURCE_ALLOCATED = "pipeline.resource.allocated"
    RESOURCE_RELEASED = "pipeline.resource.released"
    RESOURCE_CONFLICT = "pipeline.resource.conflict"

    # Health Inspector
    HEALTH_CHECK_STARTED = "pipeline.health.check_started"
    HEALTH_CHECK_COMPLETED = "pipeline.health.check_completed"
    HEALTH_WARNING = "pipeline.health.warning"
    HEALTH_CRITICAL = "pipeline.health.critical"

    # CC Session Manager (EPOCH 8 - Visibility & Reliability)
    CC_SESSION_CREATED = "cc.session.created"
    CC_SESSION_STARTED = "cc.session.started"
    CC_SESSION_COMPLETED = "cc.session.completed"
    CC_SESSION_FAILED = "cc.session.failed"
    CC_SESSION_CRASHED = "cc.session.crashed"
    CC_SESSION_STUCK = "cc.session.stuck"
    CC_SESSION_RESTARTING = "cc.session.restarting"
    CC_SESSION_RESTARTED = "cc.session.restarted"
    CC_SESSION_KILLED = "cc.session.killed"

    # CC Output Streaming
    CC_OUTPUT_LINE = "cc.output.line"
    CC_OUTPUT_ERROR = "cc.output.error"
    CC_OUTPUT_COMPLETION = "cc.output.completion"

    # CC Health Monitoring
    CC_HEARTBEAT = "cc.heartbeat"
    CC_HEARTBEAT_TIMEOUT = "cc.heartbeat.timeout"
    CC_RUNTIME_WARNING = "cc.runtime.warning"
    CC_RUNTIME_LIMIT = "cc.runtime.limit"

    # CC Commands
    CC_COMMAND_SENT = "cc.command.sent"
    CC_COMMAND_RESPONSE = "cc.command.response"


class Severity(str, Enum):
    """Event severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ==========================================================================
# Core Event Structure
# ==========================================================================

@dataclass
class NHEvent:
    """
    Base event structure for all NH operations.
    Every action in the system emits an NHEvent.
    """
    # Identity
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Classification
    category: EventCategory = EventCategory.SYSTEM
    event_type: EventType = EventType.SYSTEM_START
    severity: Severity = Severity.INFO
    
    # Context
    session_id: Optional[str] = None      # Current session/job
    task_id: Optional[str] = None         # Parent task
    agent_id: Optional[str] = None        # Agent that emitted
    correlation_id: Optional[str] = None  # Link related events
    
    # Content
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Progress (for trackable operations)
    progress_current: Optional[int] = None
    progress_total: Optional[int] = None
    progress_percent: Optional[float] = None
    
    # Timing
    duration_ms: Optional[float] = None
    
    # Cost tracking (for LLM calls)
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    cost_usd: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NHEvent':
        """Create from dictionary"""
        # Convert string enums back
        if 'category' in data:
            data['category'] = EventCategory(data['category'])
        if 'event_type' in data:
            data['event_type'] = EventType(data['event_type'])
        if 'severity' in data:
            data['severity'] = Severity(data['severity'])
        return cls(**data)


# ==========================================================================
# Specialized Event Builders
# ==========================================================================

class EventBuilder:
    """Factory for creating specific event types"""
    
    @staticmethod
    def agent_thinking(
        agent_id: str,
        thought: str,
        context: Dict[str, Any] = None,
        session_id: str = None,
        task_id: str = None,
    ) -> NHEvent:
        """Agent is reasoning/planning"""
        return NHEvent(
            category=EventCategory.AGENT,
            event_type=EventType.AGENT_THINKING,
            agent_id=agent_id,
            session_id=session_id,
            task_id=task_id,
            message=thought,
            details=context or {},
        )
    
    @staticmethod
    def agent_decision(
        agent_id: str,
        decision: str,
        reasoning: str,
        options_considered: List[str] = None,
        session_id: str = None,
        task_id: str = None,
    ) -> NHEvent:
        """Agent made a decision"""
        return NHEvent(
            category=EventCategory.AGENT,
            event_type=EventType.AGENT_DECISION,
            agent_id=agent_id,
            session_id=session_id,
            task_id=task_id,
            message=decision,
            details={
                "reasoning": reasoning,
                "options_considered": options_considered or [],
            },
        )
    
    @staticmethod
    def task_progress(
        task_id: str,
        message: str,
        current: int,
        total: int,
        step_name: str = None,
        session_id: str = None,
    ) -> NHEvent:
        """Task progress update"""
        return NHEvent(
            category=EventCategory.AGENT,
            event_type=EventType.TASK_PROGRESS,
            task_id=task_id,
            session_id=session_id,
            message=message,
            progress_current=current,
            progress_total=total,
            progress_percent=(current / total * 100) if total > 0 else 0,
            details={"step_name": step_name} if step_name else {},
        )
    
    @staticmethod
    def file_operation(
        operation: str,  # read, write, create, delete
        file_path: str,
        size_bytes: int = None,
        lines: int = None,
        session_id: str = None,
        task_id: str = None,
    ) -> NHEvent:
        """File system operation"""
        event_types = {
            "read": EventType.FILE_READ,
            "write": EventType.FILE_WRITE,
            "create": EventType.FILE_CREATE,
            "delete": EventType.FILE_DELETE,
        }
        return NHEvent(
            category=EventCategory.FILE,
            event_type=event_types.get(operation, EventType.FILE_READ),
            session_id=session_id,
            task_id=task_id,
            message=f"{operation.upper()}: {file_path}",
            details={
                "path": file_path,
                "size_bytes": size_bytes,
                "lines": lines,
            },
        )
    
    @staticmethod
    def llm_request(
        model: str,
        prompt_preview: str,
        max_tokens: int,
        session_id: str = None,
        task_id: str = None,
    ) -> NHEvent:
        """LLM API request"""
        return NHEvent(
            category=EventCategory.API,
            event_type=EventType.LLM_REQUEST,
            session_id=session_id,
            task_id=task_id,
            message=f"LLM Request to {model}",
            details={
                "model": model,
                "prompt_preview": prompt_preview[:200] + "..." if len(prompt_preview) > 200 else prompt_preview,
                "max_tokens": max_tokens,
            },
        )
    
    @staticmethod
    def llm_complete(
        model: str,
        tokens_input: int,
        tokens_output: int,
        duration_ms: float,
        cost_usd: float = None,
        session_id: str = None,
        task_id: str = None,
    ) -> NHEvent:
        """LLM API response complete"""
        return NHEvent(
            category=EventCategory.API,
            event_type=EventType.LLM_COMPLETE,
            session_id=session_id,
            task_id=task_id,
            message=f"LLM Response from {model}: {tokens_output} tokens",
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            duration_ms=duration_ms,
            cost_usd=cost_usd,
            details={"model": model},
        )
    
    @staticmethod
    def analysis_finding(
        finding_type: str,
        severity: Severity,
        message: str,
        file_path: str = None,
        line_number: int = None,
        recommendation: str = None,
        session_id: str = None,
        task_id: str = None,
    ) -> NHEvent:
        """Analysis discovered something"""
        return NHEvent(
            category=EventCategory.ANALYSIS,
            event_type=EventType.ANALYSIS_FINDING,
            severity=severity,
            session_id=session_id,
            task_id=task_id,
            message=message,
            details={
                "finding_type": finding_type,
                "file_path": file_path,
                "line_number": line_number,
                "recommendation": recommendation,
            },
        )

    # ======================================================================
    # Pipeline Orchestrator Events (EPOCH 7)
    # ======================================================================

    @staticmethod
    def pipeline_stage_started(
        pipeline_run_id: str,
        task_id: str,
        stage: str,
        agent: str,
        session_id: str = None,
    ) -> NHEvent:
        """Pipeline stage started"""
        return NHEvent(
            category=EventCategory.PIPELINE,
            event_type=EventType.STAGE_STARTED,
            session_id=session_id,
            task_id=task_id,
            message=f"Stage {stage} started with {agent}",
            details={
                "pipeline_run_id": pipeline_run_id,
                "stage": stage,
                "agent": agent,
            },
        )

    @staticmethod
    def pipeline_stage_completed(
        pipeline_run_id: str,
        task_id: str,
        stage: str,
        trust_score: float,
        duration_ms: float = None,
        session_id: str = None,
    ) -> NHEvent:
        """Pipeline stage completed"""
        return NHEvent(
            category=EventCategory.PIPELINE,
            event_type=EventType.STAGE_COMPLETED,
            session_id=session_id,
            task_id=task_id,
            message=f"Stage {stage} completed with trust score {trust_score:.1f}",
            duration_ms=duration_ms,
            details={
                "pipeline_run_id": pipeline_run_id,
                "stage": stage,
                "trust_score": trust_score,
            },
        )

    @staticmethod
    def handoff_token_created(
        pipeline_run_id: str,
        task_id: str,
        from_stage: str,
        to_stage: str,
        trust_score: float,
        valid: bool,
        session_id: str = None,
    ) -> NHEvent:
        """Handoff token created between stages"""
        severity = Severity.INFO if valid else Severity.WARNING
        return NHEvent(
            category=EventCategory.PIPELINE,
            event_type=EventType.HANDOFF_CREATED,
            severity=severity,
            session_id=session_id,
            task_id=task_id,
            message=f"Handoff {from_stage}→{to_stage}: score {trust_score:.1f} ({'valid' if valid else 'rejected'})",
            details={
                "pipeline_run_id": pipeline_run_id,
                "from_stage": from_stage,
                "to_stage": to_stage,
                "trust_score": trust_score,
                "valid": valid,
            },
        )

    @staticmethod
    def neural_ralph_attempt(
        pipeline_run_id: str,
        task_id: str,
        error_type: str,
        attempt: int,
        max_retries: int,
        session_id: str = None,
    ) -> NHEvent:
        """Neural Ralph correction attempt"""
        return NHEvent(
            category=EventCategory.PIPELINE,
            event_type=EventType.NEURAL_RALPH_ATTEMPT,
            session_id=session_id,
            task_id=task_id,
            message=f"Neural Ralph attempt {attempt}/{max_retries} for {error_type}",
            details={
                "pipeline_run_id": pipeline_run_id,
                "error_type": error_type,
                "attempt": attempt,
                "max_retries": max_retries,
            },
        )

    @staticmethod
    def escalation_triggered(
        pipeline_run_id: str,
        task_id: str,
        from_level: str,
        to_level: str,
        reason: str,
        session_id: str = None,
    ) -> NHEvent:
        """Escalation triggered to higher agent level"""
        severity = Severity.WARNING if to_level != "human" else Severity.CRITICAL
        return NHEvent(
            category=EventCategory.PIPELINE,
            event_type=EventType.ESCALATION_TRIGGERED,
            severity=severity,
            session_id=session_id,
            task_id=task_id,
            message=f"Escalated {from_level}→{to_level}: {reason}",
            details={
                "pipeline_run_id": pipeline_run_id,
                "from_level": from_level,
                "to_level": to_level,
                "reason": reason,
            },
        )

    @staticmethod
    def po_review_required(
        pipeline_run_id: str,
        task_id: str,
        task_title: str,
        health_score: float,
        blockers: List[str] = None,
        session_id: str = None,
    ) -> NHEvent:
        """PO review required for pipeline"""
        severity = Severity.WARNING if blockers else Severity.INFO
        return NHEvent(
            category=EventCategory.PIPELINE,
            event_type=EventType.PO_REVIEW_REQUIRED,
            severity=severity,
            session_id=session_id,
            task_id=task_id,
            message=f"PO Review required for: {task_title}",
            details={
                "pipeline_run_id": pipeline_run_id,
                "task_title": task_title,
                "health_score": health_score,
                "blockers": blockers or [],
            },
        )

    @staticmethod
    def guardrail_violation(
        rule_name: str,
        layer: str,
        attempted_action: str,
        blocked: bool,
        pipeline_run_id: str = None,
        task_id: str = None,
        session_id: str = None,
    ) -> NHEvent:
        """Guardrail violation detected"""
        severity = Severity.ERROR if blocked else Severity.WARNING
        return NHEvent(
            category=EventCategory.PIPELINE,
            event_type=EventType.GUARDRAIL_VIOLATION,
            severity=severity,
            session_id=session_id,
            task_id=task_id,
            message=f"Guardrail [{layer}] {rule_name}: {'BLOCKED' if blocked else 'WARNING'}",
            details={
                "pipeline_run_id": pipeline_run_id,
                "rule_name": rule_name,
                "layer": layer,
                "attempted_action": attempted_action,
                "blocked": blocked,
            },
        )

    @staticmethod
    def resource_allocated(
        task_id: str,
        resource_type: str,
        value: int,
        pipeline_run_id: str = None,
        session_id: str = None,
    ) -> NHEvent:
        """Resource allocated to pipeline"""
        return NHEvent(
            category=EventCategory.PIPELINE,
            event_type=EventType.RESOURCE_ALLOCATED,
            session_id=session_id,
            task_id=task_id,
            message=f"Allocated {resource_type}: {value}",
            details={
                "pipeline_run_id": pipeline_run_id,
                "resource_type": resource_type,
                "value": value,
            },
        )

    # ======================================================================
    # CC Session Manager Events (EPOCH 8)
    # ======================================================================

    @staticmethod
    def cc_session_created(
        cc_session_id: str,
        session_name: str,
        working_directory: str,
        platform: str,
        pipeline_run_id: str = None,
        stage_id: str = None,
    ) -> NHEvent:
        """CC session created"""
        return NHEvent(
            category=EventCategory.CC_SESSION,
            event_type=EventType.CC_SESSION_CREATED,
            session_id=cc_session_id,
            message=f"CC Session created: {session_name}",
            details={
                "cc_session_id": cc_session_id,
                "session_name": session_name,
                "working_directory": working_directory,
                "platform": platform,
                "pipeline_run_id": pipeline_run_id,
                "stage_id": stage_id,
            },
        )

    @staticmethod
    def cc_session_started(
        cc_session_id: str,
        session_name: str,
        task_prompt_preview: str,
        dangerous_mode: bool = True,
    ) -> NHEvent:
        """CC session started executing task"""
        return NHEvent(
            category=EventCategory.CC_SESSION,
            event_type=EventType.CC_SESSION_STARTED,
            session_id=cc_session_id,
            message=f"CC Session {session_name} started",
            details={
                "cc_session_id": cc_session_id,
                "session_name": session_name,
                "task_preview": task_prompt_preview[:200] if task_prompt_preview else None,
                "dangerous_mode": dangerous_mode,
            },
        )

    @staticmethod
    def cc_session_completed(
        cc_session_id: str,
        session_name: str,
        duration_seconds: float,
        output_lines: int,
    ) -> NHEvent:
        """CC session completed task successfully"""
        return NHEvent(
            category=EventCategory.CC_SESSION,
            event_type=EventType.CC_SESSION_COMPLETED,
            severity=Severity.INFO,
            session_id=cc_session_id,
            message=f"CC Session {session_name} completed",
            duration_ms=duration_seconds * 1000,
            details={
                "cc_session_id": cc_session_id,
                "session_name": session_name,
                "duration_seconds": duration_seconds,
                "output_lines": output_lines,
            },
        )

    @staticmethod
    def cc_session_failed(
        cc_session_id: str,
        session_name: str,
        error: str,
    ) -> NHEvent:
        """CC session task failed"""
        return NHEvent(
            category=EventCategory.CC_SESSION,
            event_type=EventType.CC_SESSION_FAILED,
            severity=Severity.ERROR,
            session_id=cc_session_id,
            message=f"CC Session {session_name} failed: {error[:100]}",
            details={
                "cc_session_id": cc_session_id,
                "session_name": session_name,
                "error": error,
            },
        )

    @staticmethod
    def cc_session_crashed(
        cc_session_id: str,
        session_name: str,
        exit_code: int = None,
        last_output: str = None,
    ) -> NHEvent:
        """CC session process crashed"""
        return NHEvent(
            category=EventCategory.CC_SESSION,
            event_type=EventType.CC_SESSION_CRASHED,
            severity=Severity.ERROR,
            session_id=cc_session_id,
            message=f"CC Session {session_name} CRASHED (exit code: {exit_code})",
            details={
                "cc_session_id": cc_session_id,
                "session_name": session_name,
                "exit_code": exit_code,
                "last_output": last_output[-500:] if last_output else None,
            },
        )

    @staticmethod
    def cc_session_stuck(
        cc_session_id: str,
        session_name: str,
        seconds_since_output: float,
    ) -> NHEvent:
        """CC session appears stuck (no output)"""
        return NHEvent(
            category=EventCategory.CC_SESSION,
            event_type=EventType.CC_SESSION_STUCK,
            severity=Severity.WARNING,
            session_id=cc_session_id,
            message=f"CC Session {session_name} stuck ({seconds_since_output:.0f}s no output)",
            details={
                "cc_session_id": cc_session_id,
                "session_name": session_name,
                "seconds_since_output": seconds_since_output,
            },
        )

    @staticmethod
    def cc_session_restarting(
        cc_session_id: str,
        session_name: str,
        reason: str,
        restart_count: int,
        max_restarts: int,
    ) -> NHEvent:
        """CC session being restarted"""
        return NHEvent(
            category=EventCategory.CC_SESSION,
            event_type=EventType.CC_SESSION_RESTARTING,
            severity=Severity.WARNING,
            session_id=cc_session_id,
            message=f"CC Session {session_name} restarting ({restart_count}/{max_restarts}): {reason}",
            details={
                "cc_session_id": cc_session_id,
                "session_name": session_name,
                "reason": reason,
                "restart_count": restart_count,
                "max_restarts": max_restarts,
            },
        )

    @staticmethod
    def cc_session_restarted(
        old_session_id: str,
        new_session_id: str,
        new_session_name: str,
        context_lines: int,
    ) -> NHEvent:
        """CC session restarted with new process"""
        return NHEvent(
            category=EventCategory.CC_SESSION,
            event_type=EventType.CC_SESSION_RESTARTED,
            session_id=new_session_id,
            message=f"CC Session restarted as {new_session_name}",
            details={
                "old_session_id": old_session_id,
                "new_session_id": new_session_id,
                "new_session_name": new_session_name,
                "context_lines": context_lines,
            },
        )

    @staticmethod
    def cc_output_line(
        cc_session_id: str,
        session_name: str,
        line_number: int,
        content: str,
        is_error: bool = False,
    ) -> NHEvent:
        """CC session output line"""
        return NHEvent(
            category=EventCategory.CC_SESSION,
            event_type=EventType.CC_OUTPUT_LINE,
            severity=Severity.ERROR if is_error else Severity.DEBUG,
            session_id=cc_session_id,
            message=content[:200] if content else "",
            details={
                "cc_session_id": cc_session_id,
                "session_name": session_name,
                "line_number": line_number,
                "is_error": is_error,
            },
        )

    @staticmethod
    def cc_heartbeat(
        cc_session_id: str,
        session_name: str,
        runtime_seconds: float,
        output_lines: int,
    ) -> NHEvent:
        """CC session heartbeat (periodic health update)"""
        return NHEvent(
            category=EventCategory.CC_SESSION,
            event_type=EventType.CC_HEARTBEAT,
            severity=Severity.DEBUG,
            session_id=cc_session_id,
            message=f"CC Heartbeat: {session_name} ({runtime_seconds:.0f}s, {output_lines} lines)",
            details={
                "cc_session_id": cc_session_id,
                "session_name": session_name,
                "runtime_seconds": runtime_seconds,
                "output_lines": output_lines,
            },
        )

    @staticmethod
    def cc_runtime_warning(
        cc_session_id: str,
        session_name: str,
        runtime_minutes: float,
        max_runtime_minutes: int,
    ) -> NHEvent:
        """CC session approaching runtime limit"""
        return NHEvent(
            category=EventCategory.CC_SESSION,
            event_type=EventType.CC_RUNTIME_WARNING,
            severity=Severity.WARNING,
            session_id=cc_session_id,
            message=f"CC Session {session_name} runtime warning: {runtime_minutes:.1f}/{max_runtime_minutes} min",
            details={
                "cc_session_id": cc_session_id,
                "session_name": session_name,
                "runtime_minutes": runtime_minutes,
                "max_runtime_minutes": max_runtime_minutes,
            },
        )

    @staticmethod
    def cc_command_sent(
        cc_session_id: str,
        session_name: str,
        command: str,
    ) -> NHEvent:
        """Command sent to CC session"""
        return NHEvent(
            category=EventCategory.CC_SESSION,
            event_type=EventType.CC_COMMAND_SENT,
            session_id=cc_session_id,
            message=f"Command sent to {session_name}: {command[:100]}",
            details={
                "cc_session_id": cc_session_id,
                "session_name": session_name,
                "command": command,
            },
        )


# ==========================================================================
# Event Aggregation for UI
# ==========================================================================

@dataclass
class TaskState:
    """Aggregated state for a single task"""
    id: str
    name: str
    status: str = "pending"  # pending, running, completed, failed
    progress_percent: float = 0
    current_step: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    events: List[NHEvent] = field(default_factory=list)
    sub_tasks: List['TaskState'] = field(default_factory=list)


@dataclass  
class AgentState:
    """Aggregated state for an agent"""
    id: str
    name: str
    role: str
    status: str = "idle"  # idle, thinking, acting, waiting, error
    current_thought: Optional[str] = None
    current_action: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0
    events: List[NHEvent] = field(default_factory=list)


@dataclass
class SessionState:
    """Complete state for a session/job"""
    id: str
    name: str
    status: str = "initializing"  # initializing, running, paused, completed, failed
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    
    # Progress
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    progress_percent: float = 0
    
    # Agents
    agents: Dict[str, AgentState] = field(default_factory=dict)
    
    # Tasks (hierarchical)
    root_tasks: List[TaskState] = field(default_factory=list)
    
    # All events (for log view)
    events: List[NHEvent] = field(default_factory=list)
    
    # Costs
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_cost_usd: float = 0
    
    # Files affected
    files_read: List[str] = field(default_factory=list)
    files_written: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for WebSocket transmission"""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "progress_percent": self.progress_percent,
            "agents": {k: asdict(v) for k, v in self.agents.items()},
            "root_tasks": [asdict(t) for t in self.root_tasks],
            "total_tokens_input": self.total_tokens_input,
            "total_tokens_output": self.total_tokens_output,
            "total_cost_usd": self.total_cost_usd,
            "files_read": self.files_read,
            "files_written": self.files_written,
            "files_created": self.files_created,
        }
