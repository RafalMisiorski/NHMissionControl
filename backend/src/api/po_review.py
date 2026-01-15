"""
PO Review API Routes.

REST endpoints for Product Owner review management.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.models import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStage,
    POReviewRequest,
)

router = APIRouter(prefix="/api/v1/po-review", tags=["po-review"])


# ==========================================================================
# Schemas
# ==========================================================================

class ReviewQueueItem(BaseModel):
    """Item in the PO review queue."""
    id: UUID
    pipeline_run_id: UUID
    task_id: str
    task_title: str
    project_name: Optional[str]
    priority: str
    health_score: float
    tests_passed: int
    tests_failed: int
    tests_skipped: int
    coverage_percent: Optional[float]
    warnings: list[str]
    blockers: list[str]
    preview_url: Optional[str]
    status: str
    created_at: str

    class Config:
        from_attributes = True


class ApproveRequest(BaseModel):
    """Request to approve a review."""
    feedback: Optional[str] = Field(None, description="Optional approval feedback")
    approved_by: str = Field("PO", description="Name/identifier of approver")


class RequestChangesRequest(BaseModel):
    """Request to request changes."""
    feedback: str = Field(..., description="Required feedback for changes")
    requested_by: str = Field("PO", description="Name/identifier of requester")


class RejectRequest(BaseModel):
    """Request to reject a review."""
    reason: str = Field(..., description="Reason for rejection")
    rejected_by: str = Field("PO", description="Name/identifier of rejecter")


class ReviewResponse(BaseModel):
    """Response after review action."""
    id: UUID
    pipeline_run_id: UUID
    status: str
    decision_by: Optional[str]
    decision_at: Optional[str]
    feedback: Optional[str]
    message: str

    class Config:
        from_attributes = True


# ==========================================================================
# Endpoints
# ==========================================================================

@router.get("/queue", response_model=list[ReviewQueueItem])
async def get_review_queue(
    priority: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all items awaiting PO review.

    Returns tasks in PO_REVIEW stage sorted by priority.
    """
    # Get pipeline runs in PO_REVIEW stage
    query = (
        select(PipelineRun)
        .where(PipelineRun.current_stage == PipelineStage.PO_REVIEW)
        .where(PipelineRun.status == PipelineRunStatus.RUNNING)
    )

    if priority:
        query = query.where(PipelineRun.priority == priority)

    # Order by priority (critical > high > normal > low)
    result = await db.execute(query.order_by(PipelineRun.created_at.asc()))
    runs = result.scalars().all()

    items = []
    for run in runs:
        # Get or create review request
        review_result = await db.execute(
            select(POReviewRequest).where(POReviewRequest.pipeline_run_id == run.id)
        )
        review = review_result.scalar_one_or_none()

        if not review:
            # Create review request if doesn't exist
            review = await _create_review_request(db, run)

        items.append(_to_queue_item(run, review))

    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
    items.sort(key=lambda x: priority_order.get(x.priority, 2))

    return items


@router.get("/{run_id}", response_model=ReviewQueueItem)
async def get_review_item(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific review item by pipeline run ID."""
    result = await db.execute(
        select(PipelineRun).where(PipelineRun.id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run {run_id} not found",
        )

    review_result = await db.execute(
        select(POReviewRequest).where(POReviewRequest.pipeline_run_id == run.id)
    )
    review = review_result.scalar_one_or_none()

    if not review:
        review = await _create_review_request(db, run)

    return _to_queue_item(run, review)


@router.post("/{run_id}/approve", response_model=ReviewResponse)
async def approve_review(
    run_id: UUID,
    request: ApproveRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Approve a PO review - moves pipeline to DEPLOYING stage.

    Requires:
    - No blockers present
    - Health score >= policy minimum (default 70)
    """
    run, review = await _get_run_and_review(db, run_id)

    # Check for blockers
    if review.blockers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve with blockers: {review.blockers}",
        )

    # Update review
    review.status = "approved"
    review.decision_by = request.approved_by
    review.decision_at = datetime.now(timezone.utc)
    review.feedback = request.feedback

    # Move pipeline to deploying
    run.current_stage = PipelineStage.DEPLOYING

    await db.commit()

    return ReviewResponse(
        id=review.id,
        pipeline_run_id=run.id,
        status="approved",
        decision_by=review.decision_by,
        decision_at=review.decision_at.isoformat() if review.decision_at else None,
        feedback=review.feedback,
        message=f"Approved and moved to {PipelineStage.DEPLOYING.value}",
    )


@router.post("/{run_id}/request-changes", response_model=ReviewResponse)
async def request_changes(
    run_id: UUID,
    request: RequestChangesRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request changes - moves pipeline back to DEVELOPING stage.

    Requires feedback describing what needs to change.
    """
    run, review = await _get_run_and_review(db, run_id)

    # Update review
    review.status = "changes_requested"
    review.decision_by = request.requested_by
    review.decision_at = datetime.now(timezone.utc)
    review.feedback = request.feedback

    # Move pipeline back to developing
    run.current_stage = PipelineStage.DEVELOPING
    run.retry_count = 0  # Reset retry count

    await db.commit()

    return ReviewResponse(
        id=review.id,
        pipeline_run_id=run.id,
        status="changes_requested",
        decision_by=review.decision_by,
        decision_at=review.decision_at.isoformat() if review.decision_at else None,
        feedback=review.feedback,
        message=f"Changes requested, moved back to {PipelineStage.DEVELOPING.value}",
    )


@router.post("/{run_id}/reject", response_model=ReviewResponse)
async def reject_review(
    run_id: UUID,
    request: RejectRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reject a PO review - cancels the pipeline run.

    Requires a reason for rejection.
    """
    run, review = await _get_run_and_review(db, run_id)

    # Update review
    review.status = "rejected"
    review.decision_by = request.rejected_by
    review.decision_at = datetime.now(timezone.utc)
    review.feedback = request.reason

    # Cancel pipeline
    run.status = PipelineRunStatus.CANCELLED
    run.current_stage = PipelineStage.CANCELLED
    run.completed_at = datetime.now(timezone.utc)
    run.error_message = f"Rejected by {request.rejected_by}: {request.reason}"

    await db.commit()

    return ReviewResponse(
        id=review.id,
        pipeline_run_id=run.id,
        status="rejected",
        decision_by=review.decision_by,
        decision_at=review.decision_at.isoformat() if review.decision_at else None,
        feedback=review.feedback,
        message="Pipeline cancelled due to rejection",
    )


@router.get("/stats/summary")
async def get_review_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get summary statistics for PO reviews."""
    # Count pending reviews
    pending_result = await db.execute(
        select(POReviewRequest).where(POReviewRequest.status == "pending")
    )
    pending = len(pending_result.scalars().all())

    # Count by status
    all_result = await db.execute(select(POReviewRequest))
    all_reviews = all_result.scalars().all()

    status_counts = {}
    for review in all_reviews:
        status_counts[review.status] = status_counts.get(review.status, 0) + 1

    # Average health score of pending reviews
    pending_reviews_result = await db.execute(
        select(POReviewRequest).where(POReviewRequest.status == "pending")
    )
    pending_reviews = pending_reviews_result.scalars().all()
    avg_health = (
        sum(float(r.health_score) for r in pending_reviews) / len(pending_reviews)
        if pending_reviews
        else 0
    )

    return {
        "pending_count": pending,
        "status_breakdown": status_counts,
        "average_health_score": round(avg_health, 1),
        "blocked_count": sum(1 for r in pending_reviews if r.blockers),
    }


# ==========================================================================
# Helper Functions
# ==========================================================================

async def _get_run_and_review(
    db: AsyncSession, run_id: UUID
) -> tuple[PipelineRun, POReviewRequest]:
    """Get pipeline run and its review request."""
    run_result = await db.execute(
        select(PipelineRun).where(PipelineRun.id == run_id)
    )
    run = run_result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run {run_id} not found",
        )

    if run.current_stage != PipelineStage.PO_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pipeline not in PO review stage (current: {run.current_stage.value})",
        )

    review_result = await db.execute(
        select(POReviewRequest).where(POReviewRequest.pipeline_run_id == run.id)
    )
    review = review_result.scalar_one_or_none()

    if not review:
        review = await _create_review_request(db, run)

    return run, review


async def _create_review_request(
    db: AsyncSession, run: PipelineRun
) -> POReviewRequest:
    """Create a PO review request for a pipeline run."""
    # Determine health score from trust score or default
    health_score = float(run.final_trust_score) if run.final_trust_score else 70.0

    # Determine blockers and warnings
    blockers = []
    warnings = []

    if health_score < 70:
        blockers.append(f"Health score {health_score:.0f}% below minimum 70%")

    if health_score < 85:
        warnings.append(f"Health score {health_score:.0f}% is below recommended 85%")

    # Create preview URL if resources allocated
    preview_url = None
    if run.resource_allocations:
        for alloc in run.resource_allocations:
            if alloc.resource_type.value == "frontend_port" and alloc.is_active:
                preview_url = f"http://localhost:{alloc.value}"
                break

    review = POReviewRequest(
        id=uuid4(),
        pipeline_run_id=run.id,
        status="pending",
        health_score=Decimal(str(health_score)),
        tests_passed=0,  # Would come from stage execution
        tests_failed=0,
        tests_skipped=0,
        coverage_percent=None,
        warnings=warnings,
        blockers=blockers,
        preview_url=preview_url,
    )

    db.add(review)
    await db.commit()
    await db.refresh(review)

    return review


def _to_queue_item(run: PipelineRun, review: POReviewRequest) -> ReviewQueueItem:
    """Convert run and review to queue item."""
    return ReviewQueueItem(
        id=review.id,
        pipeline_run_id=run.id,
        task_id=run.task_id,
        task_title=run.task_title,
        project_name=run.project_name,
        priority=run.priority,
        health_score=float(review.health_score),
        tests_passed=review.tests_passed,
        tests_failed=review.tests_failed,
        tests_skipped=review.tests_skipped,
        coverage_percent=float(review.coverage_percent) if review.coverage_percent else None,
        warnings=review.warnings,
        blockers=review.blockers,
        preview_url=review.preview_url,
        status=review.status,
        created_at=review.created_at.isoformat() if review.created_at else None,
    )
