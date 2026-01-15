"""
Guardrails Engine - 4-layer constraint enforcement.

Ensures pipeline operates within defined boundaries.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import (
    GuardrailLayer,
    GuardrailViolation,
    PipelineStage,
    EscalationLevel,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of guardrail validation."""
    allowed: bool
    layer: GuardrailLayer
    rule: str
    message: str
    violation_id: Optional[UUID] = None


@dataclass
class PolicyBounds:
    """Bounds for a configurable policy."""
    value: Any
    min_value: Any
    max_value: Any
    description: str


class GuardrailsEngine:
    """
    4-layer constraint enforcement system.

    Layers (from strictest to most flexible):
    1. INVARIANTS - Never changeable (hardcoded rules)
    2. CONTRACTS - Schema-validated structures
    3. POLICIES - Configurable within bounds
    4. PREFERENCES - Freely changeable

    All violations are logged for audit purposes.
    """

    # Layer 1: INVARIANTS (never changeable)
    INVARIANTS = {
        "stage_order": {
            "value": [
                "queued", "developing", "testing",
                "verifying", "po_review", "deploying", "completed"
            ],
            "description": "Pipeline stages must follow this order",
        },
        "critical_requires_opus": {
            "value": True,
            "description": "Critical priority tasks must use Opus",
        },
        "po_review_required": {
            "value": True,
            "description": "PO review stage cannot be skipped",
        },
        "human_final_escalation": {
            "value": True,
            "description": "Human is always the final escalation level",
        },
        "min_trust_score": {
            "value": 70,
            "description": "Minimum trust score to proceed between stages",
        },
    }

    # Layer 2: CONTRACTS (schema definitions)
    CONTRACTS = {
        "handoff_token": {
            "required_fields": [
                "pipeline_run_id", "from_stage", "to_stage",
                "trust_score", "verification", "signature"
            ],
        },
        "pipeline_run": {
            "required_fields": [
                "task_id", "task_title", "current_stage",
                "status", "escalation_level"
            ],
        },
        "po_review_request": {
            "required_fields": [
                "pipeline_run_id", "health_score",
                "tests_passed", "tests_failed"
            ],
        },
    }

    # Layer 3: POLICIES (configurable within bounds)
    POLICIES = {
        "min_health_for_po_review": PolicyBounds(
            value=70, min_value=50, max_value=100,
            description="Minimum health score required for PO review",
        ),
        "max_retry_attempts": PolicyBounds(
            value=3, min_value=1, max_value=10,
            description="Maximum retry attempts per stage",
        ),
        "auto_approve_threshold": PolicyBounds(
            value=90, min_value=85, max_value=100,
            description="Health score threshold for auto-approval (if enabled)",
        ),
        "test_coverage_requirement": PolicyBounds(
            value=70, min_value=0, max_value=100,
            description="Minimum test coverage percentage",
        ),
        "max_lint_errors": PolicyBounds(
            value=10, min_value=0, max_value=50,
            description="Maximum lint errors allowed",
        ),
    }

    # Layer 4: PREFERENCES (freely changeable)
    PREFERENCES = {
        "default_agent": "sonnet",
        "notification_channel": "syncwave",
        "dashboard_theme": "dark",
        "show_detailed_logs": True,
        "auto_cleanup_stale": True,
        "stale_cleanup_hours": 24,
    }

    # Role permissions
    ROLE_PERMISSIONS = {
        "ceo": {
            "can_approve_po_review": True,
            "can_override_guardrails": True,
            "can_modify_policies": True,
            "can_modify_invariants": False,  # Even CEO can't change invariants
        },
        "cto": {
            "can_approve_po_review": True,
            "can_override_guardrails": False,
            "can_modify_policies": True,
            "can_modify_invariants": False,
        },
        "po": {
            "can_approve_po_review": True,
            "can_override_guardrails": False,
            "can_modify_policies": False,
            "can_modify_invariants": False,
        },
        "dev": {
            "can_approve_po_review": False,
            "can_override_guardrails": False,
            "can_modify_policies": False,
            "can_modify_invariants": False,
        },
        "nh_worker": {
            "can_approve_po_review": False,
            "can_override_guardrails": False,
            "can_modify_policies": False,
            "can_modify_invariants": False,
        },
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_action(
        self,
        action: str,
        context: dict,
        actor: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate an action against all guardrail layers.

        Args:
            action: Action being attempted
            context: Context data for validation
            actor: Who/what is attempting the action

        Returns:
            ValidationResult indicating if action is allowed
        """
        # Check invariants first (strictest)
        result = self._check_invariants(action, context)
        if not result.allowed:
            await self._log_violation(result, actor, context)
            return result

        # Check contracts
        result = self._check_contracts(action, context)
        if not result.allowed:
            await self._log_violation(result, actor, context)
            return result

        # Check policies
        result = self._check_policies(action, context)
        if not result.allowed:
            await self._log_violation(result, actor, context)
            return result

        return ValidationResult(
            allowed=True,
            layer=GuardrailLayer.PREFERENCE,
            rule="none",
            message="Action allowed",
        )

    async def validate_stage_transition(
        self,
        from_stage: PipelineStage,
        to_stage: PipelineStage,
    ) -> bool:
        """
        Validate a stage transition follows the correct order.

        Args:
            from_stage: Current stage
            to_stage: Target stage

        Returns:
            True if transition is valid
        """
        stage_order = self.INVARIANTS["stage_order"]["value"]

        try:
            from_index = stage_order.index(from_stage.value)
            to_index = stage_order.index(to_stage.value)

            # Must move forward (or stay same)
            if to_index >= from_index:
                return True

            # Backward transition not allowed
            logger.warning(f"Invalid stage transition: {from_stage.value} → {to_stage.value}")
            return False

        except ValueError:
            # Stage not in order list (failed/cancelled)
            return True  # Allow transitions to terminal states

    async def validate_escalation(
        self,
        current_level: EscalationLevel,
        priority: str,
    ) -> ValidationResult:
        """
        Validate escalation level matches priority requirements.

        Args:
            current_level: Current escalation level
            priority: Task priority

        Returns:
            ValidationResult
        """
        # Critical tasks require Opus (invariant)
        if priority == "critical" and current_level != EscalationLevel.OPUS:
            if current_level != EscalationLevel.HUMAN:
                return ValidationResult(
                    allowed=False,
                    layer=GuardrailLayer.INVARIANT,
                    rule="critical_requires_opus",
                    message="Critical tasks must use Opus agent",
                )

        return ValidationResult(
            allowed=True,
            layer=GuardrailLayer.INVARIANT,
            rule="escalation_valid",
            message="Escalation level valid",
        )

    def _check_invariants(self, action: str, context: dict) -> ValidationResult:
        """Check action against invariants."""
        # Check if trying to skip PO review
        if action == "skip_stage":
            target_stage = context.get("stage")
            if target_stage == "po_review" and self.INVARIANTS["po_review_required"]["value"]:
                return ValidationResult(
                    allowed=False,
                    layer=GuardrailLayer.INVARIANT,
                    rule="po_review_required",
                    message="PO review stage cannot be skipped",
                )

        # Check minimum trust score
        if action == "stage_transition":
            trust_score = context.get("trust_score", 0)
            min_score = self.INVARIANTS["min_trust_score"]["value"]
            if trust_score < min_score:
                return ValidationResult(
                    allowed=False,
                    layer=GuardrailLayer.INVARIANT,
                    rule="min_trust_score",
                    message=f"Trust score {trust_score} below minimum {min_score}",
                )

        return ValidationResult(
            allowed=True,
            layer=GuardrailLayer.INVARIANT,
            rule="passed",
            message="Invariant checks passed",
        )

    def _check_contracts(self, action: str, context: dict) -> ValidationResult:
        """Check action against contracts."""
        contract_type = context.get("contract_type")

        if contract_type and contract_type in self.CONTRACTS:
            contract = self.CONTRACTS[contract_type]
            required = contract.get("required_fields", [])

            data = context.get("data", {})
            missing = [f for f in required if f not in data]

            if missing:
                return ValidationResult(
                    allowed=False,
                    layer=GuardrailLayer.CONTRACT,
                    rule=f"{contract_type}_schema",
                    message=f"Missing required fields: {missing}",
                )

        return ValidationResult(
            allowed=True,
            layer=GuardrailLayer.CONTRACT,
            rule="passed",
            message="Contract checks passed",
        )

    def _check_policies(self, action: str, context: dict) -> ValidationResult:
        """Check action against policies."""
        if action == "po_review_request":
            health_score = context.get("health_score", 0)
            min_health = self.POLICIES["min_health_for_po_review"].value

            if health_score < min_health:
                return ValidationResult(
                    allowed=False,
                    layer=GuardrailLayer.POLICY,
                    rule="min_health_for_po_review",
                    message=f"Health score {health_score} below policy minimum {min_health}",
                )

        return ValidationResult(
            allowed=True,
            layer=GuardrailLayer.POLICY,
            rule="passed",
            message="Policy checks passed",
        )

    async def _log_violation(
        self,
        result: ValidationResult,
        actor: Optional[str],
        context: dict,
    ):
        """Log a guardrail violation."""
        violation = GuardrailViolation(
            id=uuid4(),
            layer=result.layer,
            rule_name=result.rule,
            attempted_action=context.get("action", "unknown"),
            blocked=not result.allowed,
            actor=actor,
            context=context,
        )

        self.db.add(violation)
        await self.db.commit()

        result.violation_id = violation.id

        logger.warning(
            f"Guardrail violation: {result.layer.value}:{result.rule} - {result.message}"
        )

    def get_policy(self, name: str) -> Optional[PolicyBounds]:
        """Get a policy's current value and bounds."""
        return self.POLICIES.get(name)

    def update_policy(self, name: str, value: Any) -> bool:
        """
        Update a policy value within its bounds.

        Args:
            name: Policy name
            value: New value

        Returns:
            True if update successful
        """
        if name not in self.POLICIES:
            return False

        policy = self.POLICIES[name]

        if policy.min_value <= value <= policy.max_value:
            policy.value = value
            logger.info(f"Updated policy {name} to {value}")
            return True

        logger.warning(f"Policy {name} value {value} outside bounds [{policy.min_value}, {policy.max_value}]")
        return False

    def get_preference(self, name: str) -> Any:
        """Get a preference value."""
        return self.PREFERENCES.get(name)

    def update_preference(self, name: str, value: Any):
        """Update a preference value (no restrictions)."""
        self.PREFERENCES[name] = value
        logger.info(f"Updated preference {name} to {value}")

    def get_configuration(self) -> dict:
        """Get full guardrails configuration."""
        return {
            "invariants": {k: v["value"] for k, v in self.INVARIANTS.items()},
            "contracts": list(self.CONTRACTS.keys()),
            "policies": {
                k: {
                    "value": v.value,
                    "min": v.min_value,
                    "max": v.max_value,
                    "description": v.description,
                }
                for k, v in self.POLICIES.items()
            },
            "preferences": self.PREFERENCES,
            "roles": list(self.ROLE_PERMISSIONS.keys()),
        }

    def check_role_permission(self, role: str, permission: str) -> bool:
        """Check if a role has a specific permission."""
        role_perms = self.ROLE_PERMISSIONS.get(role, {})
        return role_perms.get(permission, False)
