"""
NH Mission Control - Epoch 3: Pipeline Tests
=============================================

EPOCH 3 - ACTIVE

These tests define the expected behavior for pipeline endpoints.
CC must implement the endpoints to make all tests pass.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import Opportunity, OpportunitySource, OpportunityStatus, User


# ==========================================================================
# Fixtures
# ==========================================================================

@pytest.fixture
async def sample_opportunity(db_session: AsyncSession, test_user: User) -> Opportunity:
    """Create a sample opportunity for testing."""
    opp = Opportunity(
        id=uuid4(),
        user_id=test_user.id,
        title="Sample Python API Project",
        description="Build a REST API for e-commerce platform",
        source=OpportunitySource.UPWORK,
        status=OpportunityStatus.LEAD,
        value=Decimal("5000.00"),
        currency="EUR",
        probability=50,
        client_name="Test Client",
        client_rating=Decimal("4.85"),
        tech_stack=["Python", "FastAPI", "PostgreSQL"],
    )
    db_session.add(opp)
    await db_session.commit()
    await db_session.refresh(opp)
    return opp


@pytest.fixture
async def multiple_opportunities(
    db_session: AsyncSession, test_user: User
) -> list[Opportunity]:
    """Create multiple opportunities for testing."""
    opportunities = []
    
    statuses = [
        OpportunityStatus.LEAD,
        OpportunityStatus.QUALIFIED,
        OpportunityStatus.PROPOSAL,
        OpportunityStatus.WON,
        OpportunityStatus.LOST,
    ]
    
    for i, status in enumerate(statuses):
        opp = Opportunity(
            id=uuid4(),
            user_id=test_user.id,
            title=f"Opportunity {i + 1}",
            source=OpportunitySource.UPWORK,
            status=status,
            value=Decimal(str((i + 1) * 1000)),
            currency="EUR",
            probability=50 if status not in [OpportunityStatus.WON, OpportunityStatus.LOST] else (100 if status == OpportunityStatus.WON else 0),
        )
        db_session.add(opp)
        opportunities.append(opp)
    
    await db_session.commit()
    for opp in opportunities:
        await db_session.refresh(opp)
    
    return opportunities


# ==========================================================================
# List Opportunities Tests
# ==========================================================================

class TestListOpportunities:
    """Tests for listing opportunities."""
    
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        """Returns empty list when no opportunities."""
        response = await client.get(
            "/api/v1/pipeline/opportunities",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
    
    async def test_list_with_opportunities(
        self,
        client: AsyncClient,
        auth_headers: dict,
        multiple_opportunities: list[Opportunity],
    ):
        """Returns all user's opportunities."""
        response = await client.get(
            "/api/v1/pipeline/opportunities",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 5
    
    async def test_list_filter_by_status(
        self,
        client: AsyncClient,
        auth_headers: dict,
        multiple_opportunities: list[Opportunity],
    ):
        """Can filter by status."""
        response = await client.get(
            "/api/v1/pipeline/opportunities?status=lead",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "lead"
    
    async def test_list_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict,
        multiple_opportunities: list[Opportunity],
    ):
        """Pagination works correctly."""
        response = await client.get(
            "/api/v1/pipeline/opportunities?page=1&page_size=2",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["pages"] == 3
    
    async def test_list_requires_auth(self, client: AsyncClient):
        """Listing requires authentication."""
        response = await client.get("/api/v1/pipeline/opportunities")
        
        assert response.status_code == 401


# ==========================================================================
# Get Opportunity Tests
# ==========================================================================

class TestGetOpportunity:
    """Tests for getting a single opportunity."""
    
    async def test_get_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_opportunity: Opportunity,
    ):
        """Can get own opportunity by ID."""
        response = await client.get(
            f"/api/v1/pipeline/opportunities/{sample_opportunity.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_opportunity.id)
        assert data["title"] == sample_opportunity.title
    
    async def test_get_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Returns 404 for nonexistent opportunity."""
        response = await client.get(
            f"/api/v1/pipeline/opportunities/{uuid4()}",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
    
    async def test_get_other_users_opportunity(
        self,
        client: AsyncClient,
        admin_headers: dict,  # Different user
        sample_opportunity: Opportunity,  # Belongs to test_user
    ):
        """Cannot get another user's opportunity."""
        response = await client.get(
            f"/api/v1/pipeline/opportunities/{sample_opportunity.id}",
            headers=admin_headers,
        )
        
        assert response.status_code == 404


# ==========================================================================
# Create Opportunity Tests
# ==========================================================================

class TestCreateOpportunity:
    """Tests for creating opportunities."""
    
    async def test_create_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Can create opportunity with valid data."""
        response = await client.post(
            "/api/v1/pipeline/opportunities",
            headers=auth_headers,
            json={
                "title": "New API Project",
                "description": "Build REST API",
                "source": "upwork",
                "value": 5000,
                "currency": "EUR",
                "tech_stack": ["Python", "FastAPI"],
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New API Project"
        assert data["status"] == "lead"  # Initial status
        assert data["probability"] == 50  # Default
    
    async def test_create_minimal(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Can create with only required fields."""
        response = await client.post(
            "/api/v1/pipeline/opportunities",
            headers=auth_headers,
            json={"title": "Minimal Opportunity"},
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Minimal Opportunity"
        assert data["source"] == "other"  # Default
    
    async def test_create_validation(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Validation rejects invalid data."""
        response = await client.post(
            "/api/v1/pipeline/opportunities",
            headers=auth_headers,
            json={
                "title": "",  # Empty title
                "value": -100,  # Negative value
            },
        )
        
        assert response.status_code == 422


# ==========================================================================
# Update Opportunity Tests
# ==========================================================================

class TestUpdateOpportunity:
    """Tests for updating opportunities."""
    
    async def test_update_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_opportunity: Opportunity,
    ):
        """Can update opportunity fields."""
        response = await client.patch(
            f"/api/v1/pipeline/opportunities/{sample_opportunity.id}",
            headers=auth_headers,
            json={
                "title": "Updated Title",
                "value": 7500,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert float(data["value"]) == 7500.0
    
    async def test_update_partial(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_opportunity: Opportunity,
    ):
        """Partial update only changes provided fields."""
        original_description = sample_opportunity.description
        
        response = await client.patch(
            f"/api/v1/pipeline/opportunities/{sample_opportunity.id}",
            headers=auth_headers,
            json={"title": "New Title Only"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title Only"
        assert data["description"] == original_description


# ==========================================================================
# Delete Opportunity Tests
# ==========================================================================

class TestDeleteOpportunity:
    """Tests for deleting opportunities."""
    
    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_opportunity: Opportunity,
    ):
        """Can soft delete opportunity."""
        response = await client.delete(
            f"/api/v1/pipeline/opportunities/{sample_opportunity.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        
        # Verify it's not in list anymore
        list_response = await client.get(
            "/api/v1/pipeline/opportunities",
            headers=auth_headers,
        )
        assert list_response.json()["total"] == 0
    
    async def test_delete_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Returns 404 for nonexistent opportunity."""
        response = await client.delete(
            f"/api/v1/pipeline/opportunities/{uuid4()}",
            headers=auth_headers,
        )
        
        assert response.status_code == 404


# ==========================================================================
# Move Opportunity Tests
# ==========================================================================

class TestMoveOpportunity:
    """Tests for moving opportunities through pipeline."""
    
    async def test_move_lead_to_qualified(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_opportunity: Opportunity,
    ):
        """Can move from LEAD to QUALIFIED."""
        response = await client.post(
            f"/api/v1/pipeline/opportunities/{sample_opportunity.id}/move",
            headers=auth_headers,
            json={"status": "qualified"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "qualified"
    
    async def test_move_to_won_sets_probability(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Moving to WON sets probability to 100."""
        # Create opportunity in NEGOTIATING status
        opp = Opportunity(
            id=uuid4(),
            user_id=test_user.id,
            title="Negotiating Deal",
            status=OpportunityStatus.NEGOTIATING,
            probability=75,
        )
        db_session.add(opp)
        await db_session.commit()
        
        response = await client.post(
            f"/api/v1/pipeline/opportunities/{opp.id}/move",
            headers=auth_headers,
            json={"status": "won"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "won"
        assert data["probability"] == 100
    
    async def test_move_to_lost_sets_probability(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_opportunity: Opportunity,
    ):
        """Moving to LOST sets probability to 0."""
        response = await client.post(
            f"/api/v1/pipeline/opportunities/{sample_opportunity.id}/move",
            headers=auth_headers,
            json={"status": "lost"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "lost"
        assert data["probability"] == 0


# ==========================================================================
# Pipeline Stats Tests
# ==========================================================================

class TestPipelineStats:
    """Tests for pipeline statistics."""
    
    async def test_stats_empty(self, client: AsyncClient, auth_headers: dict):
        """Returns stats even with no opportunities."""
        response = await client.get(
            "/api/v1/pipeline/stats",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_opportunities"] == 0
    
    async def test_stats_with_opportunities(
        self,
        client: AsyncClient,
        auth_headers: dict,
        multiple_opportunities: list[Opportunity],
    ):
        """Returns correct statistics."""
        response = await client.get(
            "/api/v1/pipeline/stats",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_opportunities"] == 5
        assert len(data["stages"]) > 0


# ==========================================================================
# NH Analysis Tests
# ==========================================================================

class TestNHAnalysis:
    """Tests for NH analysis endpoints."""
    
    async def test_analyze_opportunity(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_opportunity: Opportunity,
    ):
        """Can run NH analysis on opportunity."""
        response = await client.post(
            f"/api/v1/pipeline/opportunities/{sample_opportunity.id}/analyze",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert 0 <= data["score"] <= 100
        assert "strengths" in data
        assert "risks" in data
        assert "recommendations" in data
    
    async def test_generate_proposal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_opportunity: Opportunity,
    ):
        """Can generate proposal draft."""
        response = await client.post(
            f"/api/v1/pipeline/opportunities/{sample_opportunity.id}/proposal",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "subject" in data
        assert "intro" in data
        assert "approach" in data
        assert "pricing" in data
    
    async def test_estimate_effort(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_opportunity: Opportunity,
    ):
        """Can estimate effort for opportunity."""
        response = await client.post(
            f"/api/v1/pipeline/opportunities/{sample_opportunity.id}/estimate",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "complexity_tier" in data
        assert 1 <= data["complexity_tier"] <= 5
        assert "total_hours_expected" in data
        assert "suggested_price" in data
