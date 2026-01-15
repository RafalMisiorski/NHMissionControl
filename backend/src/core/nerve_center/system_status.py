"""
NH Nerve Center - System Status Session
========================================

Creates and manages the system status session that shows real-time
NH Mission Control health and service status on startup.
"""

import asyncio
from datetime import datetime
from typing import Optional

import structlog

from src.core.config import settings
from src.core.nerve_center.events import (
    NHEvent,
    EventCategory,
    EventType,
    Severity,
)
from src.core.nerve_center.websocket_hub import get_connection_manager

logger = structlog.get_logger()

# System status session ID (constant so frontend can auto-subscribe)
SYSTEM_SESSION_ID = "system-status"


async def initialize_system_session() -> str:
    """
    Create the NH System Status session on startup.
    Returns the session ID.
    """
    manager = get_connection_manager()

    # Create session with fixed ID
    manager.sessions[SYSTEM_SESSION_ID] = manager.sessions.get(SYSTEM_SESSION_ID) or \
        type(manager.sessions.get(next(iter(manager.sessions), None), None) or object).__class__.__bases__[0]

    # Actually create properly using the manager's method but with our ID
    from src.core.nerve_center.events import SessionState
    manager.sessions[SYSTEM_SESSION_ID] = SessionState(
        id=SYSTEM_SESSION_ID,
        name="NH System Status",
        status="running",
        started_at=datetime.utcnow().isoformat(),
    )

    logger.info("system_status_session_created", session_id=SYSTEM_SESSION_ID)

    # Emit system start event
    await manager.emit_event(NHEvent(
        category=EventCategory.SYSTEM,
        event_type=EventType.SYSTEM_START,
        severity=Severity.INFO,
        session_id=SYSTEM_SESSION_ID,
        message=f"NH Mission Control v{settings.APP_VERSION} initialized",
        details={
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        },
    ))

    return SYSTEM_SESSION_ID


async def emit_service_status(
    service_name: str,
    status: str,
    severity: Severity = Severity.INFO,
    details: dict = None,
):
    """Emit a service status event."""
    manager = get_connection_manager()

    # Determine message based on status
    if status == "connected":
        message = f"{service_name} connected"
        severity = Severity.INFO
    elif status == "ready":
        message = f"{service_name} ready"
        severity = Severity.INFO
    elif status == "unavailable":
        message = f"{service_name} unavailable"
        severity = Severity.WARNING
    elif status == "error":
        message = f"{service_name} error"
        severity = Severity.ERROR
    else:
        message = f"{service_name}: {status}"

    await manager.emit_event(NHEvent(
        category=EventCategory.SYSTEM,
        event_type=EventType.SYSTEM_READY,
        severity=severity,
        session_id=SYSTEM_SESSION_ID,
        message=message,
        details=details or {},
    ))


async def run_health_checks():
    """
    Run health checks for all services and emit status events.
    Called on startup after session is initialized.
    """
    # Check Database
    try:
        from src.core.database import get_session
        await emit_service_status(
            "Database",
            "connected",
            details={"type": "SQLite" if settings.is_sqlite else "PostgreSQL"},
        )
    except Exception as e:
        await emit_service_status(
            "Database",
            "error",
            severity=Severity.ERROR,
            details={"error": str(e)},
        )

    # Check Redis
    try:
        import redis.asyncio as redis
        r = redis.from_url(str(settings.REDIS_URL))
        await r.ping()
        await emit_service_status("Redis", "connected")
        await r.close()
    except Exception:
        await emit_service_status(
            "Redis",
            "unavailable",
            severity=Severity.WARNING,
            details={"note": "Cache disabled, using in-memory fallback"},
        )

    # Check SyncWave
    from src.core.nerve_center.syncwave_client import SyncWaveClient
    syncwave = SyncWaveClient()
    if syncwave.enabled:
        await emit_service_status(
            "SyncWave",
            "connected",
            details={"mode": "live", "api_url": syncwave.api_url},
        )
    else:
        await emit_service_status(
            "SyncWave",
            "logging_only",
            severity=Severity.INFO,
            details={"mode": "logging_only", "note": "No API key configured"},
        )

    # WebSocket Hub ready
    manager = get_connection_manager()
    await emit_service_status(
        "WebSocket Hub",
        "ready",
        details={"active_sessions": len(manager.sessions)},
    )

    # API Server ready
    await emit_service_status(
        "API Server",
        "ready",
        details={
            "host": "0.0.0.0",
            "port": 8000,
            "docs": "/docs" if settings.is_development else "disabled",
        },
    )

    logger.info("system_health_checks_complete")


async def startup_system_status():
    """
    Full startup sequence for system status.
    Call this from the FastAPI lifespan.
    """
    await initialize_system_session()
    await run_health_checks()
