"""
NH Mission Control - Test Fixtures
===================================

Shared pytest fixtures for all tests.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.main import app
from src.core.config import settings
from src.core.database import Base, get_db
from src.core.models import User, UserRole
from src.api.deps import create_access_token


# ==========================================================================
# Test Database Setup
# ==========================================================================

# Use in-memory SQLite for tests (fast)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ==========================================================================
# Event Loop Fixture
# ==========================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==========================================================================
# Database Fixtures
# ==========================================================================

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a clean database session for each test.
    
    Creates all tables before test, drops after.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide test HTTP client with database override.
    """
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


# ==========================================================================
# User Fixtures
# ==========================================================================

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """
    Create a test user.
    
    Password: TestPass123!
    """
    from passlib.hash import bcrypt
    
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash=bcrypt.hash("TestPass123!"),
        name="Test User",
        role=UserRole.USER,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """
    Create a test admin user.
    
    Password: AdminPass123!
    """
    from passlib.hash import bcrypt
    
    user = User(
        id=uuid4(),
        email="admin@example.com",
        password_hash=bcrypt.hash("AdminPass123!"),
        name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def inactive_user(db_session: AsyncSession) -> User:
    """Create an inactive test user."""
    from passlib.hash import bcrypt
    
    user = User(
        id=uuid4(),
        email="inactive@example.com",
        password_hash=bcrypt.hash("TestPass123!"),
        name="Inactive User",
        role=UserRole.USER,
        is_active=False,
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def unverified_user(db_session: AsyncSession) -> User:
    """Create a user with unverified email."""
    from passlib.hash import bcrypt
    
    user = User(
        id=uuid4(),
        email="unverified@example.com",
        password_hash=bcrypt.hash("TestPass123!"),
        name="Unverified User",
        role=UserRole.USER,
        is_active=True,
        email_verified=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ==========================================================================
# Auth Fixtures
# ==========================================================================

@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """Get authorization headers for test user."""
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(test_admin: User) -> dict[str, str]:
    """Get authorization headers for admin user."""
    token = create_access_token(test_admin.id)
    return {"Authorization": f"Bearer {token}"}


# ==========================================================================
# Helper Functions
# ==========================================================================

def unique_email() -> str:
    """Generate a unique email for tests."""
    return f"test_{uuid4().hex[:8]}@example.com"


# ==========================================================================
# Test Markers
# ==========================================================================

# Mark all tests as async by default
pytestmark = pytest.mark.asyncio
