"""
NH Asset Registry - Core Schema
================================

Central knowledge base for all resources available to NH:
- Hardware assets (printers, scanners, servers)
- Software/Service subscriptions (APIs, CLI tools, platforms)
- Projects (active, paused, completed)
- AI Tool capabilities (who does what best)

This is NH's "memory" of what resources exist and how to use them.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from uuid import uuid4
import json


# ==========================================================================
# Enums
# ==========================================================================

class AssetType(str, Enum):
    """Top-level asset categories"""
    HARDWARE = "hardware"
    SOFTWARE = "software"
    SERVICE = "service"
    API = "api"
    PROJECT = "project"
    AI_TOOL = "ai_tool"
    SUBSCRIPTION = "subscription"
    INFRASTRUCTURE = "infrastructure"


class AssetStatus(str, Enum):
    """Asset availability status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    PENDING = "pending"
    MAINTENANCE = "maintenance"


class ProjectStatus(str, Enum):
    """Project lifecycle status"""
    IDEA = "idea"
    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ProjectPriority(str, Enum):
    """Project priority levels"""
    CRITICAL = "critical"      # NH core, income-generating
    HIGH = "high"              # Important for goals
    MEDIUM = "medium"          # Nice to have
    LOW = "low"                # Backburner
    EXPERIMENTAL = "experimental"  # Learning/exploration


class AIToolCapability(str, Enum):
    """What AI tools can do"""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DOCUMENTATION = "documentation"
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    REFACTORING = "refactoring"
    DATA_ANALYSIS = "data_analysis"
    RESEARCH = "research"
    CREATIVE = "creative"
    AUTOMATION = "automation"
    DEVOPS = "devops"


class TaskComplexity(str, Enum):
    """Task complexity for delegation"""
    TRIVIAL = "trivial"        # Simple, repetitive
    LOW = "low"                # Straightforward
    MEDIUM = "medium"          # Some nuance required
    HIGH = "high"              # Complex reasoning
    CRITICAL = "critical"      # Mission-critical, needs best


# ==========================================================================
# Base Asset
# ==========================================================================

@dataclass
class Asset:
    """Base class for all assets"""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    type: AssetType = AssetType.SOFTWARE
    status: AssetStatus = AssetStatus.ACTIVE
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    notes: str = ""
    
    # Links
    url: Optional[str] = None
    documentation_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


# ==========================================================================
# Hardware Assets
# ==========================================================================

@dataclass
class HardwareAsset(Asset):
    """Physical hardware"""
    type: AssetType = AssetType.HARDWARE
    
    # Hardware specifics
    manufacturer: str = ""
    model: str = ""
    serial_number: Optional[str] = None
    purchase_date: Optional[str] = None
    warranty_until: Optional[str] = None
    
    # Capabilities
    capabilities: List[str] = field(default_factory=list)
    
    # Location
    location: str = "home_office"
    
    # Usage
    usage_notes: str = ""
    maintenance_schedule: Optional[str] = None


# ==========================================================================
# Service/Subscription Assets
# ==========================================================================

@dataclass
class ServiceAsset(Asset):
    """Software service or subscription"""
    type: AssetType = AssetType.SERVICE
    
    # Subscription details
    provider: str = ""
    plan_name: str = ""
    plan_tier: str = ""  # free, pro, enterprise
    
    # Costs
    monthly_cost_usd: float = 0.0
    billing_cycle: str = "monthly"  # monthly, yearly, usage
    
    # Limits
    rate_limits: Dict[str, Any] = field(default_factory=dict)
    quotas: Dict[str, Any] = field(default_factory=dict)
    
    # Access
    api_key_location: str = ""  # env var name or secret manager path
    auth_method: str = ""  # api_key, oauth, jwt
    
    # Renewal
    renewal_date: Optional[str] = None
    auto_renew: bool = True


@dataclass
class APIAsset(Asset):
    """API access"""
    type: AssetType = AssetType.API
    
    # API details
    provider: str = ""
    base_url: str = ""
    version: str = ""
    
    # Authentication
    auth_method: str = ""
    api_key_env_var: str = ""
    
    # Limits
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_day: Optional[int] = None
    monthly_quota: Optional[int] = None
    
    # Costs
    cost_per_request: float = 0.0
    cost_per_1k_tokens: float = 0.0
    monthly_free_tier: Optional[int] = None


# ==========================================================================
# AI Tool Assets
# ==========================================================================

@dataclass
class AIToolAsset(Asset):
    """AI tool or model"""
    type: AssetType = AssetType.AI_TOOL
    
    # Tool details
    provider: str = ""
    model_name: str = ""
    cli_command: Optional[str] = None
    
    # Capabilities - what it's good at
    capabilities: List[AIToolCapability] = field(default_factory=list)
    
    # Optimal use cases
    best_for: List[str] = field(default_factory=list)
    avoid_for: List[str] = field(default_factory=list)
    
    # Complexity range it handles well
    min_complexity: TaskComplexity = TaskComplexity.TRIVIAL
    max_complexity: TaskComplexity = TaskComplexity.CRITICAL
    
    # Performance characteristics
    speed: str = "medium"  # fast, medium, slow
    quality: str = "medium"  # low, medium, high, excellent
    cost_efficiency: str = "medium"  # low, medium, high
    
    # Context
    context_window: int = 0
    supports_vision: bool = False
    supports_code_execution: bool = False
    
    # Costs
    cost_per_1k_input_tokens: float = 0.0
    cost_per_1k_output_tokens: float = 0.0


# ==========================================================================
# Project Assets
# ==========================================================================

@dataclass
class ProjectAsset(Asset):
    """Project definition"""
    type: AssetType = AssetType.PROJECT
    
    # Project identity
    codename: str = ""
    full_name: str = ""
    
    # Status
    project_status: ProjectStatus = ProjectStatus.IDEA
    priority: ProjectPriority = ProjectPriority.MEDIUM
    
    # Classification
    category: str = ""  # trading, ai, automation, web, etc.
    tech_stack: List[str] = field(default_factory=list)
    
    # Repository
    repo_url: Optional[str] = None
    repo_path: Optional[str] = None
    branch: str = "main"
    
    # Progress
    completion_percent: float = 0.0
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    
    # Time tracking
    started_at: Optional[str] = None
    target_completion: Optional[str] = None
    last_worked_on: Optional[str] = None
    estimated_hours_remaining: Optional[float] = None
    
    # Income potential
    income_potential: str = ""  # none, low, medium, high, critical
    monetization_strategy: str = ""
    
    # Dependencies
    depends_on_projects: List[str] = field(default_factory=list)  # Project IDs
    depends_on_assets: List[str] = field(default_factory=list)    # Asset IDs
    
    # NH integration
    nh_layer: Optional[int] = None  # Which NH layer this belongs to
    can_delegate_to: List[str] = field(default_factory=list)  # AI tools that can work on this


# ==========================================================================
# Infrastructure Assets
# ==========================================================================

@dataclass
class InfrastructureAsset(Asset):
    """Infrastructure/Platform assets"""
    type: AssetType = AssetType.INFRASTRUCTURE
    
    # Platform details
    provider: str = ""
    platform_type: str = ""  # paas, iaas, container, serverless
    
    # Resources
    compute_resources: Dict[str, Any] = field(default_factory=dict)
    storage_gb: float = 0.0
    bandwidth_gb: float = 0.0
    
    # Costs
    monthly_cost_usd: float = 0.0
    usage_based: bool = False
    
    # Access
    dashboard_url: str = ""
    cli_tool: str = ""
    
    # Deployed services
    deployed_services: List[str] = field(default_factory=list)


# ==========================================================================
# Tool Delegation Rules
# ==========================================================================

@dataclass
class DelegationRule:
    """Rule for delegating work to AI tools"""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    
    # Conditions
    task_types: List[AIToolCapability] = field(default_factory=list)
    complexity_range: tuple = (TaskComplexity.TRIVIAL, TaskComplexity.CRITICAL)
    project_priorities: List[ProjectPriority] = field(default_factory=list)
    
    # Target tool
    primary_tool: str = ""  # AI tool ID
    fallback_tools: List[str] = field(default_factory=list)
    
    # Rationale
    rationale: str = ""
    
    # Constraints
    requires_review: bool = False
    max_autonomous_changes: int = 10  # Max files to change without review
    

@dataclass
class DelegationMatrix:
    """Complete delegation configuration"""
    rules: List[DelegationRule] = field(default_factory=list)
    default_tool: str = ""  # Default AI tool ID
    
    def get_tool_for_task(
        self,
        task_type: AIToolCapability,
        complexity: TaskComplexity,
        project_priority: ProjectPriority = None,
    ) -> str:
        """Find best tool for a task"""
        for rule in self.rules:
            if task_type in rule.task_types:
                min_c, max_c = rule.complexity_range
                complexity_order = list(TaskComplexity)
                if (complexity_order.index(min_c) <= 
                    complexity_order.index(complexity) <= 
                    complexity_order.index(max_c)):
                    if not rule.project_priorities or project_priority in rule.project_priorities:
                        return rule.primary_tool
        
        return self.default_tool


# ==========================================================================
# Asset Registry
# ==========================================================================

@dataclass
class AssetRegistry:
    """Central registry of all assets"""
    
    # Collections
    hardware: Dict[str, HardwareAsset] = field(default_factory=dict)
    services: Dict[str, ServiceAsset] = field(default_factory=dict)
    apis: Dict[str, APIAsset] = field(default_factory=dict)
    ai_tools: Dict[str, AIToolAsset] = field(default_factory=dict)
    projects: Dict[str, ProjectAsset] = field(default_factory=dict)
    infrastructure: Dict[str, InfrastructureAsset] = field(default_factory=dict)
    
    # Delegation
    delegation_matrix: DelegationMatrix = field(default_factory=DelegationMatrix)
    
    # Metadata
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str = "1.0.0"
    
    def add_asset(self, asset: Asset):
        """Add asset to appropriate collection"""
        if isinstance(asset, HardwareAsset):
            self.hardware[asset.id] = asset
        elif isinstance(asset, ServiceAsset):
            self.services[asset.id] = asset
        elif isinstance(asset, APIAsset):
            self.apis[asset.id] = asset
        elif isinstance(asset, AIToolAsset):
            self.ai_tools[asset.id] = asset
        elif isinstance(asset, ProjectAsset):
            self.projects[asset.id] = asset
        elif isinstance(asset, InfrastructureAsset):
            self.infrastructure[asset.id] = asset
        
        self.last_updated = datetime.utcnow().isoformat()
    
    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """Get asset by ID from any collection"""
        for collection in [
            self.hardware, self.services, self.apis,
            self.ai_tools, self.projects, self.infrastructure
        ]:
            if asset_id in collection:
                return collection[asset_id]
        return None
    
    def get_active_projects(self) -> List[ProjectAsset]:
        """Get all active projects"""
        return [p for p in self.projects.values() 
                if p.project_status == ProjectStatus.ACTIVE]
    
    def get_projects_by_priority(self, priority: ProjectPriority) -> List[ProjectAsset]:
        """Get projects by priority"""
        return [p for p in self.projects.values() 
                if p.priority == priority]
    
    def get_tool_for_task(
        self,
        task_type: AIToolCapability,
        complexity: TaskComplexity,
        project_priority: ProjectPriority = None,
    ) -> Optional[AIToolAsset]:
        """Get best AI tool for a task"""
        tool_id = self.delegation_matrix.get_tool_for_task(
            task_type, complexity, project_priority
        )
        return self.ai_tools.get(tool_id)
    
    def get_available_capabilities(self) -> Dict[AIToolCapability, List[str]]:
        """Get all available capabilities and which tools provide them"""
        capabilities = {}
        for tool in self.ai_tools.values():
            if tool.status == AssetStatus.ACTIVE:
                for cap in tool.capabilities:
                    if cap not in capabilities:
                        capabilities[cap] = []
                    capabilities[cap].append(tool.id)
        return capabilities
    
    def estimate_monthly_costs(self) -> Dict[str, float]:
        """Estimate total monthly costs"""
        return {
            "services": sum(s.monthly_cost_usd for s in self.services.values() 
                          if s.status == AssetStatus.ACTIVE),
            "infrastructure": sum(i.monthly_cost_usd for i in self.infrastructure.values()
                                 if i.status == AssetStatus.ACTIVE),
            "total": sum(s.monthly_cost_usd for s in self.services.values() 
                        if s.status == AssetStatus.ACTIVE) +
                    sum(i.monthly_cost_usd for i in self.infrastructure.values()
                        if i.status == AssetStatus.ACTIVE)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "hardware": {k: v.to_dict() for k, v in self.hardware.items()},
            "services": {k: v.to_dict() for k, v in self.services.items()},
            "apis": {k: v.to_dict() for k, v in self.apis.items()},
            "ai_tools": {k: v.to_dict() for k, v in self.ai_tools.items()},
            "projects": {k: v.to_dict() for k, v in self.projects.items()},
            "infrastructure": {k: v.to_dict() for k, v in self.infrastructure.items()},
            "last_updated": self.last_updated,
            "version": self.version,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON"""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    def summary(self) -> str:
        """Generate human-readable summary"""
        active_projects = self.get_active_projects()
        costs = self.estimate_monthly_costs()
        
        return f"""
NH Asset Registry Summary
=========================

Hardware Assets: {len(self.hardware)}
Services/Subscriptions: {len(self.services)}
API Integrations: {len(self.apis)}
AI Tools: {len(self.ai_tools)}
Projects: {len(self.projects)} ({len(active_projects)} active)
Infrastructure: {len(self.infrastructure)}

Estimated Monthly Costs: ${costs['total']:.2f}

Active Projects:
{chr(10).join(f"  - [{p.priority.value.upper()}] {p.name} ({p.completion_percent:.0f}%)" for p in active_projects[:10])}

Last Updated: {self.last_updated}
"""
