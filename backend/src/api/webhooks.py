"""
NH GitHub Integration
======================

Handles GitHub webhooks to automatically:
1. Update project completion % based on activity
2. Track commits and PRs
3. Send notifications via SyncWave
4. Update Asset Registry

Setup:
1. Go to GitHub repo → Settings → Webhooks → Add webhook
2. Payload URL: https://your-domain/api/v1/webhooks/github
3. Content type: application/json
4. Secret: your-webhook-secret
5. Events: Push, Pull requests
"""

import hmac
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import os
import re

from fastapi import APIRouter, Request, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel


# ==========================================================================
# Configuration
# ==========================================================================

# Repo name → Project ID mapping
REPO_PROJECT_MAP = {
    "neural-holding": "nh",
    "nh-mission-control": "nhmc",
    "nh-nerve-center": "nhmc",
    "synaptic-weavers": "sw",
    "signal-factory": "sf",
    "time-organization-app": "toa",
    "prospect-finder": "pf",
    "floor-plan-recognition": "fpr",
    "career-navigator": "cn",
    "ultrasinger": "us",
}

# Project completion tracking
PROJECT_COMPLETION = {
    "nh": 35.0,
    "nhmc": 60.0,
    "sw": 70.0,
    "sf": 65.0,
    "toa": 25.0,
    "pf": 5.0,
    "fpr": 20.0,
    "cn": 40.0,
    "us": 50.0,
}


# ==========================================================================
# Commit Analysis
# ==========================================================================

class CommitType(str, Enum):
    """Types of commits based on conventional commits"""
    FEAT = "feat"       # New feature
    FIX = "fix"         # Bug fix
    DOCS = "docs"       # Documentation
    STYLE = "style"     # Formatting
    REFACTOR = "refactor"
    TEST = "test"       # Tests
    CHORE = "chore"     # Maintenance
    OTHER = "other"


@dataclass
class CommitAnalysis:
    """Analysis of a single commit"""
    sha: str
    message: str
    commit_type: CommitType
    files_changed: int
    additions: int
    deletions: int
    
    # Heuristic scores
    feature_score: float = 0.0
    test_score: float = 0.0
    doc_score: float = 0.0
    
    @property
    def total_score(self) -> float:
        """Total progress score from this commit"""
        return self.feature_score + self.test_score + self.doc_score


def analyze_commit_message(message: str) -> CommitType:
    """Analyze commit message to determine type"""
    message_lower = message.lower()
    
    # Check for conventional commit prefixes
    prefixes = {
        "feat": CommitType.FEAT,
        "fix": CommitType.FIX,
        "docs": CommitType.DOCS,
        "style": CommitType.STYLE,
        "refactor": CommitType.REFACTOR,
        "test": CommitType.TEST,
        "chore": CommitType.CHORE,
    }
    
    for prefix, commit_type in prefixes.items():
        if message_lower.startswith(f"{prefix}:") or message_lower.startswith(f"{prefix}("):
            return commit_type
    
    # Fallback heuristics
    if any(word in message_lower for word in ["add", "implement", "create", "new"]):
        return CommitType.FEAT
    if any(word in message_lower for word in ["fix", "bug", "error", "issue"]):
        return CommitType.FIX
    if any(word in message_lower for word in ["doc", "readme", "comment"]):
        return CommitType.DOCS
    if any(word in message_lower for word in ["test", "spec"]):
        return CommitType.TEST
    
    return CommitType.OTHER


def calculate_commit_score(commit: CommitAnalysis) -> float:
    """
    Calculate progress score for a commit.
    
    Scoring heuristics:
    - Feature commits: 1.0-3.0 points based on size
    - Bug fixes: 0.5-1.5 points
    - Tests: 0.5-1.0 points
    - Docs: 0.25-0.5 points
    - Other: 0.1-0.25 points
    """
    base_scores = {
        CommitType.FEAT: 1.5,
        CommitType.FIX: 0.75,
        CommitType.TEST: 0.5,
        CommitType.DOCS: 0.25,
        CommitType.REFACTOR: 0.5,
        CommitType.STYLE: 0.1,
        CommitType.CHORE: 0.1,
        CommitType.OTHER: 0.1,
    }
    
    base = base_scores.get(commit.commit_type, 0.1)
    
    # Scale by size (capped)
    size_multiplier = min(1 + (commit.files_changed * 0.1), 2.0)
    
    return base * size_multiplier


def analyze_commits(commits: List[Dict[str, Any]]) -> List[CommitAnalysis]:
    """Analyze a list of commits from webhook payload"""
    analyses = []
    
    for commit in commits:
        analysis = CommitAnalysis(
            sha=commit.get("id", "")[:8],
            message=commit.get("message", ""),
            commit_type=analyze_commit_message(commit.get("message", "")),
            files_changed=len(commit.get("added", [])) + len(commit.get("modified", [])),
            additions=0,  # Would need API call for detailed stats
            deletions=0,
        )
        
        # Calculate scores
        score = calculate_commit_score(analysis)
        
        if analysis.commit_type == CommitType.FEAT:
            analysis.feature_score = score
        elif analysis.commit_type == CommitType.TEST:
            analysis.test_score = score
        elif analysis.commit_type == CommitType.DOCS:
            analysis.doc_score = score
        else:
            analysis.feature_score = score * 0.5
        
        analyses.append(analysis)
    
    return analyses


# ==========================================================================
# Progress Calculator
# ==========================================================================

@dataclass
class ProgressUpdate:
    """Calculated progress update"""
    project_id: str
    old_completion: float
    new_completion: float
    change: float
    commits_analyzed: int
    breakdown: Dict[str, float] = field(default_factory=dict)


def calculate_progress_update(
    project_id: str,
    commits: List[CommitAnalysis],
    current_completion: float,
) -> ProgressUpdate:
    """
    Calculate progress update from commits.
    
    Rules:
    - Each commit contributes 0.1-3.0% based on type/size
    - Total single push capped at 5%
    - Cannot exceed 95% (final 5% reserved for release)
    """
    total_score = sum(c.total_score for c in commits)
    
    # Cap single push at 5%
    progress_change = min(total_score, 5.0)
    
    # Calculate new completion (cap at 95%)
    new_completion = min(current_completion + progress_change, 95.0)
    
    # Breakdown by type
    breakdown = {
        "features": sum(c.feature_score for c in commits),
        "tests": sum(c.test_score for c in commits),
        "docs": sum(c.doc_score for c in commits),
    }
    
    return ProgressUpdate(
        project_id=project_id,
        old_completion=current_completion,
        new_completion=new_completion,
        change=new_completion - current_completion,
        commits_analyzed=len(commits),
        breakdown=breakdown,
    )


# ==========================================================================
# FastAPI Webhook Handler
# ==========================================================================

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "your-secret-here")


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature:
        return False
    
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
):
    """
    Handle GitHub webhook events.
    
    Supported events:
    - push: Update completion based on commits
    - pull_request: Track PR activity
    - release: Mark project as 100% for that version
    """
    payload = await request.body()
    
    # Verify signature in production
    # if not verify_signature(payload, x_hub_signature_256):
    #     raise HTTPException(401, "Invalid signature")
    
    data = json.loads(payload)
    
    if x_github_event == "push":
        return await handle_push(data, background_tasks)
    elif x_github_event == "pull_request":
        return await handle_pull_request(data, background_tasks)
    elif x_github_event == "release":
        return await handle_release(data, background_tasks)
    
    return {"status": "ignored", "event": x_github_event}


async def handle_push(data: Dict[str, Any], background_tasks: BackgroundTasks) -> Dict:
    """Handle push event"""
    repo_name = data.get("repository", {}).get("name", "")
    project_id = REPO_PROJECT_MAP.get(repo_name)
    
    if not project_id:
        return {"status": "ignored", "reason": f"Unknown repo: {repo_name}"}
    
    commits = data.get("commits", [])
    if not commits:
        return {"status": "ignored", "reason": "No commits"}
    
    # Analyze commits
    analyses = analyze_commits(commits)
    
    # Calculate progress
    current = PROJECT_COMPLETION.get(project_id, 0)
    update = calculate_progress_update(project_id, analyses, current)
    
    # Update stored completion
    PROJECT_COMPLETION[project_id] = update.new_completion
    
    # Queue SyncWave notification if significant change
    if update.change >= 1.0:
        background_tasks.add_task(
            send_progress_notification,
            update,
        )
    
    return {
        "status": "processed",
        "project": project_id,
        "commits": len(commits),
        "progress_change": f"+{update.change:.1f}%",
        "new_completion": f"{update.new_completion:.1f}%",
        "breakdown": update.breakdown,
    }


async def handle_pull_request(data: Dict[str, Any], background_tasks: BackgroundTasks) -> Dict:
    """Handle PR event"""
    action = data.get("action", "")
    pr = data.get("pull_request", {})
    repo_name = data.get("repository", {}).get("name", "")
    
    project_id = REPO_PROJECT_MAP.get(repo_name)
    if not project_id:
        return {"status": "ignored"}
    
    # Notify on merged PRs
    if action == "closed" and pr.get("merged"):
        background_tasks.add_task(
            send_pr_merged_notification,
            project_id,
            pr.get("title", ""),
        )
    
    return {"status": "processed", "action": action}


async def handle_release(data: Dict[str, Any], background_tasks: BackgroundTasks) -> Dict:
    """Handle release event"""
    action = data.get("action", "")
    release = data.get("release", {})
    repo_name = data.get("repository", {}).get("name", "")
    
    project_id = REPO_PROJECT_MAP.get(repo_name)
    if not project_id:
        return {"status": "ignored"}
    
    if action == "published":
        # Mark as 100% complete for this version
        # (In practice, might reset for next version)
        PROJECT_COMPLETION[project_id] = 100.0
        
        background_tasks.add_task(
            send_release_notification,
            project_id,
            release.get("tag_name", ""),
        )
    
    return {"status": "processed", "action": action}


# ==========================================================================
# SyncWave Notification Helpers
# ==========================================================================

async def send_progress_notification(update: ProgressUpdate):
    """Send progress update to SyncWave"""
    # TODO: Call SyncWave API
    print(f"""
📊 Progress Update: {update.project_id.upper()}
   {update.old_completion:.0f}% → {update.new_completion:.0f}% (+{update.change:.1f}%)
   Commits: {update.commits_analyzed}
   Breakdown: {update.breakdown}
""")


async def send_pr_merged_notification(project_id: str, pr_title: str):
    """Send PR merged notification"""
    print(f"🔀 PR Merged: {project_id.upper()} - {pr_title}")


async def send_release_notification(project_id: str, version: str):
    """Send release notification"""
    print(f"🎉 Released: {project_id.upper()} {version}")


# ==========================================================================
# API to Query Progress
# ==========================================================================

@router.get("/projects/{project_id}/progress")
async def get_project_progress(project_id: str):
    """Get current project progress"""
    if project_id not in PROJECT_COMPLETION:
        raise HTTPException(404, f"Project not found: {project_id}")
    
    return {
        "project_id": project_id,
        "completion": PROJECT_COMPLETION[project_id],
        "updated_at": datetime.utcnow().isoformat(),
    }


@router.get("/projects/progress")
async def get_all_progress():
    """Get progress for all projects"""
    return {
        "projects": [
            {"id": pid, "completion": comp}
            for pid, comp in PROJECT_COMPLETION.items()
        ],
        "updated_at": datetime.utcnow().isoformat(),
    }


