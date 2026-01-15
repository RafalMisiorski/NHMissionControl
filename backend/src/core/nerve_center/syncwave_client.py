"""
NH SyncWave Integration
========================

Integration layer between NH systems and SyncWave app.
Handles:
- Task notifications (start, complete, fail)
- Blocker alerts
- Progress updates
- GitHub webhook events
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import httpx
import structlog

from src.core.config import settings

logger = structlog.get_logger()


# ==========================================================================
# Notification Types
# ==========================================================================

class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationCategory(str, Enum):
    TASK = "task"
    ALERT = "alert"
    UPDATE = "update"
    ERROR = "error"
    GITHUB = "github"
    BLOCKER = "blocker"


# ==========================================================================
# API Models
# ==========================================================================

class NotificationRequest(BaseModel):
    title: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    category: NotificationCategory = NotificationCategory.UPDATE
    action_url: Optional[str] = None
    data: Dict[str, Any] = {}


class TaskNotification(BaseModel):
    task_id: str
    task_title: str
    status: str  # started, completed, failed
    tool: Optional[str] = None
    reason: Optional[str] = None
    error: Optional[str] = None


class BlockerAlert(BaseModel):
    project_id: str
    project_name: str
    blocker: str
    suggestion: str
    can_resolve: bool = False


class GitHubWebhook(BaseModel):
    repository: str
    event: str  # push, pull_request, etc.
    branch: str
    commits: int = 0
    message: Optional[str] = None


class ProgressUpdate(BaseModel):
    project_id: str
    project_name: str
    old_completion: float
    new_completion: float
    change_source: str = "manual"  # manual, github, auto


# ==========================================================================
# SyncWave Client
# ==========================================================================

class SyncWaveClient:
    """
    Client for SyncWave notification API.
    Sends notifications from NH to your phone.
    """
    
    def __init__(
        self,
        api_url: str = None,
        api_key: str = None,
    ):
        self.api_url = api_url or settings.SYNCWAVE_API_URL
        self.api_key = api_key or settings.SYNCWAVE_API_KEY
        self._client = httpx.AsyncClient(timeout=30.0)
        
        # Log initialization status
        if self.enabled:
            logger.info("syncwave_client_initialized", mode="live", api_url=self.api_url)
        else:
            logger.info("syncwave_client_initialized", mode="logging_only")
    
    @property
    def enabled(self) -> bool:
        """Check if SyncWave is properly configured"""
        return bool(self.api_key) and settings.SYNCWAVE_ENABLED
    
    async def send(self, notification: NotificationRequest) -> bool:
        """Send notification to SyncWave or log if disabled"""
        # Log notification when disabled
        if not self.enabled:
            logger.info(
                "syncwave_notification_logged",
                title=notification.title,
                body=notification.body,
                priority=notification.priority.value,
                category=notification.category.value,
                mode="disabled"
            )
            return True  # Return success in logging mode
        
        # Send to SyncWave API when enabled
        try:
            response = await self._client.post(
                f"{self.api_url}/api/v1/notifications",
                json=notification.dict(),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
            if response.status_code == 200:
                logger.debug("syncwave_notification_sent", title=notification.title)
                return True
            else:
                logger.warning(
                    "syncwave_notification_failed",
                    title=notification.title,
                    status_code=response.status_code
                )
                return False
        except Exception as e:
            logger.error("syncwave_error", error=str(e), title=notification.title)
            return False
    
    # ==================== Task Notifications ====================
    
    async def notify_task_started(self, task: TaskNotification):
        """Notify that a task has started"""
        return await self.send(NotificationRequest(
            title=f"🚀 Task Started",
            body=f"{task.task_title[:40]}\n→ {task.tool}: {task.reason[:50] if task.reason else ''}",
            priority=NotificationPriority.NORMAL,
            category=NotificationCategory.TASK,
            data={"task_id": task.task_id, "status": "started"},
        ))
    
    async def notify_task_completed(self, task: TaskNotification):
        """Notify that a task completed"""
        return await self.send(NotificationRequest(
            title=f"✅ Task Completed",
            body=f"{task.task_title[:40]}\nFinished by {task.tool}",
            priority=NotificationPriority.NORMAL,
            category=NotificationCategory.TASK,
            data={"task_id": task.task_id, "status": "completed"},
        ))
    
    async def notify_task_failed(self, task: TaskNotification):
        """Notify that a task failed"""
        return await self.send(NotificationRequest(
            title=f"❌ Task Failed",
            body=f"{task.task_title[:40]}\nError: {task.error[:50] if task.error else 'Unknown'}",
            priority=NotificationPriority.HIGH,
            category=NotificationCategory.ERROR,
            data={"task_id": task.task_id, "status": "failed", "error": task.error},
        ))
    
    # ==================== Blocker Alerts ====================
    
    async def notify_blocker_resolvable(self, alert: BlockerAlert):
        """Alert when a blocker might be resolvable"""
        return await self.send(NotificationRequest(
            title=f"🔓 Blocker Update: {alert.project_name}",
            body=f"{alert.blocker}\n💡 {alert.suggestion}",
            priority=NotificationPriority.HIGH,
            category=NotificationCategory.BLOCKER,
            data={
                "project_id": alert.project_id,
                "blocker": alert.blocker,
                "can_resolve": alert.can_resolve,
            },
        ))
    
    async def notify_blocker_resolved(self, project_id: str, project_name: str, blocker: str):
        """Notify when a blocker has been resolved"""
        return await self.send(NotificationRequest(
            title=f"🎉 Blocker Resolved: {project_name}",
            body=f"'{blocker}' is no longer blocking progress!",
            priority=NotificationPriority.HIGH,
            category=NotificationCategory.BLOCKER,
            data={"project_id": project_id, "resolved": True},
        ))
    
    # ==================== GitHub Updates ====================
    
    async def notify_github_push(self, webhook: GitHubWebhook):
        """Notify on GitHub push"""
        return await self.send(NotificationRequest(
            title=f"📦 Push: {webhook.repository}",
            body=f"{webhook.commits} commit(s) to {webhook.branch}\n{webhook.message[:50] if webhook.message else ''}",
            priority=NotificationPriority.LOW,
            category=NotificationCategory.GITHUB,
            data={"repo": webhook.repository, "branch": webhook.branch},
        ))
    
    async def notify_github_pr(self, webhook: GitHubWebhook, action: str):
        """Notify on PR events"""
        return await self.send(NotificationRequest(
            title=f"🔀 PR {action}: {webhook.repository}",
            body=f"{webhook.message[:60] if webhook.message else 'No description'}",
            priority=NotificationPriority.NORMAL,
            category=NotificationCategory.GITHUB,
            data={"repo": webhook.repository, "action": action},
        ))
    
    # ==================== Progress Updates ====================
    
    async def notify_progress_update(self, update: ProgressUpdate):
        """Notify on significant progress change"""
        change = update.new_completion - update.old_completion
        emoji = "📈" if change > 0 else "📉"
        
        return await self.send(NotificationRequest(
            title=f"{emoji} Progress: {update.project_name}",
            body=f"{update.old_completion:.0f}% → {update.new_completion:.0f}% ({change:+.0f}%)",
            priority=NotificationPriority.NORMAL if abs(change) < 10 else NotificationPriority.HIGH,
            category=NotificationCategory.UPDATE,
            data={
                "project_id": update.project_id,
                "old": update.old_completion,
                "new": update.new_completion,
                "source": update.change_source,
            },
        ))


# ==========================================================================
# FastAPI Endpoints for SyncWave Integration
# ==========================================================================

app = FastAPI(title="NH SyncWave Integration", version="1.0.0")
client = SyncWaveClient()


@app.post("/api/v1/notify/task")
async def notify_task(task: TaskNotification, background_tasks: BackgroundTasks):
    """Send task notification"""
    if task.status == "started":
        background_tasks.add_task(client.notify_task_started, task)
    elif task.status == "completed":
        background_tasks.add_task(client.notify_task_completed, task)
    elif task.status == "failed":
        background_tasks.add_task(client.notify_task_failed, task)
    else:
        raise HTTPException(400, f"Unknown status: {task.status}")
    
    return {"status": "queued"}


@app.post("/api/v1/notify/blocker")
async def notify_blocker(alert: BlockerAlert, background_tasks: BackgroundTasks):
    """Send blocker alert"""
    background_tasks.add_task(client.notify_blocker_resolvable, alert)
    return {"status": "queued"}


@app.post("/api/v1/notify/progress")
async def notify_progress(update: ProgressUpdate, background_tasks: BackgroundTasks):
    """Send progress update notification"""
    # Only notify on significant changes (>5%)
    if abs(update.new_completion - update.old_completion) >= 5:
        background_tasks.add_task(client.notify_progress_update, update)
        return {"status": "queued"}
    return {"status": "skipped", "reason": "Change too small"}


@app.post("/api/v1/webhooks/github")
async def github_webhook(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """
    Handle GitHub webhook events.
    Configure in GitHub: Settings → Webhooks → Add webhook
    Payload URL: https://your-domain/api/v1/webhooks/github
    """
    event_type = payload.get("action", "push")
    repo = payload.get("repository", {}).get("name", "unknown")
    
    webhook = GitHubWebhook(
        repository=repo,
        event=event_type,
        branch=payload.get("ref", "").replace("refs/heads/", ""),
        commits=len(payload.get("commits", [])),
        message=payload.get("head_commit", {}).get("message"),
    )
    
    if "commits" in payload:
        # Push event
        background_tasks.add_task(client.notify_github_push, webhook)
        
        # Auto-update completion % based on commits (example heuristic)
        # In production, would analyze commits more carefully
        background_tasks.add_task(
            auto_update_completion_from_github,
            repo,
            len(payload.get("commits", [])),
        )
    
    elif "pull_request" in payload:
        # PR event
        background_tasks.add_task(
            client.notify_github_pr,
            webhook,
            payload.get("action", "updated"),
        )
    
    return {"status": "processed"}


async def auto_update_completion_from_github(repo: str, commit_count: int):
    """
    Auto-update project completion based on GitHub activity.
    This is a simplified heuristic - in production would be more sophisticated.
    """
    # Map repo names to project IDs
    repo_to_project = {
        "neural-holding": "nh",
        "nh-mission-control": "nhmc",
        "synaptic-weavers": "sw",
        "signal-factory": "sf",
        "time-organization-app": "toa",
    }
    
    project_id = repo_to_project.get(repo)
    if not project_id:
        return
    
    # Simple heuristic: each commit = 0.5% progress (capped)
    # In production, would analyze commit content, tests, etc.
    progress_increment = min(commit_count * 0.5, 5.0)
    
    # TODO: Update Asset Registry with new completion %
    # registry = get_registry()
    # project = registry.projects.get(project_id)
    # if project:
    #     old = project.completion_percent
    #     project.completion_percent = min(100, old + progress_increment)
    #     await client.notify_progress_update(ProgressUpdate(...))
    
    logger.info("github_progress_update", project_id=project_id, increment=progress_increment)


# ==========================================================================
# Blocker Monitoring
# ==========================================================================

class BlockerMonitor:
    """
    Monitors project blockers and suggests when they might be resolvable.
    Runs periodically or on-demand.
    """
    
    def __init__(self, syncwave: SyncWaveClient):
        self.syncwave = syncwave
        
        # Known blockers and their resolution hints
        self.blocker_hints = {
            "watermark handling": {
                "keywords": ["watermark removal", "image inpainting", "opencv watermark"],
                "suggestion": "New OpenCV/PIL techniques available for watermark removal",
            },
            "ifc export": {
                "keywords": ["ifcopenshell", "ifc python", "bim export"],
                "suggestion": "Check IfcOpenShell updates or alternative IFC libraries",
            },
        }
    
    async def check_blockers(self, project_id: str, blockers: List[str]):
        """Check if any blockers might be resolvable"""
        for blocker in blockers:
            blocker_lower = blocker.lower()
            for key, hints in self.blocker_hints.items():
                if key in blocker_lower:
                    # Found a known blocker type
                    await self.syncwave.notify_blocker_resolvable(BlockerAlert(
                        project_id=project_id,
                        project_name=project_id.upper(),
                        blocker=blocker,
                        suggestion=hints["suggestion"],
                        can_resolve=True,
                    ))


# ==========================================================================
# Startup
# ==========================================================================

@app.on_event("startup")
async def startup():
    """Initialize on startup"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                    NH SYNCWAVE INTEGRATION                            ║
║                                                                       ║
║  Endpoints:                                                           ║
║  • POST /api/v1/notify/task     - Task notifications                 ║
║  • POST /api/v1/notify/blocker  - Blocker alerts                     ║
║  • POST /api/v1/notify/progress - Progress updates                   ║
║  • POST /api/v1/webhooks/github - GitHub webhook receiver            ║
║                                                                       ║
╚══════════════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
