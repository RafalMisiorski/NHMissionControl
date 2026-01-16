"""
Interactive PTY Backend for CC Sessions (EPOCH 9)
=================================================

Provides true interactive terminal sessions for Claude Code.
Unlike headless mode (-p flag), interactive mode keeps the session
alive for multi-turn conversations with full context preservation.

Key differences from headless:
- No -p flag - CC stays open
- User can send multiple prompts
- Context is preserved across prompts
- Can see CC's thinking in real-time
- Supports AWAITING_INPUT state
"""

import asyncio
import os
import platform
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, AsyncIterator, Callable, List, Any
from uuid import uuid4

import structlog

logger = structlog.get_logger()


# ==========================================================================
# Output Chunk Types
# ==========================================================================

@dataclass
class OutputChunk:
    """A chunk of output from the interactive session."""
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_error: bool = False
    raw_bytes: bytes = field(default_factory=bytes)


# ==========================================================================
# Interactive Backend Interface
# ==========================================================================

class InteractiveBackend(ABC):
    """
    Abstract interface for interactive PTY sessions.

    Unlike the headless SessionBackend, this maintains a persistent
    connection to Claude Code for multi-turn interactions.
    """

    @abstractmethod
    async def start(
        self,
        working_dir: str,
        dangerous_mode: bool = True,
    ) -> bool:
        """
        Start an interactive Claude Code session.

        Args:
            working_dir: Directory where CC will run
            dangerous_mode: Use --dangerously-skip-permissions

        Returns:
            True if session started successfully
        """
        pass

    @abstractmethod
    async def send_prompt(self, prompt: str) -> None:
        """
        Send a prompt to the running Claude session.

        Args:
            prompt: The prompt text to send
        """
        pass

    @abstractmethod
    async def send_input(self, text: str) -> None:
        """
        Send raw input (not a prompt) to the session.

        Use for responding to CC's questions, confirmations, etc.
        """
        pass

    @abstractmethod
    async def read_output(self) -> AsyncIterator[OutputChunk]:
        """
        Async iterator that yields output chunks as they arrive.

        This is the main way to stream CC's responses in real-time.
        """
        pass

    @abstractmethod
    async def is_alive(self) -> bool:
        """Check if the PTY process is still running."""
        pass

    @abstractmethod
    async def is_awaiting_input(self) -> bool:
        """Check if CC is waiting for user input."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the interactive session gracefully."""
        pass

    @abstractmethod
    async def kill(self) -> None:
        """Force kill the session."""
        pass

    @abstractmethod
    def get_full_output(self) -> str:
        """Get all accumulated output as a single string."""
        pass


# ==========================================================================
# Windows PTY Backend (pywinpty/ConPTY)
# ==========================================================================

class WindowsPTYBackend(InteractiveBackend):
    """
    Windows interactive PTY backend using pywinpty (ConPTY).

    This provides true terminal emulation on Windows, supporting:
    - ANSI escape sequences
    - Color output
    - Interactive prompts
    - Proper resize handling
    """

    def __init__(self, cols: int = 120, rows: int = 40):
        self.cols = cols
        self.rows = rows

        # PTY process
        self._pty = None
        self._process = None

        # Output queue for async reading
        self._output_queue: asyncio.Queue[OutputChunk] = asyncio.Queue()
        self._output_buffer: List[str] = []
        self._read_task: Optional[asyncio.Task] = None

        # State
        self._running = False
        self._awaiting_input = False
        self._last_output_time: Optional[datetime] = None

        # Output file for logging
        self._output_file: Optional[str] = None

    async def start(
        self,
        working_dir: str,
        dangerous_mode: bool = True,
    ) -> bool:
        """Start interactive CC session using pywinpty."""
        try:
            # Import pywinpty (will fail gracefully if not installed)
            try:
                import winpty
                self._use_winpty = True
            except ImportError:
                logger.warning("pywinpty not available, falling back to subprocess")
                self._use_winpty = False

            # Create output file for logging
            self._output_file = os.path.join(
                tempfile.gettempdir(),
                f"cc-interactive-{uuid4().hex[:8]}.log"
            )
            Path(self._output_file).touch()

            if self._use_winpty:
                return await self._start_with_winpty(working_dir, dangerous_mode)
            else:
                return await self._start_with_subprocess(working_dir, dangerous_mode)

        except Exception as e:
            logger.error("Failed to start interactive session", error=str(e))
            return False

    async def _start_with_winpty(
        self,
        working_dir: str,
        dangerous_mode: bool,
    ) -> bool:
        """Start using pywinpty for true ConPTY support."""
        import winpty

        # Build CC command
        cc_cmd = "claude"
        if dangerous_mode:
            cc_cmd += " --dangerously-skip-permissions"

        # Prepare environment: remove ANTHROPIC_API_KEY to force subscription usage
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)  # Remove if present

        # Create PTY
        self._pty = winpty.PtyProcess.spawn(
            cc_cmd,
            cwd=working_dir,
            dimensions=(self.rows, self.cols),
            env=env,
        )

        self._running = True
        self._awaiting_input = True  # Initial state: waiting for first prompt

        # Start async read loop
        self._read_task = asyncio.create_task(self._read_loop_winpty())

        logger.info(
            "Interactive CC session started (winpty)",
            working_dir=working_dir,
            dangerous_mode=dangerous_mode,
        )

        return True

    async def _start_with_subprocess(
        self,
        working_dir: str,
        dangerous_mode: bool,
    ) -> bool:
        """Fallback: Start using subprocess (limited PTY support)."""
        import subprocess

        # Build CC command
        cc_args = ["claude"]
        if dangerous_mode:
            cc_args.append("--dangerously-skip-permissions")

        # Prepare environment: remove ANTHROPIC_API_KEY to force subscription usage
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)  # Remove if present

        # Start process with pipes
        self._process = subprocess.Popen(
            cc_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=working_dir,
            bufsize=0,  # Unbuffered
            creationflags=subprocess.CREATE_NO_WINDOW,
            env=env,
        )

        self._running = True
        self._awaiting_input = True

        # Start async read loop
        self._read_task = asyncio.create_task(self._read_loop_subprocess())

        logger.info(
            "Interactive CC session started (subprocess fallback)",
            working_dir=working_dir,
            dangerous_mode=dangerous_mode,
        )

        return True

    async def _read_loop_winpty(self) -> None:
        """Read loop for winpty backend."""
        while self._running and self._pty:
            try:
                # Check if PTY is alive
                if not self._pty.isalive():
                    logger.info("PTY process exited")
                    self._running = False
                    break

                # Non-blocking read using executor
                def read_with_timeout():
                    try:
                        return self._pty.read(4096)
                    except Exception:
                        return ""

                data = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, read_with_timeout),
                    timeout=0.5,
                )

                if data:
                    await self._process_output(data)
                else:
                    # No data, check awaiting state
                    await self._check_awaiting_state()
                    await asyncio.sleep(0.1)

            except asyncio.TimeoutError:
                # No data available, check if still waiting
                await self._check_awaiting_state()
            except Exception as e:
                if self._running:
                    logger.error("Read error (winpty)", error=str(e))
                break

    async def _read_loop_subprocess(self) -> None:
        """Read loop for subprocess fallback."""
        while self._running and self._process:
            try:
                # Read from stdout
                data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._process.stdout.read(4096) if self._process.stdout else b"",
                )

                if data:
                    await self._process_output(data.decode("utf-8", errors="replace"))
                elif self._process.poll() is not None:
                    # Process ended
                    self._running = False
                    break
                else:
                    await asyncio.sleep(0.05)  # Small delay to prevent busy loop

            except Exception as e:
                if self._running:
                    logger.error("Read error (subprocess)", error=str(e))
                break

    async def _process_output(self, data: str) -> None:
        """Process incoming output data."""
        now = datetime.now(timezone.utc)
        self._last_output_time = now

        # Store in buffer
        self._output_buffer.append(data)

        # Write to log file
        if self._output_file:
            try:
                with open(self._output_file, "a", encoding="utf-8", errors="replace") as f:
                    f.write(data)
            except Exception:
                pass

        # Check for awaiting input indicators
        await self._check_awaiting_state()

        # Queue the chunk
        chunk = OutputChunk(
            content=data,
            timestamp=now,
            raw_bytes=data.encode("utf-8", errors="replace") if isinstance(data, str) else data,
        )
        await self._output_queue.put(chunk)

    async def _check_awaiting_state(self) -> None:
        """Check if CC is waiting for user input based on output patterns."""
        # Get recent output
        recent = "".join(self._output_buffer[-10:]) if self._output_buffer else ""

        # Patterns that indicate CC is waiting for input
        awaiting_patterns = [
            "> ",           # Standard prompt
            ">>> ",         # Python-style prompt
            "? ",           # Question prompt
            ": ",           # Selection prompt
            "[Y/n]",        # Yes/No prompt
            "[y/N]",
            "Press Enter",  # Continuation prompt
            "Continue?",    # Continuation question
        ]

        # Check if any pattern matches at the end of recent output
        self._awaiting_input = any(
            recent.rstrip().endswith(pattern.rstrip())
            for pattern in awaiting_patterns
        )

        # Also check for no output for > 2 seconds (likely waiting)
        if self._last_output_time:
            seconds_since = (datetime.now(timezone.utc) - self._last_output_time).total_seconds()
            if seconds_since > 2.0:
                self._awaiting_input = True

    async def send_prompt(self, prompt: str) -> None:
        """Send a prompt to the Claude session."""
        if self._use_winpty and self._pty:
            # Use carriage return (\r) to submit in Claude Code's TUI
            self._pty.write(prompt)
            await asyncio.sleep(0.1)  # Small delay between text and submit
            self._pty.write("\r")
        elif self._process and self._process.stdin:
            self._process.stdin.write((prompt + "\r").encode())
            self._process.stdin.flush()

        self._awaiting_input = False

        logger.debug("Prompt sent", prompt_preview=prompt[:100])

    async def send_input(self, text: str) -> None:
        """Send raw input to the session."""
        if self._use_winpty and self._pty:
            self._pty.write(text)
        elif self._process and self._process.stdin:
            self._process.stdin.write(text.encode())
            self._process.stdin.flush()

        self._awaiting_input = False

    async def read_output(self) -> AsyncIterator[OutputChunk]:
        """Async iterator for output chunks."""
        while self._running:
            try:
                chunk = await asyncio.wait_for(
                    self._output_queue.get(),
                    timeout=1.0,
                )
                yield chunk
            except asyncio.TimeoutError:
                # No output, continue waiting
                if not self._running:
                    break

    async def is_alive(self) -> bool:
        """Check if PTY is still running."""
        if self._use_winpty and self._pty:
            return self._pty.isalive()
        elif self._process:
            return self._process.poll() is None
        return False

    async def is_awaiting_input(self) -> bool:
        """Check if waiting for user input."""
        return self._awaiting_input

    async def stop(self) -> None:
        """Stop the session gracefully."""
        self._running = False

        if self._use_winpty and self._pty:
            # Send Ctrl+C first
            self._pty.write("\x03")
            await asyncio.sleep(0.5)
            # Then send exit command
            self._pty.write("exit\n")
            await asyncio.sleep(1.0)
            self._pty.close()
        elif self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except:
                self._process.kill()

        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        logger.info("Interactive session stopped gracefully")

    async def kill(self) -> None:
        """Force kill the session."""
        self._running = False

        if self._use_winpty and self._pty:
            self._pty.close()
        elif self._process:
            self._process.kill()

        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        logger.info("Interactive session killed")

    def get_full_output(self) -> str:
        """Get all accumulated output."""
        return "".join(self._output_buffer)

    @property
    def output_file(self) -> Optional[str]:
        """Get the path to the output log file."""
        return self._output_file


# ==========================================================================
# Linux PTY Backend (native pty + tmux)
# ==========================================================================

class LinuxPTYBackend(InteractiveBackend):
    """
    Linux interactive PTY backend using native pty module.

    Uses the Python pty module for terminal emulation, with optional
    tmux integration for session persistence.
    """

    def __init__(self, use_tmux: bool = True, cols: int = 120, rows: int = 40):
        self.use_tmux = use_tmux
        self.cols = cols
        self.rows = rows

        # PTY file descriptors
        self._master_fd: Optional[int] = None
        self._slave_fd: Optional[int] = None
        self._pid: Optional[int] = None

        # tmux session name
        self._tmux_session: Optional[str] = None

        # Output
        self._output_queue: asyncio.Queue[OutputChunk] = asyncio.Queue()
        self._output_buffer: List[str] = []
        self._read_task: Optional[asyncio.Task] = None

        # State
        self._running = False
        self._awaiting_input = False
        self._last_output_time: Optional[datetime] = None
        self._output_file: Optional[str] = None

    async def start(
        self,
        working_dir: str,
        dangerous_mode: bool = True,
    ) -> bool:
        """Start interactive CC session using native pty or tmux."""
        try:
            import pty
            import os
            import tty

            # Create output file
            self._output_file = os.path.join(
                tempfile.gettempdir(),
                f"cc-interactive-{uuid4().hex[:8]}.log"
            )
            Path(self._output_file).touch()

            # Build CC command
            cc_cmd = "claude"
            if dangerous_mode:
                cc_cmd += " --dangerously-skip-permissions"

            if self.use_tmux:
                return await self._start_with_tmux(working_dir, cc_cmd)
            else:
                return await self._start_with_pty(working_dir, cc_cmd)

        except Exception as e:
            logger.error("Failed to start Linux interactive session", error=str(e))
            return False

    async def _start_with_tmux(self, working_dir: str, cc_cmd: str) -> bool:
        """Start using tmux for session persistence."""
        self._tmux_session = f"cc-interactive-{uuid4().hex[:8]}"

        # Create tmux session
        proc = await asyncio.create_subprocess_exec(
            "tmux", "new-session", "-d", "-s", self._tmux_session,
            "-c", working_dir, "-x", str(self.cols), "-y", str(self.rows),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        if proc.returncode != 0:
            logger.error("Failed to create tmux session")
            return False

        # Enable pipe-pane for output logging
        proc = await asyncio.create_subprocess_exec(
            "tmux", "pipe-pane", "-t", self._tmux_session,
            f"cat >> {self._output_file}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        # Send the claude command
        proc = await asyncio.create_subprocess_exec(
            "tmux", "send-keys", "-t", self._tmux_session, cc_cmd, "Enter",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        self._running = True
        self._awaiting_input = True

        # Start read loop
        self._read_task = asyncio.create_task(self._read_loop_tmux())

        logger.info(
            "Interactive CC session started (tmux)",
            session=self._tmux_session,
            working_dir=working_dir,
        )

        return True

    async def _start_with_pty(self, working_dir: str, cc_cmd: str) -> bool:
        """Start using native pty (no tmux)."""
        import pty
        import os

        # Fork process with PTY
        self._pid, self._master_fd = pty.fork()

        if self._pid == 0:
            # Child process
            os.chdir(working_dir)
            os.execvp("bash", ["bash", "-c", cc_cmd])

        # Parent process
        self._running = True
        self._awaiting_input = True

        # Start read loop
        self._read_task = asyncio.create_task(self._read_loop_pty())

        logger.info(
            "Interactive CC session started (native pty)",
            pid=self._pid,
            working_dir=working_dir,
        )

        return True

    async def _read_loop_tmux(self) -> None:
        """Read loop for tmux backend using pipe-pane output."""
        last_size = 0

        while self._running:
            try:
                if self._output_file and os.path.exists(self._output_file):
                    current_size = os.path.getsize(self._output_file)

                    if current_size > last_size:
                        with open(self._output_file, "r", encoding="utf-8", errors="replace") as f:
                            f.seek(last_size)
                            data = f.read()

                        if data:
                            await self._process_output(data)
                            last_size = current_size

                await asyncio.sleep(0.1)

            except Exception as e:
                if self._running:
                    logger.error("Read error (tmux)", error=str(e))
                break

    async def _read_loop_pty(self) -> None:
        """Read loop for native pty."""
        import os
        import select

        while self._running and self._master_fd:
            try:
                # Check if data available
                r, _, _ = select.select([self._master_fd], [], [], 0.1)

                if r:
                    data = os.read(self._master_fd, 4096).decode("utf-8", errors="replace")
                    if data:
                        await self._process_output(data)

            except OSError:
                # PTY closed
                self._running = False
                break
            except Exception as e:
                if self._running:
                    logger.error("Read error (pty)", error=str(e))
                break

    async def _process_output(self, data: str) -> None:
        """Process incoming output data."""
        now = datetime.now(timezone.utc)
        self._last_output_time = now

        self._output_buffer.append(data)

        # Check awaiting state
        await self._check_awaiting_state()

        # Queue chunk
        chunk = OutputChunk(
            content=data,
            timestamp=now,
        )
        await self._output_queue.put(chunk)

    async def _check_awaiting_state(self) -> None:
        """Check if CC is waiting for input."""
        recent = "".join(self._output_buffer[-10:]) if self._output_buffer else ""

        awaiting_patterns = ["> ", ">>> ", "? ", ": ", "[Y/n]", "[y/N]", "Press Enter", "Continue?"]

        self._awaiting_input = any(
            recent.rstrip().endswith(pattern.rstrip())
            for pattern in awaiting_patterns
        )

        if self._last_output_time:
            seconds_since = (datetime.now(timezone.utc) - self._last_output_time).total_seconds()
            if seconds_since > 2.0:
                self._awaiting_input = True

    async def send_prompt(self, prompt: str) -> None:
        """Send prompt to the session."""
        if self.use_tmux and self._tmux_session:
            proc = await asyncio.create_subprocess_exec(
                "tmux", "send-keys", "-t", self._tmux_session, prompt, "Enter",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        elif self._master_fd:
            import os
            os.write(self._master_fd, (prompt + "\n").encode())

        self._awaiting_input = False

    async def send_input(self, text: str) -> None:
        """Send raw input."""
        if self.use_tmux and self._tmux_session:
            proc = await asyncio.create_subprocess_exec(
                "tmux", "send-keys", "-t", self._tmux_session, "-l", text,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        elif self._master_fd:
            import os
            os.write(self._master_fd, text.encode())

        self._awaiting_input = False

    async def read_output(self) -> AsyncIterator[OutputChunk]:
        """Async iterator for output chunks."""
        while self._running:
            try:
                chunk = await asyncio.wait_for(
                    self._output_queue.get(),
                    timeout=1.0,
                )
                yield chunk
            except asyncio.TimeoutError:
                if not self._running:
                    break

    async def is_alive(self) -> bool:
        """Check if session is alive."""
        if self.use_tmux and self._tmux_session:
            proc = await asyncio.create_subprocess_exec(
                "tmux", "has-session", "-t", self._tmux_session,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0
        elif self._pid:
            import os
            try:
                os.kill(self._pid, 0)
                return True
            except OSError:
                return False
        return False

    async def is_awaiting_input(self) -> bool:
        """Check if waiting for input."""
        return self._awaiting_input

    async def stop(self) -> None:
        """Stop the session gracefully."""
        self._running = False

        if self.use_tmux and self._tmux_session:
            # Send Ctrl+C and exit
            proc = await asyncio.create_subprocess_exec(
                "tmux", "send-keys", "-t", self._tmux_session, "C-c",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            await asyncio.sleep(0.5)

            proc = await asyncio.create_subprocess_exec(
                "tmux", "send-keys", "-t", self._tmux_session, "exit", "Enter",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            await asyncio.sleep(1.0)

            # Kill session
            proc = await asyncio.create_subprocess_exec(
                "tmux", "kill-session", "-t", self._tmux_session,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        elif self._master_fd:
            import os
            try:
                os.close(self._master_fd)
            except:
                pass

        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        logger.info("Interactive session stopped")

    async def kill(self) -> None:
        """Force kill the session."""
        self._running = False

        if self.use_tmux and self._tmux_session:
            proc = await asyncio.create_subprocess_exec(
                "tmux", "kill-session", "-t", self._tmux_session,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        elif self._pid:
            import os
            import signal
            try:
                os.kill(self._pid, signal.SIGKILL)
            except:
                pass

        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        logger.info("Interactive session killed")

    def get_full_output(self) -> str:
        """Get all output."""
        return "".join(self._output_buffer)

    @property
    def output_file(self) -> Optional[str]:
        """Get output file path."""
        return self._output_file


# ==========================================================================
# Factory Function
# ==========================================================================

def create_interactive_backend(
    cols: int = 120,
    rows: int = 40,
) -> InteractiveBackend:
    """
    Create the appropriate interactive backend for the current platform.

    Args:
        cols: Terminal width in columns
        rows: Terminal height in rows

    Returns:
        InteractiveBackend instance
    """
    if platform.system() == "Windows":
        return WindowsPTYBackend(cols=cols, rows=rows)
    else:
        return LinuxPTYBackend(use_tmux=True, cols=cols, rows=rows)
