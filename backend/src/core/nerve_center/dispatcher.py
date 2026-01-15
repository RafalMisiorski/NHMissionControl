"""
NH CC Dispatcher - Intelligent Task Router
============================================

Claude Code as the central dispatcher that:
1. Receives tasks from user or NH systems
2. Analyzes complexity and requirements
3. Routes to appropriate AI tool (Opus/Sonnet/Gemini/Codex)
4. Monitors execution via Nerve Center
5. Sends notifications via SyncWave

Architecture:
┌─────────────────────────────────────────────────────────────────────────┐
│                           CC DISPATCHER                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────┐     ┌──────────────┐     ┌─────────────────────┐        │
│   │  User   │────▶│ CC Dispatcher │────▶│   AI Tool Selection │        │
│   │ Request │     │   (Claude)   │     │                     │        │
│   └─────────┘     └──────┬───────┘     │  ┌───────────────┐  │        │
│                          │             │  │ Claude Opus   │  │        │
│   ┌─────────┐            │             │  │ (Critical)    │  │        │
│   │SyncWave │◀───────────┤             │  ├───────────────┤  │        │
│   │  App    │            │             │  │ Claude Sonnet │  │        │
│   └─────────┘            │             │  │ (Standard)    │  │        │
│       │                  │             │  ├───────────────┤  │        │
│       ▼                  │             │  │ Gemini CLI    │  │        │
│   ┌─────────┐            │             │  │ (Docs/Free)   │  │        │
│   │ Phone   │            │             │  ├───────────────┤  │        │
│   │  Notif  │            │             │  │ Codex CLI     │  │        │
│   └─────────┘            │             │  │ (Simple)      │  │        │
│                          │             │  └───────────────┘  │        │
│                          │             └─────────────────────┘        │
│                          │                                             │
│                          ▼                                             │
│                  ┌───────────────┐                                     │
│                  │ Nerve Center  │                                     │
│                  │ (Monitoring)  │                                     │
│                  └───────────────┘                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
"""

import json
import subprocess
import asyncio
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from uuid import uuid4
import structlog

from src.core.config import settings

logger = structlog.get_logger()


# ==========================================================================
# Enums
# ==========================================================================

class TaskComplexity(str, Enum):
    TRIVIAL = "trivial"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskType(str, Enum):
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DOCUMENTATION = "documentation"
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    REFACTORING = "refactoring"
    ANALYSIS = "analysis"
    RESEARCH = "research"


class AITool(str, Enum):
    CLAUDE_OPUS = "claude-opus"
    CLAUDE_SONNET = "claude-sonnet"
    GEMINI_CLI = "gemini-cli"
    CODEX_CLI = "codex-cli"


class ProjectPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    EXPERIMENTAL = "experimental"


# ==========================================================================
# Task Definition
# ==========================================================================

@dataclass
class DispatchTask:
    """A task to be dispatched to an AI tool"""
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Task description
    title: str = ""
    description: str = ""
    task_type: TaskType = TaskType.CODE_GENERATION
    
    # Complexity assessment
    complexity: TaskComplexity = TaskComplexity.MEDIUM
    estimated_tokens: int = 0
    
    # Project context
    project_id: Optional[str] = None
    project_priority: ProjectPriority = ProjectPriority.MEDIUM
    
    # File context
    files_involved: List[str] = field(default_factory=list)
    working_directory: Optional[str] = None
    
    # Constraints
    requires_review: bool = False
    max_file_changes: int = 10
    timeout_minutes: int = 30
    
    # Routing
    assigned_tool: Optional[AITool] = None
    routing_reason: str = ""
    
    # Execution
    status: str = "pending"  # pending, dispatched, running, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None
    
    # SyncWave notification
    notify_on_complete: bool = True
    notify_on_error: bool = True


# ==========================================================================
# Routing Rules
# ==========================================================================

@dataclass
class RoutingRule:
    """Rule for routing tasks to AI tools"""
    name: str
    conditions: Dict[str, Any]
    target_tool: AITool
    priority: int = 0  # Higher = checked first
    rationale: str = ""


class RoutingEngine:
    """
    Determines which AI tool should handle a task.
    Uses rules from Asset Registry delegation matrix.
    """
    
    def __init__(self):
        self.rules = self._build_default_rules()
    
    def _build_default_rules(self) -> List[RoutingRule]:
        """Build routing rules from delegation matrix"""
        return [
            # Rule 1: NH core ALWAYS goes to Opus
            RoutingRule(
                name="NH Core to Opus",
                conditions={
                    "project_priority": [ProjectPriority.CRITICAL],
                },
                target_tool=AITool.CLAUDE_OPUS,
                priority=100,
                rationale="Critical projects always use Claude Opus - no exceptions",
            ),
            
            # Rule 2: Architecture decisions → Opus
            RoutingRule(
                name="Architecture to Opus",
                conditions={
                    "task_type": [TaskType.ARCHITECTURE],
                    "complexity": [TaskComplexity.MEDIUM, TaskComplexity.HIGH, TaskComplexity.CRITICAL],
                },
                target_tool=AITool.CLAUDE_OPUS,
                priority=90,
                rationale="Architecture decisions require highest quality reasoning",
            ),
            
            # Rule 3: Complex debugging → Opus
            RoutingRule(
                name="Complex Debugging to Opus",
                conditions={
                    "task_type": [TaskType.DEBUGGING],
                    "complexity": [TaskComplexity.HIGH, TaskComplexity.CRITICAL],
                },
                target_tool=AITool.CLAUDE_OPUS,
                priority=85,
                rationale="Complex bugs need sophisticated analysis",
            ),
            
            # Rule 4: Documentation → Gemini (free!)
            RoutingRule(
                name="Documentation to Gemini",
                conditions={
                    "task_type": [TaskType.DOCUMENTATION],
                    "complexity": [TaskComplexity.TRIVIAL, TaskComplexity.LOW, TaskComplexity.MEDIUM],
                },
                target_tool=AITool.GEMINI_CLI,
                priority=80,
                rationale="Gemini is free and good for documentation - saves Claude tokens",
            ),
            
            # Rule 5: Simple code tasks → Codex
            RoutingRule(
                name="Simple Code to Codex",
                conditions={
                    "task_type": [TaskType.CODE_GENERATION, TaskType.REFACTORING, TaskType.TESTING],
                    "complexity": [TaskComplexity.TRIVIAL, TaskComplexity.LOW],
                    "project_priority": [ProjectPriority.LOW, ProjectPriority.EXPERIMENTAL, ProjectPriority.MEDIUM],
                },
                target_tool=AITool.CODEX_CLI,
                priority=70,
                rationale="Simple tasks on non-critical projects - Codex is sufficient",
            ),
            
            # Rule 6: Medium complexity code → Sonnet
            RoutingRule(
                name="Medium Code to Sonnet",
                conditions={
                    "task_type": [TaskType.CODE_GENERATION, TaskType.CODE_REVIEW, TaskType.TESTING],
                    "complexity": [TaskComplexity.LOW, TaskComplexity.MEDIUM],
                },
                target_tool=AITool.CLAUDE_SONNET,
                priority=60,
                rationale="Sonnet is balanced - good quality, reasonable cost",
            ),
            
            # Rule 7: Research → Gemini (large context)
            RoutingRule(
                name="Research to Gemini",
                conditions={
                    "task_type": [TaskType.RESEARCH, TaskType.ANALYSIS],
                    "complexity": [TaskComplexity.TRIVIAL, TaskComplexity.LOW, TaskComplexity.MEDIUM],
                },
                target_tool=AITool.GEMINI_CLI,
                priority=50,
                rationale="Gemini has 1M context window - good for research",
            ),
            
            # Default: Sonnet for anything else
            RoutingRule(
                name="Default to Sonnet",
                conditions={},  # Matches everything
                target_tool=AITool.CLAUDE_SONNET,
                priority=0,
                rationale="Sonnet is the balanced default choice",
            ),
        ]
    
    def route(self, task: DispatchTask) -> AITool:
        """
        Determine best AI tool for a task.
        Returns tool and sets routing_reason on task.
        """
        # Sort rules by priority (highest first)
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            if self._matches_rule(task, rule):
                task.assigned_tool = rule.target_tool
                task.routing_reason = rule.rationale
                return rule.target_tool
        
        # Should never reach here due to default rule
        task.assigned_tool = AITool.CLAUDE_SONNET
        task.routing_reason = "No specific rule matched - using default"
        return AITool.CLAUDE_SONNET
    
    def _matches_rule(self, task: DispatchTask, rule: RoutingRule) -> bool:
        """Check if task matches rule conditions"""
        for field, allowed_values in rule.conditions.items():
            task_value = getattr(task, field, None)
            if task_value is not None and task_value not in allowed_values:
                return False
        return True


# ==========================================================================
# SyncWave Integration
# ==========================================================================

@dataclass
class SyncWaveNotification:
    """Notification to send via SyncWave"""
    title: str
    body: str
    priority: str = "normal"  # low, normal, high, urgent
    category: str = "task"    # task, alert, update, error
    action_url: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


class SyncWaveClient:
    """
    Client for sending notifications to SyncWave app.
    SyncWave streams from PC to phone with CC integration.
    """
    
    def __init__(self, api_url: str = None, api_key: str = None):
        self.api_url = api_url or settings.SYNCWAVE_API_URL
        self.api_key = api_key or settings.SYNCWAVE_API_KEY
    
    @property
    def enabled(self) -> bool:
        """Check if SyncWave is properly configured"""
        return bool(self.api_key) and settings.SYNCWAVE_ENABLED
    
    async def send_notification(self, notification: SyncWaveNotification) -> bool:
        """Send notification to SyncWave or log if disabled"""
        # Log notification (always - for debugging/audit)
        logger.info(
            "syncwave_dispatcher_notification",
            title=notification.title,
            body=notification.body[:50],
            priority=notification.priority,
            category=notification.category,
            enabled=self.enabled
        )
        
        # In disabled mode, just return success (we logged it above)
        if not self.enabled:
            return True
        
        # TODO: Implement actual SyncWave API call when enabled
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{self.api_url}/api/notifications",
        #         json={
        #             "title": notification.title,
        #             "body": notification.body,
        #             "priority": notification.priority,
        #             "category": notification.category,
        #             "data": notification.data,
        #         },
        #         headers={"Authorization": f"Bearer {self.api_key}"}
        #     )
        #     return response.status_code == 200
        
        return True
    
    async def send_task_started(self, task: DispatchTask):
        """Notify that task has started"""
        await self.send_notification(SyncWaveNotification(
            title=f"🚀 Task Started: {task.title[:30]}",
            body=f"Assigned to {task.assigned_tool.value}. {task.routing_reason}",
            priority="normal",
            category="task",
            data={"task_id": task.id, "tool": task.assigned_tool.value},
        ))
    
    async def send_task_completed(self, task: DispatchTask):
        """Notify that task completed successfully"""
        await self.send_notification(SyncWaveNotification(
            title=f"✅ Task Completed: {task.title[:30]}",
            body=f"Finished by {task.assigned_tool.value}",
            priority="normal",
            category="task",
            data={"task_id": task.id, "status": "completed"},
        ))
    
    async def send_task_failed(self, task: DispatchTask):
        """Notify that task failed"""
        await self.send_notification(SyncWaveNotification(
            title=f"❌ Task Failed: {task.title[:30]}",
            body=f"Error: {task.error[:50] if task.error else 'Unknown error'}",
            priority="high",
            category="error",
            data={"task_id": task.id, "error": task.error},
        ))
    
    async def send_blocker_alert(self, project_id: str, blocker: str, suggestion: str):
        """Alert when a blocker might be resolvable"""
        await self.send_notification(SyncWaveNotification(
            title=f"🔓 Blocker Update: {project_id}",
            body=f"{blocker} - {suggestion}",
            priority="high",
            category="alert",
            data={"project_id": project_id, "blocker": blocker},
        ))


# ==========================================================================
# AI Tool Executors
# ==========================================================================

class ToolExecutor:
    """Base class for AI tool execution"""
    
    async def execute(self, task: DispatchTask, prompt: str) -> str:
        raise NotImplementedError


class GeminiExecutor(ToolExecutor):
    """Execute tasks via Gemini CLI"""
    
    async def execute(self, task: DispatchTask, prompt: str) -> str:
        """Run gemini CLI command"""
        cmd = f'gemini "{prompt}"'
        
        # For safety, we'll just return the command for now
        # In production, would use subprocess
        return f"[GEMINI CLI] Would execute: {cmd[:100]}..."
        
        # Production code:
        # result = subprocess.run(
        #     ["gemini", prompt],
        #     capture_output=True,
        #     text=True,
        #     timeout=task.timeout_minutes * 60
        # )
        # return result.stdout


class CodexExecutor(ToolExecutor):
    """Execute tasks via Codex CLI"""
    
    async def execute(self, task: DispatchTask, prompt: str) -> str:
        """Run codex CLI command"""
        cmd = f'codex "{prompt}"'
        return f"[CODEX CLI] Would execute: {cmd[:100]}..."


class ClaudeExecutor(ToolExecutor):
    """Execute tasks via Claude API"""
    
    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        self.model = model
    
    async def execute(self, task: DispatchTask, prompt: str) -> str:
        """Call Claude API"""
        # Would use anthropic SDK
        return f"[CLAUDE {self.model}] Would call API with prompt..."


# ==========================================================================
# Main Dispatcher
# ==========================================================================

class CCDispatcher:
    """
    Claude Code Dispatcher - Central task routing hub.
    
    Receives tasks, analyzes them, routes to appropriate AI tool,
    monitors execution, and sends notifications via SyncWave.
    """
    
    def __init__(self):
        self.routing_engine = RoutingEngine()
        self.syncwave = SyncWaveClient()
        self.task_queue: List[DispatchTask] = []
        self.task_history: List[DispatchTask] = []
        
        # Tool executors
        self.executors = {
            AITool.CLAUDE_OPUS: ClaudeExecutor("claude-opus-4-5-20251101"),
            AITool.CLAUDE_SONNET: ClaudeExecutor("claude-sonnet-4-5-20250929"),
            AITool.GEMINI_CLI: GeminiExecutor(),
            AITool.CODEX_CLI: CodexExecutor(),
        }
    
    def analyze_task(self, description: str, project_id: str = None) -> DispatchTask:
        """
        Analyze a task description and create DispatchTask.
        Uses heuristics to determine complexity and type.
        """
        task = DispatchTask(
            description=description,
            project_id=project_id,
        )
        
        # Heuristic analysis
        desc_lower = description.lower()
        
        # Determine task type
        if any(word in desc_lower for word in ["document", "readme", "docs", "comment"]):
            task.task_type = TaskType.DOCUMENTATION
        elif any(word in desc_lower for word in ["test", "spec", "unit test"]):
            task.task_type = TaskType.TESTING
        elif any(word in desc_lower for word in ["bug", "fix", "error", "issue"]):
            task.task_type = TaskType.DEBUGGING
        elif any(word in desc_lower for word in ["architect", "design", "structure", "refactor major"]):
            task.task_type = TaskType.ARCHITECTURE
        elif any(word in desc_lower for word in ["review", "check", "audit"]):
            task.task_type = TaskType.CODE_REVIEW
        elif any(word in desc_lower for word in ["research", "analyze", "investigate"]):
            task.task_type = TaskType.RESEARCH
        else:
            task.task_type = TaskType.CODE_GENERATION
        
        # Determine complexity
        if any(word in desc_lower for word in ["simple", "basic", "quick", "small"]):
            task.complexity = TaskComplexity.LOW
        elif any(word in desc_lower for word in ["complex", "difficult", "major", "critical"]):
            task.complexity = TaskComplexity.HIGH
        elif any(word in desc_lower for word in ["trivial", "tiny", "minor"]):
            task.complexity = TaskComplexity.TRIVIAL
        else:
            task.complexity = TaskComplexity.MEDIUM
        
        # Set project priority from registry
        task.project_priority = self._get_project_priority(project_id)
        
        # Generate title
        task.title = description[:50] + ("..." if len(description) > 50 else "")
        
        return task
    
    def _get_project_priority(self, project_id: str) -> ProjectPriority:
        """Get project priority from Asset Registry"""
        # Project priority mapping from registry
        priorities = {
            "nh": ProjectPriority.CRITICAL,
            "nhmc": ProjectPriority.CRITICAL,
            "sw": ProjectPriority.HIGH,
            "sf": ProjectPriority.HIGH,
            "toa": ProjectPriority.HIGH,
            "pf": ProjectPriority.HIGH,
            "fpr": ProjectPriority.MEDIUM,
            "cn": ProjectPriority.LOW,
            "us": ProjectPriority.LOW,
            "cit": ProjectPriority.EXPERIMENTAL,
        }
        return priorities.get(project_id, ProjectPriority.MEDIUM)
    
    async def dispatch(self, task: DispatchTask) -> DispatchTask:
        """
        Dispatch a task to the appropriate AI tool.
        """
        # Route task
        tool = self.routing_engine.route(task)
        task.status = "dispatched"
        
        # Notify via SyncWave
        await self.syncwave.send_task_started(task)
        
        # Add to queue
        self.task_queue.append(task)
        
        return task
    
    async def execute(self, task: DispatchTask) -> DispatchTask:
        """
        Execute a dispatched task.
        """
        task.status = "running"
        
        try:
            executor = self.executors.get(task.assigned_tool)
            if not executor:
                raise ValueError(f"No executor for {task.assigned_tool}")
            
            # Build prompt
            prompt = self._build_prompt(task)
            
            # Execute
            result = await executor.execute(task, prompt)
            
            task.result = result
            task.status = "completed"
            
            # Notify success
            if task.notify_on_complete:
                await self.syncwave.send_task_completed(task)
            
        except Exception as e:
            task.error = str(e)
            task.status = "failed"
            
            # Notify failure
            if task.notify_on_error:
                await self.syncwave.send_task_failed(task)
        
        # Move to history
        if task in self.task_queue:
            self.task_queue.remove(task)
        self.task_history.append(task)
        
        return task
    
    def _build_prompt(self, task: DispatchTask) -> str:
        """Build prompt for AI tool"""
        prompt_parts = [
            f"Task: {task.description}",
            f"Type: {task.task_type.value}",
            f"Complexity: {task.complexity.value}",
        ]
        
        if task.project_id:
            prompt_parts.append(f"Project: {task.project_id}")
        
        if task.files_involved:
            prompt_parts.append(f"Files: {', '.join(task.files_involved)}")
        
        if task.working_directory:
            prompt_parts.append(f"Working directory: {task.working_directory}")
        
        return "\n".join(prompt_parts)
    
    async def dispatch_and_execute(
        self,
        description: str,
        project_id: str = None,
    ) -> DispatchTask:
        """
        Convenience method: analyze, dispatch, and execute in one call.
        """
        task = self.analyze_task(description, project_id)
        await self.dispatch(task)
        return await self.execute(task)
    
    def get_routing_explanation(self, task: DispatchTask) -> str:
        """Get human-readable explanation of routing decision"""
        return f"""
Task Routing Decision
=====================
Task: {task.title}
Type: {task.task_type.value}
Complexity: {task.complexity.value}
Project Priority: {task.project_priority.value}

→ Assigned to: {task.assigned_tool.value if task.assigned_tool else 'Not yet routed'}
→ Reason: {task.routing_reason}
"""


# ==========================================================================
# CLI Interface for CC
# ==========================================================================

async def main():
    """Example usage"""
    dispatcher = CCDispatcher()
    
    # Example tasks
    tasks = [
        ("Write README documentation for Signal Factory", "sf"),
        ("Fix critical authentication bug in NH Mission Control", "nhmc"),
        ("Add unit tests for user registration", "toa"),
        ("Design new architecture for Prospect Finder", "pf"),
        ("Simple typo fix in comments", "us"),
    ]
    
    print("\n" + "="*70)
    print("NH CC DISPATCHER - Task Routing Demo")
    print("="*70 + "\n")
    
    for desc, project_id in tasks:
        task = dispatcher.analyze_task(desc, project_id)
        dispatcher.routing_engine.route(task)
        
        print(f"📋 Task: {desc[:50]}...")
        print(f"   Project: {project_id} ({task.project_priority.value})")
        print(f"   Type: {task.task_type.value}")
        print(f"   Complexity: {task.complexity.value}")
        print(f"   ➡️  Route to: {task.assigned_tool.value}")
        print(f"   💡 Reason: {task.routing_reason}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
