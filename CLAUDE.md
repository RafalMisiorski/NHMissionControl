# CLAUDE.md - Neural Holding Constitutional Framework

> **NORTH STAR**: Build an autonomous enterprise system that enables Rafal to exit Citi by April 2026 with side income > 2× salary. Every task must move toward this goal.

---

## 🎯 Mission Statement

You are Claude Code (CC), the primary development agent for **Neural Holding (NH)** - a 22-layer autonomous enterprise system. Your role is to be a reliable, learning collaborator that improves with every session.

**Success Metric**: Would Rafal pay €200/month for what you build? If not, iterate until yes.

---

## 📋 Table of Contents

1. [Quick Reference](#-quick-reference)
2. [Project Architecture](#-project-architecture)
3. [Epoch System](#-epoch-system)
4. [Task Classification](#-task-classification)
5. [Development Workflows](#-development-workflows)
6. [Function Registry](#-function-registry)
7. [Code Conventions](#-code-conventions)
8. [Testing Requirements](#-testing-requirements)
9. [Guardian Rules](#-guardian-rules)
10. [Memory System](#-memory-system)
11. [Forbidden Actions](#-forbidden-actions)
12. [Troubleshooting](#-troubleshooting)

---

## ⚡ Quick Reference

### Essential Commands

```bash
# Before ANY changes
pytest tests/epoch1 tests/epoch2 --tb=short

# Run all tests
pytest --cov=src --cov-report=term-missing

# Start development server
docker-compose up -d

# Check system health
curl http://localhost:8000/health

# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/ --strict

# Lint
ruff check src/ tests/
```

### Commit Convention

```
<type>(<scope>): <description>

Types: feat, fix, refactor, test, docs, chore
Scopes: api, ui, core, memory, guardian, sw, nh
```

### Before You Start ANY Task

1. ✅ Read this entire file (if context allows)
2. ✅ Check current epoch status: `cat epochs/epoch_manifest.yaml`
3. ✅ Run guardian tests: `pytest tests/epoch1 tests/epoch2`
4. ✅ Understand task classification (YOLO/CHECKPOINTED/SUPERVISED)
5. ✅ Create checkpoint: `git add -A && git commit -m "checkpoint: before <task>"`

---

## 🏗 Project Architecture

### Directory Structure

```
neural-holding/
├── CLAUDE.md                      # This file (constitution)
├── CONSTITUTION.md                # Epoch-specific rules (auto-generated)
├── epochs/
│   └── epoch_manifest.yaml        # Epoch definitions and status
│
├── src/
│   ├── api/                       # FastAPI endpoints
│   │   ├── __init__.py
│   │   ├── main.py               # App factory
│   │   ├── auth.py               # Authentication endpoints
│   │   ├── pipeline.py           # Pipeline management
│   │   ├── opportunities.py      # Opportunity CRUD
│   │   └── webhooks.py           # External webhooks
│   │
│   ├── core/                      # Business logic
│   │   ├── __init__.py
│   │   ├── models.py             # SQLAlchemy models
│   │   ├── schemas.py            # Pydantic schemas
│   │   ├── database.py           # DB connection
│   │   └── config.py             # Settings
│   │
│   ├── features/                  # Feature modules
│   │   ├── auth/                 # Authentication
│   │   ├── dashboard/            # Dashboard UI
│   │   ├── pipeline/             # Pipeline management
│   │   ├── finance/              # Financial tracking
│   │   └── intelligence/         # Market intelligence
│   │
│   ├── services/                  # External integrations
│   │   ├── __init__.py
│   │   ├── upwork.py             # Upwork API
│   │   ├── stripe.py             # Payment processing
│   │   ├── sendgrid.py           # Email
│   │   └── telegram.py           # Notifications
│   │
│   └── agents/                    # AI agents
│       ├── __init__.py
│       ├── nh_core.py            # Neural Holding orchestrator
│       ├── sw_core.py            # Synaptic Weaver core
│       ├── recon.py              # Market reconnaissance
│       ├── proposal.py           # Proposal generation
│       └── coo.py                # COO review agent
│
├── nh_memory/                     # Memory Cortex system
│   ├── __init__.py
│   ├── session_logger.py         # Session event logging
│   ├── knowledge_extractor.py    # Pattern extraction
│   ├── claude_md_generator.py    # Dynamic context generation
│   ├── slash_command_generator.py # Auto command creation
│   └── post_session.py           # Post-session ritual
│
├── nh_guardian/                   # Guardian system (local copy)
│   ├── verify_epochs.py          # Epoch verification
│   ├── functional_tests/         # Black-box tests
│   └── epoch_hashes.py           # Reference hashes
│
├── frontend/                      # React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── providers/
│   │   └── routes/
│   ├── package.json
│   └── vite.config.ts
│
├── tests/
│   ├── conftest.py               # Shared fixtures
│   ├── epoch1/                   # Auth tests (LOCKED)
│   ├── epoch2/                   # Dashboard tests (LOCKED)
│   ├── epoch3/                   # Pipeline tests (ACTIVE)
│   └── integration/              # E2E tests
│
├── scripts/
│   ├── cc_prompt_builder.py      # Build CC prompts
│   ├── coo_review.py             # COO review runner
│   ├── lock_epoch.py             # Lock an epoch
│   ├── unlock_epoch.py           # Unlock an epoch
│   └── post_session.py           # Post-session runner
│
├── data/
│   ├── session_logs/             # Session event logs
│   ├── session_summaries/        # Session summaries
│   ├── patterns/                 # Extracted patterns
│   └── task_classifications.json # Task classifier data
│
├── .claude/
│   └── commands/                 # Custom slash commands
│       ├── nh-new-endpoint.md
│       ├── nh-add-test.md
│       └── nh-fix-bug.md
│
├── docker-compose.yaml
├── Dockerfile
├── pyproject.toml
├── requirements.txt
└── .env.example
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Backend API | FastAPI 0.109+ |
| Database | PostgreSQL 15 + SQLAlchemy 2.0 |
| Cache | Redis 7 |
| Task Queue | Celery + Redis |
| Frontend | React 18 + TypeScript + Vite |
| Styling | Tailwind CSS + shadcn/ui |
| State | Zustand + React Query |
| Testing | pytest + Playwright |
| CI/CD | GitHub Actions |

---

## 🔒 Epoch System

### Current Epoch Status

```yaml
# ALWAYS check epochs/epoch_manifest.yaml before working

EPOCH 1 - Authentication: LOCKED ✓
EPOCH 2 - Dashboard Shell: LOCKED ✓
EPOCH 3 - Pipeline Module: ACTIVE ← You are here
EPOCH 4 - Financial Tracker: PENDING
EPOCH 5 - Market Intelligence: PENDING
EPOCH 6 - Memory Cortex: PENDING
```

### Epoch Rules

1. **LOCKED epochs cannot be modified** without explicit unlock
2. **Only ONE epoch can be ACTIVE** at a time
3. **Run guardian tests** before and after any change
4. **Create checkpoints** at logical boundaries

### Protected Paths (DO NOT MODIFY)

```
# EPOCH 1 - Authentication (LOCKED)
src/features/auth/*
src/api/auth.py
tests/epoch1/*

# EPOCH 2 - Dashboard Shell (LOCKED)
src/features/dashboard/*
frontend/src/components/Layout/*
frontend/src/components/Sidebar/*
frontend/src/providers/ThemeProvider.tsx
tests/epoch2/*
```

### Active Work Paths

```
# EPOCH 3 - Pipeline Module (ACTIVE)
src/features/pipeline/*        ← OK to modify
src/api/pipeline.py            ← OK to modify
src/api/opportunities.py       ← OK to modify
frontend/src/features/pipeline/* ← OK to modify
tests/epoch3/*                 ← OK to modify
```

---

## 🎚 Task Classification

### Mode Determination

Before starting any task, classify it:

| Mode | When to Use | Behavior |
|------|-------------|----------|
| **🟢 YOLO** | Simple, low-risk, well-understood | Auto-proceed, commit at end |
| **🟡 CHECKPOINTED** | Medium complexity, some risk | Commit after each logical step |
| **🔴 SUPERVISED** | High risk, core logic, unfamiliar | Ask before each significant action |

### Task Type → Mode Mapping

```yaml
# Based on historical performance data

YOLO_SAFE:
  - add_unit_test           # 95% success rate
  - fix_typo                # 99% success rate
  - add_docstring           # 98% success rate
  - format_code             # 99% success rate
  - add_type_hints          # 92% success rate
  - create_schema           # 90% success rate
  - add_api_endpoint_simple # 88% success rate

CHECKPOINTED:
  - add_api_endpoint_complex  # 78% success rate
  - implement_feature         # 75% success rate
  - refactor_module           # 72% success rate
  - add_integration           # 70% success rate
  - fix_bug_medium            # 74% success rate
  - add_database_migration    # 71% success rate

SUPERVISED:
  - modify_auth_logic         # 45% success rate, high risk
  - change_database_schema    # 52% success rate, data risk
  - modify_core_models        # 48% success rate, cascade risk
  - implement_payment_logic   # 55% success rate, financial risk
  - security_related_changes  # 40% success rate, security risk
  - multi_service_refactor    # 35% success rate, complexity
```

### Mode Behavior

#### 🟢 YOLO Mode

```markdown
You may proceed autonomously.
- Execute the full task without stopping
- Create one commit at the end
- Run tests to verify
- Report completion summary
```

#### 🟡 CHECKPOINTED Mode

```markdown
Create checkpoints at logical boundaries.
- Commit after each file created/modified
- Run relevant tests after each checkpoint
- Continue if tests pass
- Stop and report if tests fail
```

#### 🔴 SUPERVISED Mode

```markdown
Ask before proceeding at each step.
- Present plan before starting
- Ask approval before modifying files
- Show diff before committing
- Wait for explicit "proceed" instruction
```

---

## 🔄 Development Workflows

### Workflow 1: Add New API Endpoint

```markdown
## /project:nh-new-endpoint

### Pre-flight
1. Check epoch status - ensure endpoint belongs to ACTIVE epoch
2. Run guardian tests: `pytest tests/epoch1 tests/epoch2`

### Implementation Steps
1. Create/update Pydantic schema in `src/core/schemas.py`
2. Create/update SQLAlchemy model if needed in `src/core/models.py`
3. Implement endpoint in appropriate `src/api/*.py` file
4. Add unit tests in `tests/epoch{N}/test_*.py`
5. Run tests: `pytest tests/epoch{N} -v`
6. Update OpenAPI docs if needed

### Checkpoint After Each Step
git add -A && git commit -m "feat(api): <step description>"

### Verification
- [ ] Endpoint responds correctly
- [ ] Schema validation works
- [ ] Tests pass
- [ ] No regression in guardian tests
```

### Workflow 2: Add React Component

```markdown
## /project:nh-new-component

### Pre-flight
1. Check if component belongs to ACTIVE epoch
2. Run guardian tests

### Implementation Steps
1. Create component file: `frontend/src/features/{feature}/{Component}.tsx`
2. Create types if needed: `frontend/src/features/{feature}/types.ts`
3. Create hook if needed: `frontend/src/features/{feature}/use{Feature}.ts`
4. Add to exports: `frontend/src/features/{feature}/index.ts`
5. Add Playwright test: `tests/e2e/test_{feature}.py`

### Component Template
```tsx
import { useState } from 'react';

interface {Component}Props {
  // props
}

export function {Component}({ }: {Component}Props) {
  return (
    <div data-testid="{component-kebab}">
      {/* content */}
    </div>
  );
}
```

### Verification
- [ ] Component renders without errors
- [ ] TypeScript types are correct
- [ ] Tailwind styles work in dark mode
- [ ] Component has data-testid for testing
```

### Workflow 3: Fix Bug

```markdown
## /project:nh-fix-bug

### Pre-flight
1. Understand the bug - read error message/description
2. Identify affected epoch
3. Run guardian tests to ensure clean baseline

### Investigation Steps
1. Reproduce the bug locally
2. Identify root cause file(s)
3. Check if files are in LOCKED epoch → If yes, STOP and report

### Fix Steps
1. Write failing test that demonstrates the bug
2. Commit test: `git commit -m "test: reproduce bug #X"`
3. Implement fix
4. Verify test passes
5. Run full test suite
6. Commit fix: `git commit -m "fix(<scope>): description (#X)"`

### Verification
- [ ] Bug is fixed
- [ ] New test prevents regression
- [ ] No other tests broken
- [ ] Guardian tests still pass
```

### Workflow 4: TDD Implementation

```markdown
## /project:nh-tdd

### Phase 1: Write Tests First
1. Create test file if not exists
2. Write test cases for expected behavior
3. Run tests - verify they FAIL
4. Commit: `git commit -m "test: add tests for {feature}"`

### Phase 2: Implement
1. Write minimum code to pass tests
2. Run tests after each change
3. Iterate until all tests pass
4. Commit: `git commit -m "feat: implement {feature}"`

### Phase 3: Refactor
1. Improve code quality
2. Ensure tests still pass
3. Commit: `git commit -m "refactor: clean up {feature}"`

### Rules
- NEVER modify tests to make them pass
- Tests define the contract
- Implementation serves the tests
```

---

## 📚 Function Registry

### Core API Functions

#### Authentication (`src/api/auth.py`)

```python
# EPOCH 1 - LOCKED - DO NOT MODIFY

async def register_user(data: UserCreate) -> User
    """Register new user. Returns created user without password."""
    
async def login(data: LoginRequest) -> TokenResponse
    """Authenticate user. Returns access + refresh tokens."""
    
async def logout(token: str) -> None
    """Invalidate refresh token."""
    
async def refresh_token(refresh: str) -> TokenResponse
    """Issue new access token using refresh token."""
    
async def get_current_user(token: str) -> User
    """Decode JWT and return current user. Raises 401 if invalid."""
    
async def verify_email(token: str) -> None
    """Verify email address using verification token."""
    
async def request_password_reset(email: str) -> None
    """Send password reset email. Always returns 200 (security)."""
    
async def reset_password(token: str, new_password: str) -> None
    """Reset password using reset token."""
```

#### Pipeline (`src/api/pipeline.py`)

```python
# EPOCH 3 - ACTIVE - OK TO MODIFY

async def list_opportunities(
    user: User,
    status: Optional[OpportunityStatus] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Opportunity]
    """List opportunities with optional status filter."""
    
async def get_opportunity(user: User, opportunity_id: UUID) -> Opportunity
    """Get single opportunity by ID. Raises 404 if not found."""
    
async def create_opportunity(user: User, data: OpportunityCreate) -> Opportunity
    """Create new opportunity. Sets initial status to LEAD."""
    
async def update_opportunity(
    user: User, 
    opportunity_id: UUID, 
    data: OpportunityUpdate
) -> Opportunity
    """Update opportunity. Partial update supported."""
    
async def move_opportunity(
    user: User,
    opportunity_id: UUID,
    new_status: OpportunityStatus
) -> Opportunity
    """Move opportunity to new pipeline stage. Logs transition."""
    
async def delete_opportunity(user: User, opportunity_id: UUID) -> None
    """Soft delete opportunity. Sets deleted_at timestamp."""
    
async def get_pipeline_stats(user: User) -> PipelineStats
    """Get pipeline statistics: counts by stage, total value, etc."""
```

#### Opportunities (`src/api/opportunities.py`)

```python
# EPOCH 3 - ACTIVE - OK TO MODIFY

async def analyze_opportunity(opportunity_id: UUID) -> OpportunityAnalysis
    """Run NH analysis on opportunity. Returns score, risks, recommendations."""
    
async def generate_proposal(opportunity_id: UUID) -> ProposalDraft
    """Generate proposal draft using NH proposal agent."""
    
async def estimate_effort(opportunity_id: UUID) -> EffortEstimate
    """Estimate effort using historical data and SW classification."""
    
async def get_similar_opportunities(opportunity_id: UUID) -> List[Opportunity]
    """Find similar past opportunities for reference."""
```

### Core Services

#### NH Core (`src/agents/nh_core.py`)

```python
class NeuralHoldingOrchestrator:
    """Main orchestrator for Neural Holding operations."""
    
    async def process_lead(self, lead: RawLead) -> ProcessedLead
        """Process raw lead through analysis pipeline."""
        
    async def score_opportunity(self, opp: Opportunity) -> OpportunityScore
        """Score opportunity on multiple dimensions."""
        
    async def generate_proposal(self, opp: Opportunity) -> Proposal
        """Generate complete proposal with pricing."""
        
    async def plan_execution(self, opp: Opportunity) -> ExecutionPlan
        """Create SW execution plan for approved opportunity."""
        
    async def monitor_project(self, project_id: UUID) -> ProjectStatus
        """Monitor ongoing project status."""
```

#### SW Core (`src/agents/sw_core.py`)

```python
class SynapticWeaverCore:
    """Core Synaptic Weaver code generation engine."""
    
    async def generate_backend(self, spec: BackendSpec) -> GeneratedCode
        """Generate complete FastAPI backend from spec."""
        
    async def generate_frontend(self, spec: FrontendSpec) -> GeneratedCode
        """Generate React frontend from spec."""
        
    async def run_tests(self, code: GeneratedCode) -> TestResults
        """Run generated tests against code."""
        
    async def fix_errors(self, code: GeneratedCode, errors: List[Error]) -> GeneratedCode
        """Attempt to fix errors in generated code."""
        
    async def estimate_complexity(self, spec: Spec) -> ComplexityTier
        """Estimate complexity tier (1-5) for a specification."""
```

#### COO Agent (`src/agents/coo.py`)

```python
class COOAgent:
    """Chief Operating Officer review agent."""
    
    async def review_changes(self, diff: str, context: ReviewContext) -> ReviewResult
        """Review code changes for quality and alignment."""
        
    async def check_north_star_alignment(self, changes: str) -> AlignmentScore
        """Check if changes align with North Star goal."""
        
    async def detect_drift(self, session_log: SessionLog) -> List[DriftWarning]
        """Detect potential drift from objectives."""
        
    async def approve_merge(self, pr: PullRequest) -> MergeDecision
        """Make final merge decision."""
```

### Memory Cortex Functions

#### Session Logger (`nh_memory/session_logger.py`)

```python
class SessionLogger:
    """Captures all session events for learning."""
    
    def __init__(self, session_id: str) -> None
        """Initialize logger for new session."""
        
    def start_task(self, task_id: str, task_type: str, description: str) -> None
        """Mark task start. Records timestamp and context."""
        
    def complete_task(self, success: bool, resolution: str = "") -> None
        """Mark task completion. Calculates duration."""
        
    def log_error(self, error_type: str, message: str, context: dict) -> None
        """Log error encountered during task."""
        
    def log_error_resolution(self, method: str, self_resolved: bool) -> None
        """Log how error was resolved."""
        
    def log_rollback(self, reason: str) -> None
        """Log rollback event."""
        
    def log_human_intervention(self, reason: str, action: str) -> None
        """Log when human had to intervene."""
        
    def log_pattern_discovered(self, pattern: Pattern) -> None
        """Log newly discovered pattern."""
        
    def generate_summary(self) -> SessionSummary
        """Generate complete session summary with learnings."""
```

#### Knowledge Extractor (`nh_memory/knowledge_extractor.py`)

```python
class KnowledgeExtractor:
    """Extracts patterns from historical sessions."""
    
    def __init__(self, summaries_dir: Path) -> None
        """Initialize with path to session summaries."""
        
    def extract_patterns(self) -> List[Pattern]
        """Extract recurring success patterns."""
        
    def extract_anti_patterns(self) -> List[Pattern]
        """Extract recurring failure patterns."""
        
    def build_task_classifier(self) -> Dict[str, TaskClassification]
        """Build task classification model from data."""
        
    def get_relevant_patterns(self, task_type: str) -> List[Pattern]
        """Get patterns relevant to specific task type."""
        
    def get_relevant_anti_patterns(self, task_type: str) -> List[Pattern]
        """Get anti-patterns to avoid for task type."""
```

#### Dynamic CLAUDE.md Generator (`nh_memory/claude_md_generator.py`)

```python
class DynamicClaudeMdGenerator:
    """Generates context-aware CLAUDE.md for each task."""
    
    def __init__(self) -> None
        """Initialize with knowledge base."""
        
    def generate(self, context: TaskContext) -> str
        """Generate complete CLAUDE.md for specific task."""
        
    def generate_mode_section(self, task_type: str) -> str
        """Generate mode recommendation section."""
        
    def generate_pattern_section(self, task_type: str) -> str
        """Generate relevant patterns section."""
        
    def generate_anti_pattern_section(self, task_type: str) -> str
        """Generate things-to-avoid section."""
        
    def generate_stats_section(self, task_type: str) -> str
        """Generate historical stats section."""
```

#### Slash Command Generator (`nh_memory/slash_command_generator.py`)

```python
class SlashCommandGenerator:
    """Auto-generates slash commands from repeated workflows."""
    
    def __init__(self, sessions_dir: Path) -> None
        """Initialize with session logs directory."""
        
    def analyze_and_generate(self) -> List[Command]
        """Analyze sessions and generate new commands."""
        
    def find_repeated_sequences(self) -> Dict[str, SequenceData]
        """Find task sequences that repeat across sessions."""
        
    def generate_command(self, sequence: str, data: SequenceData) -> Command
        """Generate slash command for repeated sequence."""
```

#### Post-Session Ritual (`nh_memory/post_session.py`)

```python
def run_post_session_ritual(logger: SessionLogger) -> PostSessionReport
    """
    Complete post-session analysis:
    1. Generate session summary
    2. Extract patterns and anti-patterns
    3. Update task classifier
    4. Suggest CLAUDE.md updates
    5. Generate new slash commands
    """
```

### Guardian Functions

#### Epoch Verification (`nh_guardian/verify_epochs.py`)

```python
def hash_file(filepath: Path) -> str
    """Generate SHA-256 hash of file contents."""
    
def verify_epoch(epoch_id: str, repo_path: Path) -> EpochVerification
    """Verify single epoch's integrity against stored hashes."""
    
def verify_all_epochs(repo_path: Path) -> bool
    """Verify all locked epochs. Returns False if any violated."""
```

#### Functional Tests (`nh_guardian/functional_tests/`)

```python
# These test BEHAVIOR, not code structure

class TestAuthBehavior:
    """Black-box tests for authentication."""
    
    def test_can_register_new_user(self) -> None
    def test_cannot_register_duplicate_email(self) -> None
    def test_can_login_with_valid_credentials(self) -> None
    def test_cannot_login_with_wrong_password(self) -> None
    def test_protected_route_requires_token(self) -> None
    def test_password_not_in_responses(self) -> None

class TestDashboardBehavior:
    """Black-box tests for dashboard UI."""
    
    def test_sidebar_navigation_works(self) -> None
    def test_dark_mode_toggle_works(self) -> None
    def test_dark_mode_persists(self) -> None
    def test_metric_cards_display(self) -> None
    def test_mobile_layout_works(self) -> None
```

### Database Models (`src/core/models.py`)

```python
class User(Base):
    """User account model."""
    id: UUID
    email: str
    password_hash: str
    name: str
    role: UserRole
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime

class Opportunity(Base):
    """Pipeline opportunity model."""
    id: UUID
    user_id: UUID
    title: str
    description: str
    source: OpportunitySource  # UPWORK, USEME, DIRECT
    status: OpportunityStatus  # LEAD, QUALIFIED, PROPOSAL, NEGOTIATING, WON, DELIVERED, LOST
    value: Decimal
    currency: str
    probability: int  # 0-100
    client_name: str
    client_rating: Optional[float]
    tech_stack: List[str]
    nh_score: Optional[int]
    created_at: datetime
    updated_at: datetime

class Project(Base):
    """Active project model."""
    id: UUID
    opportunity_id: UUID
    status: ProjectStatus
    started_at: datetime
    deadline: datetime
    completed_at: Optional[datetime]
    total_hours: float
    sw_hours: float
    review_hours: float

class FinancialRecord(Base):
    """Income/expense record."""
    id: UUID
    user_id: UUID
    type: RecordType  # INCOME, EXPENSE
    category: str
    amount: Decimal
    currency: str
    source: str
    date: date
    notes: str

class SessionLog(Base):
    """Development session log."""
    id: UUID
    session_id: str
    started_at: datetime
    ended_at: datetime
    tasks_attempted: int
    tasks_completed: int
    errors_total: int
    patterns_discovered: JSON
    anti_patterns_discovered: JSON
```

---

## 📏 Code Conventions

### Python Style

```python
# Use type hints everywhere
def process_lead(lead: RawLead, options: ProcessOptions | None = None) -> ProcessedLead:
    """
    Process raw lead through analysis pipeline.
    
    Args:
        lead: Raw lead data from scraper
        options: Optional processing configuration
        
    Returns:
        Processed lead with scores and analysis
        
    Raises:
        ValidationError: If lead data is invalid
        ProcessingError: If analysis fails
    """
    ...

# Use dataclasses or Pydantic for data structures
@dataclass
class ProcessOptions:
    include_competitors: bool = True
    depth: AnalysisDepth = AnalysisDepth.STANDARD
    
# Async by default for I/O operations
async def fetch_opportunity(opp_id: UUID) -> Opportunity:
    ...

# Use context managers for resources
async with get_db_session() as session:
    ...
```

### TypeScript/React Style

```typescript
// Use functional components with TypeScript
interface OpportunityCardProps {
  opportunity: Opportunity;
  onMove: (id: string, status: Status) => void;
  onDelete: (id: string) => void;
}

export function OpportunityCard({ 
  opportunity, 
  onMove, 
  onDelete 
}: OpportunityCardProps) {
  // Always include data-testid for testing
  return (
    <div data-testid={`opportunity-card-${opportunity.id}`}>
      ...
    </div>
  );
}

// Use custom hooks for logic
function useOpportunities() {
  return useQuery({
    queryKey: ['opportunities'],
    queryFn: fetchOpportunities,
  });
}

// Tailwind: Use semantic class grouping
// Layout | Spacing | Typography | Colors | Effects
className="flex items-center gap-4 p-4 text-sm text-gray-700 dark:text-gray-300 rounded-lg shadow-sm"
```

### Naming Conventions

```
Files:
  - Python: snake_case.py
  - TypeScript: PascalCase.tsx (components), camelCase.ts (utilities)
  - Tests: test_*.py or *.test.ts

Functions/Methods:
  - Python: snake_case
  - TypeScript: camelCase
  - React hooks: use{Name}

Classes:
  - PascalCase everywhere

Constants:
  - SCREAMING_SNAKE_CASE

Database:
  - Tables: plural snake_case (opportunities, session_logs)
  - Columns: snake_case
```

---

## 🧪 Testing Requirements

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── epoch1/               # LOCKED - Auth tests
│   ├── test_register.py
│   ├── test_login.py
│   └── test_protected.py
├── epoch2/               # LOCKED - Dashboard tests
│   ├── test_layout.py
│   └── test_theme.py
├── epoch3/               # ACTIVE - Pipeline tests
│   ├── test_opportunities.py
│   ├── test_pipeline_flow.py
│   └── test_stats.py
└── integration/          # E2E tests
    └── test_full_flow.py
```

### Test Requirements

1. **Every new function must have tests**
2. **Tests must be in appropriate epoch folder**
3. **Use pytest fixtures for setup/teardown**
4. **Mock external services, not internal logic**
5. **Minimum 80% coverage for new code**

### Running Tests

```bash
# Run all tests
pytest

# Run specific epoch
pytest tests/epoch3 -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run guardian tests only
pytest tests/epoch1 tests/epoch2 -v --tb=short

# Run single test
pytest tests/epoch3/test_opportunities.py::test_create_opportunity -v
```

---

## 🛡 Guardian Rules

### Pre-Change Checklist

```markdown
Before making ANY changes:

□ 1. Run guardian tests
     pytest tests/epoch1 tests/epoch2 --tb=short
     
□ 2. Check epoch status
     cat epochs/epoch_manifest.yaml
     
□ 3. Verify files are in ACTIVE epoch
     If file is in LOCKED epoch → STOP
     
□ 4. Create checkpoint
     git add -A && git commit -m "checkpoint: before <change>"
```

### Post-Change Checklist

```markdown
After making changes:

□ 1. Run relevant tests
     pytest tests/epoch{N} -v
     
□ 2. Run guardian tests again
     pytest tests/epoch1 tests/epoch2 --tb=short
     
□ 3. Check for type errors
     mypy src/ --strict
     
□ 4. Format code
     black src/ tests/ && isort src/ tests/
     
□ 5. Commit with proper message
     git commit -m "<type>(<scope>): <description>"
```

### Epoch Violation Response

If you accidentally modify a LOCKED epoch:

```bash
# 1. Immediately revert
git checkout HEAD -- <file>

# 2. If already committed
git revert HEAD

# 3. Report the violation
echo "EPOCH VIOLATION: Modified <file> in LOCKED epoch <N>" 
```

---

## 🧠 Memory System

### Session Logging

Every session should be logged. At session start:

```python
from nh_memory import SessionLogger

logger = SessionLogger(session_id="session_20260113_143022")
```

Log events during work:

```python
# Task start
logger.start_task(
    task_id="add-websocket",
    task_type="add_api_endpoint_complex",
    description="Add WebSocket support for real-time updates"
)

# Errors
logger.log_error(
    error_type="import_error",
    message="Module 'websockets' not found",
    context={"file": "src/api/ws.py", "line": 5}
)

# Resolution
logger.log_error_resolution(
    method="pip install websockets",
    self_resolved=True
)

# Task complete
logger.complete_task(success=True)
```

### Post-Session Ritual

After EVERY session, run:

```bash
python scripts/post_session.py <session_id>
```

This will:
1. Generate session summary
2. Extract patterns/anti-patterns
3. Update task classifier
4. Suggest CLAUDE.md updates
5. Generate new slash commands if patterns found

### Using Historical Knowledge

Before starting a task, check for relevant patterns:

```python
from nh_memory import KnowledgeExtractor

extractor = KnowledgeExtractor()
patterns = extractor.get_relevant_patterns("add_api_endpoint_complex")
anti_patterns = extractor.get_relevant_anti_patterns("add_api_endpoint_complex")
```

---

## 🚫 Forbidden Actions

### NEVER Do These

```markdown
1. ❌ Modify files in LOCKED epochs without explicit unlock
2. ❌ Skip guardian tests before changes
3. ❌ Commit without running tests
4. ❌ Delete test files
5. ❌ Modify epoch_manifest.yaml directly
6. ❌ Change database schema without migration
7. ❌ Hardcode secrets or credentials
8. ❌ Ignore type errors
9. ❌ Skip post-session logging
10. ❌ Work on multiple epochs simultaneously
```

### ALWAYS Do These

```markdown
1. ✅ Run guardian tests before AND after changes
2. ✅ Create checkpoint commits at logical boundaries
3. ✅ Write tests for new functions
4. ✅ Use type hints
5. ✅ Log session events
6. ✅ Check task classification before starting
7. ✅ Follow commit message convention
8. ✅ Update CLAUDE.md if you discover new patterns
9. ✅ Ask when uncertain (especially in SUPERVISED mode)
10. ✅ Run post-session ritual when done
```

---

## 🔧 Troubleshooting

### Common Issues

#### Tests Failing After Changes

```bash
# 1. Check which tests fail
pytest --tb=short

# 2. If guardian tests fail, you broke a locked epoch
git diff tests/epoch1 tests/epoch2

# 3. Revert if needed
git checkout HEAD -- <files>
```

#### Import Errors

```bash
# 1. Ensure virtual environment is active
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install package in dev mode
pip install -e .
```

#### Database Errors

```bash
# 1. Check PostgreSQL is running
docker-compose ps

# 2. Run migrations
alembic upgrade head

# 3. Reset database (CAREFUL - deletes data)
alembic downgrade base && alembic upgrade head
```

#### Type Errors

```bash
# 1. Run mypy
mypy src/ --strict

# 2. Common fixes:
#    - Add Optional[] for nullable types
#    - Add return type annotations
#    - Use TypedDict for complex dicts
```

### Getting Help

If stuck:
1. Check this CLAUDE.md first
2. Search tests for similar patterns
3. Check session logs for past solutions
4. Ask with full context (error message, file, what you tried)

---

## 📝 Update Log

When you discover new patterns or anti-patterns, add them here:

```markdown
### Discovered Patterns

- [2026-01-13] WebSocket endpoints: Use async context managers for connections
- [2026-01-12] Pydantic schemas: Always add Config class with from_attributes=True

### Discovered Anti-Patterns

- [2026-01-13] AVOID: Modifying SQLAlchemy models without migration
- [2026-01-12] AVOID: Using raw SQL queries (use ORM)
```

---

## 🏁 Session Checklist

### Starting a Session

```markdown
□ Read CLAUDE.md (at least Quick Reference)
□ Check epoch status
□ Run guardian tests
□ Initialize session logger
□ Identify task classification (YOLO/CHECKPOINTED/SUPERVISED)
□ Create initial checkpoint
```

### Ending a Session

```markdown
□ Commit all changes with proper messages
□ Run full test suite
□ Run guardian tests
□ Complete session log
□ Run post-session ritual
□ Note any new patterns discovered
```

---

**Remember: The goal is not just to write code, but to build a system that learns and improves. Every session should leave the codebase AND the knowledge base better than before.**
