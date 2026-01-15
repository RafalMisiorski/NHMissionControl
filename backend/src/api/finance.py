"""
NH Mission Control - Finance API
=================================

Financial tracking endpoints for income, expenses, and goals.

EPOCH 4 - Financial Tracker.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import CurrentUser, DbSession
from src.core.models import (
    FinancialGoal,
    FinancialRecord,
    FinancialRecordType,
    GoalStatus,
    User,
)
from src.core.schemas import (
    FinancialDashboard,
    FinancialGoalCreate,
    FinancialGoalResponse,
    FinancialGoalUpdate,
    FinancialRecordCreate,
    FinancialRecordResponse,
    FinancialRecordUpdate,
    GoalProgress,
    MessageResponse,
    QuickStats,
)

router = APIRouter(prefix="/finance", tags=["Finance"])


# ==========================================================================
# Helper Functions
# ==========================================================================


def calculate_goal_progress(goal: FinancialGoal) -> GoalProgress:
    """Calculate progress for a single goal."""
    progress_percent = Decimal("0")
    if goal.target_amount > 0:
        progress_percent = (goal.current_amount / goal.target_amount) * 100
        progress_percent = min(progress_percent, Decimal("100"))

    remaining = max(goal.target_amount - goal.current_amount, Decimal("0"))

    days_remaining = None
    if goal.deadline:
        # Handle both timezone-aware and naive datetimes
        deadline = goal.deadline
        now = datetime.now(timezone.utc)
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        delta = deadline - now
        days_remaining = max(0, delta.days)

    return GoalProgress(
        goal_id=goal.id,
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        currency=goal.currency,
        progress_percent=progress_percent.quantize(Decimal("0.01")),
        remaining_amount=remaining,
        is_north_star=goal.is_north_star,
        status=goal.status,
        days_remaining=days_remaining,
    )


# ==========================================================================
# Financial Records (Income & Expenses)
# ==========================================================================


@router.get(
    "/records",
    response_model=list[FinancialRecordResponse],
    summary="List financial records",
)
async def list_records(
    current_user: CurrentUser,
    db: DbSession,
    record_type: Optional[FinancialRecordType] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[FinancialRecordResponse]:
    """
    List financial records for the current user.

    Supports filtering by type (income/expense), date range, category, and source.
    """
    query = select(FinancialRecord).where(
        and_(
            FinancialRecord.user_id == current_user.id,
            FinancialRecord.deleted_at.is_(None),
        )
    )

    if record_type:
        query = query.where(FinancialRecord.record_type == record_type)
    if start_date:
        query = query.where(FinancialRecord.record_date >= start_date)
    if end_date:
        query = query.where(FinancialRecord.record_date <= end_date)
    if category:
        query = query.where(FinancialRecord.category == category)
    if source:
        query = query.where(FinancialRecord.source == source)

    query = query.order_by(FinancialRecord.record_date.desc())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    records = result.scalars().all()

    return [FinancialRecordResponse.model_validate(r) for r in records]


@router.post(
    "/records",
    response_model=FinancialRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create financial record",
)
async def create_record(
    data: FinancialRecordCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> FinancialRecordResponse:
    """Create a new financial record (income or expense)."""
    record = FinancialRecord(
        user_id=current_user.id,
        record_type=data.record_type,
        category=data.category,
        amount=data.amount,
        currency=data.currency,
        source=data.source,
        description=data.description,
        record_date=data.record_date,
        project_id=data.project_id,
    )

    db.add(record)
    await db.commit()
    await db.refresh(record)

    return FinancialRecordResponse.model_validate(record)


@router.get(
    "/records/{record_id}",
    response_model=FinancialRecordResponse,
    summary="Get financial record",
)
async def get_record(
    record_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> FinancialRecordResponse:
    """Get a specific financial record."""
    result = await db.execute(
        select(FinancialRecord).where(
            and_(
                FinancialRecord.id == record_id,
                FinancialRecord.user_id == current_user.id,
                FinancialRecord.deleted_at.is_(None),
            )
        )
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial record not found",
        )

    return FinancialRecordResponse.model_validate(record)


@router.patch(
    "/records/{record_id}",
    response_model=FinancialRecordResponse,
    summary="Update financial record",
)
async def update_record(
    record_id: UUID,
    data: FinancialRecordUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> FinancialRecordResponse:
    """Update a financial record."""
    result = await db.execute(
        select(FinancialRecord).where(
            and_(
                FinancialRecord.id == record_id,
                FinancialRecord.user_id == current_user.id,
                FinancialRecord.deleted_at.is_(None),
            )
        )
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial record not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    await db.commit()
    await db.refresh(record)

    return FinancialRecordResponse.model_validate(record)


@router.delete(
    "/records/{record_id}",
    response_model=MessageResponse,
    summary="Delete financial record",
)
async def delete_record(
    record_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """Soft delete a financial record."""
    result = await db.execute(
        select(FinancialRecord).where(
            and_(
                FinancialRecord.id == record_id,
                FinancialRecord.user_id == current_user.id,
                FinancialRecord.deleted_at.is_(None),
            )
        )
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial record not found",
        )

    record.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    return MessageResponse(message="Financial record deleted successfully")


# ==========================================================================
# Financial Goals
# ==========================================================================


@router.get(
    "/goals",
    response_model=list[FinancialGoalResponse],
    summary="List financial goals",
)
async def list_goals(
    current_user: CurrentUser,
    db: DbSession,
    status_filter: Optional[GoalStatus] = None,
) -> list[FinancialGoalResponse]:
    """List all financial goals for the current user."""
    query = select(FinancialGoal).where(FinancialGoal.user_id == current_user.id)

    if status_filter:
        query = query.where(FinancialGoal.status == status_filter)

    query = query.order_by(FinancialGoal.is_north_star.desc(), FinancialGoal.created_at.desc())

    result = await db.execute(query)
    goals = result.scalars().all()

    return [FinancialGoalResponse.model_validate(g) for g in goals]


@router.post(
    "/goals",
    response_model=FinancialGoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create financial goal",
)
async def create_goal(
    data: FinancialGoalCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> FinancialGoalResponse:
    """
    Create a new financial goal.

    If is_north_star is True, any existing North Star goal will be demoted.
    """
    # If setting as North Star, demote existing North Star
    if data.is_north_star:
        result = await db.execute(
            select(FinancialGoal).where(
                and_(
                    FinancialGoal.user_id == current_user.id,
                    FinancialGoal.is_north_star == True,
                )
            )
        )
        existing_north_star = result.scalar_one_or_none()
        if existing_north_star:
            existing_north_star.is_north_star = False

    goal = FinancialGoal(
        user_id=current_user.id,
        name=data.name,
        target_amount=data.target_amount,
        current_amount=data.current_amount,
        currency=data.currency,
        deadline=data.deadline,
        is_north_star=data.is_north_star,
        notes=data.notes,
    )

    db.add(goal)
    await db.commit()
    await db.refresh(goal)

    return FinancialGoalResponse.model_validate(goal)


@router.get(
    "/goals/{goal_id}",
    response_model=FinancialGoalResponse,
    summary="Get financial goal",
)
async def get_goal(
    goal_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> FinancialGoalResponse:
    """Get a specific financial goal."""
    result = await db.execute(
        select(FinancialGoal).where(
            and_(
                FinancialGoal.id == goal_id,
                FinancialGoal.user_id == current_user.id,
            )
        )
    )
    goal = result.scalar_one_or_none()

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial goal not found",
        )

    return FinancialGoalResponse.model_validate(goal)


@router.patch(
    "/goals/{goal_id}",
    response_model=FinancialGoalResponse,
    summary="Update financial goal",
)
async def update_goal(
    goal_id: UUID,
    data: FinancialGoalUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> FinancialGoalResponse:
    """
    Update a financial goal.

    If setting as North Star, any existing North Star goal will be demoted.
    """
    result = await db.execute(
        select(FinancialGoal).where(
            and_(
                FinancialGoal.id == goal_id,
                FinancialGoal.user_id == current_user.id,
            )
        )
    )
    goal = result.scalar_one_or_none()

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial goal not found",
        )

    # If setting as North Star, demote existing North Star
    if data.is_north_star is True and not goal.is_north_star:
        demote_result = await db.execute(
            select(FinancialGoal).where(
                and_(
                    FinancialGoal.user_id == current_user.id,
                    FinancialGoal.is_north_star == True,
                    FinancialGoal.id != goal_id,
                )
            )
        )
        existing_north_star = demote_result.scalar_one_or_none()
        if existing_north_star:
            existing_north_star.is_north_star = False

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(goal, field, value)

    await db.commit()
    await db.refresh(goal)

    return FinancialGoalResponse.model_validate(goal)


@router.delete(
    "/goals/{goal_id}",
    response_model=MessageResponse,
    summary="Delete financial goal",
)
async def delete_goal(
    goal_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """Delete a financial goal."""
    result = await db.execute(
        select(FinancialGoal).where(
            and_(
                FinancialGoal.id == goal_id,
                FinancialGoal.user_id == current_user.id,
            )
        )
    )
    goal = result.scalar_one_or_none()

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial goal not found",
        )

    await db.delete(goal)
    await db.commit()

    return MessageResponse(message="Financial goal deleted successfully")


@router.post(
    "/goals/{goal_id}/set-north-star",
    response_model=FinancialGoalResponse,
    summary="Set goal as North Star",
)
async def set_north_star(
    goal_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> FinancialGoalResponse:
    """
    Set a goal as the North Star goal.

    Demotes any existing North Star goal.
    """
    result = await db.execute(
        select(FinancialGoal).where(
            and_(
                FinancialGoal.id == goal_id,
                FinancialGoal.user_id == current_user.id,
            )
        )
    )
    goal = result.scalar_one_or_none()

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial goal not found",
        )

    # Demote existing North Star
    demote_result = await db.execute(
        select(FinancialGoal).where(
            and_(
                FinancialGoal.user_id == current_user.id,
                FinancialGoal.is_north_star == True,
                FinancialGoal.id != goal_id,
            )
        )
    )
    existing_north_star = demote_result.scalar_one_or_none()
    if existing_north_star:
        existing_north_star.is_north_star = False

    goal.is_north_star = True
    await db.commit()
    await db.refresh(goal)

    return FinancialGoalResponse.model_validate(goal)


# ==========================================================================
# Dashboard & Stats
# ==========================================================================


@router.get(
    "/quick-stats",
    response_model=QuickStats,
    summary="Get quick financial stats",
)
async def get_quick_stats(
    current_user: CurrentUser,
    db: DbSession,
) -> QuickStats:
    """Get quick financial statistics for dashboard cards."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    # Previous month for comparison
    if month_start.month == 1:
        prev_month_start = month_start.replace(year=month_start.year - 1, month=12)
    else:
        prev_month_start = month_start.replace(month=month_start.month - 1)
    prev_month_end = month_start

    # MTD Income
    mtd_income_result = await db.execute(
        select(func.coalesce(func.sum(FinancialRecord.amount), 0)).where(
            and_(
                FinancialRecord.user_id == current_user.id,
                FinancialRecord.record_type == FinancialRecordType.INCOME,
                FinancialRecord.record_date >= month_start,
                FinancialRecord.deleted_at.is_(None),
            )
        )
    )
    mtd_income = Decimal(str(mtd_income_result.scalar() or 0))

    # MTD Expenses
    mtd_expenses_result = await db.execute(
        select(func.coalesce(func.sum(FinancialRecord.amount), 0)).where(
            and_(
                FinancialRecord.user_id == current_user.id,
                FinancialRecord.record_type == FinancialRecordType.EXPENSE,
                FinancialRecord.record_date >= month_start,
                FinancialRecord.deleted_at.is_(None),
            )
        )
    )
    mtd_expenses = Decimal(str(mtd_expenses_result.scalar() or 0))

    # YTD Income
    ytd_income_result = await db.execute(
        select(func.coalesce(func.sum(FinancialRecord.amount), 0)).where(
            and_(
                FinancialRecord.user_id == current_user.id,
                FinancialRecord.record_type == FinancialRecordType.INCOME,
                FinancialRecord.record_date >= year_start,
                FinancialRecord.deleted_at.is_(None),
            )
        )
    )
    ytd_income = Decimal(str(ytd_income_result.scalar() or 0))

    # YTD Expenses
    ytd_expenses_result = await db.execute(
        select(func.coalesce(func.sum(FinancialRecord.amount), 0)).where(
            and_(
                FinancialRecord.user_id == current_user.id,
                FinancialRecord.record_type == FinancialRecordType.EXPENSE,
                FinancialRecord.record_date >= year_start,
                FinancialRecord.deleted_at.is_(None),
            )
        )
    )
    ytd_expenses = Decimal(str(ytd_expenses_result.scalar() or 0))

    # Previous month income for comparison
    prev_month_income_result = await db.execute(
        select(func.coalesce(func.sum(FinancialRecord.amount), 0)).where(
            and_(
                FinancialRecord.user_id == current_user.id,
                FinancialRecord.record_type == FinancialRecordType.INCOME,
                FinancialRecord.record_date >= prev_month_start,
                FinancialRecord.record_date < prev_month_end,
                FinancialRecord.deleted_at.is_(None),
            )
        )
    )
    prev_month_income = Decimal(str(prev_month_income_result.scalar() or 0))

    # Previous month expenses for comparison
    prev_month_expenses_result = await db.execute(
        select(func.coalesce(func.sum(FinancialRecord.amount), 0)).where(
            and_(
                FinancialRecord.user_id == current_user.id,
                FinancialRecord.record_type == FinancialRecordType.EXPENSE,
                FinancialRecord.record_date >= prev_month_start,
                FinancialRecord.record_date < prev_month_end,
                FinancialRecord.deleted_at.is_(None),
            )
        )
    )
    prev_month_expenses = Decimal(str(prev_month_expenses_result.scalar() or 0))

    # Calculate percentage changes
    income_change = None
    if prev_month_income > 0:
        income_change = ((mtd_income - prev_month_income) / prev_month_income * 100).quantize(
            Decimal("0.01")
        )

    expense_change = None
    if prev_month_expenses > 0:
        expense_change = ((mtd_expenses - prev_month_expenses) / prev_month_expenses * 100).quantize(
            Decimal("0.01")
        )

    return QuickStats(
        mtd_income=mtd_income,
        mtd_expenses=mtd_expenses,
        mtd_net=mtd_income - mtd_expenses,
        ytd_income=ytd_income,
        ytd_expenses=ytd_expenses,
        ytd_net=ytd_income - ytd_expenses,
        income_change_percent=income_change,
        expense_change_percent=expense_change,
    )


@router.get(
    "/dashboard",
    response_model=FinancialDashboard,
    summary="Get financial dashboard",
)
async def get_dashboard(
    current_user: CurrentUser,
    db: DbSession,
) -> FinancialDashboard:
    """Get comprehensive financial dashboard data."""
    # Get quick stats
    quick_stats = await get_quick_stats(current_user, db)

    # Get North Star goal
    north_star_result = await db.execute(
        select(FinancialGoal).where(
            and_(
                FinancialGoal.user_id == current_user.id,
                FinancialGoal.is_north_star == True,
            )
        )
    )
    north_star_goal = north_star_result.scalar_one_or_none()
    north_star = calculate_goal_progress(north_star_goal) if north_star_goal else None

    # Get all active goals
    goals_result = await db.execute(
        select(FinancialGoal).where(
            and_(
                FinancialGoal.user_id == current_user.id,
                FinancialGoal.status == GoalStatus.ACTIVE,
            )
        ).order_by(FinancialGoal.is_north_star.desc(), FinancialGoal.created_at.desc())
    )
    goals = [calculate_goal_progress(g) for g in goals_result.scalars().all()]

    # Recent income (last 10)
    recent_income_result = await db.execute(
        select(FinancialRecord).where(
            and_(
                FinancialRecord.user_id == current_user.id,
                FinancialRecord.record_type == FinancialRecordType.INCOME,
                FinancialRecord.deleted_at.is_(None),
            )
        ).order_by(FinancialRecord.record_date.desc()).limit(10)
    )
    recent_income = [
        FinancialRecordResponse.model_validate(r)
        for r in recent_income_result.scalars().all()
    ]

    # Recent expenses (last 10)
    recent_expenses_result = await db.execute(
        select(FinancialRecord).where(
            and_(
                FinancialRecord.user_id == current_user.id,
                FinancialRecord.record_type == FinancialRecordType.EXPENSE,
                FinancialRecord.deleted_at.is_(None),
            )
        ).order_by(FinancialRecord.record_date.desc()).limit(10)
    )
    recent_expenses = [
        FinancialRecordResponse.model_validate(r)
        for r in recent_expenses_result.scalars().all()
    ]

    # Income by source (current month)
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    income_by_source_result = await db.execute(
        select(
            FinancialRecord.source,
            func.sum(FinancialRecord.amount).label("total"),
        ).where(
            and_(
                FinancialRecord.user_id == current_user.id,
                FinancialRecord.record_type == FinancialRecordType.INCOME,
                FinancialRecord.record_date >= month_start,
                FinancialRecord.deleted_at.is_(None),
            )
        ).group_by(FinancialRecord.source)
    )
    income_by_source = {row.source: Decimal(str(row.total)) for row in income_by_source_result}

    # Expenses by category (current month)
    expenses_by_category_result = await db.execute(
        select(
            FinancialRecord.category,
            func.sum(FinancialRecord.amount).label("total"),
        ).where(
            and_(
                FinancialRecord.user_id == current_user.id,
                FinancialRecord.record_type == FinancialRecordType.EXPENSE,
                FinancialRecord.record_date >= month_start,
                FinancialRecord.deleted_at.is_(None),
            )
        ).group_by(FinancialRecord.category)
    )
    expenses_by_category = {
        row.category: Decimal(str(row.total)) for row in expenses_by_category_result
    }

    return FinancialDashboard(
        quick_stats=quick_stats,
        north_star=north_star,
        goals=goals,
        recent_income=recent_income,
        recent_expenses=recent_expenses,
        income_by_source=income_by_source,
        expenses_by_category=expenses_by_category,
    )
