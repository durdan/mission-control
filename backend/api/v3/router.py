"""
V3 API Router
Aggregates all V3 API endpoints
"""

from fastapi import APIRouter
from api.v3 import clusters, resources, rbac, metrics

# Create main V3 router
router = APIRouter(prefix="/api/v3")

# Include sub-routers
router.include_router(clusters.router, prefix="/clusters", tags=["Clusters"])
router.include_router(resources.router, prefix="/resources", tags=["Resources"])
router.include_router(rbac.router, prefix="/rbac", tags=["RBAC"])
router.include_router(metrics.router, prefix="/metrics", tags=["Metrics"])


@router.get("/")
async def v3_info():
    """
    Get V3 API information
    """
    return {
        "version": "3.0.0",
        "description": "Mission Control V3 Enterprise API",
        "features": [
            "Multi-cluster management",
            "Advanced approval workflows",
            "Resource provisioning",
            "Role-based access control",
            "Real-time metrics and monitoring"
        ],
        "endpoints": {
            "clusters": "/api/v3/clusters",
            "resources": "/api/v3/resources",
            "rbac": "/api/v3/rbac",
            "metrics": "/api/v3/metrics"
        }
    }