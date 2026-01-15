"""
NH Nerve Center - WebSocket Hub
================================

Real-time event streaming via WebSocket.
Clients connect to receive live updates on all NH operations.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Set, Optional, Callable, Any, List
from dataclasses import dataclass, field
from uuid import uuid4
from enum import Enum
import logging

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from .events import (
    NHEvent, EventCategory, EventType, Severity,
    EventBuilder, SessionState, TaskState, AgentState
)

logger = logging.getLogger(__name__)


# ==========================================================================
# WebSocket Message Types
# ==========================================================================

class WSMessageType(str, Enum):
    """WebSocket message types"""
    # Client -> Server
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"
    COMMAND = "command"
    
    # Server -> Client
    EVENT = "event"
    STATE = "state"
    STATE_DELTA = "state_delta"
    PONG = "pong"
    ERROR = "error"
    CONNECTED = "connected"


@dataclass
class WSMessage:
    """WebSocket message structure"""
    type: WSMessageType
    payload: Any
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    message_id: str = field(default_factory=lambda: str(uuid4()))
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
        })
    
    @classmethod
    def from_json(cls, data: str) -> 'WSMessage':
        parsed = json.loads(data)
        return cls(
            type=WSMessageType(parsed["type"]),
            payload=parsed.get("payload"),
            timestamp=parsed.get("timestamp", datetime.utcnow().isoformat()),
            message_id=parsed.get("message_id", str(uuid4())),
        )


# ==========================================================================
# Connection Manager
# ==========================================================================

@dataclass
class ClientConnection:
    """Represents a connected WebSocket client"""
    id: str
    websocket: WebSocket
    connected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    subscribed_sessions: Set[str] = field(default_factory=set)
    subscribed_categories: Set[EventCategory] = field(default_factory=set)
    filter_severity: Severity = Severity.DEBUG  # Minimum severity to receive
    is_active: bool = True


class ConnectionManager:
    """
    Manages WebSocket connections and event distribution.
    Singleton that handles all real-time communication.
    """
    
    _instance: Optional['ConnectionManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.connections: Dict[str, ClientConnection] = {}
        self.sessions: Dict[str, SessionState] = {}
        self.event_history: List[NHEvent] = []
        self.max_history: int = 10000
        self._lock = asyncio.Lock()
        self._initialized = True
    
    async def connect(self, websocket: WebSocket) -> str:
        """Accept new WebSocket connection"""
        await websocket.accept()
        
        client_id = str(uuid4())
        connection = ClientConnection(
            id=client_id,
            websocket=websocket,
        )
        
        async with self._lock:
            self.connections[client_id] = connection
        
        # Send connection confirmation
        await self._send_to_client(client_id, WSMessage(
            type=WSMessageType.CONNECTED,
            payload={
                "client_id": client_id,
                "active_sessions": list(self.sessions.keys()),
            }
        ))
        
        logger.info(f"Client {client_id} connected. Total: {len(self.connections)}")
        return client_id
    
    async def disconnect(self, client_id: str):
        """Handle client disconnection"""
        async with self._lock:
            if client_id in self.connections:
                self.connections[client_id].is_active = False
                del self.connections[client_id]
        
        logger.info(f"Client {client_id} disconnected. Total: {len(self.connections)}")
    
    async def handle_message(self, client_id: str, message: WSMessage):
        """Handle incoming message from client"""
        connection = self.connections.get(client_id)
        if not connection:
            return
        
        if message.type == WSMessageType.PING:
            await self._send_to_client(client_id, WSMessage(
                type=WSMessageType.PONG,
                payload={"received": message.timestamp}
            ))
        
        elif message.type == WSMessageType.SUBSCRIBE:
            session_id = message.payload.get("session_id")
            if session_id:
                connection.subscribed_sessions.add(session_id)
                # Send current state
                if session_id in self.sessions:
                    await self._send_to_client(client_id, WSMessage(
                        type=WSMessageType.STATE,
                        payload=self.sessions[session_id].to_dict()
                    ))
        
        elif message.type == WSMessageType.UNSUBSCRIBE:
            session_id = message.payload.get("session_id")
            if session_id:
                connection.subscribed_sessions.discard(session_id)
        
        elif message.type == WSMessageType.COMMAND:
            # Handle commands like pause, resume, cancel
            await self._handle_command(client_id, message.payload)
    
    async def _handle_command(self, client_id: str, payload: Dict[str, Any]):
        """Handle command from client"""
        command = payload.get("command")
        session_id = payload.get("session_id")
        
        # Emit event for command handlers to pick up
        event = NHEvent(
            category=EventCategory.USER,
            event_type=EventType.AGENT_ACTION,
            session_id=session_id,
            message=f"User command: {command}",
            details=payload,
        )
        await self.emit_event(event)
    
    async def _send_to_client(self, client_id: str, message: WSMessage):
        """Send message to specific client"""
        connection = self.connections.get(client_id)
        if not connection or not connection.is_active:
            return
        
        try:
            if connection.websocket.client_state == WebSocketState.CONNECTED:
                await connection.websocket.send_text(message.to_json())
        except Exception as e:
            logger.error(f"Error sending to {client_id}: {e}")
            connection.is_active = False
    
    async def broadcast_event(self, event: NHEvent):
        """Broadcast event to all subscribed clients"""
        message = WSMessage(
            type=WSMessageType.EVENT,
            payload=event.to_dict()
        )
        
        for client_id, connection in list(self.connections.items()):
            if not connection.is_active:
                continue
            
            # Check subscription filters
            if event.session_id and event.session_id not in connection.subscribed_sessions:
                # Client not subscribed to this session, skip unless subscribed to all
                if connection.subscribed_sessions:  # Has specific subscriptions
                    continue
            
            # Check severity filter
            severity_order = [Severity.DEBUG, Severity.INFO, Severity.WARNING, Severity.ERROR, Severity.CRITICAL]
            if severity_order.index(event.severity) < severity_order.index(connection.filter_severity):
                continue
            
            await self._send_to_client(client_id, message)
    
    async def broadcast_state(self, session_id: str):
        """Broadcast full state update for a session"""
        if session_id not in self.sessions:
            return
        
        message = WSMessage(
            type=WSMessageType.STATE,
            payload=self.sessions[session_id].to_dict()
        )
        
        for client_id, connection in list(self.connections.items()):
            if not connection.is_active:
                continue
            
            if not connection.subscribed_sessions or session_id in connection.subscribed_sessions:
                await self._send_to_client(client_id, message)
    
    # ==========================================================================
    # Session Management
    # ==========================================================================
    
    def create_session(self, name: str) -> str:
        """Create new execution session"""
        session_id = str(uuid4())
        self.sessions[session_id] = SessionState(
            id=session_id,
            name=name,
        )
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, **updates):
        """Update session state"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)
    
    # ==========================================================================
    # Event Emission
    # ==========================================================================
    
    async def emit_event(self, event: NHEvent):
        """
        Emit event to all subscribers and update state.
        This is the main entry point for all NH operations.
        """
        # Store in history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history:]
        
        # Update session state based on event
        if event.session_id:
            await self._update_state_from_event(event)
        
        # Broadcast to clients
        await self.broadcast_event(event)
    
    async def _update_state_from_event(self, event: NHEvent):
        """Update session state based on event"""
        session = self.sessions.get(event.session_id)
        if not session:
            return
        
        # Add event to session
        session.events.append(event)
        
        # Update based on event type
        if event.event_type == EventType.TASK_START:
            session.status = "running"
        
        elif event.event_type == EventType.TASK_COMPLETE:
            session.completed_tasks += 1
            if session.total_tasks > 0:
                session.progress_percent = (session.completed_tasks / session.total_tasks) * 100
        
        elif event.event_type == EventType.TASK_FAIL:
            session.failed_tasks += 1
        
        elif event.event_type == EventType.LLM_COMPLETE:
            if event.tokens_input:
                session.total_tokens_input += event.tokens_input
            if event.tokens_output:
                session.total_tokens_output += event.tokens_output
            if event.cost_usd:
                session.total_cost_usd += event.cost_usd
        
        elif event.event_type == EventType.FILE_READ:
            path = event.details.get("path")
            if path and path not in session.files_read:
                session.files_read.append(path)
        
        elif event.event_type == EventType.FILE_WRITE:
            path = event.details.get("path")
            if path and path not in session.files_written:
                session.files_written.append(path)
        
        elif event.event_type == EventType.FILE_CREATE:
            path = event.details.get("path")
            if path and path not in session.files_created:
                session.files_created.append(path)
        
        # Broadcast updated state
        await self.broadcast_state(event.session_id)


# ==========================================================================
# Global Instance
# ==========================================================================

_connection_manager: Optional[ConnectionManager] = None

def get_connection_manager() -> ConnectionManager:
    """Get or create the global connection manager"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


# ==========================================================================
# FastAPI WebSocket Endpoint
# ==========================================================================

async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint handler.
    Add to your FastAPI app:
    
    @app.websocket("/api/v1/nerve-center/ws")
    async def nerve_center_ws(websocket: WebSocket):
        await websocket_endpoint(websocket)
    """
    manager = get_connection_manager()
    client_id = await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = WSMessage.from_json(data)
                await manager.handle_message(client_id, message)
            except json.JSONDecodeError:
                await manager._send_to_client(client_id, WSMessage(
                    type=WSMessageType.ERROR,
                    payload={"error": "Invalid JSON"}
                ))
    except WebSocketDisconnect:
        await manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        await manager.disconnect(client_id)


# ==========================================================================
# Helper Decorator for Event Emission
# ==========================================================================

def emit_events(session_id: str = None, task_id: str = None):
    """
    Decorator that automatically emits start/complete/error events.
    
    Usage:
    @emit_events(session_id="my-session")
    async def my_function():
        ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            manager = get_connection_manager()
            func_name = func.__name__
            
            # Emit start event
            await manager.emit_event(NHEvent(
                category=EventCategory.AGENT,
                event_type=EventType.TASK_START,
                session_id=session_id,
                task_id=task_id,
                message=f"Starting: {func_name}",
            ))
            
            start_time = datetime.utcnow()
            
            try:
                result = await func(*args, **kwargs)
                
                duration = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                # Emit complete event
                await manager.emit_event(NHEvent(
                    category=EventCategory.AGENT,
                    event_type=EventType.TASK_COMPLETE,
                    session_id=session_id,
                    task_id=task_id,
                    message=f"Completed: {func_name}",
                    duration_ms=duration,
                ))
                
                return result
                
            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                # Emit error event
                await manager.emit_event(NHEvent(
                    category=EventCategory.AGENT,
                    event_type=EventType.TASK_FAIL,
                    severity=Severity.ERROR,
                    session_id=session_id,
                    task_id=task_id,
                    message=f"Failed: {func_name} - {str(e)}",
                    duration_ms=duration,
                    details={"error": str(e)},
                ))
                raise
        
        return wrapper
    return decorator
