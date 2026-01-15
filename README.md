# NH Mission Control

Real-time command center dashboard for Neural Holding operations.

## Quick Start

```bash
# Start all services
docker-compose up -d

# Frontend: http://localhost:3000
# API: http://localhost:8300
# API Docs: http://localhost:8300/docs
# Health: http://localhost:8300/health
```

## Architecture

### Backend (FastAPI)
- Port: 8300
- Health endpoint: `/health`
- API v1: `/api/v1/`

### Frontend (React + Vite + TypeScript)
- Port: 3000
- Tailwind CSS for styling
- Dark mode by default
- React Router for navigation

### Services
- PostgreSQL 16 (port 5432)
- Redis 7 (port 6379)

## Modules

1. **Dashboard** - Mission Control Overview
2. **Pipeline** - CI/CD Pipeline Management
3. **SW Operations** - Agent & Workflow Management
4. **Finance** - Cost Tracking & Budget
5. **Intelligence** - Market & Competitive Intel
6. **Briefing** - Daily Operations Briefing

## Development

```bash
# Backend only
cd app && uvicorn main:app --reload --port 8300

# Frontend only
cd frontend && npm run dev
```

## Phase 1 Status

- [x] Project structure
- [x] FastAPI backend with health endpoint
- [x] React frontend with dark theme
- [x] Navigation between 6 modules
- [x] Docker Compose configuration
- [x] PostgreSQL and Redis setup

## Next Phases

- Phase 2: Real-time data connections
- Phase 3: Agent monitoring integration
- Phase 4: Intelligence feeds
- Phase 5: Automated briefings
