"""
V3 Resource Provisioning API
Manages infrastructure resources for OpenClaw agents and clusters
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from datetime import datetime

from services.resource_provisioner import (
    resource_provisioner,
    ProvisioningStrategy,
    ResourceProvider
)
from services.event_manager import event_manager

router = APIRouter()


# ========================================
# Request/Response Models
# ========================================

class ComputeSpec(BaseModel):
    """Compute resource specification"""
    vcpus: int = 2
    memory_gb: int = 4
    instance_type: Optional[str] = "n1-standard-1"
    accelerators: List[str] = []


class StorageSpec(BaseModel):
    """Storage resource specification"""
    disk_gb: int = 100
    disk_type: str = "pd-standard"
    iops: Optional[int] = 1000


class NetworkSpec(BaseModel):
    """Network resource specification"""
    bandwidth_mbps: int = 1000
    static_ips: int = 0
    load_balancers: int = 0


class ResourceRequest(BaseModel):
    """Resource provisioning request"""
    name: str
    description: Optional[str] = None
    compute: Optional[ComputeSpec] = None
    storage: Optional[StorageSpec] = None
    network: Optional[NetworkSpec] = None
    strategy: str = "immediate"
    tags: List[str] = []
    metadata: dict = {}


class ScaleRequest(BaseModel):
    """Resource scaling request"""
    compute: Optional[ComputeSpec] = None
    storage: Optional[StorageSpec] = None
    direction: str = "up"  # up or down
    auto_scale: bool = False


class ResourceResponse(BaseModel):
    """Resource provisioning response"""
    provision_id: str
    status: str
    resources: dict
    created_at: datetime
    estimated_cost: Optional[dict] = None


# ========================================
# Provisioning Endpoints
# ========================================

@router.post("/provision")
async def provision_resources(request: ResourceRequest):
    """
    Provision new resources for OpenClaw infrastructure
    """
    try:
        # Parse strategy
        strategy = ProvisioningStrategy[request.strategy.upper()]
        
        # Build provisioning request
        provision_request = {
            "name": request.name,
            "description": request.description,
            "compute": request.compute.dict() if request.compute else None,
            "storage": request.storage.dict() if request.storage else None,
            "network": request.network.dict() if request.network else None,
            "tags": request.tags,
            "metadata": request.metadata
        }
        
        # Estimate cost
        cost_estimate = await resource_provisioner.estimate_cost(provision_request)
        
        # Provision resources
        result = await resource_provisioner.provision_resources(
            provision_request,
            strategy
        )
        
        # Add provision ID if not present
        if isinstance(result, dict) and 'provision_id' not in result:
            result['provision_id'] = "prov-" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
        
        return {
            **result,
            "estimated_cost": cost_estimate
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/provision/{provision_id}")
async def deprovision_resources(provision_id: str):
    """
    Release provisioned resources
    """
    try:
        success = await resource_provisioner.deprovision_resources(provision_id)
        return {
            "provision_id": provision_id,
            "status": "deprovisioned" if success else "failed",
            "message": "Resources released successfully" if success else "Failed to release resources"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/provision/{provision_id}/scale")
async def scale_resources(provision_id: str, scale_request: ScaleRequest):
    """
    Scale provisioned resources up or down
    """
    try:
        scale_spec = {}
        
        if scale_request.compute:
            scale_spec['compute'] = scale_request.compute.dict()
        
        if scale_request.storage:
            scale_spec['storage'] = scale_request.storage.dict()
        
        result = await resource_provisioner.scale_resources(
            provision_id,
            scale_spec
        )
        
        return {
            "provision_id": provision_id,
            "status": "scaled",
            "direction": scale_request.direction,
            "resources": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========================================
# Resource Pool Management
# ========================================

@router.get("/pools")
async def list_resource_pools():
    """
    List available resource pools
    """
    pools = []
    
    for pool_id, pool in resource_provisioner.resource_pools.items():
        pools.append({
            "pool_id": pool_id,
            "name": pool.get('name', 'Unknown'),
            "provider": pool.get('provider', ResourceProvider.GCP).value,
            "region": pool.get('region', 'unknown'),
            "available": pool.get('available', False)
        })
    
    return pools


@router.get("/pools/{pool_id}")
async def get_resource_pool(pool_id: str):
    """
    Get details of a specific resource pool
    """
    pool = resource_provisioner.resource_pools.get(pool_id)
    
    if not pool:
        raise HTTPException(status_code=404, detail="Resource pool not found")
    
    return {
        "pool_id": pool_id,
        **pool
    }


# ========================================
# Quota Management
# ========================================

@router.get("/quotas")
async def get_resource_quotas():
    """
    Get current resource quotas and usage
    """
    usage = await resource_provisioner.get_quota_usage()
    
    return {
        "quotas": usage,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/quotas/available")
async def get_available_capacity():
    """
    Get available resource capacity
    """
    usage = await resource_provisioner.get_quota_usage()
    
    available = {
        "compute": {
            "vcpus": usage['compute']['vcpus_total'] - usage['compute']['vcpus_used'],
            "memory_gb": usage['compute']['memory_gb_total'] - usage['compute']['memory_gb_used']
        },
        "storage": {
            "disk_gb": usage['storage']['disk_gb_total'] - usage['storage']['disk_gb_used']
        },
        "network": {
            "static_ips": usage['network']['static_ips_total'] - usage['network']['static_ips_used']
        }
    }
    
    return available


# ========================================
# Cost Management
# ========================================

@router.post("/estimate")
async def estimate_resource_cost(request: ResourceRequest):
    """
    Estimate cost for resource request
    """
    provision_request = {
        "compute": request.compute.dict() if request.compute else None,
        "storage": request.storage.dict() if request.storage else None,
        "network": request.network.dict() if request.network else None
    }
    
    estimate = await resource_provisioner.estimate_cost(provision_request)
    
    return estimate


@router.get("/costs/report")
async def get_cost_report(
    start_date: datetime = Query(..., description="Start date for report"),
    end_date: datetime = Query(..., description="End date for report")
):
    """
    Generate cost report for date range
    """
    report = await resource_provisioner.get_cost_report(start_date, end_date)
    return report


# ========================================
# Active Provisions
# ========================================

@router.get("/provisions")
async def list_active_provisions():
    """
    List all active resource provisions
    """
    provisions = []
    
    for provision_id, provision in resource_provisioner.active_provisions.items():
        provisions.append({
            "provision_id": provision_id,
            "status": provision.get('status', 'unknown'),
            "strategy": provision.get('strategy', ProvisioningStrategy.IMMEDIATE).value,
            "created_at": provision.get('created_at', datetime.utcnow()).isoformat(),
            "resources": provision.get('resources', {})
        })
    
    return provisions


@router.get("/provisions/{provision_id}")
async def get_provision_details(provision_id: str):
    """
    Get details of a specific provision
    """
    provision = resource_provisioner.active_provisions.get(provision_id)
    
    if not provision:
        raise HTTPException(status_code=404, detail="Provision not found")
    
    return {
        "provision_id": provision_id,
        **provision,
        "created_at": provision.get('created_at', datetime.utcnow()).isoformat()
    }


# ========================================
# Pre-warming and Optimization
# ========================================

@router.post("/prewarm")
async def prewarm_resources(request: ResourceRequest):
    """
    Pre-warm resources for faster provisioning
    """
    try:
        provision_request = {
            "name": f"prewarm-{request.name}",
            "compute": request.compute.dict() if request.compute else None,
            "storage": request.storage.dict() if request.storage else None,
            "network": request.network.dict() if request.network else None
        }
        
        result = await resource_provisioner.provision_resources(
            provision_request,
            ProvisioningStrategy.PRE_WARMED
        )
        
        return {
            "status": "prewarmed",
            "resources": result,
            "message": "Resources pre-warmed successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/optimize")
async def optimize_resource_allocation():
    """
    Optimize resource allocation across all provisions
    """
    # This would run optimization algorithms
    return {
        "status": "optimization_complete",
        "optimizations": [],
        "savings": {
            "cost_reduction": "0%",
            "resource_efficiency": "0%"
        }
    }


# ========================================
# Health and Status
# ========================================

@router.get("/health")
async def get_provisioner_health():
    """
    Get health status of resource provisioner
    """
    return {
        "status": "healthy",
        "running": resource_provisioner._running,
        "active_provisions": len(resource_provisioner.active_provisions),
        "resource_pools": len(resource_provisioner.resource_pools),
        "timestamp": datetime.utcnow().isoformat()
    }