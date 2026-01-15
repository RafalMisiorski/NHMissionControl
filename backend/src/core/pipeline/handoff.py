"""
Handoff Token Generator - Gate verification between stages.

Creates cryptographically signed tokens with trust scoring.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import HandoffToken, PipelineStage

logger = logging.getLogger(__name__)


class HandoffTokenGenerator:
    """
    Creates handoff tokens (gate tokens) for stage transitions.

    Trust Score Calculation (0-100):
    - Tests passed: up to 40 points (proportional to pass rate)
    - Lint clean: up to 20 points (reduced by errors)
    - Health check: up to 30 points (API responds, UI loads)
    - No console errors: up to 10 points

    A token must have trust_score >= 70 to allow stage transition.
    """

    # Score weights
    MAX_TESTS_SCORE = 40.0
    MAX_LINT_SCORE = 20.0
    MAX_HEALTH_SCORE = 30.0
    MAX_CONSOLE_SCORE = 10.0

    def __init__(self, db: AsyncSession, secret_key: str = "nh-pipeline-secret"):
        self.db = db
        self.secret_key = secret_key

    async def create_token(
        self,
        pipeline_run_id: UUID,
        from_stage: PipelineStage,
        to_stage: PipelineStage,
        verification_results: dict,
    ) -> HandoffToken:
        """
        Create a handoff token for a stage transition.

        Args:
            pipeline_run_id: The pipeline run this token belongs to
            from_stage: Source stage
            to_stage: Destination stage
            verification_results: Results from verification checks

        Returns:
            Created HandoffToken
        """
        # Calculate individual scores
        tests_score = self._calculate_tests_score(verification_results)
        lint_score = self._calculate_lint_score(verification_results)
        health_score = self._calculate_health_score(verification_results)
        console_score = self._calculate_console_score(verification_results)

        # Total trust score
        trust_score = tests_score + lint_score + health_score + console_score

        # Create signature
        signature = self._sign_token(
            pipeline_run_id=str(pipeline_run_id),
            from_stage=from_stage.value,
            to_stage=to_stage.value,
            trust_score=float(trust_score),
            verification=verification_results,
        )

        token = HandoffToken(
            id=uuid4(),
            pipeline_run_id=pipeline_run_id,
            from_stage=from_stage,
            to_stage=to_stage,
            trust_score=Decimal(str(round(trust_score, 2))),
            verification=verification_results,
            tests_score=Decimal(str(round(tests_score, 2))),
            lint_score=Decimal(str(round(lint_score, 2))),
            health_score=Decimal(str(round(health_score, 2))),
            console_score=Decimal(str(round(console_score, 2))),
            signature=signature,
            valid=True,
        )

        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)

        logger.info(
            f"Created handoff token {token.id}: {from_stage.value}→{to_stage.value} "
            f"score={trust_score:.2f}"
        )

        return token

    def _calculate_tests_score(self, results: dict) -> float:
        """
        Calculate tests score (max 40 points).

        Proportional to pass rate: passed / (passed + failed)
        Skipped tests don't affect score.
        """
        tests_passed = results.get("tests_passed", 0)
        tests_failed = results.get("tests_failed", 0)

        if tests_passed + tests_failed == 0:
            # No tests run - give partial credit
            return self.MAX_TESTS_SCORE * 0.5

        pass_rate = tests_passed / (tests_passed + tests_failed)
        return self.MAX_TESTS_SCORE * pass_rate

    def _calculate_lint_score(self, results: dict) -> float:
        """
        Calculate lint score (max 20 points).

        Reduced by lint errors:
        - 0 errors: 20 points
        - 1-5 errors: 15 points
        - 6-10 errors: 10 points
        - 11-20 errors: 5 points
        - >20 errors: 0 points
        """
        lint_errors = results.get("lint_errors", 0)

        if lint_errors == 0:
            return self.MAX_LINT_SCORE
        elif lint_errors <= 5:
            return 15.0
        elif lint_errors <= 10:
            return 10.0
        elif lint_errors <= 20:
            return 5.0
        else:
            return 0.0

    def _calculate_health_score(self, results: dict) -> float:
        """
        Calculate health score (max 30 points).

        Based on health check results:
        - API responds: 15 points
        - UI loads (Playwright): 15 points
        Or use provided health_score directly if available.
        """
        # If a direct health_score is provided, use it
        if "health_score" in results:
            health = results["health_score"]
            # Normalize to our max (30 points)
            return min(self.MAX_HEALTH_SCORE, (health / 100.0) * self.MAX_HEALTH_SCORE)

        # Otherwise calculate from individual checks
        score = 0.0

        if results.get("api_responds", False):
            score += 15.0
        if results.get("ui_loads", False):
            score += 15.0

        return score

    def _calculate_console_score(self, results: dict) -> float:
        """
        Calculate console errors score (max 10 points).

        - 0 console errors: 10 points
        - 1-2 errors: 7 points
        - 3-5 errors: 4 points
        - >5 errors: 0 points
        """
        console_errors = results.get("console_errors", 0)

        if console_errors == 0:
            return self.MAX_CONSOLE_SCORE
        elif console_errors <= 2:
            return 7.0
        elif console_errors <= 5:
            return 4.0
        else:
            return 0.0

    def _sign_token(
        self,
        pipeline_run_id: str,
        from_stage: str,
        to_stage: str,
        trust_score: float,
        verification: dict,
    ) -> str:
        """
        Create SHA256 signature for the token.

        Args:
            pipeline_run_id: Pipeline run ID
            from_stage: Source stage
            to_stage: Destination stage
            trust_score: Calculated trust score
            verification: Verification results

        Returns:
            64-character hex string (SHA256 hash)
        """
        # Create deterministic payload
        payload = {
            "pipeline_run_id": pipeline_run_id,
            "from_stage": from_stage,
            "to_stage": to_stage,
            "trust_score": round(trust_score, 2),
            "verification": json.dumps(verification, sort_keys=True),
            "secret": self.secret_key,
        }

        # Serialize and hash
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hashlib.sha256(payload_str.encode()).hexdigest()

        return signature

    def verify_signature(self, token: HandoffToken) -> bool:
        """
        Verify a token's signature is valid.

        Args:
            token: The handoff token to verify

        Returns:
            True if signature is valid
        """
        expected_signature = self._sign_token(
            pipeline_run_id=str(token.pipeline_run_id),
            from_stage=token.from_stage.value,
            to_stage=token.to_stage.value,
            trust_score=float(token.trust_score),
            verification=token.verification,
        )

        return token.signature == expected_signature

    async def invalidate_token(self, token: HandoffToken, reason: str):
        """
        Invalidate a handoff token.

        Args:
            token: Token to invalidate
            reason: Reason for invalidation
        """
        token.valid = False
        token.rejected_reason = reason
        await self.db.commit()
        logger.info(f"Invalidated token {token.id}: {reason}")

    async def get_token(self, token_id: UUID) -> Optional[HandoffToken]:
        """Get a handoff token by ID."""
        from sqlalchemy import select

        result = await self.db.execute(
            select(HandoffToken).where(HandoffToken.id == token_id)
        )
        return result.scalar_one_or_none()

    async def get_tokens_for_run(self, pipeline_run_id: UUID) -> list[HandoffToken]:
        """Get all handoff tokens for a pipeline run."""
        from sqlalchemy import select

        result = await self.db.execute(
            select(HandoffToken)
            .where(HandoffToken.pipeline_run_id == pipeline_run_id)
            .order_by(HandoffToken.created_at)
        )
        return list(result.scalars().all())
