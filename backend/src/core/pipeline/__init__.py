"""
NH Pipeline Orchestrator - "Taśmociąg"
======================================

The Pipeline Orchestrator manages task execution through multiple stages
with handoff tokens (gate verification), auto-correction (Neural Ralph),
and escalation management.

EPOCH 7 - Pipeline Orchestrator module.
EPOCH 8 - CC Session Manager (Visibility & Reliability)

Components:
- PipelineOrchestrator: Main execution engine
- HandoffTokenGenerator: Gate token creation with trust scoring
- NeuralRalph: Auto-correction system
- HealthInspector: Verification system (pytest, lint, Playwright)
- ResourceManager: Dynamic port allocation
- EscalationManager: Agent upgrade path
- GuardrailsEngine: 4-layer constraint enforcement
- EpochManager: System versioning
- CCSessionManager: Claude Code session visibility & reliability (EPOCH 8)
"""

from src.core.pipeline.orchestrator import PipelineOrchestrator
from src.core.pipeline.handoff import HandoffTokenGenerator
from src.core.pipeline.neural_ralph import NeuralRalph
from src.core.pipeline.health_inspector import HealthInspector
from src.core.pipeline.resource_manager import ResourceManager
from src.core.pipeline.escalation import EscalationManager
from src.core.pipeline.guardrails import GuardrailsEngine
from src.core.pipeline.epochs import EpochManager
from src.core.pipeline.cc_session_manager import CCSessionManager

__all__ = [
    "PipelineOrchestrator",
    "HandoffTokenGenerator",
    "NeuralRalph",
    "HealthInspector",
    "ResourceManager",
    "EscalationManager",
    "GuardrailsEngine",
    "EpochManager",
    "CCSessionManager",
]
