#!/usr/bin/env python3
"""
Mock FastAPI backend for V3 dashboard
Provides mock data without requiring PostgreSQL or Redis
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import random
import uvicorn

app = FastAPI(title="Mission Control V3 Mock API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data models
class Cluster(BaseModel):
    cluster_id: str
    name: str
    gateway_url: str
    region: str
    status: str
    current_agents: int
    max_agents: int
    utilization: float
    last_heartbeat: str

class MetricData(BaseModel):
    timestamp: str
    value: float
    label: str

class Resource(BaseModel):
    id: str
    name: str
    type: str
    status: str
    allocation: float
    cost: float

class Workflow(BaseModel):
    id: str
    name: str
    status: str
    steps: List[Dict[str, Any]]
    created_at: str
    updated_at: str

# Mock data generators
def generate_mock_clusters() -> List[Cluster]:
    """Generate mock cluster data"""
    regions = ["us-west-2", "us-east-1", "eu-west-1", "ap-southeast-1"]
    statuses = ["active", "active", "active", "degraded", "maintenance"]
    
    clusters = []
    for i in range(4):
        cluster = Cluster(
            cluster_id=f"cluster-{i+1:03d}",
            name=f"OpenClaw {regions[i]}",
            gateway_url=f"ws://gateway-{i+1}.openclaw.io:18789",
            region=regions[i],
            status=random.choice(statuses),
            current_agents=random.randint(5, 20),
            max_agents=25,
            utilization=random.uniform(20, 95),
            last_heartbeat=datetime.now().isoformat()
        )
        clusters.append(cluster)
    return clusters

def generate_mock_metrics(metric_type: str) -> List[MetricData]:
    """Generate mock metrics data"""
    data = []
    for i in range(24):
        data.append(MetricData(
            timestamp=f"{i:02d}:00",
            value=random.uniform(30, 90) if metric_type == "cpu" else random.uniform(40, 80),
            label=metric_type.upper()
        ))
    return data

def generate_mock_resources() -> List[Resource]:
    """Generate mock resource data"""
    resources = []
    resource_types = ["compute", "memory", "storage", "network"]
    
    for i, res_type in enumerate(resource_types):
        resources.append(Resource(
            id=f"res-{i+1:03d}",
            name=f"{res_type.capitalize()} Pool {i+1}",
            type=res_type,
            status="active" if i < 3 else "warning",
            allocation=random.uniform(40, 90),
            cost=random.uniform(100, 500)
        ))
    return resources

def generate_mock_workflows() -> List[Workflow]:
    """Generate mock workflow data"""
    workflows = []
    workflow_names = [
        "Data Processing Pipeline",
        "Model Training Workflow",
        "Report Generation",
        "Backup and Archive"
    ]
    
    for i, name in enumerate(workflow_names):
        steps = [
            {"name": "Initialize", "status": "completed"},
            {"name": "Process", "status": "completed" if i < 2 else "running"},
            {"name": "Validate", "status": "pending" if i >= 2 else "completed"},
            {"name": "Complete", "status": "pending"}
        ]
        
        workflows.append(Workflow(
            id=f"wf-{i+1:03d}",
            name=name,
            status="completed" if i < 2 else ("running" if i == 2 else "pending"),
            steps=steps,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        ))
    return workflows

# API Endpoints
@app.get("/")
def read_root():
    return {"message": "Mission Control V3 Mock API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/v3/clusters")
def get_clusters() -> List[Cluster]:
    """Get all clusters"""
    return generate_mock_clusters()

@app.get("/api/v3/clusters/{cluster_id}")
def get_cluster(cluster_id: str) -> Cluster:
    """Get specific cluster"""
    clusters = generate_mock_clusters()
    for cluster in clusters:
        if cluster.cluster_id == cluster_id:
            return cluster
    raise HTTPException(status_code=404, detail="Cluster not found")

@app.get("/api/v3/metrics")
def get_metrics(metric_type: str = "cpu") -> Dict[str, Any]:
    """Get metrics data"""
    return {
        "metric_type": metric_type,
        "data": generate_mock_metrics(metric_type),
        "summary": {
            "average": random.uniform(50, 70),
            "peak": random.uniform(80, 95),
            "current": random.uniform(40, 60)
        }
    }

@app.get("/api/v3/resources")
def get_resources() -> List[Resource]:
    """Get resource allocation data"""
    return generate_mock_resources()

@app.get("/api/v3/resources/summary")
def get_resources_summary() -> Dict[str, Any]:
    """Get resource summary"""
    resources = generate_mock_resources()
    total_cost = sum(r.cost for r in resources)
    avg_allocation = sum(r.allocation for r in resources) / len(resources)
    
    return {
        "total_resources": len(resources),
        "total_cost": round(total_cost, 2),
        "average_allocation": round(avg_allocation, 2),
        "resources": resources
    }

@app.get("/api/v3/workflows")
def get_workflows() -> List[Workflow]:
    """Get workflow data"""
    return generate_mock_workflows()

@app.get("/api/v3/workflows/{workflow_id}")
def get_workflow(workflow_id: str) -> Workflow:
    """Get specific workflow"""
    workflows = generate_mock_workflows()
    for workflow in workflows:
        if workflow.id == workflow_id:
            return workflow
    raise HTTPException(status_code=404, detail="Workflow not found")

@app.post("/api/v3/workflows")
def create_workflow(name: str, description: str = "") -> Dict[str, Any]:
    """Create a new workflow"""
    workflow_id = f"wf-{random.randint(100, 999):03d}"
    return {
        "id": workflow_id,
        "name": name,
        "description": description,
        "status": "created",
        "created_at": datetime.now().isoformat()
    }

@app.get("/api/v3/agents")
def get_v3_agents() -> Dict[str, Any]:
    """Get V3 agent information"""
    clusters = generate_mock_clusters()
    total_agents = sum(c.current_agents for c in clusters)
    
    return {
        "total_agents": total_agents,
        "clusters": len(clusters),
        "distribution": [
            {"cluster": c.name, "agents": c.current_agents}
            for c in clusters
        ]
    }

if __name__ == "__main__":
    print("🚀 Starting Mission Control V3 Mock Backend...")
    print("📡 API Documentation: http://localhost:8001/docs")
    print("🎯 Dashboard: http://localhost:3000/v3")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)