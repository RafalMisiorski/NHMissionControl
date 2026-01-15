"""
NH Mission Control - FastAPI Application
=========================================

Main application factory with all routers and middleware.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api import auth, finance, nerve_center, notifications, pipeline, webhooks
from src.api import pipeline_orchestrator, po_review, resources, guardrails
from src.api import cc_sessions
from src.core.nerve_center import websocket_endpoint as nerve_center_ws_endpoint
from src.core.nerve_center import startup_system_status
from src.core.config import settings
from src.core.database import close_db, init_db
from src.core.schemas import ErrorResponse, HealthResponse

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.is_production else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


# ==========================================================================
# Lifespan
# ==========================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.
    
    Startup:
    - Initialize database connection
    - Run any startup tasks
    
    Shutdown:
    - Close database connections
    - Cleanup resources
    """
    # Startup
    logger.info("Starting NH Mission Control", version=settings.APP_VERSION)
    
    await init_db()
    logger.info("Database initialized")
    
    # Initialize system status session for Nerve Center
    await startup_system_status()
    logger.info("System status session initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down NH Mission Control")
    await close_db()
    logger.info("Database connections closed")


# ==========================================================================
# App Factory
# ==========================================================================

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Neural Holding Mission Control - Autonomous Enterprise Dashboard",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )
    
    # ==========================================================================
    # Middleware
    # ==========================================================================
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # ==========================================================================
    # Exception Handlers
    # ==========================================================================
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle uncaught exceptions."""
        logger.error(
            "Unhandled exception",
            exc_info=exc,
            path=request.url.path,
            method=request.method,
        )
        
        if settings.is_development:
            detail = str(exc)
        else:
            detail = "An unexpected error occurred"
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="Internal Server Error",
                detail=detail,
                code="INTERNAL_ERROR",
            ).model_dump(),
        )
    
    # ==========================================================================
    # Routers
    # ==========================================================================
    
    # Health check (no prefix)
    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="Health check",
    )
    async def health_check() -> HealthResponse:
        """
        Check application health.
        
        Returns status of:
        - Application
        - Database connection
        - Redis connection
        """
        # TODO: Actually check database and redis
        return HealthResponse(
            status="healthy",
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT,
            database="connected",  # TODO: Actually check
            redis="connected",     # TODO: Actually check
        )
    
    # API v1 routes
    app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
    app.include_router(pipeline.router, prefix=settings.API_V1_PREFIX)
    app.include_router(finance.router, prefix=settings.API_V1_PREFIX)
    app.include_router(notifications.router, prefix=settings.API_V1_PREFIX)
    app.include_router(nerve_center.router, prefix=settings.API_V1_PREFIX)
    app.include_router(webhooks.router, prefix=settings.API_V1_PREFIX)

    # Pipeline Orchestrator (EPOCH 7 - Taśmociąg)
    app.include_router(pipeline_orchestrator.router)
    app.include_router(po_review.router)
    app.include_router(resources.router)
    app.include_router(guardrails.router)

    # CC Session Manager (EPOCH 8 - Visibility & Reliability)
    app.include_router(cc_sessions.router)

    # ==========================================================================
    # WebSocket Endpoints
    # ==========================================================================

    @app.websocket("/api/v1/nerve-center/ws")
    async def nerve_center_websocket(websocket: WebSocket):
        """WebSocket endpoint for Nerve Center real-time event streaming."""
        await nerve_center_ws_endpoint(websocket)

    # ==========================================================================
    # Root Endpoint
    # ==========================================================================
    
    @app.get("/", tags=["Root"])
    async def root() -> dict:
        """Root endpoint with API info."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs" if settings.is_development else "Disabled in production",
            "health": "/health",
            "api": settings.API_V1_PREFIX,
        }
    
    return app


# ==========================================================================
# Application Instance
# ==========================================================================

app = create_app()


# ==========================================================================
# Development Server
# ==========================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level="info",
    )
