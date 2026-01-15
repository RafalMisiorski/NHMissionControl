"""
NH Mission Control - Notifications API
======================================

API endpoints for sending notifications via SyncWave integration.
Handles task notifications, blocker alerts, and progress updates.
"""

from typing import Dict, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel

from src.core.nerve_center import (
    SyncWaveClient,
    TaskNotification,
    BlockerAlert,
    ProgressUpdate,
)


router = APIRouter(prefix="/notify", tags=["Notifications"])

# Global SyncWave client instance
_syncwave_client: SyncWaveClient | None = None


def get_syncwave_client() -> SyncWaveClient:
    """Get or create SyncWave client instance."""
    global _syncwave_client
    if _syncwave_client is None:
        _syncwave_client = SyncWaveClient()
    return _syncwave_client


# ==========================================================================
# Request/Response Models
# ==========================================================================

class TaskNotificationRequest(BaseModel):
    """Request model for task notifications."""
    task_id: str
    task_title: str
    status: str  # started, completed, failed
    tool: str | None = None
    reason: str | None = None
    error: str | None = None


class BlockerAlertRequest(BaseModel):
    """Request model for blocker alerts."""
    project_id: str
    project_name: str
    blocker: str
    suggestion: str
    can_resolve: bool = False


class ProgressUpdateRequest(BaseModel):
    """Request model for progress updates."""
    project_id: str
    project_name: str
    old_completion: float
    new_completion: float
    change_source: str = "manual"  # manual, github, auto


class NotificationResponse(BaseModel):
    """Response model for notification endpoints."""
    status: str
    reason: str | None = None


class SyncWaveStatusResponse(BaseModel):
    """Response model for SyncWave status endpoint."""
    syncwave_enabled: bool
    mode: str  # "live" or "logging_only"
    api_url: str | None = None


# ==========================================================================
# Status Endpoint
# ==========================================================================

@router.get(
    "/status",
    response_model=SyncWaveStatusResponse,
    summary="Get SyncWave integration status",
)
async def notification_status() -> SyncWaveStatusResponse:
    """
    Check if SyncWave integration is enabled.
    
    Returns:
    - syncwave_enabled: Whether notifications are sent to SyncWave API
    - mode: "live" (sending to API) or "logging_only" (just logging)
    - api_url: The SyncWave API URL (only shown when enabled)
    """
    client = get_syncwave_client()
    return SyncWaveStatusResponse(
        syncwave_enabled=client.enabled,
        mode="live" if client.enabled else "logging_only",
        api_url=client.api_url if client.enabled else None,
    )


# ==========================================================================
# Task Notifications
# ==========================================================================

@router.post(
    "/task",
    response_model=NotificationResponse,
    summary="Send task notification",
    responses={
        200: {"description": "Notification queued"},
        400: {"description": "Unknown status"},
    },
)
async def notify_task(
    data: TaskNotificationRequest,
    background_tasks: BackgroundTasks,
) -> NotificationResponse:
    """
    Send a task notification via SyncWave.

    Supported statuses:
    - started: Task has started execution
    - completed: Task completed successfully
    - failed: Task failed with error
    """
    client = get_syncwave_client()
    task = TaskNotification(
        task_id=data.task_id,
        task_title=data.task_title,
        status=data.status,
        tool=data.tool,
        reason=data.reason,
        error=data.error,
    )

    if data.status == "started":
        background_tasks.add_task(client.notify_task_started, task)
    elif data.status == "completed":
        background_tasks.add_task(client.notify_task_completed, task)
    elif data.status == "failed":
        background_tasks.add_task(client.notify_task_failed, task)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown status: {data.status}",
        )

    return NotificationResponse(status="queued")


# ==========================================================================
# Blocker Alerts
# ==========================================================================

@router.post(
    "/blocker",
    response_model=NotificationResponse,
    summary="Send blocker alert",
    responses={
        200: {"description": "Alert queued"},
    },
)
async def notify_blocker(
    data: BlockerAlertRequest,
    background_tasks: BackgroundTasks,
) -> NotificationResponse:
    """
    Send a blocker alert via SyncWave.

    Use this to notify when a project is blocked and may be resolvable.
    """
    client = get_syncwave_client()
    alert = BlockerAlert(
        project_id=data.project_id,
        project_name=data.project_name,
        blocker=data.blocker,
        suggestion=data.suggestion,
        can_resolve=data.can_resolve,
    )

    background_tasks.add_task(client.notify_blocker_resolvable, alert)

    return NotificationResponse(status="queued")


# ==========================================================================
# Progress Updates
# ==========================================================================

@router.post(
    "/progress",
    response_model=NotificationResponse,
    summary="Send progress update",
    responses={
        200: {"description": "Update queued or skipped"},
    },
)
async def notify_progress(
    data: ProgressUpdateRequest,
    background_tasks: BackgroundTasks,
) -> NotificationResponse:
    """
    Send a progress update notification via SyncWave.

    Only notifies on significant changes (>=5%).
    Smaller changes are skipped to avoid notification spam.
    """
    client = get_syncwave_client()

    # Only notify on significant changes
    change = abs(data.new_completion - data.old_completion)
    if change < 5:
        return NotificationResponse(status="skipped", reason="Change too small")

    update = ProgressUpdate(
        project_id=data.project_id,
        project_name=data.project_name,
        old_completion=data.old_completion,
        new_completion=data.new_completion,
        change_source=data.change_source,
    )

    background_tasks.add_task(client.notify_progress_update, update)

    return NotificationResponse(status="queued")


# ==========================================================================
# Blocker Resolution
# ==========================================================================

@router.post(
    "/blocker-resolved",
    response_model=NotificationResponse,
    summary="Send blocker resolved notification",
    responses={
        200: {"description": "Notification queued"},
    },
)
async def notify_blocker_resolved(
    project_id: str,
    project_name: str,
    blocker: str,
    background_tasks: BackgroundTasks,
) -> NotificationResponse:
    """
    Notify when a blocker has been resolved.
    """
    client = get_syncwave_client()

    background_tasks.add_task(
        client.notify_blocker_resolved,
        project_id,
        project_name,
        blocker,
    )

    return NotificationResponse(status="queued")
