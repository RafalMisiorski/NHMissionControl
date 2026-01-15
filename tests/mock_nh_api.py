"""Mock NH API Server for E2E testing"""
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI(title="Mock NH API", description="Mock server for E2E testing")


def _create_initial_jobs() -> list[dict]:
    """Create initial sample jobs for testing."""
    now = datetime.now(timezone.utc)
    return [
        {
            "id": "job_001",
            "type": "build",
            "project_path": "D:/Projects/SignalForge",
            "description": "Build production bundle",
            "priority": "high",
            "status": "running",
            "requires_approval": False,
            "auto_approved_by_afk": False,
            "created_at": (now - timedelta(minutes=15)).isoformat(),
            "started_at": (now - timedelta(minutes=10)).isoformat(),
            "completed_at": None,
            "output": None,
            "error": None,
        },
        {
            "id": "job_002",
            "type": "test",
            "project_path": "D:/Projects/NHMissionControl",
            "description": "Run E2E Playwright tests",
            "priority": "normal",
            "status": "pending",
            "requires_approval": True,
            "auto_approved_by_afk": False,
            "created_at": (now - timedelta(minutes=5)).isoformat(),
            "started_at": None,
            "completed_at": None,
            "output": None,
            "error": None,
        },
        {
            "id": "job_003",
            "type": "fix",
            "project_path": "D:/Projects/SalonBook",
            "description": "Fix authentication bug in login flow",
            "priority": "critical",
            "status": "approved",
            "requires_approval": True,
            "auto_approved_by_afk": True,
            "created_at": (now - timedelta(minutes=30)).isoformat(),
            "started_at": None,
            "completed_at": None,
            "output": None,
            "error": None,
        },
        {
            "id": "job_004",
            "type": "analyze",
            "project_path": "D:/Projects/fabryka-sygnalow",
            "description": "Analyze codebase structure and dependencies",
            "priority": "low",
            "status": "completed",
            "requires_approval": False,
            "auto_approved_by_afk": False,
            "created_at": (now - timedelta(hours=2)).isoformat(),
            "started_at": (now - timedelta(hours=2, minutes=-5)).isoformat(),
            "completed_at": (now - timedelta(hours=1)).isoformat(),
            "output": "Analysis complete. 15 modules identified.",
            "error": None,
        },
        {
            "id": "job_005",
            "type": "deploy",
            "project_path": "D:/Projects/TenantHub",
            "description": "Deploy to staging environment",
            "priority": "high",
            "status": "failed",
            "requires_approval": True,
            "auto_approved_by_afk": False,
            "created_at": (now - timedelta(hours=1)).isoformat(),
            "started_at": (now - timedelta(minutes=45)).isoformat(),
            "completed_at": (now - timedelta(minutes=40)).isoformat(),
            "output": None,
            "error": "Connection timeout to staging server",
        },
        {
            "id": "job_006",
            "type": "refactor",
            "project_path": "D:/Projects/Learning_Platform",
            "description": "Refactor user service module",
            "priority": "normal",
            "status": "needs_review",
            "requires_approval": True,
            "auto_approved_by_afk": False,
            "created_at": (now - timedelta(minutes=20)).isoformat(),
            "started_at": (now - timedelta(minutes=18)).isoformat(),
            "completed_at": None,
            "output": "Refactoring complete, awaiting review",
            "error": None,
        },
    ]


# In-memory storage for mock data
_jobs: list[dict] = _create_initial_jobs()
_afk_status: dict = {
    "active": False,
    "started_at": None,
    "duration_hours": None,
    "approved_types": [],
    "jobs_processed": 0,
    "pause_on_error": True,
}


class JobSubmitRequest(BaseModel):
    project: str
    description: str
    job_type: str = "build"
    priority: str = "normal"
    requires_approval: bool = True
    auto_approve_in_afk: bool = True
    phase_prompts: list[str] = []
    resume_previous: bool = False
    session_id: Optional[str] = None
    callback_url: Optional[str] = None


class AFKStartRequest(BaseModel):
    duration_hours: float = 8
    approved_types: list[str] = []
    pause_on_error: bool = True


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "neural-holding",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0-mock",
    }


@app.get("/api/health")
async def api_health():
    """API health check endpoint (for /nh/health proxy)"""
    return {
        "status": "healthy",
        "service": "neural-holding",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0-mock",
    }


@app.get("/api/settings")
async def get_settings():
    """Get NH API settings"""
    return {
        "version": "1.0.0-mock",
        "environment": "test",
        "features": {
            "afk_mode": True,
            "parallel_execution": True,
            "quality_gates": True,
        },
    }


# Job endpoints
@app.post("/api/jobs/submit")
async def submit_job(job: JobSubmitRequest):
    """Submit a new job"""
    job_id = f"job_{len(_jobs) + 1:03d}"
    new_job = {
        "id": job_id,
        "type": job.job_type,
        "project_path": job.project,
        "description": job.description,
        "priority": job.priority,
        "status": "pending",
        "requires_approval": job.requires_approval,
        "auto_approved_by_afk": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None,
        "output": None,
        "error": None,
    }
    _jobs.append(new_job)
    return new_job


@app.get("/api/jobs")
async def get_jobs(status: Optional[str] = None, limit: int = 50):
    """Get list of jobs"""
    jobs = _jobs
    if status:
        jobs = [j for j in jobs if j["status"] == status]
    return jobs[:limit]


@app.get("/api/jobs/pending-approvals")
async def get_pending_approvals():
    """Get jobs pending approval"""
    return [j for j in _jobs if j["status"] == "pending" and j["requires_approval"]]


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Get specific job"""
    for job in _jobs:
        if job["id"] == job_id:
            return job
    return {"error": "Job not found"}


@app.get("/api/jobs/{job_id}/detail")
async def get_job_detail(job_id: str):
    """Get detailed job information"""
    for job in _jobs:
        if job["id"] == job_id:
            return {**job, "logs": [], "metrics": {}}
    return {"error": "Job not found"}


@app.post("/api/jobs/{job_id}/approve")
async def approve_job(job_id: str):
    """Approve a job"""
    for job in _jobs:
        if job["id"] == job_id:
            job["status"] = "approved"
            return job
    return {"error": "Job not found"}


@app.post("/api/jobs/{job_id}/reject")
async def reject_job(job_id: str):
    """Reject a job"""
    for job in _jobs:
        if job["id"] == job_id:
            job["status"] = "cancelled"
            return job
    return {"error": "Job not found"}


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a job"""
    for job in _jobs:
        if job["id"] == job_id:
            job["status"] = "cancelled"
            return job
    return {"error": "Job not found"}


@app.post("/api/jobs/{job_id}/skip")
async def skip_job(job_id: str):
    """Skip a job"""
    for job in _jobs:
        if job["id"] == job_id:
            job["status"] = "cancelled"
            return job
    return {"error": "Job not found"}


@app.post("/api/jobs/clear")
async def clear_jobs():
    """Clear all jobs"""
    _jobs.clear()
    return {"message": "All jobs cleared", "count": 0}


# Queue endpoints
@app.get("/api/queue/status")
async def get_queue_status():
    """Get queue status"""
    return {
        "total_jobs": len(_jobs),
        "pending_jobs": len([j for j in _jobs if j["status"] == "pending"]),
        "running_jobs": len([j for j in _jobs if j["status"] == "running"]),
        "completed_jobs": len([j for j in _jobs if j["status"] == "completed"]),
        "failed_jobs": len([j for j in _jobs if j["status"] == "failed"]),
        "jobs": _jobs[:10],
    }


# AFK endpoints
@app.get("/api/afk/status")
async def get_afk_status():
    """Get AFK mode status"""
    return _afk_status


@app.post("/api/afk/start")
async def start_afk(request: AFKStartRequest):
    """Start AFK mode"""
    global _afk_status
    _afk_status = {
        "active": True,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "duration_hours": request.duration_hours,
        "approved_types": request.approved_types,
        "jobs_processed": 0,
        "pause_on_error": request.pause_on_error,
    }
    return _afk_status


@app.post("/api/afk/stop")
async def stop_afk():
    """Stop AFK mode"""
    global _afk_status
    _afk_status["active"] = False
    return _afk_status


@app.get("/api/afk/activity")
async def get_afk_activity():
    """Get AFK activity logs"""
    return []


# Strategy endpoints
@app.get("/api/strategy/master")
async def get_master_strategy():
    """Get master strategy"""
    return {
        "vision": "Build autonomous AI operations",
        "goals": ["Increase efficiency", "Reduce manual work"],
        "current_focus": "Testing and validation",
    }


@app.put("/api/strategy/master")
async def update_master_strategy(strategy: dict):
    """Update master strategy"""
    return strategy


@app.get("/api/strategy/projects")
async def get_project_strategies():
    """Get project strategies"""
    return []


@app.get("/api/strategy/okr-progress")
async def get_okr_progress():
    """Get OKR progress"""
    return {
        "objectives": [],
        "overall_progress": 0.0,
    }


# Gap analysis endpoints
@app.get("/api/gaps")
async def get_gaps():
    """Get all gaps"""
    return []


@app.get("/api/gaps/project/{project_name}")
async def get_project_gaps(project_name: str):
    """Get project-specific gaps"""
    return []


@app.post("/api/gaps/analyze")
async def analyze_gaps():
    """Trigger gap analysis"""
    return {"status": "analysis_started", "timestamp": datetime.now(timezone.utc).isoformat()}


# Briefing endpoints
@app.get("/api/briefing")
async def get_briefing():
    """Get morning briefing"""
    return {
        "id": "briefing_001",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": [],
        "summary": "No items for today",
    }


@app.post("/api/briefing/generate")
async def generate_briefing():
    """Generate new briefing"""
    return {
        "id": "briefing_002",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": [],
        "summary": "Newly generated briefing",
    }


@app.post("/api/briefing/{briefing_id}/approve/{item_id}")
async def approve_briefing_item(briefing_id: str, item_id: str):
    """Approve a briefing item"""
    return {"status": "approved", "briefing_id": briefing_id, "item_id": item_id}


@app.post("/api/briefing/{briefing_id}/approve-all")
async def approve_all_briefing_items(briefing_id: str):
    """Approve all briefing items"""
    return {"status": "all_approved", "briefing_id": briefing_id}


# Projects endpoints
@app.get("/api/projects")
async def get_nh_projects():
    """Get all NH projects"""
    return [
        {"name": "MockProject1", "path": "D:/Projects/MockProject1", "status": "active"},
        {"name": "MockProject2", "path": "D:/Projects/MockProject2", "status": "active"},
    ]


@app.get("/api/projects/{project_name}/health")
async def get_project_health(project_name: str):
    """Get project health score"""
    return {
        "project_name": project_name,
        "health_score": 85.0,
        "issues": [],
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


# Governor endpoints
@app.get("/api/governor/status")
async def get_governor_status():
    """Get governor status"""
    return {
        "enabled": True,
        "rules_count": 5,
        "last_enforcement": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/governor/rules")
async def get_governor_rules():
    """Get governor rules"""
    return [
        {"name": "No infinite loops", "enabled": True},
        {"name": "Catch specific exceptions", "enabled": True},
    ]


# Parallelism endpoints
@app.get("/api/parallelism/config")
async def get_parallelism_config():
    """Get parallelism configuration"""
    return {
        "max_concurrent_jobs": 4,
        "max_parallel_agents": 6,
        "per_project_limits": {},
    }


@app.put("/api/parallelism/config")
async def update_parallelism_config(config: dict):
    """Update parallelism configuration"""
    return config


@app.get("/api/parallelism/status")
async def get_parallelism_status():
    """Get parallelism status"""
    return {
        "current_jobs": 0,
        "current_agents": 0,
        "capacity_available": True,
    }


# Quality gates endpoints
@app.get("/api/quality-gates/status")
async def get_quality_gates_status():
    """Get quality gates status"""
    return {
        "passed": True,
        "gates": [
            {"name": "lint", "status": "passed"},
            {"name": "tests", "status": "passed"},
        ],
    }


@app.post("/api/quality-gates/run")
async def run_quality_gates():
    """Run quality gates"""
    return {
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def run_mock_server(host: str = "0.0.0.0", port: int = 8100):
    """Run the mock NH API server"""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_mock_server()
