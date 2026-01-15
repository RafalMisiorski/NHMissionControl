"""
NH Mission Control - Nerve Center API
======================================

REST endpoints for Nerve Center session management.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.core.nerve_center import (
    get_connection_manager,
    SYSTEM_SESSION_ID,
)


router = APIRouter(prefix="/nerve-center", tags=["Nerve Center"])


# ==========================================================================
# Response Models
# ==========================================================================

class SessionSummary(BaseModel):
    """Summary of a session for listing."""
    id: str
    name: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    progress_percent: float
    total_tasks: int
    completed_tasks: int
    failed_tasks: int


class SessionListResponse(BaseModel):
    """Response for listing sessions."""
    sessions: List[SessionSummary]
    system_session_id: str


class SessionDetailResponse(BaseModel):
    """Detailed session information."""
    id: str
    name: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    progress_percent: float
    total_tokens_input: int
    total_tokens_output: int
    total_cost_usd: float
    files_read: List[str]
    files_written: List[str]
    files_created: List[str]
    event_count: int


# ==========================================================================
# Endpoints
# ==========================================================================

@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="List all active sessions",
)
async def list_sessions() -> SessionListResponse:
    """
    Get list of all active Nerve Center sessions.

    Returns the system status session ID for auto-subscription.
    """
    manager = get_connection_manager()

    sessions = []
    for session_id, session in manager.sessions.items():
        sessions.append(SessionSummary(
            id=session.id,
            name=session.name,
            status=session.status,
            started_at=session.started_at,
            completed_at=session.completed_at,
            progress_percent=session.progress_percent,
            total_tasks=session.total_tasks,
            completed_tasks=session.completed_tasks,
            failed_tasks=session.failed_tasks,
        ))

    return SessionListResponse(
        sessions=sessions,
        system_session_id=SYSTEM_SESSION_ID,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionDetailResponse,
    summary="Get session details",
)
async def get_session(session_id: str) -> SessionDetailResponse:
    """Get detailed information about a specific session."""
    manager = get_connection_manager()

    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )

    return SessionDetailResponse(
        id=session.id,
        name=session.name,
        status=session.status,
        started_at=session.started_at,
        completed_at=session.completed_at,
        total_tasks=session.total_tasks,
        completed_tasks=session.completed_tasks,
        failed_tasks=session.failed_tasks,
        progress_percent=session.progress_percent,
        total_tokens_input=session.total_tokens_input,
        total_tokens_output=session.total_tokens_output,
        total_cost_usd=session.total_cost_usd,
        files_read=session.files_read,
        files_written=session.files_written,
        files_created=session.files_created,
        event_count=len(session.events),
    )


@router.get(
    "/status",
    summary="Get Nerve Center status",
)
async def nerve_center_status() -> dict:
    """
    Get overall Nerve Center status.

    Returns connection counts and system health.
    """
    manager = get_connection_manager()

    return {
        "active_connections": len(manager.connections),
        "active_sessions": len(manager.sessions),
        "system_session_id": SYSTEM_SESSION_ID,
        "event_history_count": len(manager.event_history),
    }

class EventResponse(BaseModel):
    """Event data for API responses."""
    id: str
    timestamp: str
    category: str
    event_type: str
    severity: str
    message: str
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    details: dict = {}


@router.get(
    "/events",
    response_model=List[EventResponse],
    summary="Get recent events",
)
async def get_recent_events(limit: int = 20) -> List[EventResponse]:
    """Get recent events from event history."""
    manager = get_connection_manager()
    
    events = []
    for event in manager.event_history[-limit:]:
        events.append(EventResponse(
            id=event.id,
            timestamp=event.timestamp,
            category=event.category.value if hasattr(event.category, 'value') else str(event.category),
            event_type=event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
            severity=event.severity.value if hasattr(event.severity, 'value') else str(event.severity),
            message=event.message,
            session_id=event.session_id,
            agent_id=event.agent_id,
            details=event.details or {},
        ))
    
    return events
