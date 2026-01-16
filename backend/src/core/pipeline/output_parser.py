"""
CC Output Parser (EPOCH 9)
==========================

Parses Claude Code terminal output to extract granular events:
- Tool calls (antml:function_calls blocks)
- Tool results (function_results blocks)
- Thinking/reasoning text
- Errors and warnings
- Awaiting input indicators

This enables real-time monitoring of CC's actions and reasoning.
"""

import re
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any, Iterator
from uuid import uuid4

import structlog

from src.core.models import CCEventType

logger = structlog.get_logger()


# ==========================================================================
# Parser State Machine
# ==========================================================================

class ParserState(str, Enum):
    """Current state of the output parser."""
    IDLE = "idle"                       # Normal output
    IN_FUNCTION_CALLS = "in_function_calls"  # Inside antml:function_calls block
    IN_FUNCTION_RESULTS = "in_function_results"  # Inside function_results block
    IN_THINKING = "in_thinking"         # Inside antml:thinking block
    IN_CODE_BLOCK = "in_code_block"     # Inside ``` code block


# ==========================================================================
# Parsed Events
# ==========================================================================

@dataclass
class ParsedEvent:
    """A parsed event from CC output."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: CCEventType = CCEventType.THINKING
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Tool call info (for TOOL_CALL_START/END)
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[str] = None
    tool_duration_ms: Optional[int] = None

    # Content
    content: Optional[str] = None
    raw_text: str = ""

    # Error info
    is_error: bool = False
    error_type: Optional[str] = None

    # Line tracking
    line_start: Optional[int] = None
    line_end: Optional[int] = None

    # Parent event (for nested events)
    parent_event_id: Optional[str] = None


# ==========================================================================
# CC Output Parser
# ==========================================================================

class CCOutputParser:
    """
    Stateful parser for Claude Code terminal output.

    Maintains state to handle multi-line XML blocks and extracts
    structured events from the raw text stream.
    """

    # XML tag patterns (using raw strings to handle angle brackets)
    TAG_FUNCTION_CALLS_START = "antml:function_calls"
    TAG_FUNCTION_CALLS_END = "/antml:function_calls"
    TAG_INVOKE_START = "antml:invoke"
    TAG_INVOKE_END = "/antml:invoke"
    TAG_PARAMETER_START = "antml:parameter"
    TAG_PARAMETER_END = "/antml:parameter"
    TAG_FUNCTION_RESULTS_START = "function_results"
    TAG_FUNCTION_RESULTS_END = "/function_results"
    TAG_THINKING_START = "antml:thinking"
    TAG_THINKING_END = "/antml:thinking"

    # Error patterns
    ERROR_PATTERNS = [
        (r"Error:", "general_error"),
        (r"error\[", "compilation_error"),
        (r"FAILED", "test_failure"),
        (r"Exception:", "exception"),
        (r"Traceback", "traceback"),
        (r"fatal:", "fatal_error"),
        (r"panic:", "panic"),
        (r"ENOENT", "file_not_found"),
        (r"Permission denied", "permission_denied"),
        (r"SyntaxError", "syntax_error"),
        (r"TypeError", "type_error"),
        (r"ReferenceError", "reference_error"),
        (r"ModuleNotFoundError", "module_not_found"),
        (r"ImportError", "import_error"),
    ]

    # Awaiting input patterns
    AWAITING_PATTERNS = [
        r"^>\s*$",                    # Bare prompt
        r">>>\s*$",                   # Python prompt
        r"\?\s*$",                    # Question prompt
        r"\[Y/n\]",                   # Yes/No
        r"\[y/N\]",                   # No/Yes
        r"Press Enter",              # Continuation
        r"Continue\?",               # Continue question
        r"waiting for input",        # Explicit waiting
    ]

    def __init__(self):
        self.state = ParserState.IDLE
        self.current_line = 0
        self.buffer: List[str] = []

        # Current block being parsed
        self._block_start_line: Optional[int] = None
        self._block_content: List[str] = []
        self._current_tool_call: Optional[ParsedEvent] = None

        # Tool call timing
        self._tool_start_times: Dict[str, datetime] = {}

    def reset(self):
        """Reset parser state."""
        self.state = ParserState.IDLE
        self.current_line = 0
        self.buffer = []
        self._block_start_line = None
        self._block_content = []
        self._current_tool_call = None
        self._tool_start_times = {}

    def parse_chunk(self, chunk: str) -> Iterator[ParsedEvent]:
        """
        Parse a chunk of output and yield events.

        This is the main entry point for streaming parsing.
        """
        lines = chunk.split("\n")

        for line in lines:
            self.current_line += 1
            self.buffer.append(line)

            # Yield events from parsing this line
            yield from self._parse_line(line)

    def _parse_line(self, line: str) -> Iterator[ParsedEvent]:
        """Parse a single line and yield events."""
        stripped = line.strip()

        # State machine transitions
        if self.state == ParserState.IDLE:
            yield from self._parse_idle(line, stripped)
        elif self.state == ParserState.IN_FUNCTION_CALLS:
            yield from self._parse_function_calls(line, stripped)
        elif self.state == ParserState.IN_FUNCTION_RESULTS:
            yield from self._parse_function_results(line, stripped)
        elif self.state == ParserState.IN_THINKING:
            yield from self._parse_thinking(line, stripped)
        elif self.state == ParserState.IN_CODE_BLOCK:
            yield from self._parse_code_block(line, stripped)

    def _parse_idle(self, line: str, stripped: str) -> Iterator[ParsedEvent]:
        """Parse line while in IDLE state."""

        # Check for function_calls start
        if self._contains_tag(stripped, self.TAG_FUNCTION_CALLS_START):
            self.state = ParserState.IN_FUNCTION_CALLS
            self._block_start_line = self.current_line
            self._block_content = [line]
            return

        # Check for function_results start
        if self._contains_tag(stripped, self.TAG_FUNCTION_RESULTS_START):
            self.state = ParserState.IN_FUNCTION_RESULTS
            self._block_start_line = self.current_line
            self._block_content = [line]
            return

        # Check for thinking start
        if self._contains_tag(stripped, self.TAG_THINKING_START):
            self.state = ParserState.IN_THINKING
            self._block_start_line = self.current_line
            self._block_content = [line]
            return

        # Check for code block start
        if stripped.startswith("```"):
            self.state = ParserState.IN_CODE_BLOCK
            self._block_start_line = self.current_line
            self._block_content = [line]
            return

        # Check for errors
        for pattern, error_type in self.ERROR_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                yield ParsedEvent(
                    event_type=CCEventType.ERROR,
                    content=line,
                    raw_text=line,
                    is_error=True,
                    error_type=error_type,
                    line_start=self.current_line,
                    line_end=self.current_line,
                )
                return

        # Check for awaiting input
        for pattern in self.AWAITING_PATTERNS:
            if re.search(pattern, stripped):
                yield ParsedEvent(
                    event_type=CCEventType.DECISION,
                    content="Awaiting user input",
                    raw_text=line,
                    line_start=self.current_line,
                    line_end=self.current_line,
                )
                return

        # Regular output - could be thinking or decision text
        if stripped and not stripped.startswith("#"):  # Skip comments
            yield ParsedEvent(
                event_type=CCEventType.THINKING,
                content=stripped,
                raw_text=line,
                line_start=self.current_line,
                line_end=self.current_line,
            )

    def _parse_function_calls(self, line: str, stripped: str) -> Iterator[ParsedEvent]:
        """Parse line while inside function_calls block."""
        self._block_content.append(line)

        # Check for invoke start - extract tool name
        if self._contains_tag(stripped, self.TAG_INVOKE_START):
            tool_name = self._extract_attribute(stripped, "name")
            if tool_name:
                event_id = str(uuid4())
                self._current_tool_call = ParsedEvent(
                    event_id=event_id,
                    event_type=CCEventType.TOOL_CALL_START,
                    tool_name=tool_name,
                    tool_input={},
                    line_start=self.current_line,
                )
                self._tool_start_times[event_id] = datetime.now(timezone.utc)
                yield self._current_tool_call

        # Check for parameter - add to current tool call
        if self._contains_tag(stripped, self.TAG_PARAMETER_START):
            param_name = self._extract_attribute(stripped, "name")
            if param_name and self._current_tool_call:
                # Extract parameter value (may span multiple lines)
                param_value = self._extract_tag_content(line, self.TAG_PARAMETER_START, self.TAG_PARAMETER_END)
                if param_value and self._current_tool_call.tool_input is not None:
                    # Try to parse as JSON first
                    try:
                        self._current_tool_call.tool_input[param_name] = json.loads(param_value)
                    except json.JSONDecodeError:
                        self._current_tool_call.tool_input[param_name] = param_value

        # Check for invoke end
        if self._contains_tag(stripped, self.TAG_INVOKE_END):
            if self._current_tool_call:
                self._current_tool_call.line_end = self.current_line

        # Check for function_calls end
        if self._contains_tag(stripped, self.TAG_FUNCTION_CALLS_END):
            self.state = ParserState.IDLE
            self._current_tool_call = None
            self._block_content = []
            self._block_start_line = None

    def _parse_function_results(self, line: str, stripped: str) -> Iterator[ParsedEvent]:
        """Parse line while inside function_results block."""
        self._block_content.append(line)

        # Check for function_results end
        if self._contains_tag(stripped, self.TAG_FUNCTION_RESULTS_END):
            # Find matching tool call and create TOOL_CALL_END event
            result_content = "\n".join(self._block_content[1:-1])  # Exclude tags

            # Calculate duration if we have a start time
            duration_ms = None
            if self._tool_start_times:
                # Get most recent start time
                for event_id, start_time in list(self._tool_start_times.items()):
                    duration = datetime.now(timezone.utc) - start_time
                    duration_ms = int(duration.total_seconds() * 1000)
                    del self._tool_start_times[event_id]
                    break

            yield ParsedEvent(
                event_type=CCEventType.TOOL_CALL_END,
                tool_output=result_content,
                tool_duration_ms=duration_ms,
                content=result_content[:500],  # Truncate for content field
                raw_text="\n".join(self._block_content),
                line_start=self._block_start_line,
                line_end=self.current_line,
            )

            self.state = ParserState.IDLE
            self._block_content = []
            self._block_start_line = None

    def _parse_thinking(self, line: str, stripped: str) -> Iterator[ParsedEvent]:
        """Parse line while inside thinking block."""
        self._block_content.append(line)

        # Check for thinking end
        if self._contains_tag(stripped, self.TAG_THINKING_END):
            thinking_content = "\n".join(self._block_content[1:-1])  # Exclude tags

            yield ParsedEvent(
                event_type=CCEventType.THINKING,
                content=thinking_content,
                raw_text="\n".join(self._block_content),
                line_start=self._block_start_line,
                line_end=self.current_line,
            )

            self.state = ParserState.IDLE
            self._block_content = []
            self._block_start_line = None

    def _parse_code_block(self, line: str, stripped: str) -> Iterator[ParsedEvent]:
        """Parse line while inside code block."""
        self._block_content.append(line)

        # Check for code block end
        if stripped.startswith("```") and len(self._block_content) > 1:
            # Determine if this is a file operation
            first_line = self._block_content[0] if self._block_content else ""
            event_type = CCEventType.THINKING

            # Check for bash command
            if "```bash" in first_line or "```shell" in first_line:
                event_type = CCEventType.BASH_COMMAND

            yield ParsedEvent(
                event_type=event_type,
                content="\n".join(self._block_content[1:-1]),  # Exclude ``` markers
                raw_text="\n".join(self._block_content),
                line_start=self._block_start_line,
                line_end=self.current_line,
            )

            self.state = ParserState.IDLE
            self._block_content = []
            self._block_start_line = None

    def _contains_tag(self, text: str, tag_name: str) -> bool:
        """Check if text contains the specified tag."""
        # Handle both <tag> and </tag> patterns
        return f"<{tag_name}" in text or f"<{tag_name}>" in text

    def _extract_attribute(self, text: str, attr_name: str) -> Optional[str]:
        """Extract attribute value from XML-like tag."""
        pattern = rf'{attr_name}=["\']([^"\']+)["\']'
        match = re.search(pattern, text)
        return match.group(1) if match else None

    def _extract_tag_content(self, text: str, start_tag: str, end_tag: str) -> Optional[str]:
        """Extract content between opening and closing tags (single line)."""
        pattern = rf"<{start_tag}[^>]*>(.+?)<{end_tag}>"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else None

    def get_recent_context(self, lines: int = 50) -> str:
        """Get recent output for context."""
        return "\n".join(self.buffer[-lines:])


# ==========================================================================
# Event Stream Processor
# ==========================================================================

class EventStreamProcessor:
    """
    Higher-level processor that aggregates parsed events into
    a structured event stream.
    """

    def __init__(self):
        self.parser = CCOutputParser()
        self.events: List[ParsedEvent] = []
        self.tool_calls: List[ParsedEvent] = []
        self.errors: List[ParsedEvent] = []
        self.thinking_blocks: List[ParsedEvent] = []

    def process(self, chunk: str) -> List[ParsedEvent]:
        """Process a chunk of output and return new events."""
        new_events = []

        for event in self.parser.parse_chunk(chunk):
            self.events.append(event)
            new_events.append(event)

            # Categorize
            if event.event_type in (CCEventType.TOOL_CALL_START, CCEventType.TOOL_CALL_END):
                self.tool_calls.append(event)
            elif event.event_type == CCEventType.ERROR:
                self.errors.append(event)
            elif event.event_type == CCEventType.THINKING:
                self.thinking_blocks.append(event)

        return new_events

    def get_tool_summary(self) -> Dict[str, int]:
        """Get summary of tool calls by name."""
        summary: Dict[str, int] = {}
        for event in self.tool_calls:
            if event.tool_name:
                summary[event.tool_name] = summary.get(event.tool_name, 0) + 1
        return summary

    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of errors by type."""
        summary: Dict[str, int] = {}
        for event in self.errors:
            error_type = event.error_type or "unknown"
            summary[error_type] = summary.get(error_type, 0) + 1
        return summary

    def reset(self):
        """Reset the processor."""
        self.parser.reset()
        self.events = []
        self.tool_calls = []
        self.errors = []
        self.thinking_blocks = []


# ==========================================================================
# Utility Functions
# ==========================================================================

def extract_file_operations(events: List[ParsedEvent]) -> Dict[str, List[str]]:
    """
    Extract file operations from parsed events.

    Returns dict with keys: 'read', 'write', 'edit'
    """
    operations: Dict[str, List[str]] = {"read": [], "write": [], "edit": []}

    for event in events:
        if event.event_type == CCEventType.TOOL_CALL_START and event.tool_input:
            tool_name = event.tool_name or ""

            if tool_name.lower() == "read":
                file_path = event.tool_input.get("file_path", "")
                if file_path:
                    operations["read"].append(file_path)

            elif tool_name.lower() == "write":
                file_path = event.tool_input.get("file_path", "")
                if file_path:
                    operations["write"].append(file_path)

            elif tool_name.lower() == "edit":
                file_path = event.tool_input.get("file_path", "")
                if file_path:
                    operations["edit"].append(file_path)

    return operations


def detect_completion(events: List[ParsedEvent], window: int = 10) -> bool:
    """
    Detect if the recent events indicate task completion.

    Looks for completion patterns in recent output.
    """
    completion_patterns = [
        r"✓.*completed",
        r"Task completed",
        r"Done\.",
        r"I've finished",
        r"All tests pass",
        r"Successfully",
        r"Changes saved",
        r"Commit.*created",
        r"Build succeeded",
    ]

    recent = events[-window:] if len(events) > window else events

    for event in recent:
        if event.content:
            for pattern in completion_patterns:
                if re.search(pattern, event.content, re.IGNORECASE):
                    return True

    return False


def detect_awaiting_input(events: List[ParsedEvent], window: int = 5) -> bool:
    """
    Detect if CC is waiting for user input based on recent events.
    """
    recent = events[-window:] if len(events) > window else events

    for event in recent:
        if event.event_type == CCEventType.DECISION:
            if event.content and "awaiting" in event.content.lower():
                return True

    return False
