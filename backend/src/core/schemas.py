"""
NH Mission Control - Pydantic Schemas
======================================

Request and response schemas for API validation.
These define the API contract - CC implements to match these.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.core.models import (
    FinancialRecordType,
    GoalStatus,
    OpportunitySource,
    OpportunityStatus,
    ProjectStatus,
    TaskMode,
    UserRole,
)


# ==========================================================================
# Base Schemas
# ==========================================================================

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""
    
    created_at: datetime
    updated_at: datetime


# ==========================================================================
# Auth Schemas - EPOCH 1
# ==========================================================================

class UserCreate(BaseSchema):
    """Schema for user registration."""
    
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseSchema):
    """Schema for user login."""
    
    email: EmailStr
    password: str


class UserResponse(TimestampSchema):
    """Schema for user in responses (no password)."""
    
    id: UUID
    email: EmailStr
    name: str
    role: UserRole
    is_active: bool
    email_verified: bool
    last_login: Optional[datetime] = None


class UserUpdate(BaseSchema):
    """Schema for updating user profile."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None


class TokenResponse(BaseSchema):
    """Schema for authentication tokens."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class RefreshTokenRequest(BaseSchema):
    """Schema for token refresh."""
    
    refresh_token: str


class PasswordResetRequest(BaseSchema):
    """Schema for password reset request."""
    
    email: EmailStr


class PasswordReset(BaseSchema):
    """Schema for password reset."""
    
    token: str
    new_password: str = Field(min_length=8, max_length=100)
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


# ==========================================================================
# Opportunity Schemas - EPOCH 3
# ==========================================================================

class OpportunityCreate(BaseSchema):
    """Schema for creating an opportunity."""
    
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None
    external_url: Optional[str] = Field(None, max_length=2000)
    source: OpportunitySource = OpportunitySource.OTHER
    value: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    currency: str = Field("EUR", pattern=r"^[A-Z]{3}$")
    probability: int = Field(50, ge=0, le=100)
    client_name: Optional[str] = Field(None, max_length=255)
    client_rating: Optional[Decimal] = Field(None, ge=0, le=5, decimal_places=2)
    client_total_spent: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    client_location: Optional[str] = Field(None, max_length=100)
    tech_stack: Optional[list[str]] = None
    deadline: Optional[datetime] = None
    expected_close_date: Optional[datetime] = None
    notes: Optional[str] = None


class OpportunityUpdate(BaseSchema):
    """Schema for updating an opportunity (partial)."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    external_url: Optional[str] = Field(None, max_length=2000)
    source: Optional[OpportunitySource] = None
    value: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    currency: Optional[str] = Field(None, pattern=r"^[A-Z]{3}$")
    probability: Optional[int] = Field(None, ge=0, le=100)
    client_name: Optional[str] = Field(None, max_length=255)
    client_rating: Optional[Decimal] = Field(None, ge=0, le=5, decimal_places=2)
    client_total_spent: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    client_location: Optional[str] = Field(None, max_length=100)
    tech_stack: Optional[list[str]] = None
    deadline: Optional[datetime] = None
    expected_close_date: Optional[datetime] = None
    notes: Optional[str] = None


class OpportunityResponse(TimestampSchema):
    """Schema for opportunity in responses."""
    
    id: UUID
    user_id: UUID
    title: str
    description: Optional[str]
    external_url: Optional[str]
    source: OpportunitySource
    status: OpportunityStatus
    value: Optional[Decimal]
    currency: str
    probability: int
    client_name: Optional[str]
    client_rating: Optional[Decimal]
    client_total_spent: Optional[Decimal]
    client_location: Optional[str]
    tech_stack: Optional[list[str]]
    nh_score: Optional[int]
    nh_analysis: Optional[dict]
    deadline: Optional[datetime]
    expected_close_date: Optional[datetime]
    notes: Optional[str]
    deleted_at: Optional[datetime]


class OpportunityMoveRequest(BaseSchema):
    """Schema for moving opportunity to new status."""
    
    status: OpportunityStatus
    notes: Optional[str] = None


class OpportunityListResponse(BaseSchema):
    """Schema for paginated opportunity list."""
    
    items: list[OpportunityResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ==========================================================================
# Pipeline Stats Schemas - EPOCH 3
# ==========================================================================

class PipelineStageStats(BaseSchema):
    """Stats for a single pipeline stage."""
    
    status: OpportunityStatus
    count: int
    total_value: Decimal
    weighted_value: Decimal  # value * probability


class PipelineStats(BaseSchema):
    """Overall pipeline statistics."""
    
    stages: list[PipelineStageStats]
    total_opportunities: int
    total_value: Decimal
    weighted_pipeline_value: Decimal
    conversion_rate: Decimal  # won / (won + lost)
    avg_deal_size: Decimal
    opportunities_by_source: dict[str, int]


# ==========================================================================
# NH Analysis Schemas - EPOCH 3
# ==========================================================================

class OpportunityAnalysis(BaseSchema):
    """NH analysis results for an opportunity."""
    
    opportunity_id: UUID
    score: int = Field(ge=0, le=100)
    
    # Breakdown
    budget_fit_score: int = Field(ge=0, le=100)
    client_quality_score: int = Field(ge=0, le=100)
    technical_fit_score: int = Field(ge=0, le=100)
    timeline_fit_score: int = Field(ge=0, le=100)
    competition_score: int = Field(ge=0, le=100)
    
    # Insights
    strengths: list[str]
    risks: list[str]
    recommendations: list[str]
    
    # Classification
    sw_difficulty_tier: int = Field(ge=1, le=5)
    recommended_mode: TaskMode
    
    # Estimates
    estimated_hours: Decimal
    estimated_sw_hours: Decimal
    suggested_price: Decimal
    
    analyzed_at: datetime


class ProposalDraft(BaseSchema):
    """Generated proposal draft."""
    
    opportunity_id: UUID
    
    # Content
    subject: str
    greeting: str
    intro: str
    approach: str
    timeline: str
    pricing: str
    closing: str
    
    # Metadata
    word_count: int
    estimated_reading_time_seconds: int
    
    # Questions to ask client
    clarifying_questions: list[str]
    
    generated_at: datetime


class EffortEstimate(BaseSchema):
    """Effort estimation for an opportunity."""
    
    opportunity_id: UUID
    
    # Classification
    complexity_tier: int = Field(ge=1, le=5)
    
    # Time estimates
    total_hours_min: Decimal
    total_hours_max: Decimal
    total_hours_expected: Decimal
    
    sw_generation_hours: Decimal
    review_hours: Decimal
    communication_hours: Decimal
    buffer_hours: Decimal
    
    # Pricing
    market_rate_min: Decimal
    market_rate_max: Decimal
    suggested_price: Decimal
    floor_price: Decimal
    
    # Efficiency
    effective_hourly_rate: Decimal
    margin_vs_manual: Decimal  # percentage
    
    estimated_at: datetime


# ==========================================================================
# Project Schemas - EPOCH 4
# ==========================================================================

class ProjectCreate(BaseSchema):
    """Schema for creating a project."""
    
    opportunity_id: Optional[UUID] = None
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None
    contract_value: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    currency: str = Field("EUR", pattern=r"^[A-Z]{3}$")
    deadline: Optional[datetime] = None
    estimated_hours: Optional[Decimal] = Field(None, ge=0, decimal_places=2)


class ProjectUpdate(BaseSchema):
    """Schema for updating a project."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    deadline: Optional[datetime] = None
    estimated_hours: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    actual_hours: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    sw_hours: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    review_hours: Optional[Decimal] = Field(None, ge=0, decimal_places=2)


class ProjectResponse(TimestampSchema):
    """Schema for project in responses."""
    
    id: UUID
    user_id: UUID
    opportunity_id: Optional[UUID]
    title: str
    description: Optional[str]
    status: ProjectStatus
    contract_value: Optional[Decimal]
    currency: str
    started_at: Optional[datetime]
    deadline: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_hours: Optional[Decimal]
    actual_hours: Decimal
    sw_hours: Decimal
    review_hours: Decimal


# ==========================================================================
# Financial Schemas - EPOCH 4
# ==========================================================================

class FinancialRecordCreate(BaseSchema):
    """Schema for creating a financial record."""
    
    record_type: FinancialRecordType
    category: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(ge=0, decimal_places=2)
    currency: str = Field("EUR", pattern=r"^[A-Z]{3}$")
    source: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    record_date: datetime
    project_id: Optional[UUID] = None


class FinancialRecordUpdate(BaseSchema):
    """Schema for updating a financial record."""
    
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    currency: Optional[str] = Field(None, pattern=r"^[A-Z]{3}$")
    source: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    record_date: Optional[datetime] = None


class FinancialRecordResponse(TimestampSchema):
    """Schema for financial record in responses."""
    
    id: UUID
    user_id: UUID
    record_type: FinancialRecordType
    category: str
    amount: Decimal
    currency: str
    source: str
    description: Optional[str]
    record_date: datetime
    project_id: Optional[UUID]
    deleted_at: Optional[datetime]


class FinancialSummary(BaseSchema):
    """Financial summary for dashboard."""

    period_start: datetime
    period_end: datetime

    # Income
    total_income: Decimal
    income_by_source: dict[str, Decimal]
    income_by_category: dict[str, Decimal]

    # Expenses
    total_expenses: Decimal
    expenses_by_category: dict[str, Decimal]

    # Net
    net_income: Decimal

    # Comparison
    previous_period_income: Optional[Decimal]
    income_change_percent: Optional[Decimal]


# ==========================================================================
# Financial Goal Schemas - EPOCH 4
# ==========================================================================


class FinancialGoalCreate(BaseSchema):
    """Schema for creating a financial goal."""

    name: str = Field(min_length=1, max_length=255)
    target_amount: Decimal = Field(ge=0, decimal_places=2)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    currency: str = Field("EUR", pattern=r"^[A-Z]{3}$")
    deadline: Optional[datetime] = None
    is_north_star: bool = False
    notes: Optional[str] = None


class FinancialGoalUpdate(BaseSchema):
    """Schema for updating a financial goal."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    target_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    current_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    currency: Optional[str] = Field(None, pattern=r"^[A-Z]{3}$")
    deadline: Optional[datetime] = None
    status: Optional[GoalStatus] = None
    is_north_star: Optional[bool] = None
    notes: Optional[str] = None


class FinancialGoalResponse(TimestampSchema):
    """Schema for financial goal in responses."""

    id: UUID
    user_id: UUID
    name: str
    target_amount: Decimal
    current_amount: Decimal
    currency: str
    deadline: Optional[datetime]
    status: GoalStatus
    is_north_star: bool
    notes: Optional[str]


class GoalProgress(BaseSchema):
    """Progress tracking for a goal."""

    goal_id: UUID
    name: str
    target_amount: Decimal
    current_amount: Decimal
    currency: str
    progress_percent: Decimal
    remaining_amount: Decimal
    is_north_star: bool
    status: GoalStatus
    days_remaining: Optional[int]


class QuickStats(BaseSchema):
    """Quick financial stats for dashboard cards."""

    mtd_income: Decimal
    mtd_expenses: Decimal
    mtd_net: Decimal
    ytd_income: Decimal
    ytd_expenses: Decimal
    ytd_net: Decimal
    income_change_percent: Optional[Decimal]  # vs previous month
    expense_change_percent: Optional[Decimal]


class FinancialDashboard(BaseSchema):
    """Full financial dashboard data."""

    quick_stats: QuickStats
    north_star: Optional[GoalProgress]
    goals: list[GoalProgress]
    recent_income: list[FinancialRecordResponse]
    recent_expenses: list[FinancialRecordResponse]
    income_by_source: dict[str, Decimal]
    expenses_by_category: dict[str, Decimal]


# ==========================================================================
# Session Log Schemas - EPOCH 6
# ==========================================================================

class SessionLogCreate(BaseSchema):
    """Schema for creating a session log."""
    
    session_id: str = Field(min_length=1, max_length=100)
    started_at: datetime


class SessionLogUpdate(BaseSchema):
    """Schema for updating a session log."""
    
    ended_at: Optional[datetime] = None
    tasks_attempted: Optional[int] = Field(None, ge=0)
    tasks_completed: Optional[int] = Field(None, ge=0)
    tasks_failed: Optional[int] = Field(None, ge=0)
    errors_total: Optional[int] = Field(None, ge=0)
    errors_self_resolved: Optional[int] = Field(None, ge=0)
    rollbacks: Optional[int] = Field(None, ge=0)
    patterns_discovered: Optional[list[dict]] = None
    anti_patterns_discovered: Optional[list[dict]] = None
    claude_md_suggestions: Optional[list[str]] = None


class SessionLogResponse(TimestampSchema):
    """Schema for session log in responses."""
    
    id: UUID
    session_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    tasks_attempted: int
    tasks_completed: int
    tasks_failed: int
    errors_total: int
    errors_self_resolved: int
    rollbacks: int
    patterns_discovered: Optional[list[dict]]
    anti_patterns_discovered: Optional[list[dict]]
    claude_md_suggestions: Optional[list[str]]


# ==========================================================================
# Pattern Schemas - EPOCH 6
# ==========================================================================

class PatternResponse(TimestampSchema):
    """Schema for pattern in responses."""
    
    id: UUID
    pattern_type: str
    task_types: list[str]
    description: str
    recommendation: str
    claude_md_snippet: Optional[str]
    evidence_count: int
    confidence: Decimal
    is_active: bool


class TaskClassificationResponse(TimestampSchema):
    """Schema for task classification in responses."""
    
    id: UUID
    task_type: str
    recommended_mode: TaskMode
    sample_count: int
    success_rate: Decimal
    avg_time_seconds: Decimal
    human_intervention_rate: Decimal
    common_errors: Optional[list[str]]


# ==========================================================================
# Common Response Schemas
# ==========================================================================

class MessageResponse(BaseSchema):
    """Generic message response."""
    
    message: str
    success: bool = True


class ErrorResponse(BaseSchema):
    """Error response schema."""
    
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class HealthResponse(BaseSchema):
    """Health check response."""
    
    status: str
    version: str
    environment: str
    database: str
    redis: str
