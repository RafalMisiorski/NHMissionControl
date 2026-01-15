"""
NH Agent Orchestrator
======================

The central brain that coordinates all NH operations.
Manages agents, tasks, and provides full transparency through events.
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable, Awaitable
from dataclasses import dataclass, field
from uuid import uuid4
from enum import Enum
import logging

from .events import (
    NHEvent, EventCategory, EventType, Severity,
    EventBuilder, SessionState, TaskState, AgentState
)
from .websocket_hub import get_connection_manager, ConnectionManager

logger = logging.getLogger(__name__)


# ==========================================================================
# Agent Definitions
# ==========================================================================

class AgentRole(str, Enum):
    """Predefined agent roles"""
    ANALYZER = "analyzer"
    PLANNER = "planner"
    GENERATOR = "generator"
    VALIDATOR = "validator"
    EXECUTOR = "executor"


@dataclass
class AgentConfig:
    """Configuration for an agent"""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    role: AgentRole = AgentRole.ANALYZER
    model: str = "claude-3-opus"
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt: str = ""
    capabilities: List[str] = field(default_factory=list)


# ==========================================================================
# Task Definitions
# ==========================================================================

@dataclass
class TaskDefinition:
    """Definition of a task to be executed"""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    agent_role: AgentRole = AgentRole.ANALYZER
    
    # Input/Output
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # Task IDs
    
    # Execution
    execute_fn: Optional[Callable[..., Awaitable[Any]]] = None
    timeout_seconds: int = 300
    retry_count: int = 2
    
    # Sub-tasks
    sub_tasks: List['TaskDefinition'] = field(default_factory=list)


# ==========================================================================
# Agent Instance
# ==========================================================================

class Agent:
    """
    An AI agent that can perform tasks.
    Emits events for every operation for full transparency.
    """
    
    def __init__(self, config: AgentConfig, orchestrator: 'Orchestrator'):
        self.config = config
        self.orchestrator = orchestrator
        self.state = AgentState(
            id=config.id,
            name=config.name,
            role=config.role.value,
            status="idle",
            tasks_completed=0,
            tasks_failed=0,
            total_tokens=0,
            total_cost_usd=0,
        )
    
    @property
    def manager(self) -> ConnectionManager:
        return self.orchestrator.manager
    
    @property
    def session_id(self) -> str:
        return self.orchestrator.session_id
    
    async def emit(self, event: NHEvent):
        """Emit event through orchestrator"""
        event.agent_id = self.config.id
        event.session_id = self.session_id
        await self.manager.emit_event(event)
    
    async def think(self, thought: str, context: Dict[str, Any] = None):
        """Log agent thinking (visible to user)"""
        self.state.status = "thinking"
        self.state.current_thought = thought
        
        await self.emit(EventBuilder.agent_thinking(
            agent_id=self.config.id,
            thought=thought,
            context=context,
            session_id=self.session_id,
        ))
    
    async def decide(self, decision: str, reasoning: str, options: List[str] = None):
        """Log agent decision (visible to user)"""
        await self.emit(EventBuilder.agent_decision(
            agent_id=self.config.id,
            decision=decision,
            reasoning=reasoning,
            options_considered=options,
            session_id=self.session_id,
        ))
    
    async def act(self, action: str):
        """Log agent action start"""
        self.state.status = "acting"
        self.state.current_action = action
        
        await self.emit(NHEvent(
            category=EventCategory.AGENT,
            event_type=EventType.AGENT_ACTION,
            agent_id=self.config.id,
            session_id=self.session_id,
            message=f"ACTION: {action}",
        ))
    
    async def call_llm(
        self,
        prompt: str,
        max_tokens: int = None,
        temperature: float = None,
    ) -> str:
        """
        Make LLM call with full transparency.
        In production, this would call actual LLM API.
        """
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature or self.config.temperature
        
        # Emit request event
        await self.emit(EventBuilder.llm_request(
            model=self.config.model,
            prompt_preview=prompt,
            max_tokens=max_tokens,
            session_id=self.session_id,
        ))
        
        start_time = datetime.utcnow()
        
        # TODO: Actual LLM call here
        # For now, simulate
        await asyncio.sleep(0.5)  # Simulate API latency
        
        # Simulate response
        response = f"[Simulated response from {self.config.model}]"
        tokens_in = len(prompt.split()) * 1.3  # Rough estimate
        tokens_out = len(response.split()) * 1.3
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Calculate cost (example rates)
        cost_per_1k_in = 0.015 if "opus" in self.config.model else 0.003
        cost_per_1k_out = 0.075 if "opus" in self.config.model else 0.015
        cost = (tokens_in / 1000 * cost_per_1k_in) + (tokens_out / 1000 * cost_per_1k_out)
        
        # Update stats
        self.state.total_tokens += int(tokens_in + tokens_out)
        self.state.total_cost_usd += cost
        
        # Emit completion event
        await self.emit(EventBuilder.llm_complete(
            model=self.config.model,
            tokens_input=int(tokens_in),
            tokens_output=int(tokens_out),
            duration_ms=duration_ms,
            cost_usd=cost,
            session_id=self.session_id,
        ))
        
        return response
    
    async def read_file(self, path: str) -> str:
        """Read file with event emission"""
        await self.emit(EventBuilder.file_operation(
            operation="read",
            file_path=path,
            session_id=self.session_id,
        ))
        
        # TODO: Actual file read
        return f"[Contents of {path}]"
    
    async def write_file(self, path: str, content: str):
        """Write file with event emission"""
        await self.emit(EventBuilder.file_operation(
            operation="write",
            file_path=path,
            size_bytes=len(content.encode()),
            session_id=self.session_id,
        ))
        
        # TODO: Actual file write
    
    async def complete_task(self):
        """Mark current task as complete"""
        self.state.tasks_completed += 1
        self.state.status = "idle"
        self.state.current_thought = None
        self.state.current_action = None
    
    async def fail_task(self, error: str):
        """Mark current task as failed"""
        self.state.tasks_failed += 1
        self.state.status = "error"
        
        await self.emit(NHEvent(
            category=EventCategory.AGENT,
            event_type=EventType.AGENT_ERROR,
            severity=Severity.ERROR,
            agent_id=self.config.id,
            session_id=self.session_id,
            message=f"Task failed: {error}",
        ))


# ==========================================================================
# Orchestrator
# ==========================================================================

class Orchestrator:
    """
    Central coordinator for NH operations.
    Manages sessions, agents, and task execution with full transparency.
    """
    
    def __init__(self):
        self.manager = get_connection_manager()
        self.session_id: Optional[str] = None
        self.session: Optional[SessionState] = None
        self.agents: Dict[str, Agent] = {}
        self.task_queue: List[TaskDefinition] = []
        self.task_results: Dict[str, Any] = {}
        self._is_running = False
        self._is_paused = False
        self._should_cancel = False
    
    # ==========================================================================
    # Session Management
    # ==========================================================================
    
    async def create_session(self, name: str) -> str:
        """Create new execution session"""
        self.session_id = self.manager.create_session(name)
        self.session = self.manager.get_session(self.session_id)
        
        await self.emit(NHEvent(
            category=EventCategory.SYSTEM,
            event_type=EventType.SYSTEM_START,
            severity=Severity.INFO,
            session_id=self.session_id,
            message=f"Session created: {name}",
        ))
        
        return self.session_id
    
    async def emit(self, event: NHEvent):
        """Emit event to all subscribers"""
        if not event.session_id:
            event.session_id = self.session_id
        await self.manager.emit_event(event)
    
    # ==========================================================================
    # Agent Management
    # ==========================================================================
    
    async def spawn_agent(self, config: AgentConfig) -> Agent:
        """Create and register new agent"""
        agent = Agent(config, self)
        self.agents[config.id] = agent
        
        # Update session state
        if self.session:
            self.session.agents[config.id] = agent.state
        
        await self.emit(NHEvent(
            category=EventCategory.AGENT,
            event_type=EventType.AGENT_SPAWN,
            severity=Severity.INFO,
            session_id=self.session_id,
            agent_id=config.id,
            message=f"Agent spawned: {config.name} ({config.role.value})",
            details={
                "name": config.name,
                "role": config.role.value,
                "model": config.model,
            },
        ))
        
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    def get_agent_by_role(self, role: AgentRole) -> Optional[Agent]:
        """Get first agent with given role"""
        for agent in self.agents.values():
            if agent.config.role == role:
                return agent
        return None
    
    # ==========================================================================
    # Task Execution
    # ==========================================================================
    
    async def queue_task(self, task: TaskDefinition):
        """Add task to execution queue"""
        self.task_queue.append(task)
        
        if self.session:
            self.session.total_tasks += 1
            if task.sub_tasks:
                self.session.total_tasks += len(task.sub_tasks)
        
        await self.emit(NHEvent(
            category=EventCategory.AGENT,
            event_type=EventType.TASK_QUEUE,
            severity=Severity.INFO,
            session_id=self.session_id,
            task_id=task.id,
            message=f"Task queued: {task.name}",
        ))
    
    async def execute_task(self, task: TaskDefinition, parent_task_id: str = None) -> Any:
        """Execute a single task with full event emission"""
        
        # Check dependencies
        for dep_id in task.depends_on:
            if dep_id not in self.task_results:
                await self.emit(NHEvent(
                    category=EventCategory.AGENT,
                    event_type=EventType.TASK_FAIL,
                    severity=Severity.ERROR,
                    session_id=self.session_id,
                    task_id=task.id,
                    message=f"Dependency not met: {dep_id}",
                ))
                return None
        
        # Get assigned agent
        agent = self.get_agent_by_role(task.agent_role)
        if not agent:
            # Spawn agent if needed
            agent = await self.spawn_agent(AgentConfig(
                name=f"{task.agent_role.value.title()} Agent",
                role=task.agent_role,
            ))
        
        # Emit task start
        await self.emit(NHEvent(
            category=EventCategory.AGENT,
            event_type=EventType.TASK_START,
            severity=Severity.INFO,
            session_id=self.session_id,
            task_id=task.id,
            agent_id=agent.config.id,
            message=f"Starting: {task.name}",
        ))
        
        start_time = datetime.utcnow()
        
        try:
            # Execute sub-tasks first
            for i, sub_task in enumerate(task.sub_tasks):
                if self._should_cancel:
                    break
                
                while self._is_paused:
                    await asyncio.sleep(0.1)
                
                # Emit progress
                await self.emit(EventBuilder.task_progress(
                    task_id=task.id,
                    message=f"Sub-task {i+1}/{len(task.sub_tasks)}",
                    current=i,
                    total=len(task.sub_tasks),
                    step_name=sub_task.name,
                    session_id=self.session_id,
                ))
                
                await self.execute_task(sub_task, task.id)
            
            # Execute main task
            result = None
            if task.execute_fn:
                # Gather inputs from dependencies
                inputs = {
                    dep_id: self.task_results.get(dep_id)
                    for dep_id in task.depends_on
                }
                result = await task.execute_fn(agent, inputs)
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Store result
            self.task_results[task.id] = result
            
            # Update session
            if self.session:
                self.session.completed_tasks += 1
                self.session.progress_percent = (
                    self.session.completed_tasks / self.session.total_tasks * 100
                    if self.session.total_tasks > 0 else 0
                )
            
            # Emit completion
            await self.emit(NHEvent(
                category=EventCategory.AGENT,
                event_type=EventType.TASK_COMPLETE,
                severity=Severity.SUCCESS,
                session_id=self.session_id,
                task_id=task.id,
                agent_id=agent.config.id,
                message=f"Completed: {task.name}",
                duration_ms=duration_ms,
            ))
            
            await agent.complete_task()
            return result
            
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if self.session:
                self.session.failed_tasks += 1
            
            await self.emit(NHEvent(
                category=EventCategory.AGENT,
                event_type=EventType.TASK_FAIL,
                severity=Severity.ERROR,
                session_id=self.session_id,
                task_id=task.id,
                agent_id=agent.config.id,
                message=f"Failed: {task.name} - {str(e)}",
                duration_ms=duration_ms,
                details={"error": str(e)},
            ))
            
            await agent.fail_task(str(e))
            raise
    
    async def run(self):
        """Execute all queued tasks"""
        self._is_running = True
        self._should_cancel = False
        
        if self.session:
            self.session.status = "running"
        
        await self.emit(NHEvent(
            category=EventCategory.SYSTEM,
            event_type=EventType.SYSTEM_READY,
            severity=Severity.INFO,
            session_id=self.session_id,
            message="Orchestrator started execution",
        ))
        
        try:
            for task in self.task_queue:
                if self._should_cancel:
                    break
                
                while self._is_paused:
                    await asyncio.sleep(0.1)
                
                await self.execute_task(task)
            
            if not self._should_cancel:
                if self.session:
                    self.session.status = "completed"
                    self.session.completed_at = datetime.utcnow().isoformat()
                
                await self.emit(NHEvent(
                    category=EventCategory.SYSTEM,
                    event_type=EventType.SYSTEM_SHUTDOWN,
                    severity=Severity.SUCCESS,
                    session_id=self.session_id,
                    message="All tasks completed successfully",
                ))
        
        except Exception as e:
            if self.session:
                self.session.status = "failed"
            
            await self.emit(NHEvent(
                category=EventCategory.SYSTEM,
                event_type=EventType.SYSTEM_ERROR,
                severity=Severity.CRITICAL,
                session_id=self.session_id,
                message=f"Orchestrator error: {str(e)}",
            ))
        
        finally:
            self._is_running = False
    
    def pause(self):
        """Pause execution"""
        self._is_paused = True
        if self.session:
            self.session.status = "paused"
    
    def resume(self):
        """Resume execution"""
        self._is_paused = False
        if self.session:
            self.session.status = "running"
    
    def cancel(self):
        """Cancel execution"""
        self._should_cancel = True
        self._is_paused = False


# ==========================================================================
# Convenience Functions
# ==========================================================================

async def create_orchestrator(session_name: str) -> Orchestrator:
    """Create and initialize orchestrator with session"""
    orchestrator = Orchestrator()
    await orchestrator.create_session(session_name)
    return orchestrator
