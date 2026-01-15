"""
Pipeline Notifications - SyncWave notification templates.

Templates for mobile and desktop notifications.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Types of pipeline notifications."""
    PO_REVIEW_REQUIRED = "po_review_required"
    ESCALATION_TRIGGERED = "escalation_triggered"
    GUARDRAIL_VIOLATION = "guardrail_violation"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_FAILED = "pipeline_failed"
    HUMAN_INTERVENTION = "human_intervention"
    STAGE_COMPLETED = "stage_completed"
    HEALTH_WARNING = "health_warning"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class NotificationAction:
    """Action button for notification."""
    label: str
    action: str  # approve, reject, preview, view, dismiss
    url: Optional[str] = None


@dataclass
class Notification:
    """Notification payload."""
    type: NotificationType
    title: str
    body: str
    priority: NotificationPriority
    timestamp: datetime
    data: dict
    actions: list[NotificationAction]
    icon: Optional[str] = None


class NotificationTemplates:
    """
    Notification template definitions.

    Templates for SyncWave mobile notifications.
    """

    @staticmethod
    def po_review_required(
        task_id: str,
        task_title: str,
        health_score: float,
        tests_passed: int,
        tests_total: int,
        preview_url: Optional[str] = None,
    ) -> Notification:
        """Create PO review required notification."""
        test_status = f"{tests_passed}/{tests_total} tests"
        if tests_passed == tests_total:
            test_status = f"✅ {test_status}"
        else:
            test_status = f"⚠️ {test_status}"

        actions = [
            NotificationAction("Approve", "approve"),
            NotificationAction("Reject", "reject"),
        ]
        if preview_url:
            actions.append(NotificationAction("Preview", "preview", preview_url))

        return Notification(
            type=NotificationType.PO_REVIEW_REQUIRED,
            title="🔍 PO Review Required",
            body=f"{task_title}\nHealth: {health_score:.0f}%\n{test_status}",
            priority=NotificationPriority.HIGH,
            timestamp=datetime.now(timezone.utc),
            data={
                "task_id": task_id,
                "task_title": task_title,
                "health_score": health_score,
                "tests_passed": tests_passed,
                "tests_total": tests_total,
            },
            actions=actions,
            icon="🔍",
        )

    @staticmethod
    def escalation_triggered(
        task_id: str,
        task_title: str,
        from_level: str,
        to_level: str,
        reason: str,
    ) -> Notification:
        """Create escalation notification."""
        priority = NotificationPriority.HIGH
        if to_level == "opus":
            priority = NotificationPriority.URGENT

        return Notification(
            type=NotificationType.ESCALATION_TRIGGERED,
            title="⚡ Escalation Alert",
            body=f"{task_title}\n{from_level} → {to_level}\nReason: {reason}",
            priority=priority,
            timestamp=datetime.now(timezone.utc),
            data={
                "task_id": task_id,
                "task_title": task_title,
                "from_level": from_level,
                "to_level": to_level,
                "reason": reason,
            },
            actions=[
                NotificationAction("View", "view"),
            ],
            icon="⚡",
        )

    @staticmethod
    def guardrail_violation(
        rule_name: str,
        attempted_action: str,
        layer: str,
        task_id: Optional[str] = None,
    ) -> Notification:
        """Create guardrail violation notification."""
        return Notification(
            type=NotificationType.GUARDRAIL_VIOLATION,
            title="🛑 Guardrail Blocked",
            body=f"Action blocked: {attempted_action}\nRule: {rule_name}\nLayer: {layer}",
            priority=NotificationPriority.HIGH,
            timestamp=datetime.now(timezone.utc),
            data={
                "rule_name": rule_name,
                "attempted_action": attempted_action,
                "layer": layer,
                "task_id": task_id,
            },
            actions=[
                NotificationAction("View Details", "view"),
            ],
            icon="🛑",
        )

    @staticmethod
    def pipeline_completed(
        task_id: str,
        task_title: str,
        final_score: float,
        duration_minutes: int,
    ) -> Notification:
        """Create pipeline completed notification."""
        return Notification(
            type=NotificationType.PIPELINE_COMPLETED,
            title="✅ Pipeline Completed",
            body=f"{task_title}\nScore: {final_score:.0f}%\nDuration: {duration_minutes}m",
            priority=NotificationPriority.NORMAL,
            timestamp=datetime.now(timezone.utc),
            data={
                "task_id": task_id,
                "task_title": task_title,
                "final_score": final_score,
                "duration_minutes": duration_minutes,
            },
            actions=[
                NotificationAction("View", "view"),
            ],
            icon="✅",
        )

    @staticmethod
    def pipeline_failed(
        task_id: str,
        task_title: str,
        stage: str,
        error: str,
    ) -> Notification:
        """Create pipeline failed notification."""
        return Notification(
            type=NotificationType.PIPELINE_FAILED,
            title="❌ Pipeline Failed",
            body=f"{task_title}\nStage: {stage}\nError: {error[:100]}",
            priority=NotificationPriority.URGENT,
            timestamp=datetime.now(timezone.utc),
            data={
                "task_id": task_id,
                "task_title": task_title,
                "stage": stage,
                "error": error,
            },
            actions=[
                NotificationAction("View Details", "view"),
                NotificationAction("Retry", "retry"),
            ],
            icon="❌",
        )

    @staticmethod
    def human_intervention(
        task_id: str,
        task_title: str,
        reason: str,
    ) -> Notification:
        """Create human intervention required notification."""
        return Notification(
            type=NotificationType.HUMAN_INTERVENTION,
            title="🚨 Human Help Required",
            body=f"{task_title}\nReason: {reason}",
            priority=NotificationPriority.URGENT,
            timestamp=datetime.now(timezone.utc),
            data={
                "task_id": task_id,
                "task_title": task_title,
                "reason": reason,
            },
            actions=[
                NotificationAction("Take Action", "view"),
            ],
            icon="🚨",
        )

    @staticmethod
    def health_warning(
        task_id: str,
        task_title: str,
        health_score: float,
        issues: list[str],
    ) -> Notification:
        """Create health warning notification."""
        issues_text = "\n".join(f"• {issue}" for issue in issues[:3])

        return Notification(
            type=NotificationType.HEALTH_WARNING,
            title="⚠️ Health Warning",
            body=f"{task_title}\nScore: {health_score:.0f}%\n{issues_text}",
            priority=NotificationPriority.HIGH,
            timestamp=datetime.now(timezone.utc),
            data={
                "task_id": task_id,
                "task_title": task_title,
                "health_score": health_score,
                "issues": issues,
            },
            actions=[
                NotificationAction("View", "view"),
            ],
            icon="⚠️",
        )


class NotificationService:
    """
    Notification delivery service.

    Integrates with SyncWave for mobile notifications.
    """

    def __init__(self, syncwave_url: Optional[str] = None):
        self.syncwave_url = syncwave_url
        self.templates = NotificationTemplates()

    async def send(self, notification: Notification):
        """
        Send a notification via SyncWave.

        Args:
            notification: Notification to send
        """
        payload = {
            "type": notification.type.value,
            "title": notification.title,
            "body": notification.body,
            "priority": notification.priority.value,
            "timestamp": notification.timestamp.isoformat(),
            "data": notification.data,
            "actions": [
                {"label": a.label, "action": a.action, "url": a.url}
                for a in notification.actions
            ],
            "icon": notification.icon,
        }

        logger.info(f"Sending notification: {notification.type.value} - {notification.title}")

        if self.syncwave_url:
            await self._send_to_syncwave(payload)
        else:
            logger.debug(f"SyncWave not configured, notification logged only: {payload}")

    async def _send_to_syncwave(self, payload: dict):
        """Send notification to SyncWave server."""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.syncwave_url}/api/notifications",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"SyncWave notification failed: {resp.status}")
        except Exception as e:
            logger.error(f"Failed to send SyncWave notification: {e}")

    # Convenience methods
    async def notify_po_review(self, **kwargs):
        """Send PO review notification."""
        notification = self.templates.po_review_required(**kwargs)
        await self.send(notification)

    async def notify_escalation(self, **kwargs):
        """Send escalation notification."""
        notification = self.templates.escalation_triggered(**kwargs)
        await self.send(notification)

    async def notify_guardrail_violation(self, **kwargs):
        """Send guardrail violation notification."""
        notification = self.templates.guardrail_violation(**kwargs)
        await self.send(notification)

    async def notify_pipeline_completed(self, **kwargs):
        """Send pipeline completed notification."""
        notification = self.templates.pipeline_completed(**kwargs)
        await self.send(notification)

    async def notify_pipeline_failed(self, **kwargs):
        """Send pipeline failed notification."""
        notification = self.templates.pipeline_failed(**kwargs)
        await self.send(notification)

    async def notify_human_intervention(self, **kwargs):
        """Send human intervention notification."""
        notification = self.templates.human_intervention(**kwargs)
        await self.send(notification)
