"""
Guardrails API Routes.

REST endpoints for guardrails configuration and monitoring.
"""

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.models import GuardrailViolation, GuardrailLayer
from src.core.pipeline import GuardrailsEngine

router = APIRouter(prefix="/api/v1/guardrails", tags=["guardrails"])


# ==========================================================================
# Schemas
# ==========================================================================

class InvariantItem(BaseModel):
    """An invariant rule."""
    name: str
    value: Any
    description: str


class PolicyItem(BaseModel):
    """A configurable policy."""
    name: str
    value: Any
    min_value: Any
    max_value: Any
    description: str


class PreferenceItem(BaseModel):
    """A preference setting."""
    name: str
    value: Any


class RolePermissions(BaseModel):
    """Permissions for a role."""
    role: str
    can_approve_po_review: bool
    can_override_guardrails: bool
    can_modify_policies: bool
    can_modify_invariants: bool


class GuardrailsConfig(BaseModel):
    """Full guardrails configuration."""
    invariants: list[InvariantItem]
    policies: list[PolicyItem]
    preferences: list[PreferenceItem]
    roles: list[RolePermissions]


class ViolationResponse(BaseModel):
    """Guardrail violation record."""
    id: UUID
    layer: str
    rule_name: str
    attempted_action: str
    blocked: bool
    override_reason: Optional[str]
    actor: Optional[str]
    pipeline_run_id: Optional[UUID]
    context: Optional[dict]
    created_at: str

    class Config:
        from_attributes = True


class UpdatePolicyRequest(BaseModel):
    """Request to update a policy."""
    value: Any = Field(..., description="New policy value")


class UpdatePreferenceRequest(BaseModel):
    """Request to update a preference."""
    value: Any = Field(..., description="New preference value")


# ==========================================================================
# Endpoints
# ==========================================================================

@router.get("/", response_model=GuardrailsConfig)
async def get_guardrails_config(
    db: AsyncSession = Depends(get_db),
):
    """
    Get full guardrails configuration.

    Returns all invariants, policies, preferences, and role permissions.
    """
    guardrails = GuardrailsEngine(db)
    config = guardrails.get_configuration()

    # Format invariants
    invariants = [
        InvariantItem(
            name=k,
            value=v["value"] if isinstance(v, dict) else v,
            description=v.get("description", "") if isinstance(v, dict) else "",
        )
        for k, v in guardrails.INVARIANTS.items()
    ]

    # Format policies
    policies = [
        PolicyItem(
            name=name,
            value=policy.value,
            min_value=policy.min_value,
            max_value=policy.max_value,
            description=policy.description,
        )
        for name, policy in guardrails.POLICIES.items()
    ]

    # Format preferences
    preferences = [
        PreferenceItem(name=k, value=v)
        for k, v in guardrails.PREFERENCES.items()
    ]

    # Format roles
    roles = [
        RolePermissions(role=role, **perms)
        for role, perms in guardrails.ROLE_PERMISSIONS.items()
    ]

    return GuardrailsConfig(
        invariants=invariants,
        policies=policies,
        preferences=preferences,
        roles=roles,
    )


@router.get("/invariants")
async def get_invariants(
    db: AsyncSession = Depends(get_db),
):
    """
    Get all invariant rules.

    Invariants are immutable rules that cannot be changed.
    """
    guardrails = GuardrailsEngine(db)

    return {
        name: {
            "value": v["value"] if isinstance(v, dict) else v,
            "description": v.get("description", "") if isinstance(v, dict) else "",
            "changeable": False,
        }
        for name, v in guardrails.INVARIANTS.items()
    }


@router.get("/policies")
async def get_policies(
    db: AsyncSession = Depends(get_db),
):
    """
    Get all configurable policies.

    Policies can be modified within their defined bounds.
    """
    guardrails = GuardrailsEngine(db)

    return {
        name: {
            "value": policy.value,
            "min": policy.min_value,
            "max": policy.max_value,
            "description": policy.description,
        }
        for name, policy in guardrails.POLICIES.items()
    }


@router.get("/policies/{policy_name}")
async def get_policy(
    policy_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific policy."""
    guardrails = GuardrailsEngine(db)
    policy = guardrails.get_policy(policy_name)

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_name}' not found",
        )

    return {
        "name": policy_name,
        "value": policy.value,
        "min": policy.min_value,
        "max": policy.max_value,
        "description": policy.description,
    }


@router.put("/policies/{policy_name}")
async def update_policy(
    policy_name: str,
    request: UpdatePolicyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a policy value.

    The new value must be within the policy's defined bounds.
    """
    guardrails = GuardrailsEngine(db)
    policy = guardrails.get_policy(policy_name)

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_name}' not found",
        )

    # Check bounds
    if not (policy.min_value <= request.value <= policy.max_value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Value {request.value} outside bounds [{policy.min_value}, {policy.max_value}]",
        )

    success = guardrails.update_policy(policy_name, request.value)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update policy",
        )

    return {
        "name": policy_name,
        "value": request.value,
        "message": f"Policy '{policy_name}' updated to {request.value}",
    }


@router.get("/preferences")
async def get_preferences(
    db: AsyncSession = Depends(get_db),
):
    """
    Get all preferences.

    Preferences can be freely changed without restrictions.
    """
    guardrails = GuardrailsEngine(db)
    return guardrails.PREFERENCES


@router.put("/preferences/{pref_name}")
async def update_preference(
    pref_name: str,
    request: UpdatePreferenceRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a preference value (no restrictions)."""
    guardrails = GuardrailsEngine(db)

    guardrails.update_preference(pref_name, request.value)

    return {
        "name": pref_name,
        "value": request.value,
        "message": f"Preference '{pref_name}' updated",
    }


@router.get("/roles")
async def get_roles(
    db: AsyncSession = Depends(get_db),
):
    """Get all role permissions."""
    guardrails = GuardrailsEngine(db)
    return guardrails.ROLE_PERMISSIONS


@router.get("/roles/{role_name}")
async def get_role(
    role_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Get permissions for a specific role."""
    guardrails = GuardrailsEngine(db)
    perms = guardrails.ROLE_PERMISSIONS.get(role_name)

    if not perms:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role_name}' not found",
        )

    return {"role": role_name, **perms}


@router.get("/roles/{role_name}/can/{permission}")
async def check_role_permission(
    role_name: str,
    permission: str,
    db: AsyncSession = Depends(get_db),
):
    """Check if a role has a specific permission."""
    guardrails = GuardrailsEngine(db)
    has_permission = guardrails.check_role_permission(role_name, permission)

    return {
        "role": role_name,
        "permission": permission,
        "allowed": has_permission,
    }


@router.get("/violations", response_model=list[ViolationResponse])
async def get_violations(
    layer: Optional[str] = None,
    blocked_only: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent guardrail violations.

    Args:
        layer: Filter by layer (invariant, contract, policy, preference)
        blocked_only: Only show blocked violations
        limit: Maximum results
    """
    query = select(GuardrailViolation).order_by(GuardrailViolation.created_at.desc()).limit(limit)

    if layer:
        try:
            layer_enum = GuardrailLayer(layer)
            query = query.where(GuardrailViolation.layer == layer_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid layer: {layer}. Valid: invariant, contract, policy, preference",
            )

    if blocked_only:
        query = query.where(GuardrailViolation.blocked == True)

    result = await db.execute(query)
    violations = result.scalars().all()

    return [_violation_to_response(v) for v in violations]


@router.get("/violations/{violation_id}", response_model=ViolationResponse)
async def get_violation(
    violation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific violation by ID."""
    result = await db.execute(
        select(GuardrailViolation).where(GuardrailViolation.id == violation_id)
    )
    violation = result.scalar_one_or_none()

    if not violation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Violation {violation_id} not found",
        )

    return _violation_to_response(violation)


@router.get("/stage-transitions")
async def get_stage_transitions(
    db: AsyncSession = Depends(get_db),
):
    """
    Get valid stage transitions.

    Returns the stage order defined by invariants.
    """
    guardrails = GuardrailsEngine(db)
    stage_order = guardrails.INVARIANTS["stage_order"]["value"]

    transitions = []
    for i, stage in enumerate(stage_order[:-1]):
        transitions.append({
            "from": stage,
            "to": stage_order[i + 1],
            "description": f"{stage} → {stage_order[i + 1]}",
        })

    return {
        "stage_order": stage_order,
        "valid_transitions": transitions,
    }


# ==========================================================================
# Helper Functions
# ==========================================================================

def _violation_to_response(v: GuardrailViolation) -> ViolationResponse:
    """Convert violation to response model."""
    return ViolationResponse(
        id=v.id,
        layer=v.layer.value,
        rule_name=v.rule_name,
        attempted_action=v.attempted_action,
        blocked=v.blocked,
        override_reason=v.override_reason,
        actor=v.actor,
        pipeline_run_id=v.pipeline_run_id,
        context=v.context,
        created_at=v.created_at.isoformat() if v.created_at else None,
    )
