"""
Minimal test version of Mission Control V2 API
Works without PostgreSQL for testing purposes.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from datetime import datetime
import json
import asyncio
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Mission Control V2 (Test Mode)",
    version="2.0.0-test",
    description="Mission Control - OpenClaw metadata layer (Test Mode - No DB Required)"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for testing
agents_store: Dict[str, Any] = {}
tasks_store: Dict[str, Any] = {}
jobs_store: Dict[str, Any] = {}
events_store: List[Dict[str, Any]] = []
approvals_store: Dict[str, Any] = {}

# ==========================================
# Health & Info
# ==========================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Mission Control V2",
        "mode": "test",
        "status": "running",
        "docs": "http://localhost:8000/docs"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0-test",
        "environment": "test",
        "timestamp": datetime.utcnow().isoformat()
    }

# ==========================================
# Agent Endpoints
# ==========================================

@app.get("/api/v1/agents")
async def list_agents():
    """List all agents"""
    return list(agents_store.values())

@app.get("/api/v1/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent by ID"""
    if agent_id not in agents_store:
        return JSONResponse(status_code=404, content={"detail": "Agent not found"})
    return agents_store[agent_id]

@app.post("/api/v1/agents")
async def create_agent(agent_spec: dict):
    """Create a new agent (mock)"""
    agent_id = agent_spec.get("id", f"agent_{datetime.utcnow().timestamp()}")
    
    # Mock OpenClaw interaction
    agent = {
        "id": agent_id,
        "name": agent_spec.get("name"),
        "role": agent_spec.get("role"),
        "model": agent_spec.get("model"),
        "status": "provisioning",
        "openclaw_ref": f"oclaw_agent_{agent_id}",
        "workspace_path": f"/workspace/{agent_id}",
        "created_at": datetime.utcnow().isoformat()
    }
    
    agents_store[agent_id] = agent
    
    # Log event
    await log_event("agent_created", "agent", agent_id, agent)
    
    return agent

# ==========================================
# Task Endpoints
# ==========================================

@app.get("/api/v1/tasks")
async def list_tasks():
    """List all tasks"""
    return list(tasks_store.values())

@app.post("/api/v1/tasks")
async def create_task(task_spec: dict):
    """Create a new task"""
    task_id = task_spec.get("id", f"task_{datetime.utcnow().timestamp()}")
    
    task = {
        "id": task_id,
        "title": task_spec.get("title"),
        "description": task_spec.get("description"),
        "status": "pending",
        "priority": task_spec.get("priority", "P2"),
        "created_at": datetime.utcnow().isoformat()
    }
    
    tasks_store[task_id] = task
    
    # Log event
    await log_event("task_created", "task", task_id, task)
    
    return task

# ==========================================
# Job Endpoints
# ==========================================

@app.get("/api/v1/jobs")
async def list_jobs():
    """List all jobs"""
    return list(jobs_store.values())

@app.post("/api/v1/jobs")
async def create_job(job_spec: dict):
    """Create a new job"""
    job_id = f"job_{datetime.utcnow().timestamp()}"
    
    # Mock OpenClaw session
    job = {
        "id": job_id,
        "task_id": job_spec.get("task_id"),
        "agent_id": job_spec.get("agent_id"),
        "status": "running",
        "openclaw_session_ref": f"oclaw_session_{job_id}",
        "started_at": datetime.utcnow().isoformat()
    }
    
    jobs_store[job_id] = job
    
    # Log event
    await log_event("job_started", "job", job_id, job)
    
    # Simulate job completion after 5 seconds
    asyncio.create_task(simulate_job_completion(job_id))
    
    return job

async def simulate_job_completion(job_id: str):
    """Simulate job completion after delay"""
    await asyncio.sleep(5)
    if job_id in jobs_store:
        jobs_store[job_id]["status"] = "succeeded"
        jobs_store[job_id]["completed_at"] = datetime.utcnow().isoformat()
        await log_event("job_completed", "job", job_id, {"status": "succeeded"})

# ==========================================
# Event Endpoints
# ==========================================

async def log_event(event_type: str, source_type: str, source_id: str, payload: dict):
    """Log an event"""
    event = {
        "id": len(events_store) + 1,
        "type": event_type,
        "source_type": source_type,
        "source_id": source_id,
        "payload": payload,
        "created_at": datetime.utcnow().isoformat()
    }
    events_store.append(event)
    
    # Keep only last 1000 events
    if len(events_store) > 1000:
        events_store.pop(0)
    
    return event

@app.get("/api/v1/events")
async def list_events(limit: int = 100):
    """List recent events"""
    return events_store[-limit:]

@app.post("/api/v1/events")
async def create_event(event_data: dict):
    """Create a new event"""
    return await log_event(
        event_data.get("type"),
        event_data.get("source_type"),
        event_data.get("source_id"),
        event_data.get("payload", {})
    )

# ==========================================
# Approval Endpoints
# ==========================================

@app.get("/api/v1/approvals")
async def list_approvals():
    """List all approvals"""
    return list(approvals_store.values())

@app.post("/api/v1/approvals")
async def create_approval(approval_spec: dict):
    """Create approval request"""
    approval_id = f"approval_{datetime.utcnow().timestamp()}"
    
    approval = {
        "id": approval_id,
        "entity_type": approval_spec.get("entity_type"),
        "entity_id": approval_spec.get("entity_id"),
        "action": approval_spec.get("action"),
        "status": "pending",
        "requester": approval_spec.get("requester"),
        "created_at": datetime.utcnow().isoformat()
    }
    
    approvals_store[approval_id] = approval
    
    # Log event
    await log_event("approval_requested", "approval", approval_id, approval)
    
    return approval

# ==========================================
# SSE Streaming
# ==========================================

async def event_generator():
    """Generate SSE events"""
    # Send initial connection message
    yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
    
    # Send keepalive every 30 seconds
    while True:
        await asyncio.sleep(30)
        yield f": keepalive\n\n"

@app.get("/api/v1/stream")
async def stream_events():
    """SSE endpoint for live updates"""
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

# ==========================================
# Fleet Endpoints (Bonus)
# ==========================================

fleets_store: Dict[str, Any] = {}

@app.get("/api/v1/fleets")
async def list_fleets():
    """List all fleets"""
    return list(fleets_store.values())

@app.post("/api/v1/fleets")
async def create_fleet(fleet_spec: dict):
    """Create a new fleet"""
    fleet_id = fleet_spec.get("id", f"fleet_{datetime.utcnow().timestamp()}")
    
    fleet = {
        "id": fleet_id,
        "name": fleet_spec.get("name"),
        "description": fleet_spec.get("description"),
        "created_at": datetime.utcnow().isoformat()
    }
    
    fleets_store[fleet_id] = fleet
    
    return fleet

# ==========================================
# Mock OpenClaw Status
# ==========================================

@app.get("/api/v1/openclaw/status")
async def openclaw_status():
    """Get mock OpenClaw status"""
    return {
        "connected": True,
        "gateway_url": "ws://127.0.0.1:18789",
        "agents_online": len(agents_store),
        "active_sessions": len([j for j in jobs_store.values() if j["status"] == "running"]),
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)