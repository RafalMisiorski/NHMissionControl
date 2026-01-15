"""
NH Mission Control - Database Models
=====================================

SQLAlchemy models for all entities.
These define the database schema - CC should NOT modify these
without explicit approval.
"""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


# ==========================================================================
# Enums
# ==========================================================================

class UserRole(str, enum.Enum):
    """User roles for access control."""
    ADMIN = "admin"
    USER = "user"


class OpportunitySource(str, enum.Enum):
    """Source of opportunity/lead."""
    UPWORK = "upwork"
    USEME = "useme"
    DIRECT = "direct"
    REFERRAL = "referral"
    OTHER = "other"


class OpportunityStatus(str, enum.Enum):
    """Pipeline stage for opportunities."""
    LEAD = "lead"              # Just discovered
    QUALIFIED = "qualified"    # Reviewed, worth pursuing
    PROPOSAL = "proposal"      # Proposal sent
    NEGOTIATING = "negotiating"  # In discussion
    WON = "won"                # Contract signed
    DELIVERED = "delivered"    # Project completed
    LOST = "lost"              # Did not win


class ProjectStatus(str, enum.Enum):
    """Status of active projects."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class FinancialRecordType(str, enum.Enum):
    """Type of financial record."""
    INCOME = "income"
    EXPENSE = "expense"


class TaskMode(str, enum.Enum):
    """Task execution mode classification."""
    YOLO = "yolo"              # Autonomous execution
    CHECKPOINTED = "checkpointed"  # Regular commits
    SUPERVISED = "supervised"   # Human approval needed


class GoalStatus(str, enum.Enum):
    """Status of financial goal."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ==========================================================================
# Pipeline Orchestrator Enums (EPOCH 7)
# ==========================================================================

class PipelineStage(str, enum.Enum):
    """Pipeline execution stages."""
    QUEUED = "queued"
    DEVELOPING = "developing"
    TESTING = "testing"
    VERIFYING = "verifying"
    PO_REVIEW = "po_review"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineRunStatus(str, enum.Enum):
    """Overall pipeline run status."""
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EscalationLevel(str, enum.Enum):
    """Agent escalation levels."""
    CODEX = "codex"       # Fast, cost-effective
    SONNET = "sonnet"     # Balanced
    OPUS = "opus"         # Most capable
    HUMAN = "human"       # Final escalation


class GuardrailLayer(str, enum.Enum):
    """Guardrail constraint layers."""
    INVARIANT = "invariant"   # Never changeable
    CONTRACT = "contract"      # Schema-validated
    POLICY = "policy"          # Bounded configurable
    PREFERENCE = "preference"  # Freely changeable


class ResourceType(str, enum.Enum):
    """Types of allocatable resources."""
    FRONTEND_PORT = "frontend_port"
    BACKEND_PORT = "backend_port"
    DATABASE_PORT = "database_port"
    REDIS_PORT = "redis_port"
    TEST_PORT = "test_port"


class EpochStatus(str, enum.Enum):
    """Epoch lifecycle status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    DEPRECATED = "deprecated"


class CCSessionStatus(str, enum.Enum):
    """Claude Code session status."""
    IDLE = "idle"           # Created but not started
    STARTING = "starting"   # CC process starting
    RUNNING = "running"     # Actively executing task
    STUCK = "stuck"         # No output for heartbeat timeout
    COMPLETED = "completed" # Task finished successfully
    FAILED = "failed"       # Task failed
    CRASHED = "crashed"     # Process crashed/terminated
    RESTARTING = "restarting"  # Being restarted with context


class CCSessionPlatform(str, enum.Enum):
    """Platform for CC session execution."""
    WINDOWS = "windows"  # Uses pywinpty/ConPTY
    LINUX = "linux"      # Uses tmux
    WSL = "wsl"          # WSL with tmux


# ==========================================================================
# Mixins
# ==========================================================================

class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin that adds soft delete capability."""
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


# ==========================================================================
# Models
# ==========================================================================

class User(Base, TimestampMixin):
    """
    User account model.
    
    EPOCH 1 - LOCKED after implementation.
    """
    
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    opportunities: Mapped[list["Opportunity"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
    projects: Mapped[list["Project"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
    financial_records: Mapped[list["FinancialRecord"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
    financial_goals: Mapped[list["FinancialGoal"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class RefreshToken(Base, TimestampMixin):
    """
    Refresh token storage for JWT authentication.
    
    EPOCH 1 - LOCKED after implementation.
    """
    
    __tablename__ = "refresh_tokens"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    def __repr__(self) -> str:
        return f"<RefreshToken {self.id}>"


class Opportunity(Base, TimestampMixin, SoftDeleteMixin):
    """
    Pipeline opportunity/lead model.
    
    EPOCH 3 - Pipeline Module.
    """
    
    __tablename__ = "opportunities"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Basic info
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    external_url: Mapped[Optional[str]] = mapped_column(
        String(2000),
        nullable=True,
    )
    
    # Source & Classification
    source: Mapped[OpportunitySource] = mapped_column(
        Enum(OpportunitySource),
        default=OpportunitySource.OTHER,
        nullable=False,
    )
    status: Mapped[OpportunityStatus] = mapped_column(
        Enum(OpportunityStatus),
        default=OpportunityStatus.LEAD,
        nullable=False,
        index=True,
    )
    
    # Value
    value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="EUR",
        nullable=False,
    )
    probability: Mapped[int] = mapped_column(
        Integer,
        default=50,
        nullable=False,
    )  # 0-100
    
    # Client info
    client_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    client_rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )  # e.g., 4.85
    client_total_spent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    client_location: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    
    # Technical
    tech_stack: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
        nullable=True,
    )
    
    # NH Analysis
    nh_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )  # 0-100
    nh_analysis: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # Timeline
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expected_close_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="opportunities")
    project: Mapped[Optional["Project"]] = relationship(
        back_populates="opportunity",
        uselist=False,
    )
    status_history: Mapped[list["OpportunityStatusHistory"]] = relationship(
        back_populates="opportunity",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Opportunity {self.title[:50]}>"


class OpportunityStatusHistory(Base, TimestampMixin):
    """
    Track status changes for opportunities.
    """
    
    __tablename__ = "opportunity_status_history"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    opportunity_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[Optional[OpportunityStatus]] = mapped_column(
        Enum(OpportunityStatus),
        nullable=True,
    )
    to_status: Mapped[OpportunityStatus] = mapped_column(
        Enum(OpportunityStatus),
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Relationships
    opportunity: Mapped["Opportunity"] = relationship(
        back_populates="status_history",
    )
    
    def __repr__(self) -> str:
        return f"<StatusHistory {self.from_status} -> {self.to_status}>"


class Project(Base, TimestampMixin):
    """
    Active project (from won opportunity).
    """
    
    __tablename__ = "projects"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opportunity_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Basic info
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus),
        default=ProjectStatus.NOT_STARTED,
        nullable=False,
    )
    
    # Value
    contract_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="EUR",
        nullable=False,
    )
    
    # Timeline
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Time tracking
    estimated_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )
    actual_hours: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        default=Decimal("0"),
        nullable=False,
    )
    sw_hours: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        default=Decimal("0"),
        nullable=False,
    )  # Hours generated by Synaptic Weaver
    review_hours: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        default=Decimal("0"),
        nullable=False,
    )  # Hours spent reviewing
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="projects")
    opportunity: Mapped[Optional["Opportunity"]] = relationship(
        back_populates="project",
    )
    
    def __repr__(self) -> str:
        return f"<Project {self.title[:50]}>"


class FinancialRecord(Base, TimestampMixin, SoftDeleteMixin):
    """
    Income and expense tracking.
    
    EPOCH 4 - Financial Tracker.
    """
    
    __tablename__ = "financial_records"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Type & Category
    record_type: Mapped[FinancialRecordType] = mapped_column(
        Enum(FinancialRecordType),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    # Value
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="EUR",
        nullable=False,
    )
    
    # Details
    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )  # e.g., "Citi", "Upwork", "Tools"
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Date
    record_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    
    # Reference
    project_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="financial_records")
    
    def __repr__(self) -> str:
        return f"<FinancialRecord {self.record_type.value} {self.amount} {self.currency}>"


class FinancialGoal(Base, TimestampMixin):
    """
    Financial goals for tracking North Star progress.

    EPOCH 4 - Financial Tracker.
    """

    __tablename__ = "financial_goals"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Goal details
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    target_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    current_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="EUR",
        nullable=False,
    )

    # Timeline
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Status
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus),
        default=GoalStatus.ACTIVE,
        nullable=False,
    )

    # Tracking
    is_north_star: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )  # Only one goal can be North Star

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="financial_goals")

    def __repr__(self) -> str:
        return f"<FinancialGoal {self.name}: {self.current_amount}/{self.target_amount}>"


class SessionLog(Base, TimestampMixin):
    """
    Development session logs for Memory Cortex.

    EPOCH 6 - Memory Cortex.
    """
    
    __tablename__ = "session_logs"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    session_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    
    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    
    # Metrics
    tasks_attempted: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    tasks_completed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    tasks_failed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    errors_total: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    errors_self_resolved: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    rollbacks: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    
    # Learning outputs
    patterns_discovered: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
        nullable=True,
    )
    anti_patterns_discovered: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
        nullable=True,
    )
    claude_md_suggestions: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
        nullable=True,
    )
    
    def __repr__(self) -> str:
        return f"<SessionLog {self.session_id}>"


class Pattern(Base, TimestampMixin):
    """
    Extracted patterns for knowledge base.
    
    EPOCH 6 - Memory Cortex.
    """
    
    __tablename__ = "patterns"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    pattern_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # "success", "failure", "efficiency"
    
    # Classification
    task_types: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    
    # Content
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    recommendation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    claude_md_snippet: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Confidence
    evidence_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        default=Decimal("0.5"),
        nullable=False,
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    def __repr__(self) -> str:
        return f"<Pattern {self.pattern_type}: {self.description[:50]}>"


class TaskClassification(Base, TimestampMixin):
    """
    Task type classification data.
    
    EPOCH 6 - Memory Cortex.
    """
    
    __tablename__ = "task_classifications"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    task_type: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    
    # Classification
    recommended_mode: Mapped[TaskMode] = mapped_column(
        Enum(TaskMode),
        default=TaskMode.CHECKPOINTED,
        nullable=False,
    )
    
    # Stats
    sample_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    success_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        default=Decimal("0.5"),
        nullable=False,
    )
    avg_time_seconds: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0"),
        nullable=False,
    )
    human_intervention_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        default=Decimal("0"),
        nullable=False,
    )
    
    # Common issues
    common_errors: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
        nullable=True,
    )
    
    def __repr__(self) -> str:
        return f"<TaskClassification {self.task_type}: {self.recommended_mode.value}>"


# ==========================================================================
# Pipeline Orchestrator Models (EPOCH 7 - Taśmociąg)
# ==========================================================================

class Epoch(Base, TimestampMixin):
    """
    System epoch versioning.

    Tracks the evolution of the NH system through major phases.
    EPOCH 7 - Pipeline Orchestrator.
    """

    __tablename__ = "epochs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )  # e.g., "EPOCH_1_MVP", "EPOCH_2_INTEGRATION"
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # e.g., "0.1.0"
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    features: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )  # List of enabled features
    status: Mapped[EpochStatus] = mapped_column(
        Enum(EpochStatus),
        default=EpochStatus.ACTIVE,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    pipeline_runs: Mapped[list["PipelineRun"]] = relationship(
        back_populates="epoch",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Epoch {self.name} v{self.version}>"


class PipelineRun(Base, TimestampMixin):
    """
    Pipeline execution run.

    Tracks a single task through all pipeline stages.
    EPOCH 7 - Pipeline Orchestrator.
    """

    __tablename__ = "pipeline_runs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    task_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )  # Reference to external task
    task_title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    task_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    project_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    epoch_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("epochs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Pipeline state
    current_stage: Mapped[PipelineStage] = mapped_column(
        Enum(PipelineStage),
        default=PipelineStage.QUEUED,
        nullable=False,
        index=True,
    )
    status: Mapped[PipelineRunStatus] = mapped_column(
        Enum(PipelineRunStatus),
        default=PipelineRunStatus.RUNNING,
        nullable=False,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        default="normal",
        nullable=False,
    )  # critical, high, normal, low

    # Execution
    escalation_level: Mapped[EscalationLevel] = mapped_column(
        Enum(EscalationLevel),
        default=EscalationLevel.CODEX,
        nullable=False,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Results
    final_trust_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )  # 0-100
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    run_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )

    # Relationships
    epoch: Mapped[Optional["Epoch"]] = relationship(
        back_populates="pipeline_runs",
    )
    stage_executions: Mapped[list["StageExecution"]] = relationship(
        back_populates="pipeline_run",
        lazy="selectin",
        order_by="StageExecution.created_at",
    )
    handoff_tokens: Mapped[list["HandoffToken"]] = relationship(
        back_populates="pipeline_run",
        lazy="selectin",
        order_by="HandoffToken.created_at",
    )
    resource_allocations: Mapped[list["ResourceAllocation"]] = relationship(
        back_populates="pipeline_run",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PipelineRun {self.task_id} [{self.current_stage.value}]>"


class StageExecution(Base, TimestampMixin):
    """
    Individual stage execution within a pipeline run.

    EPOCH 7 - Pipeline Orchestrator.
    """

    __tablename__ = "stage_executions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[PipelineStage] = mapped_column(
        Enum(PipelineStage),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )  # pending, running, passed, failed, skipped

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # Results
    output: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )  # {tests_passed, lint_errors, health_score, etc.}
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Agent info
    agent_used: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )  # codex, sonnet, opus
    retry_attempt: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Handoff reference
    handoff_token_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("handoff_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    pipeline_run: Mapped["PipelineRun"] = relationship(
        back_populates="stage_executions",
    )
    handoff_token: Mapped[Optional["HandoffToken"]] = relationship(
        foreign_keys=[handoff_token_id],
    )

    def __repr__(self) -> str:
        return f"<StageExecution {self.stage.value} [{self.status}]>"


class HandoffToken(Base, TimestampMixin):
    """
    Gate token for stage transitions.

    Cryptographically signed verification of stage completion.
    Trust score must be >= 70 to proceed.
    EPOCH 7 - Pipeline Orchestrator.
    """

    __tablename__ = "handoff_tokens"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Transition
    from_stage: Mapped[PipelineStage] = mapped_column(
        Enum(PipelineStage),
        nullable=False,
    )
    to_stage: Mapped[PipelineStage] = mapped_column(
        Enum(PipelineStage),
        nullable=False,
    )

    # Trust scoring
    trust_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )  # 0-100, must be >= 70 to pass

    # Verification results
    verification: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )  # {tests: {passed, failed, skipped}, lint: {errors, warnings}, health: {score, checks}}

    # Score breakdown
    tests_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0"),
        nullable=False,
    )  # Max 40 points
    lint_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0"),
        nullable=False,
    )  # Max 20 points
    health_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0"),
        nullable=False,
    )  # Max 30 points
    console_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0"),
        nullable=False,
    )  # Max 10 points

    # Cryptographic signature
    signature: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )  # SHA256 hash of payload

    # Status
    valid: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    rejected_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    pipeline_run: Mapped["PipelineRun"] = relationship(
        back_populates="handoff_tokens",
    )

    def __repr__(self) -> str:
        return f"<HandoffToken {self.from_stage.value}→{self.to_stage.value} score={self.trust_score}>"


class GuardrailViolation(Base, TimestampMixin):
    """
    Log of guardrail violation attempts.

    Records when actions are blocked by guardrails.
    EPOCH 7 - Pipeline Orchestrator.
    """

    __tablename__ = "guardrail_violations"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Violation details
    layer: Mapped[GuardrailLayer] = mapped_column(
        Enum(GuardrailLayer),
        nullable=False,
        index=True,
    )
    rule_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    attempted_action: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Outcome
    blocked: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )  # True if action was prevented
    override_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )  # If blocked=False, why was override allowed

    # Context
    actor: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )  # Who/what attempted the action
    pipeline_run_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    context: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )  # Additional context data

    def __repr__(self) -> str:
        status = "BLOCKED" if self.blocked else "ALLOWED"
        return f"<GuardrailViolation [{status}] {self.layer.value}:{self.rule_name}>"


class ResourceAllocation(Base, TimestampMixin):
    """
    Dynamic resource allocation tracking.

    Tracks ports and other resources allocated to pipeline runs.
    EPOCH 7 - Pipeline Orchestrator.
    """

    __tablename__ = "resource_allocations"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    pipeline_run_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # Resource details
    resource_type: Mapped[ResourceType] = mapped_column(
        Enum(ResourceType),
        nullable=False,
    )
    value: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )  # Port number or other numeric resource

    # Lifecycle
    allocated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    released_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    pipeline_run: Mapped[Optional["PipelineRun"]] = relationship(
        back_populates="resource_allocations",
    )

    def __repr__(self) -> str:
        status = "active" if self.is_active else "released"
        return f"<ResourceAllocation {self.resource_type.value}={self.value} [{status}]>"


class POReviewRequest(Base, TimestampMixin):
    """
    Product Owner review request.

    Tracks PO review queue and decisions.
    EPOCH 7 - Pipeline Orchestrator.
    """

    __tablename__ = "po_review_requests"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Request details
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )  # pending, approved, rejected, changes_requested

    # Metrics for review
    health_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    tests_passed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    tests_failed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    tests_skipped: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    coverage_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    # Warnings & Blockers
    warnings: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    blockers: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    # Preview
    preview_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )  # localhost URL with dynamic port

    # PO Decision
    decision_by: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    decision_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    feedback: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<POReviewRequest {self.pipeline_run_id} [{self.status}]>"


# ==========================================================================
# CC Session Manager Models (EPOCH 8 - Visibility & Reliability)
# ==========================================================================

class CCSession(Base, TimestampMixin):
    """
    Claude Code session tracking.

    Manages CC execution sessions with visibility, health monitoring,
    and automatic restart capabilities.
    EPOCH 8 - CC Session Manager.
    """

    __tablename__ = "cc_sessions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Session identification
    session_name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )  # e.g., "cc-a1b2c3d4"

    # Platform & Process
    platform: Mapped[CCSessionPlatform] = mapped_column(
        Enum(CCSessionPlatform),
        nullable=False,
    )
    process_handle: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )  # tmux session name or Windows process ID
    working_directory: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    # Status tracking
    status: Mapped[CCSessionStatus] = mapped_column(
        Enum(CCSessionStatus),
        default=CCSessionStatus.IDLE,
        nullable=False,
        index=True,
    )

    # Pipeline context
    pipeline_run_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    stage_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )  # Pipeline stage being executed
    task_prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )  # Current task prompt

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Health monitoring
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_output_line: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    output_file: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )  # Path to output log file

    # Restart tracking
    restart_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    max_restarts: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )
    parent_session_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cc_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )  # Link to previous session if restarted

    # Configuration
    dangerous_mode: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )  # --dangerously-skip-permissions
    max_runtime_minutes: Mapped[int] = mapped_column(
        Integer,
        default=25,
        nullable=False,
    )  # Auto-restart before 30min crash
    heartbeat_timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        default=60,
        nullable=False,
    )  # Mark as stuck if no output

    # Results
    exit_code: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    completion_detected: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )  # Did we detect task completion?

    # Context for restarts
    context_snapshot: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )  # Last N lines of output for restart context

    # Relationships
    pipeline_run: Mapped[Optional["PipelineRun"]] = relationship(
        foreign_keys=[pipeline_run_id],
    )
    parent_session: Mapped[Optional["CCSession"]] = relationship(
        remote_side=[id],
        foreign_keys=[parent_session_id],
    )

    def __repr__(self) -> str:
        return f"<CCSession {self.session_name} [{self.status.value}]>"


class CCSessionOutput(Base):
    """
    CC Session output line storage.

    Stores output lines for streaming and analysis.
    Uses a separate table for efficient appends and queries.
    """

    __tablename__ = "cc_session_outputs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cc_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Classification
    is_error: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_completion_marker: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<CCSessionOutput L{self.line_number}: {preview}>"
