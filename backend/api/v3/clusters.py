"""
V3 Cluster Management API
Multi-cluster support with health monitoring and load balancing
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from datetime import datetime

from services.cluster_manager import cluster_manager, DistributionStrategy
from services.event_manager import event_manager

router = APIRouter()


# ========================================
# Request/Response Models
# ========================================

class ClusterRegistration(BaseModel):
    """Cluster registration request"""
    name: str
    gateway_url: str
    region: str = "us-east"
    max_agents: int = 100
    health_check_url: Optional[str] = None
    cost_per_hour: float = 0.0
    tags: List[str] = []


class TaskDistribution(BaseModel):
    """Task distribution request"""
    task_id: str
    requirements: dict = {}
    strategy: str = "least_loaded"
    priority: int = 5


class ClusterHealthResponse(BaseModel):
    """Cluster health response"""
    cluster_id: str
    name: str
    status: str
    last_heartbeat: Optional[datetime]
    health_metrics: dict
    current_load: float


# ========================================
# Cluster Management Endpoints
# ========================================

@router.post("/")
async def register_cluster(cluster_spec: ClusterRegistration):
    """
    Register a new OpenClaw cluster for multi-cluster management
    """
    try:
        cluster = await cluster_manager.register_cluster(cluster_spec.dict())
        return {
            "cluster_id": cluster['id'],
            "name": cluster['name'],
            "status": cluster['status'].value,
            "message": "Cluster registered successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def list_clusters(
    status: Optional[str] = None,
    region: Optional[str] = None
):
    """
    List all registered clusters with optional filtering
    """
    clusters = cluster_manager.clusters.values()
    
    # Filter by status
    if status:
        clusters = [c for c in clusters if c['status'].value == status]
    
    # Filter by region
    if region:
        clusters = [c for c in clusters if c['region'].value == region]
    
    return [
        {
            "cluster_id": c['id'],
            "name": c['name'],
            "gateway_url": c['gateway_url'],
            "region": c['region'].value,
            "status": c['status'].value,
            "current_agents": c['current_agents'],
            "max_agents": c['max_agents'],
            "utilization": (c['current_agents'] / c['max_agents'] * 100) if c['max_agents'] > 0 else 0,
            "last_heartbeat": c.get('last_heartbeat')
        }
        for c in clusters
    ]


@router.get("/{cluster_id}")
async def get_cluster(cluster_id: str):
    """
    Get detailed information about a specific cluster
    """
    cluster = cluster_manager.clusters.get(cluster_id)
    
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    return {
        "cluster_id": cluster['id'],
        "name": cluster['name'],
        "gateway_url": cluster['gateway_url'],
        "region": cluster['region'].value,
        "status": cluster['status'].value,
        "current_agents": cluster['current_agents'],
        "max_agents": cluster['max_agents'],
        "health_metrics": cluster.get('health_metrics', {}),
        "last_heartbeat": cluster.get('last_heartbeat'),
        "cost_per_hour": cluster.get('cost_per_hour', 0)
    }


@router.get("/{cluster_id}/health")
async def get_cluster_health(cluster_id: str):
    """
    Get health status and metrics for a cluster
    """
    cluster = cluster_manager.clusters.get(cluster_id)
    
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    # Trigger immediate health check
    await cluster_manager._check_cluster_health(cluster_id)
    
    # Get updated cluster info
    cluster = cluster_manager.clusters.get(cluster_id)
    
    return ClusterHealthResponse(
        cluster_id=cluster['id'],
        name=cluster['name'],
        status=cluster['status'].value,
        last_heartbeat=cluster.get('last_heartbeat'),
        health_metrics=cluster.get('health_metrics', {}),
        current_load=(cluster['current_agents'] / cluster['max_agents'] * 100) if cluster['max_agents'] > 0 else 0
    )


@router.post("/{cluster_id}/drain")
async def drain_cluster(cluster_id: str):
    """
    Drain a cluster (prepare for maintenance)
    Migrates all tasks to other clusters
    """
    try:
        await cluster_manager.drain_cluster(cluster_id)
        return {
            "cluster_id": cluster_id,
            "status": "draining",
            "message": "Cluster draining initiated"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{cluster_id}")
async def unregister_cluster(
    cluster_id: str,
    force: bool = Query(False, description="Force removal without draining")
):
    """
    Unregister a cluster from management
    """
    try:
        await cluster_manager.unregister_cluster(cluster_id, drain=not force)
        return {
            "cluster_id": cluster_id,
            "message": "Cluster unregistered successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========================================
# Task Distribution Endpoints
# ========================================

@router.post("/distribute")
async def distribute_task(distribution: TaskDistribution):
    """
    Distribute a task to the optimal cluster
    """
    try:
        # Parse strategy
        strategy = DistributionStrategy[distribution.strategy.upper()]
        
        # Distribute task
        result = await cluster_manager.distribute_task(
            {
                "id": distribution.task_id,
                "requirements": distribution.requirements,
                "priority": distribution.priority
            },
            strategy
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/optimal")
async def get_optimal_cluster(
    strategy: str = "least_loaded",
    region: Optional[str] = None,
    min_capacity: int = Query(1, description="Minimum available agent capacity")
):
    """
    Get the optimal cluster based on strategy and requirements
    """
    requirements = {}
    if region:
        requirements['region'] = region
    if min_capacity:
        requirements['min_capacity'] = min_capacity
    
    try:
        strategy_enum = DistributionStrategy[strategy.upper()]
        cluster_id = await cluster_manager.get_optimal_cluster(requirements, strategy_enum)
        
        if not cluster_id:
            raise HTTPException(status_code=503, detail="No available clusters")
        
        cluster = cluster_manager.clusters[cluster_id]
        
        return {
            "cluster_id": cluster_id,
            "name": cluster['name'],
            "region": cluster['region'].value,
            "available_capacity": cluster['max_agents'] - cluster['current_agents'],
            "utilization": (cluster['current_agents'] / cluster['max_agents'] * 100) if cluster['max_agents'] > 0 else 0
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========================================
# Statistics & Monitoring
# ========================================

@router.get("/stats/overview")
async def get_cluster_stats():
    """
    Get overall cluster statistics
    """
    return cluster_manager.get_cluster_stats()


@router.get("/stats/distribution")
async def get_distribution_stats():
    """
    Get task distribution statistics across clusters
    """
    stats = {}
    
    for cluster_id, cluster in cluster_manager.clusters.items():
        stats[cluster_id] = {
            "name": cluster['name'],
            "tasks_distributed": 0,  # Would come from database
            "avg_response_time": 0,  # Would come from metrics
            "success_rate": 100,      # Would come from metrics
            "current_load": (cluster['current_agents'] / cluster['max_agents'] * 100) if cluster['max_agents'] > 0 else 0
        }
    
    return stats


@router.get("/failover/status")
async def get_failover_status():
    """
    Get current failover status and recent failover events
    """
    # In production, this would query the database for recent failover events
    return {
        "failover_enabled": True,
        "failover_threshold_minutes": 5,
        "recent_failovers": []  # Would come from event store
    }


@router.post("/failover/test")
async def test_failover(cluster_id: str):
    """
    Test failover for a specific cluster (simulation)
    """
    try:
        # Simulate cluster failure
        await cluster_manager._handle_cluster_failure(cluster_id)
        
        # Initiate failover
        await cluster_manager._initiate_failover(cluster_id)
        
        return {
            "cluster_id": cluster_id,
            "failover": "simulated",
            "message": "Failover simulation completed"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))