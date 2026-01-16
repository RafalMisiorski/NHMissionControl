"""
CC Sessions API Routes (EPOCH 8 + EPOCH 9 Interactive Mode)
============================================================

REST and WebSocket endpoints for Claude Code session management.

Headless Endpoints (EPOCH 8):
- GET    /api/v1/cc-sessions           - List all sessions
- POST   /api/v1/cc-sessions           - Create new headless session
- GET    /api/v1/cc-sessions/{id}      - Get session details
- POST   /api/v1/cc-sessions/{id}/task - Send task to session
- POST   /api/v1/cc-sessions/{id}/command - Send command/input
- GET    /api/v1/cc-sessions/{id}/output - Get session output
- GET    /api/v1/cc-sessions/{id}/screen - Get current screen
- POST   /api/v1/cc-sessions/{id}/restart - Force restart
- DELETE /api/v1/cc-sessions/{id}      - Kill session
- WS     /api/v1/cc-sessions/{id}/stream - Real-time output stream

Interactive Endpoints (EPOCH 9):
- POST   /api/v1/cc-sessions/interactive - Create interactive session
- POST   /api/v1/cc-sessions/{id}/prompt - Send prompt (interactive)
- POST   /api/v1/cc-sessions/{id}/input  - Send raw input (interactive)
- GET    /api/v1/cc-sessions/{id}/events - Get parsed events
"""

from typing import Optional, List, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.models import CCSessionStatus, CCSessionPlatform, CCSessionMode, CCEventType
from src.core.pipeline.cc_session_manager import CCSessionManager, CCSessionState
from src.core.nerve_center.events import EventBuilder, NHEvent

router = APIRouter(prefix="/api/v1/cc-sessions", tags=["cc-sessions"])


# ==========================================================================
# Schemas
# ==========================================================================

class CreateSessionRequest(BaseModel):
    """Request to create a new CC session."""
    working_directory: str = Field(..., description="Directory where CC will run")
    pipeline_run_id: Optional[str] = Field(None, description="Associated pipeline run ID")
    stage_id: Optional[str] = Field(None, description="Associated pipeline stage ID")
    max_runtime_minutes: int = Field(25, description="Auto-restart threshold (minutes)")
    max_restarts: int = Field(3, description="Maximum restart attempts")


class SendTaskRequest(BaseModel):
    """Request to send a task to CC session."""
    task_prompt: str = Field(..., description="The task/prompt to execute")
    dangerous_mode: bool = Field(True, description="Use --dangerously-skip-permissions")


class SendCommandRequest(BaseModel):
    """Request to send a command to CC session."""
    command: str = Field(..., description="Command/input to send")


class SessionResponse(BaseModel):
    """CC session response."""
    session_id: str
    session_name: str
    status: str
    platform: str
    working_directory: str
    pipeline_run_id: Optional[str]
    stage_id: Optional[str]
    task_prompt: Optional[str]
    dangerous_mode: bool
    started_at: Optional[str]
    runtime_seconds: float
    output_lines: int
    restart_count: int
    max_restarts: int
    max_runtime_minutes: int
    attach_command: str

    class Config:
        from_attributes = True


class OutputResponse(BaseModel):
    """Session output response."""
    session_id: str
    lines: List[str]
    total_lines: int


class ScreenResponse(BaseModel):
    """Session screen capture response."""
    session_id: str
    content: str


# ==========================================================================
# Interactive Session Schemas (EPOCH 9)
# ==========================================================================

class CreateInteractiveSessionRequest(BaseModel):
    """Request to create a new interactive CC session."""
    working_directory: str = Field(..., description="Directory where CC will run")
    pipeline_run_id: Optional[str] = Field(None, description="Associated pipeline run ID")
    stage_id: Optional[str] = Field(None, description="Associated pipeline stage ID")
    dangerous_mode: bool = Field(True, description="Use --dangerously-skip-permissions")


class SendPromptRequest(BaseModel):
    """Request to send a prompt to an interactive CC session."""
    prompt: str = Field(..., description="The prompt to send")


class SendInputRequest(BaseModel):
    """Request to send raw input to an interactive CC session."""
    text: str = Field(..., description="The input text to send")


class InteractiveSessionResponse(BaseModel):
    """Interactive CC session response."""
    session_id: str
    session_name: str
    status: str
    mode: str
    platform: str
    working_directory: str
    pipeline_run_id: Optional[str]
    stage_id: Optional[str]
    task_prompt: Optional[str]
    dangerous_mode: bool
    started_at: Optional[str]
    runtime_seconds: float
    output_lines: int
    prompt_count: int
    event_count: int

    class Config:
        from_attributes = True


class SessionEventResponse(BaseModel):
    """A parsed event from an interactive session."""
    event_id: str
    event_type: str
    timestamp: str
    tool_name: Optional[str]
    tool_input: Optional[Dict[str, Any]]
    tool_output: Optional[str]
    tool_duration_ms: Optional[int]
    content: Optional[str]
    is_error: bool
    error_type: Optional[str]
    line_start: Optional[int]
    line_end: Optional[int]


class EventsResponse(BaseModel):
    """Response containing parsed events from a session."""
    session_id: str
    events: List[SessionEventResponse]
    total_events: int
    tool_summary: Dict[str, int]
    error_summary: Dict[str, int]


# ==========================================================================
# Session Manager Singleton
# ==========================================================================

_session_manager: Optional[CCSessionManager] = None


async def get_session_manager(db: AsyncSession = Depends(get_db)) -> CCSessionManager:
    """Get or create the CC session manager singleton."""
    global _session_manager

    if _session_manager is None:
        async def emit_event(event: NHEvent):
            # For now, just log - will integrate with WebSocket hub later
            pass

        _session_manager = CCSessionManager(
            db_session=db,
            emit_event=emit_event,
        )
        await _session_manager.start_watchdog()

    return _session_manager


# ==========================================================================
# Helper Functions
# ==========================================================================

def _state_to_response(state: CCSessionState, attach_cmd: str) -> SessionResponse:
    """Convert CCSessionState to response model."""
    from datetime import datetime, timezone

    runtime = 0.0
    if state.started_at:
        runtime = (datetime.now(timezone.utc) - state.started_at).total_seconds()

    return SessionResponse(
        session_id=state.session_id,
        session_name=state.session_name,
        status=state.status.value,
        platform="windows",  # Will be updated when manager knows platform
        working_directory=state.working_directory,
        pipeline_run_id=state.pipeline_run_id,
        stage_id=state.stage_id,
        task_prompt=state.task_prompt,
        dangerous_mode=state.dangerous_mode,
        started_at=state.started_at.isoformat() if state.started_at else None,
        runtime_seconds=runtime,
        output_lines=len(state.output_lines),
        restart_count=state.restart_count,
        max_restarts=state.max_restarts,
        max_runtime_minutes=state.max_runtime_minutes,
        attach_command=attach_cmd,
    )


# ==========================================================================
# Endpoints
# ==========================================================================

@router.get("", response_model=List[SessionResponse])
async def list_sessions(
    status_filter: Optional[str] = None,
    pipeline_run_id: Optional[str] = None,
    manager: CCSessionManager = Depends(get_session_manager),
):
    """
    List all CC sessions.

    Args:
        status_filter: Filter by session status
        pipeline_run_id: Filter by pipeline run ID
    """
    sessions = manager.list_sessions()

    # Apply filters
    if status_filter:
        sessions = [s for s in sessions if s["status"] == status_filter]
    if pipeline_run_id:
        sessions = [s for s in sessions if s.get("pipeline_run_id") == pipeline_run_id]

    # Convert to response models
    return [
        SessionResponse(
            session_id=s["session_id"],
            session_name=s["session_name"],
            status=s["status"],
            platform=manager.platform.value if hasattr(manager, "platform") else "unknown",
            working_directory=s["working_directory"],
            pipeline_run_id=s.get("pipeline_run_id"),
            stage_id=s.get("stage_id"),
            task_prompt=None,  # Not exposed in list
            dangerous_mode=True,  # Default
            started_at=s.get("started_at"),
            runtime_seconds=s.get("runtime_seconds", 0),
            output_lines=s.get("output_lines", 0),
            restart_count=s.get("restart_count", 0),
            max_restarts=3,
            max_runtime_minutes=25,
            attach_command=s.get("attach_command", "N/A"),
        )
        for s in sessions
    ]


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    manager: CCSessionManager = Depends(get_session_manager),
):
    """
    Create a new CC session.

    Creates a terminal session ready to receive Claude Code tasks.
    """
    session_id = str(uuid4())

    state = await manager.create_session(
        session_id=session_id,
        working_directory=request.working_directory,
        pipeline_run_id=request.pipeline_run_id,
        stage_id=request.stage_id,
        max_runtime_minutes=request.max_runtime_minutes,
        max_restarts=request.max_restarts,
    )

    attach_cmd = manager.get_attach_command(session_id)
    return _state_to_response(state, attach_cmd)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    manager: CCSessionManager = Depends(get_session_manager),
):
    """Get details of a specific CC session."""
    state = manager.sessions.get(session_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    attach_cmd = manager.get_attach_command(session_id)
    return _state_to_response(state, attach_cmd)


@router.post("/{session_id}/task", response_model=SessionResponse)
async def send_task(
    session_id: str,
    request: SendTaskRequest,
    manager: CCSessionManager = Depends(get_session_manager),
):
    """
    Send a task to the CC session.

    Starts Claude Code with the given prompt.
    """
    state = manager.sessions.get(session_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    if state.status not in (CCSessionStatus.IDLE, CCSessionStatus.COMPLETED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is in {state.status.value} state. Create a new session for new tasks.",
        )

    await manager.send_task(
        session_id=session_id,
        task_prompt=request.task_prompt,
        dangerous_mode=request.dangerous_mode,
    )

    # Refresh state
    state = manager.sessions.get(session_id)
    attach_cmd = manager.get_attach_command(session_id)
    return _state_to_response(state, attach_cmd)


@router.post("/{session_id}/command", response_model=dict)
async def send_command(
    session_id: str,
    request: SendCommandRequest,
    manager: CCSessionManager = Depends(get_session_manager),
):
    """
    Send a command/input to the CC session.

    Use this to interact with CC (e.g., answer prompts, type "continue").
    """
    state = manager.sessions.get(session_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    await manager.send_command(session_id, request.command)

    return {"status": "sent", "command": request.command}


@router.get("/{session_id}/output", response_model=OutputResponse)
async def get_output(
    session_id: str,
    tail: int = 100,
    manager: CCSessionManager = Depends(get_session_manager),
):
    """
    Get recent output lines from session.

    Args:
        tail: Number of most recent lines to return (default 100)
    """
    state = manager.sessions.get(session_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    lines = await manager.get_output(session_id, tail=tail)

    return OutputResponse(
        session_id=session_id,
        lines=lines,
        total_lines=len(state.output_lines),
    )


@router.get("/{session_id}/screen", response_model=ScreenResponse)
async def get_screen(
    session_id: str,
    manager: CCSessionManager = Depends(get_session_manager),
):
    """
    Get current visible screen content.

    Returns the terminal screen as it would appear if attached.
    """
    state = manager.sessions.get(session_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    content = await manager.get_screen(session_id)

    return ScreenResponse(
        session_id=session_id,
        content=content,
    )


@router.post("/{session_id}/restart", response_model=SessionResponse)
async def restart_session(
    session_id: str,
    manager: CCSessionManager = Depends(get_session_manager),
):
    """
    Force restart a CC session.

    Preserves context from the last 50 lines of output.
    """
    state = manager.sessions.get(session_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    if state.restart_count >= state.max_restarts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Max restarts ({state.max_restarts}) reached",
        )

    # Trigger restart
    await manager._restart_session(state, "Manual restart requested")

    # Get new session state
    new_session_id = f"{state.session_id}-r{state.restart_count}"
    new_state = manager.sessions.get(new_session_id)

    if new_state:
        attach_cmd = manager.get_attach_command(new_session_id)
        return _state_to_response(new_state, attach_cmd)

    # Return old state if new not found
    attach_cmd = manager.get_attach_command(session_id)
    return _state_to_response(state, attach_cmd)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def kill_session(
    session_id: str,
    manager: CCSessionManager = Depends(get_session_manager),
):
    """Kill a CC session."""
    state = manager.sessions.get(session_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # Handle based on mode
    if state.mode == CCSessionMode.INTERACTIVE:
        await manager.kill_interactive_session(session_id)
    else:
        await manager.kill_session(session_id)


# ==========================================================================
# Interactive Session Endpoints (EPOCH 9)
# ==========================================================================

def _interactive_state_to_response(state: CCSessionState, platform: str) -> InteractiveSessionResponse:
    """Convert CCSessionState to interactive response model."""
    from datetime import datetime, timezone

    runtime = 0.0
    if state.started_at:
        runtime = (datetime.now(timezone.utc) - state.started_at).total_seconds()

    return InteractiveSessionResponse(
        session_id=state.session_id,
        session_name=state.session_name,
        status=state.status.value,
        mode=state.mode.value,
        platform=platform,
        working_directory=state.working_directory,
        pipeline_run_id=state.pipeline_run_id,
        stage_id=state.stage_id,
        task_prompt=state.task_prompt,
        dangerous_mode=state.dangerous_mode,
        started_at=state.started_at.isoformat() if state.started_at else None,
        runtime_seconds=runtime,
        output_lines=len(state.output_lines),
        prompt_count=state.prompt_count,
        event_count=len(state.parsed_events),
    )


@router.post("/interactive", response_model=InteractiveSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_interactive_session(
    request: CreateInteractiveSessionRequest,
    manager: CCSessionManager = Depends(get_session_manager),
):
    """
    Create a new interactive CC session.

    Unlike headless mode, interactive sessions:
    - Start Claude Code WITHOUT the -p flag
    - Allow multi-turn conversations
    - Preserve context across prompts
    - Parse tool calls and thinking in real-time
    """
    session_id = str(uuid4())

    try:
        state = await manager.create_interactive_session(
            session_id=session_id,
            working_directory=request.working_directory,
            pipeline_run_id=request.pipeline_run_id,
            stage_id=request.stage_id,
            dangerous_mode=request.dangerous_mode,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create interactive session: {str(e)}",
        )

    platform = manager.platform.value if hasattr(manager, "platform") else "unknown"
    return _interactive_state_to_response(state, platform)


@router.post("/{session_id}/prompt", response_model=InteractiveSessionResponse)
async def send_prompt(
    session_id: str,
    request: SendPromptRequest,
    manager: CCSessionManager = Depends(get_session_manager),
):
    """
    Send a prompt to an interactive CC session.

    Use this for multi-turn conversations. The session must be
    in interactive mode and in AWAITING_INPUT status.
    """
    state = manager.sessions.get(session_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    if state.mode != CCSessionMode.INTERACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session {session_id} is not in interactive mode. Use /task endpoint for headless mode.",
        )

    # Allow sending prompts in RUNNING state too (status detection may lag behind)
    if state.status not in (CCSessionStatus.AWAITING_INPUT, CCSessionStatus.IDLE, CCSessionStatus.RUNNING):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is in {state.status.value} state. Wait for session to be ready.",
        )

    try:
        await manager.send_prompt(session_id, request.prompt)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send prompt: {str(e)}",
        )

    # Refresh state
    state = manager.sessions.get(session_id)
    platform = manager.platform.value if hasattr(manager, "platform") else "unknown"
    return _interactive_state_to_response(state, platform)


@router.post("/{session_id}/input", response_model=dict)
async def send_input(
    session_id: str,
    request: SendInputRequest,
    manager: CCSessionManager = Depends(get_session_manager),
):
    """
    Send raw input to an interactive CC session.

    Use this for answering CC's questions or confirmations.
    Different from /prompt - this sends raw text without processing.
    """
    state = manager.sessions.get(session_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    if state.mode != CCSessionMode.INTERACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session {session_id} is not in interactive mode. Use /command endpoint for headless mode.",
        )

    try:
        await manager.send_interactive_input(session_id, request.text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send input: {str(e)}",
        )

    return {"status": "sent", "text": request.text}


@router.get("/{session_id}/events", response_model=EventsResponse)
async def get_events(
    session_id: str,
    event_type: Optional[str] = None,
    limit: int = 100,
    manager: CCSessionManager = Depends(get_session_manager),
):
    """
    Get parsed events from an interactive CC session.

    Events include tool calls, thinking blocks, errors, etc.
    Use this to monitor CC's actions at a granular level.

    Args:
        event_type: Filter by event type (e.g., "tool_call_start", "thinking", "error")
        limit: Maximum number of events to return (default 100)
    """
    state = manager.sessions.get(session_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # Parse event type filter
    event_types = None
    if event_type:
        try:
            event_types = [CCEventType(event_type)]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type: {event_type}. Valid types: {[e.value for e in CCEventType]}",
            )

    # Get events from manager
    events = await manager.get_session_events(
        session_id,
        event_types=event_types,
        limit=limit,
    )

    # Get summaries from event processor
    tool_summary = {}
    error_summary = {}
    if state.event_processor:
        tool_summary = state.event_processor.get_tool_summary()
        error_summary = state.event_processor.get_error_summary()

    return EventsResponse(
        session_id=session_id,
        events=[SessionEventResponse(**e) for e in events],
        total_events=len(state.parsed_events),
        tool_summary=tool_summary,
        error_summary=error_summary,
    )


@router.post("/{session_id}/stop", response_model=dict)
async def stop_interactive_session(
    session_id: str,
    manager: CCSessionManager = Depends(get_session_manager),
):
    """
    Gracefully stop an interactive CC session.

    This sends exit commands and waits for clean shutdown.
    Use DELETE endpoint for immediate termination.
    """
    state = manager.sessions.get(session_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    if state.mode != CCSessionMode.INTERACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session {session_id} is not in interactive mode.",
        )

    await manager.stop_interactive_session(session_id)

    return {
        "status": "stopped",
        "session_id": session_id,
        "final_status": state.status.value,
    }


# ==========================================================================
# WebSocket Endpoint for Real-time Output
# ==========================================================================

@router.websocket("/{session_id}/stream")
async def stream_output(
    websocket: WebSocket,
    session_id: str,
):
    """
    WebSocket endpoint for real-time output streaming.

    Streams output lines as they are captured from the CC session.

    Message format:
    {
        "type": "output" | "heartbeat" | "status_change" | "error",
        "data": {...}
    }
    """
    import asyncio
    from datetime import datetime, timezone

    await websocket.accept()

    # Get session manager (without dependency injection for WebSocket)
    if _session_manager is None:
        await websocket.send_json({
            "type": "error",
            "data": {"message": "Session manager not initialized"}
        })
        await websocket.close()
        return

    state = _session_manager.sessions.get(session_id)
    if not state:
        await websocket.send_json({
            "type": "error",
            "data": {"message": f"Session {session_id} not found"}
        })
        await websocket.close()
        return

    # Send initial state
    await websocket.send_json({
        "type": "status",
        "data": {
            "session_id": session_id,
            "session_name": state.session_name,
            "status": state.status.value,
            "output_lines": len(state.output_lines),
        }
    })

    # Send existing output
    for i, line in enumerate(state.output_lines):
        await websocket.send_json({
            "type": "output",
            "data": {
                "line_number": i + 1,
                "content": line,
            }
        })

    # Track last sent line
    last_sent_line = len(state.output_lines)
    last_status = state.status

    try:
        while True:
            # Check for new output
            current_lines = len(state.output_lines)
            if current_lines > last_sent_line:
                for i in range(last_sent_line, current_lines):
                    await websocket.send_json({
                        "type": "output",
                        "data": {
                            "line_number": i + 1,
                            "content": state.output_lines[i],
                        }
                    })
                last_sent_line = current_lines

            # Check for status change
            if state.status != last_status:
                await websocket.send_json({
                    "type": "status_change",
                    "data": {
                        "old_status": last_status.value,
                        "new_status": state.status.value,
                    }
                })
                last_status = state.status

                # Close on terminal states
                if state.status in (
                    CCSessionStatus.COMPLETED,
                    CCSessionStatus.FAILED,
                    CCSessionStatus.CRASHED,
                ):
                    await websocket.send_json({
                        "type": "close",
                        "data": {"reason": f"Session {state.status.value}"}
                    })
                    break

            # Send heartbeat
            await websocket.send_json({
                "type": "heartbeat",
                "data": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "runtime_seconds": (datetime.now(timezone.utc) - state.started_at).total_seconds() if state.started_at else 0,
                }
            })

            await asyncio.sleep(1)  # Poll every second

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"message": str(e)}
            })
        except:
            pass
