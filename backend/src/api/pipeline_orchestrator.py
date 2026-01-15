"""
Pipeline Orchestrator API Routes.

REST endpoints for pipeline management.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.core.models import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStage,
    StageExecution,
    HandoffToken,
    EscalationLevel,
)
from src.core.pipeline import (
    PipelineOrchestrator,
    HandoffTokenGenerator,
    NeuralRalph,
    ResourceManager,
    EscalationManager,
    GuardrailsEngine,
)

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


# ==========================================================================
# Schemas
# ==========================================================================

class CreatePipelineRunRequest(BaseModel):
    """Request to create a new pipeline run."""
    task_id: str = Field(..., description="External task identifier")
    task_title: str = Field(..., description="Human-readable task title")
    task_description: Optional[str] = Field(None, description="Full task description")
    project_name: Optional[str] = Field(None, description="Associated project name")
    priority: str = Field("normal", description="Task priority: critical, high, normal, low")


class PipelineRunResponse(BaseModel):
    """Pipeline run response."""
    id: UUID
    task_id: str
    task_title: str
    task_description: Optional[str]
    project_name: Optional[str]
    current_stage: str
    status: str
    priority: str
    escalation_level: str
    retry_count: int
    max_retries: int
    final_trust_score: Optional[float]
    error_message: Optional[str]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]

    class Config:
        from_attributes = True


class StageExecutionResponse(BaseModel):
    """Stage execution response."""
    id: UUID
    stage: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_seconds: Optional[int]
    agent_used: Optional[str]
    retry_attempt: int
    output: Optional[dict]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class HandoffTokenResponse(BaseModel):
    """Handoff token response."""
    id: UUID
    from_stage: str
    to_stage: str
    trust_score: float
    tests_score: float
    lint_score: float
    health_score: float
    console_score: float
    valid: bool
    rejected_reason: Optional[str]
    signature: str
    created_at: str

    class Config:
        from_attributes = True


class RetryRequest(BaseModel):
    """Request to retry a pipeline stage."""
    force: bool = Field(False, description="Force retry even if max retries reached")


class EscalateRequest(BaseModel):
    """Request to escalate a pipeline run."""
    target_level: Optional[str] = Field(None, description="Target escalation level")
    reason: str = Field("Manual escalation", description="Reason for escalation")


# ==========================================================================
# Endpoints
# ==========================================================================

@router.post("/runs", response_model=PipelineRunResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline_run(
    request: CreatePipelineRunRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new pipeline run for a task.

    Creates a pipeline run and places it in the QUEUED stage.
    """
    orchestrator = PipelineOrchestrator(db)

    run = await orchestrator.create_run(
        task_id=request.task_id,
        task_title=request.task_title,
        task_description=request.task_description,
        project_name=request.project_name,
        priority=request.priority,
    )

    return _run_to_response(run)


@router.get("/runs", response_model=list[PipelineRunResponse])
async def list_pipeline_runs(
    status: Optional[str] = None,
    stage: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    List pipeline runs with optional filtering.

    Args:
        status: Filter by status (running, paused, completed, failed, cancelled)
        stage: Filter by current stage
        limit: Maximum number of results
    """
    query = select(PipelineRun).order_by(PipelineRun.created_at.desc()).limit(limit)

    if status:
        try:
            status_enum = PipelineRunStatus(status)
            query = query.where(PipelineRun.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}",
            )

    if stage:
        try:
            stage_enum = PipelineStage(stage)
            query = query.where(PipelineRun.current_stage == stage_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid stage: {stage}",
            )

    result = await db.execute(query)
    runs = result.scalars().all()

    return [_run_to_response(run) for run in runs]


@router.get("/runs/{run_id}", response_model=PipelineRunResponse)
async def get_pipeline_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific pipeline run by ID."""
    result = await db.execute(
        select(PipelineRun).where(PipelineRun.id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run {run_id} not found",
        )

    return _run_to_response(run)


@router.get("/runs/{run_id}/stages", response_model=list[StageExecutionResponse])
async def get_stage_executions(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all stage executions for a pipeline run."""
    result = await db.execute(
        select(StageExecution)
        .where(StageExecution.pipeline_run_id == run_id)
        .order_by(StageExecution.created_at)
    )
    executions = result.scalars().all()

    return [_execution_to_response(ex) for ex in executions]


@router.get("/runs/{run_id}/tokens", response_model=list[HandoffTokenResponse])
async def get_handoff_tokens(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all handoff tokens for a pipeline run."""
    result = await db.execute(
        select(HandoffToken)
        .where(HandoffToken.pipeline_run_id == run_id)
        .order_by(HandoffToken.created_at)
    )
    tokens = result.scalars().all()

    return [_token_to_response(token) for token in tokens]


@router.post("/runs/{run_id}/start", response_model=PipelineRunResponse)
async def start_pipeline_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Start executing a pipeline run.

    Begins processing from the current stage.
    """
    result = await db.execute(
        select(PipelineRun).where(PipelineRun.id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run {run_id} not found",
        )

    if run.status != PipelineRunStatus.RUNNING:
        if run.status in [PipelineRunStatus.COMPLETED, PipelineRunStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start pipeline in {run.status.value} status",
            )

    # Create orchestrator with components
    resource_manager = ResourceManager(db)
    guardrails = GuardrailsEngine(db)
    handoff_generator = HandoffTokenGenerator(db)
    neural_ralph = NeuralRalph(resource_manager)
    escalation_manager = EscalationManager(db)

    orchestrator = PipelineOrchestrator(
        db=db,
        resource_manager=resource_manager,
        guardrails=guardrails,
        handoff_generator=handoff_generator,
        neural_ralph=neural_ralph,
        escalation_manager=escalation_manager,
    )

    # Execute pipeline (this runs asynchronously)
    run = await orchestrator.run(run)

    return _run_to_response(run)


@router.post("/runs/{run_id}/retry", response_model=PipelineRunResponse)
async def retry_pipeline_stage(
    run_id: UUID,
    request: RetryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger Neural Ralph retry for current stage.

    Will attempt automatic correction if retries available.
    """
    result = await db.execute(
        select(PipelineRun).where(PipelineRun.id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run {run_id} not found",
        )

    if not request.force and run.retry_count >= run.max_retries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Max retries ({run.max_retries}) reached. Use force=true to override.",
        )

    resource_manager = ResourceManager(db)
    neural_ralph = NeuralRalph(resource_manager)

    success = await neural_ralph.attempt_correction(run, run.current_stage)

    if success:
        run.retry_count += 1
        await db.commit()
        await db.refresh(run)

    return _run_to_response(run)


@router.post("/runs/{run_id}/escalate", response_model=PipelineRunResponse)
async def escalate_pipeline_run(
    run_id: UUID,
    request: EscalateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually escalate a pipeline run to a higher agent level.
    """
    result = await db.execute(
        select(PipelineRun).where(PipelineRun.id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run {run_id} not found",
        )

    escalation_manager = EscalationManager(db)

    if request.target_level:
        try:
            target = EscalationLevel(request.target_level)
            await escalation_manager.escalate_to(run, target)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid escalation level: {request.target_level}",
            )
    else:
        await escalation_manager.escalate(run)

    await db.refresh(run)
    return _run_to_response(run)


@router.post("/runs/{run_id}/pause", response_model=PipelineRunResponse)
async def pause_pipeline_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Pause a running pipeline."""
    result = await db.execute(
        select(PipelineRun).where(PipelineRun.id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run {run_id} not found",
        )

    orchestrator = PipelineOrchestrator(db)
    await orchestrator.pause(run)

    return _run_to_response(run)


@router.post("/runs/{run_id}/resume", response_model=PipelineRunResponse)
async def resume_pipeline_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused pipeline."""
    result = await db.execute(
        select(PipelineRun).where(PipelineRun.id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run {run_id} not found",
        )

    orchestrator = PipelineOrchestrator(db)
    await orchestrator.resume(run)

    return _run_to_response(run)


@router.post("/runs/{run_id}/cancel", response_model=PipelineRunResponse)
async def cancel_pipeline_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pipeline run."""
    result = await db.execute(
        select(PipelineRun).where(PipelineRun.id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run {run_id} not found",
        )

    orchestrator = PipelineOrchestrator(db)
    await orchestrator.cancel(run)

    return _run_to_response(run)


# ==========================================================================
# Helper Functions
# ==========================================================================

def _run_to_response(run: PipelineRun) -> PipelineRunResponse:
    """Convert PipelineRun to response model."""
    return PipelineRunResponse(
        id=run.id,
        task_id=run.task_id,
        task_title=run.task_title,
        task_description=run.task_description,
        project_name=run.project_name,
        current_stage=run.current_stage.value,
        status=run.status.value,
        priority=run.priority,
        escalation_level=run.escalation_level.value,
        retry_count=run.retry_count,
        max_retries=run.max_retries,
        final_trust_score=float(run.final_trust_score) if run.final_trust_score else None,
        error_message=run.error_message,
        created_at=run.created_at.isoformat() if run.created_at else None,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
    )


def _execution_to_response(ex: StageExecution) -> StageExecutionResponse:
    """Convert StageExecution to response model."""
    return StageExecutionResponse(
        id=ex.id,
        stage=ex.stage.value,
        status=ex.status,
        started_at=ex.started_at.isoformat() if ex.started_at else None,
        completed_at=ex.completed_at.isoformat() if ex.completed_at else None,
        duration_seconds=ex.duration_seconds,
        agent_used=ex.agent_used,
        retry_attempt=ex.retry_attempt,
        output=ex.output,
        error_message=ex.error_message,
    )


def _token_to_response(token: HandoffToken) -> HandoffTokenResponse:
    """Convert HandoffToken to response model."""
    return HandoffTokenResponse(
        id=token.id,
        from_stage=token.from_stage.value,
        to_stage=token.to_stage.value,
        trust_score=float(token.trust_score),
        tests_score=float(token.tests_score),
        lint_score=float(token.lint_score),
        health_score=float(token.health_score),
        console_score=float(token.console_score),
        valid=token.valid,
        rejected_reason=token.rejected_reason,
        signature=token.signature,
        created_at=token.created_at.isoformat() if token.created_at else None,
    )
