"""
NH Mission Control - Pipeline API
==================================

Pipeline and opportunity management endpoints.

EPOCH 3 - ACTIVE

==========================================================================
IMPLEMENTATION CONTRACT
==========================================================================

CC must implement all functions marked with `# TODO: Implement`.
The function signatures, docstrings, and return types define the contract.
Tests in tests/epoch3/ define expected behavior.
==========================================================================
"""

from datetime import datetime, timezone
from decimal import Decimal
from math import ceil
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from src.api.deps import CurrentUser, DbSession
from src.core.models import (
    Opportunity,
    OpportunitySource,
    OpportunityStatus,
    OpportunityStatusHistory,
)
from src.core.schemas import (
    EffortEstimate,
    MessageResponse,
    OpportunityAnalysis,
    OpportunityCreate,
    OpportunityListResponse,
    OpportunityMoveRequest,
    OpportunityResponse,
    OpportunityUpdate,
    PipelineStageStats,
    PipelineStats,
    ProposalDraft,
)

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


# ==========================================================================
# Helper Functions
# ==========================================================================

async def get_opportunity_or_404(
    opportunity_id: UUID,
    current_user_id: UUID,
    db,
) -> Opportunity:
    """Get opportunity by ID or raise 404."""
    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.user_id == current_user_id,
            Opportunity.deleted_at.is_(None),
        )
    )
    opportunity = result.scalar_one_or_none()

    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )

    return opportunity


# ==========================================================================
# Opportunity CRUD
# ==========================================================================

@router.get(
    "/opportunities",
    response_model=OpportunityListResponse,
    summary="List opportunities",
    responses={
        200: {"description": "List of opportunities"},
        401: {"description": "Not authenticated"},
    },
)
async def list_opportunities(
    current_user: CurrentUser,
    db: DbSession,
    status_filter: Optional[OpportunityStatus] = Query(
        None, alias="status", description="Filter by status"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> OpportunityListResponse:
    """
    List user's opportunities with optional filtering.
    """
    # Base query
    query = select(Opportunity).where(
        Opportunity.user_id == current_user.id,
        Opportunity.deleted_at.is_(None),
    )

    # Filter by status if provided
    if status_filter:
        query = query.where(Opportunity.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Order and paginate
    query = query.order_by(Opportunity.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    opportunities = result.scalars().all()

    # Calculate pages
    pages = ceil(total / page_size) if total > 0 else 1

    return OpportunityListResponse(
        items=[OpportunityResponse.model_validate(opp) for opp in opportunities],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/opportunities/{opportunity_id}",
    response_model=OpportunityResponse,
    summary="Get opportunity",
    responses={
        200: {"description": "Opportunity details"},
        401: {"description": "Not authenticated"},
        404: {"description": "Opportunity not found"},
    },
)
async def get_opportunity(
    opportunity_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> OpportunityResponse:
    """
    Get a single opportunity by ID.
    """
    opportunity = await get_opportunity_or_404(opportunity_id, current_user.id, db)
    return OpportunityResponse.model_validate(opportunity)


@router.post(
    "/opportunities",
    response_model=OpportunityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create opportunity",
    responses={
        201: {"description": "Opportunity created"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def create_opportunity(
    data: OpportunityCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> OpportunityResponse:
    """
    Create a new opportunity.
    """
    # Create opportunity
    opportunity = Opportunity(
        id=uuid4(),
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        external_url=data.external_url,
        source=data.source,
        status=OpportunityStatus.LEAD,  # Initial status
        value=data.value,
        currency=data.currency,
        probability=data.probability,
        client_name=data.client_name,
        client_rating=data.client_rating,
        client_total_spent=data.client_total_spent,
        client_location=data.client_location,
        tech_stack=data.tech_stack,
        deadline=data.deadline,
        expected_close_date=data.expected_close_date,
        notes=data.notes,
    )

    db.add(opportunity)

    # Create initial status history
    history = OpportunityStatusHistory(
        id=uuid4(),
        opportunity_id=opportunity.id,
        from_status=None,
        to_status=OpportunityStatus.LEAD,
        notes="Opportunity created",
    )
    db.add(history)

    await db.commit()
    await db.refresh(opportunity)

    return OpportunityResponse.model_validate(opportunity)


@router.patch(
    "/opportunities/{opportunity_id}",
    response_model=OpportunityResponse,
    summary="Update opportunity",
    responses={
        200: {"description": "Opportunity updated"},
        401: {"description": "Not authenticated"},
        404: {"description": "Opportunity not found"},
    },
)
async def update_opportunity(
    opportunity_id: UUID,
    data: OpportunityUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> OpportunityResponse:
    """
    Update an opportunity (partial update).
    """
    opportunity = await get_opportunity_or_404(opportunity_id, current_user.id, db)

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(opportunity, field, value)

    await db.commit()
    await db.refresh(opportunity)

    return OpportunityResponse.model_validate(opportunity)


@router.delete(
    "/opportunities/{opportunity_id}",
    response_model=MessageResponse,
    summary="Delete opportunity",
    responses={
        200: {"description": "Opportunity deleted"},
        401: {"description": "Not authenticated"},
        404: {"description": "Opportunity not found"},
    },
)
async def delete_opportunity(
    opportunity_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """
    Soft delete an opportunity.
    """
    opportunity = await get_opportunity_or_404(opportunity_id, current_user.id, db)

    # Soft delete
    opportunity.deleted_at = datetime.now(timezone.utc)

    await db.commit()

    return MessageResponse(message="Opportunity deleted", success=True)


# ==========================================================================
# Pipeline Status Management
# ==========================================================================

@router.post(
    "/opportunities/{opportunity_id}/move",
    response_model=OpportunityResponse,
    summary="Move opportunity to new status",
    responses={
        200: {"description": "Opportunity moved"},
        401: {"description": "Not authenticated"},
        404: {"description": "Opportunity not found"},
        422: {"description": "Invalid status transition"},
    },
)
async def move_opportunity(
    opportunity_id: UUID,
    data: OpportunityMoveRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> OpportunityResponse:
    """
    Move opportunity to a new pipeline status.
    """
    opportunity = await get_opportunity_or_404(opportunity_id, current_user.id, db)

    old_status = opportunity.status
    new_status = data.status

    # Update status
    opportunity.status = new_status

    # Special rules for WON and LOST
    if new_status == OpportunityStatus.WON:
        opportunity.probability = 100
    elif new_status == OpportunityStatus.LOST:
        opportunity.probability = 0

    # Create status history
    history = OpportunityStatusHistory(
        id=uuid4(),
        opportunity_id=opportunity.id,
        from_status=old_status,
        to_status=new_status,
        notes=data.notes,
    )
    db.add(history)

    await db.commit()
    await db.refresh(opportunity)

    return OpportunityResponse.model_validate(opportunity)


# ==========================================================================
# Pipeline Statistics
# ==========================================================================

@router.get(
    "/stats",
    response_model=PipelineStats,
    summary="Get pipeline statistics",
    responses={
        200: {"description": "Pipeline statistics"},
        401: {"description": "Not authenticated"},
    },
)
async def get_pipeline_stats(
    current_user: CurrentUser,
    db: DbSession,
) -> PipelineStats:
    """
    Get pipeline statistics for dashboard.
    """
    # Get all non-deleted opportunities
    result = await db.execute(
        select(Opportunity).where(
            Opportunity.user_id == current_user.id,
            Opportunity.deleted_at.is_(None),
        )
    )
    opportunities = result.scalars().all()

    # Calculate stats by status
    stages: list[PipelineStageStats] = []
    status_counts: dict = {}
    status_values: dict = {}
    status_weighted: dict = {}

    for opp in opportunities:
        status_name = opp.status.value if hasattr(opp.status, 'value') else str(opp.status)
        if status_name not in status_counts:
            status_counts[status_name] = 0
            status_values[status_name] = Decimal("0")
            status_weighted[status_name] = Decimal("0")

        status_counts[status_name] += 1
        value = opp.value or Decimal("0")
        status_values[status_name] += value
        status_weighted[status_name] += value * Decimal(str(opp.probability or 0)) / Decimal("100")

    for status_enum in OpportunityStatus:
        status_name = status_enum.value
        if status_name in status_counts:
            stages.append(PipelineStageStats(
                status=status_enum,
                count=status_counts[status_name],
                total_value=status_values[status_name],
                weighted_value=status_weighted[status_name],
            ))

    # Calculate totals
    total_opportunities = len(opportunities)
    total_value = sum(opp.value or Decimal("0") for opp in opportunities)
    weighted_pipeline_value = sum(
        (opp.value or Decimal("0")) * Decimal(str(opp.probability or 0)) / Decimal("100")
        for opp in opportunities
    )

    # Conversion rate
    won_count = sum(1 for opp in opportunities if opp.status == OpportunityStatus.WON)
    lost_count = sum(1 for opp in opportunities if opp.status == OpportunityStatus.LOST)
    conversion_rate = Decimal("0")
    if won_count + lost_count > 0:
        conversion_rate = Decimal(str(won_count)) / Decimal(str(won_count + lost_count))

    # Average deal size
    avg_deal_size = Decimal("0")
    if total_opportunities > 0:
        avg_deal_size = total_value / Decimal(str(total_opportunities))

    # Opportunities by source
    opportunities_by_source: dict[str, int] = {}
    for opp in opportunities:
        source_name = opp.source.value if hasattr(opp.source, 'value') else str(opp.source)
        opportunities_by_source[source_name] = opportunities_by_source.get(source_name, 0) + 1

    return PipelineStats(
        stages=stages,
        total_opportunities=total_opportunities,
        total_value=total_value,
        weighted_pipeline_value=weighted_pipeline_value,
        conversion_rate=conversion_rate,
        avg_deal_size=avg_deal_size,
        opportunities_by_source=opportunities_by_source,
    )


# ==========================================================================
# NH Analysis
# ==========================================================================

@router.post(
    "/opportunities/{opportunity_id}/analyze",
    response_model=OpportunityAnalysis,
    summary="Run NH analysis",
    responses={
        200: {"description": "Analysis results"},
        401: {"description": "Not authenticated"},
        404: {"description": "Opportunity not found"},
    },
)
async def analyze_opportunity(
    opportunity_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> OpportunityAnalysis:
    """
    Run NH analysis on an opportunity.
    """
    from src.core.models import TaskMode

    opportunity = await get_opportunity_or_404(opportunity_id, current_user.id, db)

    # Simple heuristic scoring (MVP)
    value = float(opportunity.value or 0)

    # Budget fit: €3K-15K is sweet spot
    if 3000 <= value <= 15000:
        budget_fit_score = 100
    elif 1000 <= value < 3000 or 15000 < value <= 30000:
        budget_fit_score = 70
    else:
        budget_fit_score = 40

    # Client quality
    client_quality_score = 50
    if opportunity.client_rating:
        client_quality_score = int(float(opportunity.client_rating) * 20)  # 0-5 -> 0-100
    if opportunity.client_total_spent and float(opportunity.client_total_spent) > 10000:
        client_quality_score = min(100, client_quality_score + 20)

    # Technical fit based on tech stack
    sw_techs = {"python", "fastapi", "django", "flask", "postgresql", "react", "typescript"}
    tech_stack = opportunity.tech_stack or []
    matching_techs = sum(1 for t in tech_stack if t.lower() in sw_techs)
    technical_fit_score = min(100, 50 + matching_techs * 15)

    # Timeline fit
    timeline_fit_score = 70  # Default reasonable
    if opportunity.deadline:
        days_until = (opportunity.deadline - datetime.now(timezone.utc)).days
        if days_until < 7:
            timeline_fit_score = 30  # Too tight
        elif days_until < 30:
            timeline_fit_score = 80
        else:
            timeline_fit_score = 100

    # Competition score (simulated for MVP)
    competition_score = 60

    # Overall score
    score = int(
        budget_fit_score * 0.25 +
        client_quality_score * 0.25 +
        technical_fit_score * 0.30 +
        timeline_fit_score * 0.10 +
        competition_score * 0.10
    )

    # Generate insights
    strengths = []
    risks = []
    recommendations = []

    if budget_fit_score >= 80:
        strengths.append("Budget in our sweet spot")
    elif budget_fit_score < 50:
        risks.append("Budget outside comfortable range")

    if client_quality_score >= 80:
        strengths.append("High-quality client")
    elif client_quality_score < 50:
        risks.append("Limited client history")

    if technical_fit_score >= 80:
        strengths.append("Strong tech stack match")
        recommendations.append("Use Synaptic Weaver for accelerated delivery")
    elif technical_fit_score < 50:
        risks.append("Tech stack may require additional learning")

    if timeline_fit_score < 50:
        risks.append("Tight deadline")
        recommendations.append("Negotiate extended timeline if possible")

    if not recommendations:
        recommendations.append("Proceed with standard proposal workflow")

    # Determine complexity tier and mode
    if value < 2000:
        sw_difficulty_tier = 1
        recommended_mode = TaskMode.YOLO
        estimated_hours = Decimal("10")
    elif value < 5000:
        sw_difficulty_tier = 2
        recommended_mode = TaskMode.CHECKPOINTED
        estimated_hours = Decimal("25")
    elif value < 10000:
        sw_difficulty_tier = 3
        recommended_mode = TaskMode.CHECKPOINTED
        estimated_hours = Decimal("50")
    elif value < 20000:
        sw_difficulty_tier = 4
        recommended_mode = TaskMode.SUPERVISED
        estimated_hours = Decimal("80")
    else:
        sw_difficulty_tier = 5
        recommended_mode = TaskMode.SUPERVISED
        estimated_hours = Decimal("120")

    # SW hours (typically 30-50% of total)
    estimated_sw_hours = estimated_hours * Decimal("0.4")

    # Suggested price
    suggested_price = Decimal(str(value)) if value > 0 else estimated_hours * Decimal("75")

    # Save analysis to opportunity
    opportunity.nh_score = score
    opportunity.nh_analysis = {
        "budget_fit_score": budget_fit_score,
        "client_quality_score": client_quality_score,
        "technical_fit_score": technical_fit_score,
        "timeline_fit_score": timeline_fit_score,
        "competition_score": competition_score,
        "strengths": strengths,
        "risks": risks,
        "recommendations": recommendations,
    }

    await db.commit()

    return OpportunityAnalysis(
        opportunity_id=opportunity.id,
        score=score,
        budget_fit_score=budget_fit_score,
        client_quality_score=client_quality_score,
        technical_fit_score=technical_fit_score,
        timeline_fit_score=timeline_fit_score,
        competition_score=competition_score,
        strengths=strengths,
        risks=risks,
        recommendations=recommendations,
        sw_difficulty_tier=sw_difficulty_tier,
        recommended_mode=recommended_mode,
        estimated_hours=estimated_hours,
        estimated_sw_hours=estimated_sw_hours,
        suggested_price=suggested_price,
        analyzed_at=datetime.now(timezone.utc),
    )


@router.post(
    "/opportunities/{opportunity_id}/proposal",
    response_model=ProposalDraft,
    summary="Generate proposal draft",
    responses={
        200: {"description": "Proposal draft"},
        401: {"description": "Not authenticated"},
        404: {"description": "Opportunity not found"},
    },
)
async def generate_proposal(
    opportunity_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ProposalDraft:
    """
    Generate a proposal draft for an opportunity.
    """
    opportunity = await get_opportunity_or_404(opportunity_id, current_user.id, db)

    client_name = opportunity.client_name or "there"
    title = opportunity.title
    tech_stack = opportunity.tech_stack or []
    value = opportunity.value or Decimal("0")

    # Template-based proposal generation (MVP)
    subject = f"Proposal: {title}"

    greeting = f"Hi {client_name},"

    intro = (
        f"Thank you for considering me for your {title} project. "
        f"I've reviewed your requirements and I'm confident I can deliver "
        f"a high-quality solution that meets your needs."
    )

    tech_mention = f" with {', '.join(tech_stack)}" if tech_stack else ""
    approach = (
        f"I'll build this{tech_mention} using modern best practices, "
        f"including comprehensive testing, clean architecture, and detailed documentation. "
        f"My approach ensures maintainable, scalable code that you can build upon."
    )

    timeline = (
        "I propose the following timeline:\n"
        "- Week 1: Requirements finalization and architecture design\n"
        "- Week 2-3: Core development with regular progress updates\n"
        "- Week 4: Testing, refinement, and delivery\n"
        "We can adjust this based on your specific needs."
    )

    pricing = (
        f"Investment: €{value:,.2f}\n"
        "This includes:\n"
        "- Full implementation as specified\n"
        "- Comprehensive testing\n"
        "- Documentation\n"
        "- 30-day support post-delivery\n\n"
        "Payment terms: 30% upfront, 70% on completion."
    )

    closing = (
        "I'd love to discuss this further and answer any questions you might have. "
        "Shall we schedule a quick call this week?\n\n"
        "Looking forward to working together!"
    )

    # Calculate metadata
    full_text = f"{greeting}\n\n{intro}\n\n{approach}\n\n{timeline}\n\n{pricing}\n\n{closing}"
    word_count = len(full_text.split())
    reading_time = max(30, word_count // 3)  # ~3 words per second

    clarifying_questions = [
        "Do you have existing systems this needs to integrate with?",
        "What's your preferred communication channel for updates?",
        "Are there any specific deadline constraints I should know about?",
    ]

    return ProposalDraft(
        opportunity_id=opportunity.id,
        subject=subject,
        greeting=greeting,
        intro=intro,
        approach=approach,
        timeline=timeline,
        pricing=pricing,
        closing=closing,
        word_count=word_count,
        estimated_reading_time_seconds=reading_time,
        clarifying_questions=clarifying_questions,
        generated_at=datetime.now(timezone.utc),
    )


@router.post(
    "/opportunities/{opportunity_id}/estimate",
    response_model=EffortEstimate,
    summary="Estimate effort",
    responses={
        200: {"description": "Effort estimate"},
        401: {"description": "Not authenticated"},
        404: {"description": "Opportunity not found"},
    },
)
async def estimate_effort(
    opportunity_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> EffortEstimate:
    """
    Estimate effort and pricing for an opportunity.
    """
    opportunity = await get_opportunity_or_404(opportunity_id, current_user.id, db)

    value = float(opportunity.value or 0)
    tech_stack = opportunity.tech_stack or []

    # Determine complexity tier
    if value < 2000 or len(tech_stack) <= 1:
        complexity_tier = 1
        base_hours = 10
        hourly_rate = 60
    elif value < 5000 or len(tech_stack) <= 2:
        complexity_tier = 2
        base_hours = 25
        hourly_rate = 70
    elif value < 10000 or len(tech_stack) <= 4:
        complexity_tier = 3
        base_hours = 50
        hourly_rate = 80
    elif value < 20000:
        complexity_tier = 4
        base_hours = 80
        hourly_rate = 90
    else:
        complexity_tier = 5
        base_hours = 120
        hourly_rate = 100

    # Time estimates with variance
    total_hours_min = Decimal(str(base_hours * 0.7))
    total_hours_max = Decimal(str(base_hours * 1.4))
    total_hours_expected = Decimal(str(base_hours))

    # Breakdown
    sw_generation_hours = total_hours_expected * Decimal("0.35")
    review_hours = total_hours_expected * Decimal("0.25")
    communication_hours = total_hours_expected * Decimal("0.15")
    buffer_hours = total_hours_expected * Decimal("0.25")

    # Pricing
    market_rate_min = total_hours_min * Decimal(str(hourly_rate))
    market_rate_max = total_hours_max * Decimal(str(hourly_rate * 1.2))
    suggested_price = total_hours_expected * Decimal(str(hourly_rate * 0.9))
    floor_price = total_hours_expected * Decimal(str(hourly_rate * 0.5))

    # Effective rate
    effective_hourly_rate = suggested_price / total_hours_expected if total_hours_expected > 0 else Decimal("0")

    # Margin vs manual
    manual_hours = total_hours_expected * Decimal("2")  # Assume 2x without SW
    margin_vs_manual = Decimal("50")  # 50% time savings

    return EffortEstimate(
        opportunity_id=opportunity.id,
        complexity_tier=complexity_tier,
        total_hours_min=total_hours_min,
        total_hours_max=total_hours_max,
        total_hours_expected=total_hours_expected,
        sw_generation_hours=sw_generation_hours,
        review_hours=review_hours,
        communication_hours=communication_hours,
        buffer_hours=buffer_hours,
        market_rate_min=market_rate_min,
        market_rate_max=market_rate_max,
        suggested_price=suggested_price,
        floor_price=floor_price,
        effective_hourly_rate=effective_hourly_rate,
        margin_vs_manual=margin_vs_manual,
        estimated_at=datetime.now(timezone.utc),
    )


@router.get(
    "/opportunities/{opportunity_id}/similar",
    response_model=list[OpportunityResponse],
    summary="Find similar opportunities",
    responses={
        200: {"description": "Similar opportunities"},
        401: {"description": "Not authenticated"},
        404: {"description": "Opportunity not found"},
    },
)
async def get_similar_opportunities(
    opportunity_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(5, ge=1, le=20),
) -> list[OpportunityResponse]:
    """
    Find similar past opportunities for reference.
    """
    opportunity = await get_opportunity_or_404(opportunity_id, current_user.id, db)

    # Get all other opportunities for this user
    result = await db.execute(
        select(Opportunity).where(
            Opportunity.user_id == current_user.id,
            Opportunity.deleted_at.is_(None),
            Opportunity.id != opportunity.id,
        )
    )
    all_opportunities = result.scalars().all()

    # Score similarity
    similar_opps = []
    target_value = float(opportunity.value or 0)
    target_tech = set(t.lower() for t in (opportunity.tech_stack or []))
    target_source = opportunity.source

    for opp in all_opportunities:
        score = 0

        # Tech stack overlap
        opp_tech = set(t.lower() for t in (opp.tech_stack or []))
        if target_tech and opp_tech:
            overlap = len(target_tech & opp_tech)
            score += overlap * 30

        # Value range (±30%)
        opp_value = float(opp.value or 0)
        if target_value > 0 and opp_value > 0:
            ratio = min(target_value, opp_value) / max(target_value, opp_value)
            if ratio >= 0.7:
                score += int(ratio * 40)

        # Same source
        if opp.source == target_source:
            score += 20

        if score > 0:
            similar_opps.append((score, opp))

    # Sort by score and take top N
    similar_opps.sort(key=lambda x: x[0], reverse=True)
    top_similar = [opp for _, opp in similar_opps[:limit]]

    return [OpportunityResponse.model_validate(opp) for opp in top_similar]
