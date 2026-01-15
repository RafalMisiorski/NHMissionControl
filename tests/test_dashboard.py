"""Dashboard API tests"""
from unittest.mock import AsyncMock, patch
from app.nh_api.models import QueueStatus, JobResponse, HealthStatus, AFKStatus
from datetime import datetime, timezone


def test_get_dashboard(client):
    """Test dashboard overview endpoint - returns degraded when NH API unavailable"""
    response = client.get("/api/v1/dashboard/")
    assert response.status_code == 200
    data = response.json()
    assert data["module"] == "dashboard"
    # Status is 'degraded' when NH API is not available
    assert data["status"] in ("operational", "degraded")
    assert "metrics" in data
    assert "active_projects" in data["metrics"]
    assert "running_pipelines" in data["metrics"]
    assert "system_health" in data["metrics"]


def test_get_dashboard_with_nh_data(client):
    """Test dashboard returns real NH data when connected"""
    mock_queue_status = QueueStatus(
        total_jobs=10,
        pending_jobs=2,
        running_jobs=3,
        completed_jobs=4,
        failed_jobs=1,
        jobs=[],
    )
    mock_jobs = [
        JobResponse(
            id="job1",
            type="build",
            project_path="/project/a",
            description="Build project A",
            priority="normal",
            status="running",
            requires_approval=True,
            created_at=datetime.now(timezone.utc),
        ),
        JobResponse(
            id="job2",
            type="test",
            project_path="/project/b",
            description="Test project B",
            priority="high",
            status="completed",
            requires_approval=False,
            created_at=datetime.now(timezone.utc),
        ),
    ]

    with patch("app.api.v1.dashboard.get_nh_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.get_queue_status.return_value = mock_queue_status
        mock_client.get_jobs.return_value = mock_jobs
        mock_get_client.return_value = mock_client

        response = client.get("/api/v1/dashboard/")
        assert response.status_code == 200
        data = response.json()
        assert data["module"] == "dashboard"
        assert data["status"] == "operational"
        assert data["nh_connected"] is True
        assert data["metrics"]["total_jobs"] == 10
        assert data["metrics"]["running_pipelines"] == 3
        assert data["metrics"]["completed_jobs"] == 4
        assert data["metrics"]["failed_jobs"] == 1
        assert data["metrics"]["pending_jobs"] == 2
        # System health should be 90% (9 non-failed out of 10)
        assert data["metrics"]["system_health"] == 90.0
        # 2 unique projects
        assert data["metrics"]["active_projects"] == 2


def test_get_dashboard_summary(client):
    """Test dashboard summary endpoint"""
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    # New structure includes nh_connected, queue, afk, health
    assert "nh_connected" in data


def test_get_dashboard_summary_with_nh_data(client):
    """Test dashboard summary returns real NH data when connected"""
    mock_health = HealthStatus(
        status="healthy",
        service="neural-holding",
        timestamp=datetime.now(timezone.utc),
        connected=True,
    )
    mock_queue = QueueStatus(
        total_jobs=5,
        pending_jobs=1,
        running_jobs=2,
        completed_jobs=1,
        failed_jobs=1,
        jobs=[],
    )
    mock_afk = AFKStatus(
        active=True,
        jobs_processed=10,
    )

    with patch("app.api.v1.dashboard.get_nh_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.health_check.return_value = mock_health
        mock_client.get_queue_status.return_value = mock_queue
        mock_client.get_afk_status.return_value = mock_afk
        mock_get_client.return_value = mock_client

        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["nh_connected"] is True
        assert data["health"]["connected"] is True
        assert data["queue"]["total"] == 5
        assert data["afk"]["active"] is True
        assert data["afk"]["jobs_processed"] == 10


def test_get_pipeline_status(client):
    """Test pipeline status endpoint - returns zeros when NH API unavailable"""
    response = client.get("/api/v1/pipeline/status")
    assert response.status_code == 200
    data = response.json()
    assert "running" in data
    assert "queued" in data
    assert "completed" in data
    assert "failed" in data
    assert "nh_connected" in data


def test_get_pipeline_status_with_nh_data(client):
    """Test pipeline status returns real NH queue data when connected"""
    mock_queue_status = QueueStatus(
        total_jobs=15,
        pending_jobs=3,
        running_jobs=4,
        completed_jobs=6,
        failed_jobs=2,
        jobs=[],
    )

    with patch("app.api.v1.pipeline.get_nh_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.get_queue_status.return_value = mock_queue_status
        mock_get_client.return_value = mock_client

        response = client.get("/api/v1/pipeline/status")
        assert response.status_code == 200
        data = response.json()
        assert data["running"] == 4
        assert data["queued"] == 3  # pending_jobs
        assert data["completed"] == 6
        assert data["failed"] == 2
        assert data["nh_connected"] is True


def test_get_operations(client):
    """Test operations endpoint"""
    response = client.get("/api/v1/operations/")
    assert response.status_code == 200
    data = response.json()
    assert data["module"] == "sw_operations"


def test_get_finance(client):
    """Test finance endpoint"""
    response = client.get("/api/v1/finance/")
    assert response.status_code == 200
    data = response.json()
    assert data["module"] == "finance"


def test_get_intelligence(client):
    """Test intelligence endpoint"""
    response = client.get("/api/v1/intelligence/")
    assert response.status_code == 200
    data = response.json()
    assert data["module"] == "intelligence"


def test_get_briefing(client):
    """Test briefing endpoint"""
    response = client.get("/api/v1/briefing/")
    assert response.status_code == 200
    data = response.json()
    assert data["module"] == "briefing"
