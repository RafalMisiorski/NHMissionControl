"""
Escalation Manager - Agent upgrade path management.

Handles escalation: Codex → Sonnet → Opus → Human
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import EscalationLevel, PipelineRun

logger = logging.getLogger(__name__)


class EscalationManager:
    """
    Agent escalation manager.

    Escalation Path:
    1. Codex (fast, cost-effective) - Default for normal tasks
    2. Sonnet (balanced) - For complex tasks
    3. Opus (most capable) - For critical tasks or repeated failures
    4. Human (final) - When all AI attempts fail

    Escalation is triggered:
    - After max retries exhausted
    - On critical errors
    - When guardrails require human approval
    """

    # Escalation path in order
    ESCALATION_PATH = [
        EscalationLevel.CODEX,
        EscalationLevel.SONNET,
        EscalationLevel.OPUS,
        EscalationLevel.HUMAN,
    ]

    # Agent capabilities description
    AGENT_CAPABILITIES = {
        EscalationLevel.CODEX: {
            "name": "Codex",
            "description": "Fast, cost-effective agent for straightforward tasks",
            "best_for": ["simple fixes", "routine changes", "documentation"],
            "cost": "low",
        },
        EscalationLevel.SONNET: {
            "name": "Claude Sonnet",
            "description": "Balanced agent for moderate complexity tasks",
            "best_for": ["feature development", "refactoring", "debugging"],
            "cost": "medium",
        },
        EscalationLevel.OPUS: {
            "name": "Claude Opus",
            "description": "Most capable agent for complex tasks",
            "best_for": ["architecture", "critical bugs", "complex features"],
            "cost": "high",
        },
        EscalationLevel.HUMAN: {
            "name": "Human",
            "description": "Human intervention required",
            "best_for": ["decisions requiring judgment", "unclear requirements", "final review"],
            "cost": "variable",
        },
    }

    def __init__(
        self,
        db: AsyncSession,
        notification_callback: Optional[callable] = None,
    ):
        self.db = db
        self.notification_callback = notification_callback

    async def escalate(self, pipeline_run: PipelineRun) -> EscalationLevel:
        """
        Escalate a pipeline run to the next level.

        Args:
            pipeline_run: The pipeline run to escalate

        Returns:
            New escalation level
        """
        current_level = pipeline_run.escalation_level
        current_index = self.ESCALATION_PATH.index(current_level)

        if current_index + 1 >= len(self.ESCALATION_PATH):
            # Already at human level
            logger.warning(f"Pipeline {pipeline_run.task_id} already at human escalation level")
            return EscalationLevel.HUMAN

        new_level = self.ESCALATION_PATH[current_index + 1]
        pipeline_run.escalation_level = new_level

        await self.db.commit()

        logger.info(
            f"Escalated pipeline {pipeline_run.task_id} from {current_level.value} to {new_level.value}"
        )

        # Send notification
        await self._notify_escalation(pipeline_run, current_level, new_level)

        return new_level

    async def escalate_to(
        self, pipeline_run: PipelineRun, level: EscalationLevel
    ) -> EscalationLevel:
        """
        Escalate directly to a specific level.

        Args:
            pipeline_run: The pipeline run to escalate
            level: Target escalation level

        Returns:
            New escalation level
        """
        current_level = pipeline_run.escalation_level

        if level == current_level:
            return current_level

        pipeline_run.escalation_level = level
        await self.db.commit()

        logger.info(
            f"Escalated pipeline {pipeline_run.task_id} directly to {level.value}"
        )

        await self._notify_escalation(pipeline_run, current_level, level)

        return level

    async def notify_po(self, pipeline_run: PipelineRun, reason: str):
        """
        Send notification to Product Owner.

        Args:
            pipeline_run: The pipeline run
            reason: Reason for notification
        """
        message = {
            "type": "po_notification",
            "task_id": pipeline_run.task_id,
            "task_title": pipeline_run.task_title,
            "reason": reason,
            "current_stage": pipeline_run.current_stage.value,
            "escalation_level": pipeline_run.escalation_level.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"PO notification for {pipeline_run.task_id}: {reason}")

        if self.notification_callback:
            await self.notification_callback(message)

    async def request_human_intervention(self, pipeline_run: PipelineRun, reason: str = ""):
        """
        Request human intervention (final escalation).

        Args:
            pipeline_run: The pipeline run
            reason: Reason for human intervention request
        """
        pipeline_run.escalation_level = EscalationLevel.HUMAN

        message = {
            "type": "human_intervention_required",
            "task_id": pipeline_run.task_id,
            "task_title": pipeline_run.task_title,
            "reason": reason or "All automated attempts exhausted",
            "current_stage": pipeline_run.current_stage.value,
            "retry_count": pipeline_run.retry_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.warning(
            f"Human intervention requested for {pipeline_run.task_id}: {reason}"
        )

        await self.db.commit()

        if self.notification_callback:
            await self.notification_callback(message)

    async def _notify_escalation(
        self,
        pipeline_run: PipelineRun,
        from_level: EscalationLevel,
        to_level: EscalationLevel,
    ):
        """Send escalation notification."""
        message = {
            "type": "escalation",
            "task_id": pipeline_run.task_id,
            "task_title": pipeline_run.task_title,
            "from_level": from_level.value,
            "to_level": to_level.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self.notification_callback:
            await self.notification_callback(message)

    def get_current_agent_info(self, pipeline_run: PipelineRun) -> dict:
        """
        Get information about the current agent level.

        Args:
            pipeline_run: The pipeline run

        Returns:
            Dict with agent information
        """
        level = pipeline_run.escalation_level
        info = self.AGENT_CAPABILITIES.get(level, {})

        return {
            "level": level.value,
            "name": info.get("name", level.value),
            "description": info.get("description", ""),
            "best_for": info.get("best_for", []),
            "cost": info.get("cost", "unknown"),
            "is_human": level == EscalationLevel.HUMAN,
        }

    def get_recommended_level(self, priority: str, complexity: str = "normal") -> EscalationLevel:
        """
        Get recommended initial escalation level.

        Args:
            priority: Task priority (critical, high, normal, low)
            complexity: Task complexity (simple, normal, complex)

        Returns:
            Recommended EscalationLevel
        """
        if priority == "critical":
            return EscalationLevel.OPUS
        elif priority == "high" or complexity == "complex":
            return EscalationLevel.SONNET
        else:
            return EscalationLevel.CODEX

    def can_escalate(self, pipeline_run: PipelineRun) -> bool:
        """
        Check if further escalation is possible.

        Args:
            pipeline_run: The pipeline run

        Returns:
            True if escalation is possible
        """
        return pipeline_run.escalation_level != EscalationLevel.HUMAN

    def get_escalation_history(self, pipeline_run: PipelineRun) -> list[str]:
        """
        Get escalation path taken so far.

        Args:
            pipeline_run: The pipeline run

        Returns:
            List of escalation levels reached
        """
        current_index = self.ESCALATION_PATH.index(pipeline_run.escalation_level)
        return [level.value for level in self.ESCALATION_PATH[:current_index + 1]]
