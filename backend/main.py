"""
Mission Control FastAPI Application
====================================
Metadata and coordination layer for OpenClaw agents.
We track, OpenClaw executes.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from api import agents, tasks, jobs, events, approvals, fleets
from api.v3 import router as v3_router
from services.event_manager import event_manager
from services.openclaw_adapter import openclaw_adapter
from services.cluster_manager import cluster_manager
from services.workflow_engine import workflow_engine
from services.resource_provisioner import resource_provisioner
from services.rbac_manager import rbac_manager
from services.metrics_collector import metrics_collector

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize V2 services
    await event_manager.start()
    
    # Initialize V3 services
    logger.info("Initializing V3 services...")
    await cluster_manager.start()
    await workflow_engine.start()
    await resource_provisioner.start()
    await rbac_manager.initialize()
    await metrics_collector.start()
    
    # Connect to OpenClaw gateway (listen-only)
    # await openclaw_adapter.connect_websocket()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Mission Control")
    
    # Stop V3 services
    await metrics_collector.stop()
    await resource_provisioner.stop()
    await workflow_engine.stop()
    await cluster_manager.stop()
    
    # Stop V2 services
    await event_manager.stop()
    await openclaw_adapter.close()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Mission Control - OpenClaw metadata and coordination layer",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Include API routers

# V1 API (backwards compatible)
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(fleets.router, prefix="/api/v1/fleets", tags=["fleets"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(events.router, prefix="/api/v1/events", tags=["events"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["approvals"])

# V3 API (enterprise features)
app.include_router(v3_router.router)


# SSE endpoint for live updates
@app.get("/api/v1/stream")
async def stream_events():
    """Server-sent events stream for live updates."""
    from sse_starlette.sse import EventSourceResponse
    return EventSourceResponse(event_manager.subscribe())


# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )