"""
NH Mission Control - Database Connection
=========================================

Async SQLAlchemy setup with connection pooling.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# ==========================================================================
# Engine Setup
# ==========================================================================

def create_engine() -> AsyncEngine:
    """Create async database engine with connection pooling."""
    # SQLite doesn't support pool_size/max_overflow
    if settings.is_sqlite:
        return create_async_engine(
            str(settings.DATABASE_URL),
            echo=settings.DATABASE_ECHO,
            connect_args={"check_same_thread": False},
        )
    else:
        return create_async_engine(
            str(settings.DATABASE_URL),
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            echo=settings.DATABASE_ECHO,
            pool_pre_ping=True,  # Verify connections before use
        )


engine = create_engine()


# ==========================================================================
# Session Factory
# ==========================================================================

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ==========================================================================
# Session Dependencies
# ==========================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.
    
    Usage:
        async with get_db_session() as session:
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ==========================================================================
# Lifecycle
# ==========================================================================

async def init_db() -> None:
    """Initialize database (create tables if not exist)."""
    async with engine.begin() as conn:
        # Import all models to register them
        from src.core import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
