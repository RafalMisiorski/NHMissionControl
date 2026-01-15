"""
CC Session Manager
==================

Manages Claude Code sessions with visibility and reliability.

Key features:
1. Each task runs in its own terminal session
2. Output is streamed to Nerve Center in real-time
3. Watchdog monitors health and restarts crashed sessions
4. Context is preserved across restarts
5. Cross-platform: Windows (pywinpty) and Linux (tmux)

EPOCH 8 - Visibility & Reliability
"""

import asyncio
import os
import platform
import re
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Callable, Dict, List, Any
from uuid import uuid4

import structlog

from src.core.models import CCSession, CCSessionStatus, CCSessionPlatform, CCSessionOutput
from src.core.nerve_center.events import EventBuilder, NHEvent

logger = structlog.get_logger()


# ==========================================================================
# Completion Detection Patterns
# ==========================================================================

COMPLETION_PATTERNS = [
    r"✓.*completed",
    r"Task completed",
    r"Done\.",
    r"I've finished",
    r"All tests pass",
    r"Successfully",
    r"Changes saved",
    r"Commit.*created",
    r"Build succeeded",
    r"No errors found",
]

ERROR_PATTERNS = [
    r"Error:",
    r"error\[",
    r"FAILED",
    r"Exception:",
    r"Traceback",
    r"fatal:",
    r"panic:",
    r"ENOENT",
    r"Permission denied",
]


# ==========================================================================
# Session Backend Interface
# ==========================================================================

class SessionBackend(ABC):
    """Abstract interface for terminal session management."""

    @abstractmethod
    async def create_session(
        self,
        session_name: str,
        working_dir: str,
        output_file: str,
    ) -> str:
        """Create a new terminal session. Returns process handle."""
        pass

    @abstractmethod
    async def send_keys(self, process_handle: str, keys: str) -> None:
        """Send keystrokes to the session."""
        pass

    @abstractmethod
    async def get_screen_content(self, process_handle: str) -> str:
        """Get current visible screen content."""
        pass

    @abstractmethod
    async def is_alive(self, process_handle: str) -> bool:
        """Check if session process is still running."""
        pass

    @abstractmethod
    async def kill_session(self, process_handle: str) -> None:
        """Kill the session process."""
        pass

    @abstractmethod
    def get_attach_command(self, process_handle: str) -> str:
        """Get command to manually attach to session."""
        pass


# ==========================================================================
# Windows Backend (pywinpty/subprocess)
# ==========================================================================

class WindowsBackend(SessionBackend):
    """
    Windows terminal session management.

    Uses subprocess with ConPTY for terminal emulation.
    Output is captured via pipe redirection.
    """

    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.output_files: Dict[str, str] = {}

    async def create_session(
        self,
        session_name: str,
        working_dir: str,
        output_file: str,
    ) -> str:
        """Create Windows terminal session."""

        # Use cmd.exe as shell wrapper
        # This allows us to capture output properly
        process_handle = f"win-{session_name}"

        # Create batch script to run claude and capture output
        batch_script = f"""
@echo off
cd /d "{working_dir}"
echo [CC Session Started: {session_name}]
echo Working Directory: %CD%
echo.
"""

        batch_file = Path(tempfile.gettempdir()) / f"cc_session_{session_name}.bat"
        batch_file.write_text(batch_script)

        # Start process with output redirect
        proc = subprocess.Popen(
            ["cmd.exe", "/k", str(batch_file)],
            stdin=subprocess.PIPE,
            stdout=open(output_file, "w"),
            stderr=subprocess.STDOUT,
            cwd=working_dir,
            creationflags=subprocess.CREATE_NEW_CONSOLE if platform.system() == "Windows" else 0,
        )

        self.processes[process_handle] = proc
        self.output_files[process_handle] = output_file

        logger.info("Windows session created", session_name=session_name, pid=proc.pid)
        return process_handle

    async def send_keys(self, process_handle: str, keys: str) -> None:
        """Send input to Windows process."""
        proc = self.processes.get(process_handle)
        if proc and proc.stdin:
            try:
                proc.stdin.write((keys + "\n").encode())
                proc.stdin.flush()
            except Exception as e:
                logger.error("Failed to send keys", process_handle=process_handle, error=str(e))

    async def get_screen_content(self, process_handle: str) -> str:
        """Get recent output from Windows process."""
        output_file = self.output_files.get(process_handle)
        if output_file and os.path.exists(output_file):
            try:
                with open(output_file, "r", errors="replace") as f:
                    lines = f.readlines()
                    return "".join(lines[-50:])  # Last 50 lines
            except Exception as e:
                logger.error("Failed to read output", error=str(e))
        return ""

    async def is_alive(self, process_handle: str) -> bool:
        """Check if Windows process is running."""
        proc = self.processes.get(process_handle)
        return proc is not None and proc.poll() is None

    async def kill_session(self, process_handle: str) -> None:
        """Kill Windows process."""
        proc = self.processes.get(process_handle)
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            finally:
                self.processes.pop(process_handle, None)
                self.output_files.pop(process_handle, None)

    def get_attach_command(self, process_handle: str) -> str:
        """Get command to view output on Windows."""
        output_file = self.output_files.get(process_handle)
        if output_file:
            return f'type "{output_file}" | more'
        return "N/A"


# ==========================================================================
# Linux/WSL Backend (tmux)
# ==========================================================================

class TmuxBackend(SessionBackend):
    """
    Linux/WSL terminal session management using tmux.

    Each session runs in a dedicated tmux session with
    output piped to a log file.
    """

    async def create_session(
        self,
        session_name: str,
        working_dir: str,
        output_file: str,
    ) -> str:
        """Create tmux session."""

        # Create tmux session
        proc = await asyncio.create_subprocess_exec(
            "tmux", "new-session", "-d", "-s", session_name, "-c", working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        # Enable output logging via pipe-pane
        proc = await asyncio.create_subprocess_exec(
            "tmux", "pipe-pane", "-t", session_name, f"cat >> {output_file}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        logger.info("Tmux session created", session_name=session_name)
        return session_name  # tmux session name is the handle

    async def send_keys(self, process_handle: str, keys: str) -> None:
        """Send keys to tmux session."""
        proc = await asyncio.create_subprocess_exec(
            "tmux", "send-keys", "-t", process_handle, keys, "Enter",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

    async def get_screen_content(self, process_handle: str) -> str:
        """Capture tmux pane content."""
        proc = await asyncio.create_subprocess_exec(
            "tmux", "capture-pane", "-t", process_handle, "-p",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode() if stdout else ""

    async def is_alive(self, process_handle: str) -> bool:
        """Check if tmux session exists."""
        proc = await asyncio.create_subprocess_exec(
            "tmux", "has-session", "-t", process_handle,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0

    async def kill_session(self, process_handle: str) -> None:
        """Kill tmux session."""
        proc = await asyncio.create_subprocess_exec(
            "tmux", "kill-session", "-t", process_handle,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

    def get_attach_command(self, process_handle: str) -> str:
        """Get tmux attach command."""
        return f"tmux attach -t {process_handle}"


# ==========================================================================
# CC Session State (In-Memory)
# ==========================================================================

@dataclass
class CCSessionState:
    """In-memory state for an active CC session."""

    session_id: str
    session_name: str
    process_handle: str
    working_directory: str
    output_file: str

    # Status
    status: CCSessionStatus = CCSessionStatus.IDLE

    # Pipeline context
    pipeline_run_id: Optional[str] = None
    stage_id: Optional[str] = None
    task_prompt: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None

    # Output tracking
    last_output_line: int = 0
    output_lines: List[str] = field(default_factory=list)

    # Restart tracking
    restart_count: int = 0
    max_restarts: int = 3
    parent_session_id: Optional[str] = None

    # Configuration
    dangerous_mode: bool = True
    max_runtime_minutes: int = 25
    heartbeat_timeout_seconds: int = 60


# ==========================================================================
# CC Session Manager
# ==========================================================================

class CCSessionManager:
    """
    Manages Claude Code sessions with visibility and reliability.

    Features:
    - Spawn CC in terminal sessions
    - Stream output to Nerve Center
    - Watchdog for health monitoring
    - Auto-restart on crash/timeout
    - Context preservation across restarts
    """

    def __init__(
        self,
        db_session,
        emit_event: Callable[[NHEvent], Any],
        backend: Optional[SessionBackend] = None,
    ):
        self.db = db_session
        self.emit_event = emit_event

        # Auto-detect platform and choose backend
        if backend:
            self.backend = backend
        elif platform.system() == "Windows":
            self.backend = WindowsBackend()
            self.platform = CCSessionPlatform.WINDOWS
        else:
            self.backend = TmuxBackend()
            self.platform = CCSessionPlatform.LINUX

        # Active sessions (in-memory)
        self.sessions: Dict[str, CCSessionState] = {}

        # Watchdog task
        self._watchdog_task: Optional[asyncio.Task] = None
        self._watchdog_running = False

        logger.info("CCSessionManager initialized", platform=self.platform.value)

    async def start_watchdog(self):
        """Start the watchdog monitoring task."""
        if self._watchdog_running:
            return

        self._watchdog_running = True
        self._watchdog_task = asyncio.create_task(self._watchdog_loop())
        logger.info("Watchdog started")

    async def stop_watchdog(self):
        """Stop the watchdog monitoring task."""
        self._watchdog_running = False
        if self._watchdog_task:
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                pass
        logger.info("Watchdog stopped")

    async def create_session(
        self,
        session_id: str,
        working_directory: str,
        pipeline_run_id: Optional[str] = None,
        stage_id: Optional[str] = None,
        max_runtime_minutes: int = 25,
        max_restarts: int = 3,
    ) -> CCSessionState:
        """
        Create a new CC session.

        Args:
            session_id: Unique identifier for this session
            working_directory: Directory where CC will run
            pipeline_run_id: Optional pipeline run ID
            stage_id: Optional pipeline stage
            max_runtime_minutes: Auto-restart threshold (default 25min)
            max_restarts: Maximum restart attempts (default 3)

        Returns:
            CCSessionState for the new session
        """
        session_name = f"cc-{session_id[:8]}"
        output_file = os.path.join(
            tempfile.gettempdir(),
            f"cc-output-{session_id}.log"
        )

        # Ensure output file exists
        Path(output_file).touch()

        # Create terminal session via backend
        process_handle = await self.backend.create_session(
            session_name=session_name,
            working_dir=working_directory,
            output_file=output_file,
        )

        # Create in-memory state
        state = CCSessionState(
            session_id=session_id,
            session_name=session_name,
            process_handle=process_handle,
            working_directory=working_directory,
            output_file=output_file,
            pipeline_run_id=pipeline_run_id,
            stage_id=stage_id,
            max_runtime_minutes=max_runtime_minutes,
            max_restarts=max_restarts,
        )

        self.sessions[session_id] = state

        # Emit event
        await self.emit_event(EventBuilder.cc_session_created(
            cc_session_id=session_id,
            session_name=session_name,
            working_directory=working_directory,
            platform=self.platform.value,
            pipeline_run_id=pipeline_run_id,
            stage_id=stage_id,
        ))

        logger.info(
            "CC Session created",
            session_id=session_id,
            session_name=session_name,
            working_directory=working_directory,
        )

        return state

    async def send_task(
        self,
        session_id: str,
        task_prompt: str,
        dangerous_mode: bool = True,
    ) -> None:
        """
        Send a task to the CC session.

        This starts Claude Code and sends the task prompt.

        Args:
            session_id: Session to send task to
            task_prompt: The task/prompt to execute
            dangerous_mode: Use --dangerously-skip-permissions
        """
        state = self.sessions.get(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")

        # Build CC command
        cc_cmd = "claude"
        if dangerous_mode:
            cc_cmd += " --dangerously-skip-permissions"
        cc_cmd += f' -p "{task_prompt.replace(chr(34), chr(39))}"'

        # Send to terminal
        await self.backend.send_keys(state.process_handle, cc_cmd)

        # Update state
        state.status = CCSessionStatus.RUNNING
        state.started_at = datetime.now(timezone.utc)
        state.last_heartbeat = datetime.now(timezone.utc)
        state.task_prompt = task_prompt
        state.dangerous_mode = dangerous_mode

        # Emit event
        await self.emit_event(EventBuilder.cc_session_started(
            cc_session_id=session_id,
            session_name=state.session_name,
            task_prompt_preview=task_prompt,
            dangerous_mode=dangerous_mode,
        ))

        # Start output streaming
        asyncio.create_task(self._stream_output(session_id))

        logger.info(
            "Task sent to CC session",
            session_id=session_id,
            task_preview=task_prompt[:100],
        )

    async def send_command(self, session_id: str, command: str) -> None:
        """
        Send a command/input to the CC session.

        Use this to interact with CC (e.g., answer prompts, type "continue").
        """
        state = self.sessions.get(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")

        await self.backend.send_keys(state.process_handle, command)

        await self.emit_event(EventBuilder.cc_command_sent(
            cc_session_id=session_id,
            session_name=state.session_name,
            command=command,
        ))

    async def get_output(self, session_id: str, tail: int = 100) -> List[str]:
        """Get recent output lines from session."""
        state = self.sessions.get(session_id)
        if not state:
            return []

        return state.output_lines[-tail:]

    async def get_screen(self, session_id: str) -> str:
        """Get current visible screen content."""
        state = self.sessions.get(session_id)
        if not state:
            return ""

        return await self.backend.get_screen_content(state.process_handle)

    def get_attach_command(self, session_id: str) -> str:
        """Get command to manually attach to session."""
        state = self.sessions.get(session_id)
        if not state:
            return "N/A"

        return self.backend.get_attach_command(state.process_handle)

    async def kill_session(self, session_id: str) -> None:
        """Kill a CC session."""
        state = self.sessions.get(session_id)
        if not state:
            return

        await self.backend.kill_session(state.process_handle)
        state.status = CCSessionStatus.CRASHED

        logger.info("Session killed", session_id=session_id)

    async def wait_for_completion(
        self,
        session_id: str,
        timeout: timedelta = timedelta(minutes=30),
        poll_interval: float = 2.0,
    ) -> bool:
        """
        Wait for session to complete.

        Returns True if completed successfully, False otherwise.
        """
        state = self.sessions.get(session_id)
        if not state:
            return False

        deadline = datetime.now(timezone.utc) + timeout

        while datetime.now(timezone.utc) < deadline:
            if state.status == CCSessionStatus.COMPLETED:
                return True
            if state.status in (CCSessionStatus.FAILED, CCSessionStatus.CRASHED):
                return False

            await asyncio.sleep(poll_interval)

        return False

    async def _stream_output(self, session_id: str) -> None:
        """Stream output from session to Nerve Center."""
        state = self.sessions.get(session_id)
        if not state:
            return

        while state.status == CCSessionStatus.RUNNING:
            try:
                # Read new output
                if os.path.exists(state.output_file):
                    with open(state.output_file, "r", errors="replace") as f:
                        lines = f.readlines()

                    # Process new lines
                    new_lines = lines[state.last_output_line:]
                    for line in new_lines:
                        line = line.rstrip()
                        if not line:
                            continue

                        state.output_lines.append(line)
                        state.last_output_line += 1
                        state.last_heartbeat = datetime.now(timezone.utc)

                        # Check for errors
                        is_error = any(
                            re.search(pat, line, re.IGNORECASE)
                            for pat in ERROR_PATTERNS
                        )

                        # Emit output event
                        await self.emit_event(EventBuilder.cc_output_line(
                            cc_session_id=session_id,
                            session_name=state.session_name,
                            line_number=state.last_output_line,
                            content=line,
                            is_error=is_error,
                        ))

                        # Check for completion
                        if self._detect_completion(line):
                            state.status = CCSessionStatus.COMPLETED
                            await self._handle_completion(state)
                            return

                await asyncio.sleep(0.5)  # Poll every 500ms

            except Exception as e:
                logger.error("Output streaming error", error=str(e))
                await asyncio.sleep(2)

    def _detect_completion(self, line: str) -> bool:
        """Check if line indicates task completion."""
        for pattern in COMPLETION_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False

    async def _handle_completion(self, state: CCSessionState) -> None:
        """Handle successful completion of session."""
        duration = 0.0
        if state.started_at:
            duration = (datetime.now(timezone.utc) - state.started_at).total_seconds()

        await self.emit_event(EventBuilder.cc_session_completed(
            cc_session_id=state.session_id,
            session_name=state.session_name,
            duration_seconds=duration,
            output_lines=len(state.output_lines),
        ))

        logger.info(
            "CC Session completed",
            session_id=state.session_id,
            duration_seconds=duration,
            output_lines=len(state.output_lines),
        )

    async def _watchdog_loop(self) -> None:
        """Main watchdog loop that monitors all sessions."""
        while self._watchdog_running:
            try:
                now = datetime.now(timezone.utc)

                for session_id, state in list(self.sessions.items()):
                    if state.status != CCSessionStatus.RUNNING:
                        continue

                    # Check if process is alive
                    if not await self.backend.is_alive(state.process_handle):
                        await self._handle_crash(state)
                        continue

                    # Check heartbeat timeout
                    if state.last_heartbeat:
                        seconds_since_heartbeat = (now - state.last_heartbeat).total_seconds()
                        if seconds_since_heartbeat > state.heartbeat_timeout_seconds:
                            await self._handle_stuck(state, seconds_since_heartbeat)
                            continue

                    # Check max runtime
                    if state.started_at:
                        runtime_minutes = (now - state.started_at).total_seconds() / 60

                        # Warning at 80% of max runtime
                        if runtime_minutes > state.max_runtime_minutes * 0.8:
                            await self.emit_event(EventBuilder.cc_runtime_warning(
                                cc_session_id=state.session_id,
                                session_name=state.session_name,
                                runtime_minutes=runtime_minutes,
                                max_runtime_minutes=state.max_runtime_minutes,
                            ))

                        # Restart at max runtime
                        if runtime_minutes >= state.max_runtime_minutes:
                            await self._handle_runtime_limit(state)
                            continue

                    # Emit heartbeat
                    await self.emit_event(EventBuilder.cc_heartbeat(
                        cc_session_id=state.session_id,
                        session_name=state.session_name,
                        runtime_seconds=(now - state.started_at).total_seconds() if state.started_at else 0,
                        output_lines=len(state.output_lines),
                    ))

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error("Watchdog error", error=str(e))
                await asyncio.sleep(5)

    async def _handle_crash(self, state: CCSessionState) -> None:
        """Handle session process crash."""
        state.status = CCSessionStatus.CRASHED

        await self.emit_event(EventBuilder.cc_session_crashed(
            cc_session_id=state.session_id,
            session_name=state.session_name,
            last_output="".join(state.output_lines[-20:]),
        ))

        logger.warning(
            "CC Session crashed",
            session_id=state.session_id,
        )

        # Attempt restart
        if state.restart_count < state.max_restarts:
            await self._restart_session(state, "Process crashed")

    async def _handle_stuck(self, state: CCSessionState, seconds_since_output: float) -> None:
        """Handle session that appears stuck."""
        await self.emit_event(EventBuilder.cc_session_stuck(
            cc_session_id=state.session_id,
            session_name=state.session_name,
            seconds_since_output=seconds_since_output,
        ))

        logger.warning(
            "CC Session stuck",
            session_id=state.session_id,
            seconds_since_output=seconds_since_output,
        )

        # Try sending "continue" nudge
        try:
            await self.send_command(state.session_id, "continue")
            state.last_heartbeat = datetime.now(timezone.utc)
            await asyncio.sleep(30)  # Wait for response

            # If still stuck, restart
            if state.status == CCSessionStatus.RUNNING:
                now = datetime.now(timezone.utc)
                if state.last_heartbeat:
                    seconds = (now - state.last_heartbeat).total_seconds()
                    if seconds > state.heartbeat_timeout_seconds:
                        state.status = CCSessionStatus.STUCK
                        if state.restart_count < state.max_restarts:
                            await self._restart_session(state, "Session stuck (no response to nudge)")
        except Exception as e:
            logger.error("Failed to nudge stuck session", error=str(e))

    async def _handle_runtime_limit(self, state: CCSessionState) -> None:
        """Handle session reaching runtime limit."""
        logger.warning(
            "CC Session reached runtime limit",
            session_id=state.session_id,
            max_runtime_minutes=state.max_runtime_minutes,
        )

        if state.restart_count < state.max_restarts:
            await self._restart_session(state, "Runtime limit reached (preemptive restart)")
        else:
            state.status = CCSessionStatus.FAILED
            await self.emit_event(EventBuilder.cc_session_failed(
                cc_session_id=state.session_id,
                session_name=state.session_name,
                error="Max restarts exceeded",
            ))

    async def _restart_session(self, state: CCSessionState, reason: str) -> None:
        """Restart a session with context preserved."""
        state.restart_count += 1

        await self.emit_event(EventBuilder.cc_session_restarting(
            cc_session_id=state.session_id,
            session_name=state.session_name,
            reason=reason,
            restart_count=state.restart_count,
            max_restarts=state.max_restarts,
        ))

        # Kill old session
        try:
            await self.backend.kill_session(state.process_handle)
        except Exception as e:
            logger.error("Failed to kill old session", error=str(e))

        # Get context from last output
        context_lines = state.output_lines[-50:] if state.output_lines else []
        context = "\n".join(context_lines)

        # Create new session
        new_session_id = f"{state.session_id}-r{state.restart_count}"
        new_state = await self.create_session(
            session_id=new_session_id,
            working_directory=state.working_directory,
            pipeline_run_id=state.pipeline_run_id,
            stage_id=state.stage_id,
            max_runtime_minutes=state.max_runtime_minutes,
            max_restarts=state.max_restarts - state.restart_count,
        )

        new_state.parent_session_id = state.session_id
        new_state.restart_count = state.restart_count

        # Build restart prompt with context
        restart_prompt = f"""
Continue the previous task from where it was interrupted.

Previous context (last 50 lines of output):
---
{context}
---

Original task: {state.task_prompt or 'Continue from context'}

Please continue from where you stopped. Do not repeat completed work.
"""

        # Send task to new session
        await self.send_task(
            new_state.session_id,
            restart_prompt,
            state.dangerous_mode,
        )

        await self.emit_event(EventBuilder.cc_session_restarted(
            old_session_id=state.session_id,
            new_session_id=new_session_id,
            new_session_name=new_state.session_name,
            context_lines=len(context_lines),
        ))

        # Update old state
        state.status = CCSessionStatus.RESTARTING

        logger.info(
            "CC Session restarted",
            old_session_id=state.session_id,
            new_session_id=new_session_id,
            restart_count=state.restart_count,
        )

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions."""
        return [
            {
                "session_id": s.session_id,
                "session_name": s.session_name,
                "status": s.status.value,
                "pipeline_run_id": s.pipeline_run_id,
                "stage_id": s.stage_id,
                "working_directory": s.working_directory,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "runtime_seconds": (datetime.now(timezone.utc) - s.started_at).total_seconds() if s.started_at else 0,
                "output_lines": len(s.output_lines),
                "restart_count": s.restart_count,
                "attach_command": self.backend.get_attach_command(s.process_handle),
            }
            for s in self.sessions.values()
        ]
