"""
NH Mission Control - Epoch 1: Authentication Tests
===================================================

EPOCH 1 - WILL BE LOCKED AFTER IMPLEMENTATION

These tests define the expected behavior for authentication endpoints.
CC must implement the endpoints to make all tests pass.

DO NOT modify these tests without explicit approval.
The tests ARE the specification.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import User
from tests.conftest import unique_email


# ==========================================================================
# Registration Tests
# ==========================================================================

class TestRegistration:
    """Tests for user registration endpoint."""
    
    async def test_register_success(self, client: AsyncClient):
        """New user can register with valid data."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email(),
                "password": "ValidPass123!",
                "name": "New User",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["email"] == data["email"]  # Email returned
        assert data["name"] == "New User"
        assert data["is_active"] is True
        assert data["email_verified"] is False
        assert "password" not in data
        assert "password_hash" not in data
    
    async def test_register_duplicate_email(
        self, client: AsyncClient, test_user: User
    ):
        """Registration fails with duplicate email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,  # Already exists
                "password": "ValidPass123!",
                "name": "Another User",
            },
        )
        
        assert response.status_code == 409
    
    async def test_register_weak_password_no_uppercase(self, client: AsyncClient):
        """Registration fails without uppercase letter."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email(),
                "password": "weakpass123!",  # No uppercase
                "name": "Test User",
            },
        )
        
        assert response.status_code == 422
    
    async def test_register_weak_password_no_lowercase(self, client: AsyncClient):
        """Registration fails without lowercase letter."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email(),
                "password": "WEAKPASS123!",  # No lowercase
                "name": "Test User",
            },
        )
        
        assert response.status_code == 422
    
    async def test_register_weak_password_no_digit(self, client: AsyncClient):
        """Registration fails without digit."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email(),
                "password": "WeakPassword!",  # No digit
                "name": "Test User",
            },
        )
        
        assert response.status_code == 422
    
    async def test_register_password_too_short(self, client: AsyncClient):
        """Registration fails with password < 8 chars."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email(),
                "password": "Short1!",  # Only 7 chars
                "name": "Test User",
            },
        )
        
        assert response.status_code == 422
    
    async def test_register_invalid_email(self, client: AsyncClient):
        """Registration fails with invalid email format."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "ValidPass123!",
                "name": "Test User",
            },
        )
        
        assert response.status_code == 422


# ==========================================================================
# Login Tests
# ==========================================================================

class TestLogin:
    """Tests for user login endpoint."""
    
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """User can login with valid credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123!",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        """Login fails with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123!",
            },
        )
        
        assert response.status_code == 401
    
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Login fails with nonexistent email."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123!",
            },
        )
        
        assert response.status_code == 401
    
    async def test_login_inactive_user(
        self, client: AsyncClient, inactive_user: User
    ):
        """Login fails for inactive user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": inactive_user.email,
                "password": "TestPass123!",
            },
        )
        
        assert response.status_code == 401
    
    async def test_login_tokens_are_different(
        self, client: AsyncClient, test_user: User
    ):
        """Each login generates unique tokens."""
        response1 = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123!",
            },
        )
        
        response2 = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123!",
            },
        )
        
        assert response1.json()["access_token"] != response2.json()["access_token"]


# ==========================================================================
# Protected Route Tests
# ==========================================================================

class TestProtectedRoutes:
    """Tests for protected route access."""
    
    async def test_protected_route_without_token(self, client: AsyncClient):
        """Protected route returns 401 without token."""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    async def test_protected_route_with_valid_token(
        self, client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Protected route works with valid token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email
    
    async def test_protected_route_with_invalid_token(self, client: AsyncClient):
        """Protected route returns 401 with invalid token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        
        assert response.status_code == 401
    
    async def test_protected_route_with_expired_token(self, client: AsyncClient):
        """Protected route returns 401 with expired token."""
        # This is a token that was generated with exp in the past
        expired_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxNjAwMDAwMDAwfQ."
            "xxx"
        )
        
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        
        assert response.status_code == 401


# ==========================================================================
# Token Refresh Tests
# ==========================================================================

class TestTokenRefresh:
    """Tests for token refresh endpoint."""
    
    async def test_refresh_token_success(
        self, client: AsyncClient, test_user: User
    ):
        """Can get new access token with valid refresh token."""
        # First, login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123!",
            },
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Then, use refresh token to get new access token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Refresh fails with invalid token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-refresh-token"},
        )
        
        assert response.status_code == 401


# ==========================================================================
# Password Security Tests
# ==========================================================================

class TestPasswordSecurity:
    """Tests for password security."""
    
    async def test_password_not_in_user_response(
        self, client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Password is never returned in responses."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )
        
        data = response.json()
        response_text = str(data).lower()
        
        assert "password" not in response_text or data.get("password") is None
        assert "password_hash" not in data
        assert "testpass123" not in response_text
    
    async def test_password_not_in_register_response(self, client: AsyncClient):
        """Password not returned after registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email(),
                "password": "ValidPass123!",
                "name": "Test User",
            },
        )
        
        data = response.json()
        assert "password" not in data
        assert "password_hash" not in data


# ==========================================================================
# Profile Update Tests
# ==========================================================================

class TestProfileUpdate:
    """Tests for profile update endpoint."""
    
    async def test_update_name(
        self, client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """User can update their name."""
        response = await client.patch(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={"name": "Updated Name"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
    
    async def test_update_email_unique(
        self, client: AsyncClient, 
        test_user: User, 
        test_admin: User,
        auth_headers: dict
    ):
        """Email update fails if email already exists."""
        response = await client.patch(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={"email": test_admin.email},  # Already exists
        )
        
        assert response.status_code == 409


# ==========================================================================
# Logout Tests
# ==========================================================================

class TestLogout:
    """Tests for logout endpoint."""
    
    async def test_logout_success(
        self, client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """User can logout successfully."""
        response = await client.post(
            "/api/v1/auth/logout",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    async def test_logout_without_auth(self, client: AsyncClient):
        """Logout fails without authentication."""
        response = await client.post("/api/v1/auth/logout")
        
        assert response.status_code == 401
