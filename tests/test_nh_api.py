"""Tests for NH API integration endpoints"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from app.nh_api.models import (
    JobResponse,
    QueueStatus,
    AFKStatus,
    HealthStatus,
    JobType,
    JobPriority,
    JobStatus,
)


class TestNHHealthEndpoint:
    """Tests for NH health check endpoint"""

    def test_nh_health_connected(self, client):
        """Test NH health when API is connected"""
        mock_health = HealthStatus(
            status="healthy",
            service="neural-holding",
            timestamp=datetime.now(timezone.utc),
            version="1.0.0",
            connected=True,
        )

        with patch("app.api.v1.nh.get_nh_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.health_check.return_value = mock_health
            mock_get_client.return_value = mock_client

            response = client.get("/api/v1/nh/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["connected"] is True

    def test_nh_health_disconnected(self, client):
        """Test NH health when API is disconnected"""
        mock_health = HealthStatus(
            status="disconnected",
            service="neural-holding",
            timestamp=datetime.now(timezone.utc),
            connected=False,
        )

        with patch("app.api.v1.nh.get_nh_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.health_check.return_value = mock_health
            mock_get_client.return_value = mock_client

            response = client.get("/api/v1/nh/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "disconnected"
            assert data["connected"] is False


class TestNHJobEndpoints:
    """Tests for NH job management endpoints"""

    def test_get_jobs_empty(self, client):
        """Test getting jobs when queue is empty"""
        with patch("app.api.v1.nh.get_nh_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_jobs.return_value = []
            mock_get_client.return_value = mock_client

            response = client.get("/api/v1/nh/jobs")
            assert response.status_code == 200
            assert response.json() == []

    def test_get_jobs_with_data(self, client):
        """Test getting jobs with data"""
        mock_jobs = [
            JobResponse(
                id="job_123",
                type="build",
                project_path="D:/Projects/TestProject",
                description="Test job",
                priority="normal",
                status="pending",
                requires_approval=True,
                auto_approved_by_afk=False,
                created_at=datetime.now(timezone.utc),
            ),
        ]

        with patch("app.api.v1.nh.get_nh_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_jobs.return_value = mock_jobs
            mock_get_client.return_value = mock_client

            response = client.get("/api/v1/nh/jobs")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == "job_123"
            assert data[0]["type"] == "build"

    def test_submit_job(self, client):
        """Test submitting a new job"""
        mock_job = JobResponse(
            id="job_456",
            type="fix",
            project_path="D:/Projects/TestProject",
            description="Fix the bug",
            priority="high",
            status="pending",
            requires_approval=True,
            auto_approved_by_afk=False,
            created_at=datetime.now(timezone.utc),
        )

        with patch("app.api.v1.nh.get_nh_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.submit_job.return_value = mock_job
            mock_get_client.return_value = mock_client

            response = client.post(
                "/api/v1/nh/jobs/submit",
                json={
                    "project": "D:/Projects/TestProject",
                    "description": "Fix the bug",
                    "job_type": "fix",
                    "priority": "high",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "job_456"
            assert data["status"] == "pending"

    def test_approve_job(self, client):
        """Test approving a job"""
        mock_job = JobResponse(
            id="job_789",
            type="build",
            project_path="D:/Projects/TestProject",
            description="Build feature",
            priority="normal",
            status="approved",
            requires_approval=True,
            auto_approved_by_afk=False,
            created_at=datetime.now(timezone.utc),
        )

        with patch("app.api.v1.nh.get_nh_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.approve_job.return_value = mock_job
            mock_get_client.return_value = mock_client

            response = client.post("/api/v1/nh/jobs/job_789/approve")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "approved"

    def test_reject_job(self, client):
        """Test rejecting a job"""
        mock_job = JobResponse(
            id="job_101",
            type="build",
            project_path="D:/Projects/TestProject",
            description="Build feature",
            priority="normal",
            status="cancelled",
            requires_approval=True,
            auto_approved_by_afk=False,
            created_at=datetime.now(timezone.utc),
        )

        with patch("app.api.v1.nh.get_nh_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.reject_job.return_value = mock_job
            mock_get_client.return_value = mock_client

            response = client.post(
                "/api/v1/nh/jobs/job_101/reject",
                json={"reason": "Not needed"},
            )
            assert response.status_code == 200


class TestNHQueueEndpoints:
    """Tests for NH queue status endpoints"""

    def test_get_queue_status(self, client):
        """Test getting queue status"""
        mock_status = QueueStatus(
            total_jobs=10,
            pending_jobs=3,
            running_jobs=2,
            completed_jobs=4,
            failed_jobs=1,
            jobs=[],
        )

        with patch("app.api.v1.nh.get_nh_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_queue_status.return_value = mock_status
            mock_get_client.return_value = mock_client

            response = client.get("/api/v1/nh/queue/status")
            assert response.status_code == 200
            data = response.json()
            assert data["total_jobs"] == 10
            assert data["running_jobs"] == 2


class TestNHAFKEndpoints:
    """Tests for NH AFK mode endpoints"""

    def test_get_afk_status_inactive(self, client):
        """Test getting AFK status when inactive"""
        mock_status = AFKStatus(
            active=False,
            jobs_processed=0,
            pause_on_error=True,
        )

        with patch("app.api.v1.nh.get_nh_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_afk_status.return_value = mock_status
            mock_get_client.return_value = mock_client

            response = client.get("/api/v1/nh/afk/status")
            assert response.status_code == 200
            data = response.json()
            assert data["active"] is False

    def test_start_afk(self, client):
        """Test starting AFK mode"""
        mock_status = AFKStatus(
            active=True,
            started_at=datetime.now(timezone.utc),
            duration_hours=8.0,
            approved_types=["backtest", "analyze"],
            jobs_processed=0,
            pause_on_error=True,
        )

        with patch("app.api.v1.nh.get_nh_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.start_afk.return_value = mock_status
            mock_get_client.return_value = mock_client

            response = client.post(
                "/api/v1/nh/afk/start",
                json={
                    "duration_hours": 8,
                    "approved_types": ["backtest", "analyze"],
                    "pause_on_error": True,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["active"] is True

    def test_stop_afk(self, client):
        """Test stopping AFK mode"""
        mock_status = AFKStatus(
            active=False,
            jobs_processed=5,
            pause_on_error=True,
        )

        with patch("app.api.v1.nh.get_nh_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.stop_afk.return_value = mock_status
            mock_get_client.return_value = mock_client

            response = client.post("/api/v1/nh/afk/stop")
            assert response.status_code == 200
            data = response.json()
            assert data["active"] is False


class TestNHClientModels:
    """Tests for NH API client models"""

    def test_job_types_enum(self):
        """Test JobType enum values"""
        assert JobType.FIX.value == "fix"
        assert JobType.BUILD.value == "build"
        assert JobType.ANALYZE.value == "analyze"
        assert JobType.RESEARCH.value == "research"

    def test_job_priority_enum(self):
        """Test JobPriority enum values"""
        assert JobPriority.CRITICAL.value == "critical"
        assert JobPriority.HIGH.value == "high"
        assert JobPriority.NORMAL.value == "normal"
        assert JobPriority.LOW.value == "low"

    def test_job_status_enum(self):
        """Test JobStatus enum values"""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"

    def test_job_response_model(self):
        """Test JobResponse model creation"""
        job = JobResponse(
            id="test_job",
            type="build",
            project_path="D:/Projects/Test",
            description="Test description",
            priority="normal",
            status="pending",
            requires_approval=True,
            auto_approved_by_afk=False,
            created_at=datetime.now(timezone.utc),
        )
        assert job.id == "test_job"
        assert job.type == "build"
        assert job.requires_approval is True

    def test_queue_status_model(self):
        """Test QueueStatus model creation"""
        status = QueueStatus(
            total_jobs=5,
            pending_jobs=2,
            running_jobs=1,
            completed_jobs=1,
            failed_jobs=1,
        )
        assert status.total_jobs == 5
        assert status.pending_jobs == 2

    def test_afk_status_model(self):
        """Test AFKStatus model creation"""
        status = AFKStatus(
            active=True,
            duration_hours=8.0,
            approved_types=["analyze", "backtest"],
            jobs_processed=3,
        )
        assert status.active is True
        assert status.duration_hours == 8.0
        assert len(status.approved_types) == 2
