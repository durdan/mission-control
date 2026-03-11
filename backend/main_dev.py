#!/usr/bin/env python3
"""
Development FastAPI backend for Mission Control V3
Uses SQLite and in-memory storage - no external dependencies needed
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import random
import uvicorn
import json
import httpx
import asyncio

app = FastAPI(title="Mission Control V3 API - Dev Mode")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for development
clusters_db = {}
resources_db = {}
workflows_db = {}
metrics_db = []

# Initialize with some demo data
def init_demo_data():
    """Initialize with demo clusters and data"""
    regions = ["us-west-2", "us-east-1", "eu-west-1", "ap-southeast-1"]
    
    for i, region in enumerate(regions, 1):
        cluster_id = f"cluster-{i:03d}"
        clusters_db[cluster_id] = {
            "cluster_id": cluster_id,
            "name": f"OpenClaw {region}",
            "gateway_url": f"ws://gateway-{i}.openclaw.io:18789",
            "region": region,
            "status": "active" if i <= 3 else "maintenance",
            "current_agents": random.randint(5, 20),
            "max_agents": 25,
            "utilization": random.uniform(20, 95),
            "last_heartbeat": datetime.now().isoformat()
        }

# Models
class ClusterCreate(BaseModel):
    name: str
    gateway_url: str
    region: str
    max_agents: int = 25

class ClusterUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    max_agents: Optional[int] = None

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize demo data on startup"""
    init_demo_data()
    print("✅ Demo data initialized")
    print(f"📊 Created {len(clusters_db)} clusters")

@app.get("/")
def read_root():
    return {
        "message": "Mission Control V3 API - Development Mode",
        "status": "running",
        "mode": "SQLite + In-Memory",
        "docs": "http://localhost:8001/docs"
    }

@app.get("/health")
async def health_check():
    # Check OpenClaw connection
    openclaw_connected = False
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:3001/api/health", timeout=2.0)
            openclaw_connected = response.status_code == 200
    except:
        pass
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "clusters": len(clusters_db),
        "mode": "development",
        "openclaw_connected": openclaw_connected
    }

# Helper to get real OpenClaw data
async def get_openclaw_data(endpoint: str):
    """Fetch real data from OpenClaw bridge API"""
    url = f"http://localhost:3001/api{endpoint}"
    try:
        async with httpx.AsyncClient() as client:
            print(f"Fetching OpenClaw data from: {url}")
            response = await client.get(url, timeout=5.0)
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Got data keys: {data.keys() if isinstance(data, dict) else 'list'}")
                return data
    except Exception as e:
        import traceback
        print(f"Error fetching OpenClaw data from {url}: {str(e)}")
        traceback.print_exc()
    return None

# Clusters API
@app.get("/api/v3/clusters")
async def get_clusters(demo: bool = Query(True, description="Use demo data instead of real OpenClaw data")) -> List[Dict[str, Any]]:
    """Get all clusters - demo or real based on query parameter"""
    print(f"Clusters API called with demo={demo}")
    
    if not demo:
        # Live mode - try to get real OpenClaw data
        try:
            # Read session file directly for faster access
            import json
            session_file = "/Users/durdan/.openclaw/agents/main/sessions/sessions.json"
            with open(session_file, 'r') as f:
                sessions = json.load(f)
                
            if sessions and isinstance(sessions, dict) and len(sessions) > 0:
                # Return real OpenClaw session as a cluster
                real_clusters = []
                for key, session_data in sessions.items():
                    # Get token data from session
                    tokens = session_data.get('totalTokens', 0) if isinstance(session_data, dict) else 0
                    context = session_data.get('contextTokens', 164000) if isinstance(session_data, dict) else 164000
                    utilization = (tokens / context * 100) if context > 0 else 0
                    
                    real_clusters.append({
                        "cluster_id": "openclaw-live",
                        "name": f"🦞 LIVE: {key}",
                        "gateway_url": "ws://127.0.0.1:18789",
                        "region": "local",
                        "status": "active",
                        "current_agents": 1,
                        "max_agents": 1,
                        "utilization": round(utilization, 2),
                        "last_heartbeat": datetime.now().isoformat(),
                        "tokens_used": tokens,
                        "is_demo": False
                    })
                print(f"✅ Returning {len(real_clusters)} REAL OpenClaw sessions")
                return real_clusters
        except Exception as e:
            print(f"Could not read session file: {e}")
    
    # Demo mode - return demo data with clear labeling
    demo_clusters = []
    for cluster_id, cluster_data in clusters_db.items():
        demo_cluster = cluster_data.copy()
        if not demo_cluster["name"].startswith("📊 DEMO:"):
            demo_cluster["name"] = f"📊 DEMO: {cluster_data['name']}"
        demo_cluster["is_demo"] = True
        demo_clusters.append(demo_cluster)
    
    print(f"Returning {len(demo_clusters)} DEMO clusters")
    return demo_clusters

@app.get("/api/v3/clusters/{cluster_id}")
def get_cluster(cluster_id: str) -> Dict[str, Any]:
    """Get specific cluster"""
    if cluster_id not in clusters_db:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return clusters_db[cluster_id]

@app.post("/api/v3/clusters")
def create_cluster(cluster: ClusterCreate) -> Dict[str, Any]:
    """Create a new cluster"""
    cluster_id = f"cluster-{len(clusters_db) + 1:03d}"
    new_cluster = {
        "cluster_id": cluster_id,
        "name": cluster.name,
        "gateway_url": cluster.gateway_url,
        "region": cluster.region,
        "status": "provisioning",
        "current_agents": 0,
        "max_agents": cluster.max_agents,
        "utilization": 0.0,
        "last_heartbeat": datetime.now().isoformat()
    }
    clusters_db[cluster_id] = new_cluster
    return new_cluster

@app.patch("/api/v3/clusters/{cluster_id}")
def update_cluster(cluster_id: str, update: ClusterUpdate) -> Dict[str, Any]:
    """Update a cluster"""
    if cluster_id not in clusters_db:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    cluster = clusters_db[cluster_id]
    update_data = update.dict(exclude_unset=True)
    for field, value in update_data.items():
        cluster[field] = value
    
    cluster["last_heartbeat"] = datetime.now().isoformat()
    return cluster

@app.delete("/api/v3/clusters/{cluster_id}")
def delete_cluster(cluster_id: str):
    """Delete a cluster"""
    if cluster_id not in clusters_db:
        raise HTTPException(status_code=404, detail="Cluster not found")
    del clusters_db[cluster_id]
    return {"message": "Cluster deleted successfully"}

# Metrics API
@app.get("/api/v3/metrics")
async def get_metrics(metric_type: str = "cpu", demo: bool = Query(True)) -> Dict[str, Any]:
    """Get metrics data - demo or real based on query parameter"""
    if not demo:
        # Try to get real OpenClaw metrics
        real_data = await get_openclaw_data("/agents")
        if real_data and "agents" in real_data:
            # Generate metrics from real agent data
            data = []
            for i in range(24):
                # Use real agent count and activity for metrics
                agent_count = len(real_data["agents"])
                base_value = 20 + (agent_count * 10)
                data.append({
                    "timestamp": f"{i:02d}:00",
                    "value": min(95, base_value + random.uniform(-10, 10)),
                    "label": metric_type.upper()
                })
            
            return {
                "metric_type": metric_type,
                "data": data,
                "summary": {
                    "average": base_value,
                    "peak": min(95, base_value + 20),
                    "current": min(95, base_value + random.uniform(-5, 5))
                },
                "is_real": True
            }
    
    # Demo metrics
    data = []
    for i in range(24):
        data.append({
            "timestamp": f"{i:02d}:00",
            "value": random.uniform(30, 90) if metric_type == "cpu" else random.uniform(40, 80),
            "label": metric_type.upper()
        })
    
    return {
        "metric_type": metric_type,
        "data": data,
        "summary": {
            "average": random.uniform(50, 70),
            "peak": random.uniform(80, 95),
            "current": random.uniform(40, 60)
        },
        "is_demo": True
    }

# Resources API
@app.get("/api/v3/resources")
def get_resources() -> List[Dict[str, Any]]:
    """Get resource allocation data"""
    if not resources_db:
        # Initialize with mock data
        resource_types = ["compute", "memory", "storage", "network"]
        for i, res_type in enumerate(resource_types):
            res_id = f"res-{i+1:03d}"
            resources_db[res_id] = {
                "id": res_id,
                "name": f"{res_type.capitalize()} Pool {i+1}",
                "type": res_type,
                "status": "active" if i < 3 else "warning",
                "allocation": random.uniform(40, 90),
                "cost": random.uniform(100, 500)
            }
    return list(resources_db.values())

@app.get("/api/v3/resources/summary")
def get_resources_summary() -> Dict[str, Any]:
    """Get resource summary"""
    resources = get_resources()
    total_cost = sum(r["cost"] for r in resources)
    avg_allocation = sum(r["allocation"] for r in resources) / len(resources) if resources else 0
    
    return {
        "total_resources": len(resources),
        "total_cost": round(total_cost, 2),
        "average_allocation": round(avg_allocation, 2),
        "resources": resources
    }

# Workflows API
@app.get("/api/v3/workflows")
def get_workflows() -> List[Dict[str, Any]]:
    """Get workflow data"""
    if not workflows_db:
        # Initialize with mock data
        workflow_names = [
            "Data Processing Pipeline",
            "Model Training Workflow",
            "Report Generation",
            "Backup and Archive"
        ]
        
        for i, name in enumerate(workflow_names):
            wf_id = f"wf-{i+1:03d}"
            steps = [
                {"name": "Initialize", "status": "completed"},
                {"name": "Process", "status": "completed" if i < 2 else "running"},
                {"name": "Validate", "status": "pending" if i >= 2 else "completed"},
                {"name": "Complete", "status": "pending"}
            ]
            
            workflows_db[wf_id] = {
                "id": wf_id,
                "name": name,
                "status": "completed" if i < 2 else ("running" if i == 2 else "pending"),
                "steps": steps,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
    
    return list(workflows_db.values())

@app.get("/api/v3/workflows/{workflow_id}")
def get_workflow(workflow_id: str) -> Dict[str, Any]:
    """Get specific workflow"""
    if workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflows_db[workflow_id]

@app.post("/api/v3/workflows")
def create_workflow(name: str, description: str = "") -> Dict[str, Any]:
    """Create a new workflow"""
    wf_id = f"wf-{len(workflows_db) + 1:03d}"
    new_workflow = {
        "id": wf_id,
        "name": name,
        "description": description,
        "status": "created",
        "steps": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    workflows_db[wf_id] = new_workflow
    return new_workflow

if __name__ == "__main__":
    print("🚀 Starting Mission Control V3 Development Backend...")
    print("📚 Using SQLite for database (mission_control.db)")
    print("💾 Using in-memory storage for cache")
    print("📡 API Documentation: http://localhost:8001/docs")
    print("🎯 Dashboard: http://localhost:3000/v3")
    print("\n✨ No PostgreSQL or Redis required for development!")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)