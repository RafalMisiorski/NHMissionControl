"""
NH Nerve Center - Full Transparency Infrastructure
===================================================

Real-time event streaming and agent orchestration for NH Mission Control.
"""

from .events import (
    NHEvent,
    EventCategory,
    EventType,
    Severity,
    EventBuilder,
    SessionState,
    TaskState,
    AgentState,
)
from .websocket_hub import (
    ConnectionManager,
    get_connection_manager,
    websocket_endpoint,
    emit_events,
    WSMessage,
    WSMessageType,
)
from .orchestrator import (
    Orchestrator,
    Agent,
    AgentConfig,
    AgentRole,
    TaskDefinition,
    create_orchestrator,
)
from .analyzer_engine import (
    ProjectAnalyzer,
    ExecutionEngine,
    ExecutionPlan,
    ExecutionPhase,
    ExecutionTask,
    AnalysisResult,
    TechStack,
    ProjectFile,
    LogEntry,
    TaskType,
    PhaseStatus,
    LogLevel,
    generate_refactoring_plan,
)
from .asset_registry import (
    AssetRegistry,
    AssetType,
    AssetStatus,
    ProjectStatus as AssetProjectStatus,
    ProjectPriority,
    AIToolCapability,
    TaskComplexity,
    Asset,
    HardwareAsset,
    ServiceAsset,
    APIAsset,
    AIToolAsset,
    ProjectAsset,
    InfrastructureAsset,
    DelegationRule,
    DelegationMatrix,
)
from .syncwave_client import (
    SyncWaveClient,
    NotificationPriority,
    NotificationCategory,
    NotificationRequest,
    TaskNotification,
    BlockerAlert,
    ProgressUpdate,
    BlockerMonitor,
)
from .dispatcher import (
    CCDispatcher,
    RoutingEngine,
    DispatchTask,
    ProjectPriority,
    AITool,
    RoutingRule,
)
from .system_status import (
    SYSTEM_SESSION_ID,
    initialize_system_session,
    emit_service_status,
    run_health_checks,
    startup_system_status,
)

__all__ = [
    # Events
    "NHEvent",
    "EventCategory",
    "EventType",
    "Severity",
    "EventBuilder",
    "SessionState",
    "TaskState",
    "AgentState",
    # WebSocket
    "ConnectionManager",
    "get_connection_manager",
    "websocket_endpoint",
    "emit_events",
    "WSMessage",
    "WSMessageType",
    # Orchestrator
    "Orchestrator",
    "Agent",
    "AgentConfig",
    "AgentRole",
    "TaskDefinition",
    "create_orchestrator",
    # Analyzer
    "ProjectAnalyzer",
    "ExecutionEngine",
    "ExecutionPlan",
    "ExecutionPhase",
    "ExecutionTask",
    "AnalysisResult",
    "TechStack",
    "ProjectFile",
    "LogEntry",
    "TaskType",
    "PhaseStatus",
    "LogLevel",
    "generate_refactoring_plan",
    # Asset Registry
    "AssetRegistry",
    "AssetType",
    "AssetStatus",
    "AssetProjectStatus",
    "ProjectPriority",
    "AIToolCapability",
    "TaskComplexity",
    "Asset",
    "HardwareAsset",
    "ServiceAsset",
    "APIAsset",
    "AIToolAsset",
    "ProjectAsset",
    "InfrastructureAsset",
    "DelegationRule",
    "DelegationMatrix",
    # SyncWave Client
    "SyncWaveClient",
    "NotificationPriority",
    "NotificationCategory",
    "NotificationRequest",
    "TaskNotification",
    "BlockerAlert",
    "ProgressUpdate",
    "BlockerMonitor",
    # CC Dispatcher
    "CCDispatcher",
    "RoutingEngine",
    "DispatchTask",
    "ProjectPriority",
    "AITool",
    "RoutingRule",
    # System Status
    "SYSTEM_SESSION_ID",
    "initialize_system_session",
    "emit_service_status",
    "run_health_checks",
    "startup_system_status",
]
