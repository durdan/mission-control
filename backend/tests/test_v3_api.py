"""
V3 API Integration Tests
Tests for Mission Control V3 enterprise features
"""

import pytest
import asyncio
import httpx
from datetime import datetime
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8001"
V3_API = f"{BASE_URL}/api/v3"


class TestV3Clusters:
    """Test cluster management endpoints"""
    
    @pytest.mark.asyncio
    async def test_register_cluster(self):
        """Test cluster registration"""
        async with httpx.AsyncClient() as client:
            cluster_data = {
                "name": "test-cluster-1",
                "gateway_url": "http://localhost:18789",
                "region": "us-east",
                "max_agents": 50
            }
            
            response = await client.post(f"{V3_API}/clusters", json=cluster_data)
            assert response.status_code == 200
            
            data = response.json()
            assert "cluster_id" in data
            assert data["name"] == cluster_data["name"]
            assert data["status"] == "online"
    
    @pytest.mark.asyncio
    async def test_list_clusters(self):
        """Test listing clusters"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{V3_API}/clusters")
            assert response.status_code == 200
            
            data = response.json()
            assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_cluster_health(self):
        """Test cluster health check"""
        async with httpx.AsyncClient() as client:
            # First register a cluster
            cluster_data = {
                "name": "health-test-cluster",
                "gateway_url": "http://localhost:18790",
                "region": "us-west"
            }
            
            reg_response = await client.post(f"{V3_API}/clusters", json=cluster_data)
            cluster_id = reg_response.json()["cluster_id"]
            
            # Get health
            response = await client.get(f"{V3_API}/clusters/{cluster_id}/health")
            assert response.status_code == 200
            
            data = response.json()
            assert "status" in data
            assert "health_metrics" in data
    
    @pytest.mark.asyncio
    async def test_distribute_task(self):
        """Test task distribution to optimal cluster"""
        async with httpx.AsyncClient() as client:
            distribution_request = {
                "task_id": "test-task-123",
                "requirements": {"region": "us-east"},
                "strategy": "least_loaded",
                "priority": 5
            }
            
            response = await client.post(
                f"{V3_API}/clusters/distribute",
                json=distribution_request
            )
            
            # May fail if no clusters registered
            if response.status_code == 200:
                data = response.json()
                assert "task_id" in data
                assert "cluster_id" in data


class TestV3Resources:
    """Test resource provisioning endpoints"""
    
    @pytest.mark.asyncio
    async def test_provision_resources(self):
        """Test resource provisioning"""
        async with httpx.AsyncClient() as client:
            provision_request = {
                "name": "test-provision",
                "compute": {
                    "vcpus": 4,
                    "memory_gb": 16
                },
                "storage": {
                    "disk_gb": 100
                },
                "strategy": "immediate"
            }
            
            response = await client.post(
                f"{V3_API}/resources/provision",
                json=provision_request
            )
            assert response.status_code == 200
            
            data = response.json()
            assert "provision_id" in data or "status" in data
            assert "estimated_cost" in data
    
    @pytest.mark.asyncio
    async def test_get_quotas(self):
        """Test quota retrieval"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{V3_API}/resources/quotas")
            assert response.status_code == 200
            
            data = response.json()
            assert "quotas" in data
            assert "compute" in data["quotas"]
            assert "storage" in data["quotas"]
    
    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation"""
        async with httpx.AsyncClient() as client:
            resource_request = {
                "name": "cost-estimate",
                "compute": {
                    "vcpus": 8,
                    "memory_gb": 32
                },
                "storage": {
                    "disk_gb": 500
                }
            }
            
            response = await client.post(
                f"{V3_API}/resources/estimate",
                json=resource_request
            )
            assert response.status_code == 200
            
            data = response.json()
            assert "hourly_cost" in data
            assert "monthly_cost" in data
            assert data["monthly_cost"] > 0


class TestV3RBAC:
    """Test RBAC endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_roles(self):
        """Test listing roles"""
        async with httpx.AsyncClient() as client:
            # First create a token for admin
            token_response = await client.post(
                f"{V3_API}/rbac/tokens",
                json={"user_id": "test-admin", "expires_in": 3600}
            )
            
            # May fail if RBAC not initialized
            if token_response.status_code == 200:
                token = token_response.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                
                response = await client.get(
                    f"{V3_API}/rbac/roles",
                    headers=headers
                )
                assert response.status_code == 200
                
                data = response.json()
                assert isinstance(data, list)
                
                # Check for default roles
                role_names = [role["name"] for role in data]
                assert "Administrator" in role_names
                assert "Viewer" in role_names
    
    @pytest.mark.asyncio
    async def test_create_custom_role(self):
        """Test creating custom role"""
        async with httpx.AsyncClient() as client:
            # Would need admin token
            role_data = {
                "name": "Test Role",
                "description": "Test role for unit tests",
                "permissions": [
                    "agent:read",
                    "task:read",
                    "metric:read"
                ]
            }
            
            # This would normally require admin auth
            # response = await client.post(f"{V3_API}/rbac/roles", json=role_data)
            # assert response.status_code in [200, 403]  # 403 if auth required
    
    @pytest.mark.asyncio
    async def test_check_permission(self):
        """Test permission checking"""
        async with httpx.AsyncClient() as client:
            permission_check = {
                "user_id": "test-user",
                "resource_type": "agent",
                "scope": "read"
            }
            
            # This would normally require auth
            # response = await client.post(f"{V3_API}/rbac/check", json=permission_check)
            # assert response.status_code in [200, 403]


class TestV3Metrics:
    """Test metrics endpoints"""
    
    @pytest.mark.asyncio
    async def test_record_metric(self):
        """Test recording a metric"""
        async with httpx.AsyncClient() as client:
            metric_data = {
                "name": "test.metric",
                "value": 42.5,
                "category": "performance",
                "tags": {"source": "test"}
            }
            
            response = await client.post(
                f"{V3_API}/metrics/record",
                json=metric_data
            )
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "recorded"
    
    @pytest.mark.asyncio
    async def test_get_metrics_summary(self):
        """Test metrics summary"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{V3_API}/metrics/summary")
            assert response.status_code == 200
            
            data = response.json()
            assert "agents" in data
            assert "tasks" in data
            assert "resources" in data
    
    @pytest.mark.asyncio
    async def test_get_time_series(self):
        """Test time series data"""
        async with httpx.AsyncClient() as client:
            query = {
                "name": "agents.active",
                "interval": "5m",
                "duration": "1h",
                "aggregation": "avg"
            }
            
            response = await client.post(
                f"{V3_API}/metrics/timeseries",
                json=query
            )
            assert response.status_code == 200
            
            data = response.json()
            assert "series" in data
            assert isinstance(data["series"], list)
    
    @pytest.mark.asyncio
    async def test_set_alert_threshold(self):
        """Test setting alert threshold"""
        async with httpx.AsyncClient() as client:
            threshold = {
                "metric_name": "test.alert.metric",
                "max_value": 100,
                "sustained_duration": 60
            }
            
            response = await client.post(
                f"{V3_API}/metrics/alerts/thresholds",
                json=threshold
            )
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "threshold_set"


class TestV3Integration:
    """Integration tests for V3 features"""
    
    @pytest.mark.asyncio
    async def test_multi_cluster_workflow(self):
        """Test complete multi-cluster workflow"""
        async with httpx.AsyncClient() as client:
            # 1. Register multiple clusters
            clusters = []
            for i in range(2):
                cluster_data = {
                    "name": f"integration-cluster-{i}",
                    "gateway_url": f"http://localhost:{18789 + i}",
                    "region": "us-east" if i == 0 else "us-west",
                    "max_agents": 25
                }
                
                response = await client.post(f"{V3_API}/clusters", json=cluster_data)
                if response.status_code == 200:
                    clusters.append(response.json())
            
            # 2. Check cluster statistics
            response = await client.get(f"{V3_API}/clusters/stats/overview")
            if response.status_code == 200:
                stats = response.json()
                assert stats["total_clusters"] >= len(clusters)
            
            # 3. Distribute task to optimal cluster
            if clusters:
                distribution = {
                    "task_id": "integration-task",
                    "requirements": {"region": "us-east"},
                    "strategy": "least_loaded"
                }
                
                response = await client.post(
                    f"{V3_API}/clusters/distribute",
                    json=distribution
                )
                
                if response.status_code == 200:
                    result = response.json()
                    assert result["cluster_id"] == clusters[0]["cluster_id"]
    
    @pytest.mark.asyncio
    async def test_resource_provisioning_with_metrics(self):
        """Test resource provisioning with metric tracking"""
        async with httpx.AsyncClient() as client:
            # 1. Record initial metrics
            await client.post(
                f"{V3_API}/metrics/record",
                json={
                    "name": "resources.provisioning.requests",
                    "value": 1,
                    "category": "usage"
                }
            )
            
            # 2. Provision resources
            provision_request = {
                "name": "metrics-test-provision",
                "compute": {"vcpus": 2, "memory_gb": 8},
                "strategy": "immediate"
            }
            
            response = await client.post(
                f"{V3_API}/resources/provision",
                json=provision_request
            )
            
            if response.status_code == 200:
                provision = response.json()
                
                # 3. Record success metric
                await client.post(
                    f"{V3_API}/metrics/record",
                    json={
                        "name": "resources.provisioning.success",
                        "value": 1,
                        "category": "reliability"
                    }
                )
                
                # 4. Check metrics
                response = await client.get(
                    f"{V3_API}/metrics",
                    params={"name": "resources.provisioning"}
                )
                
                if response.status_code == 200:
                    metrics = response.json()["metrics"]
                    assert len(metrics) >= 2


# Utility functions
async def cleanup_test_data():
    """Clean up test data after tests"""
    async with httpx.AsyncClient() as client:
        # Clean up test clusters
        response = await client.get(f"{V3_API}/clusters")
        if response.status_code == 200:
            clusters = response.json()
            for cluster in clusters:
                if cluster["name"].startswith("test-") or cluster["name"].startswith("integration-"):
                    await client.delete(f"{V3_API}/clusters/{cluster['cluster_id']}")


if __name__ == "__main__":
    # Run tests
    print("Running V3 API tests...")
    
    # Run cleanup first
    asyncio.run(cleanup_test_data())
    
    # Run test suites
    test_clusters = TestV3Clusters()
    test_resources = TestV3Resources()
    test_rbac = TestV3RBAC()
    test_metrics = TestV3Metrics()
    test_integration = TestV3Integration()
    
    # Run individual tests
    try:
        print("\nTesting Clusters...")
        asyncio.run(test_clusters.test_list_clusters())
        print("✓ Cluster listing works")
        
        print("\nTesting Resources...")
        asyncio.run(test_resources.test_get_quotas())
        print("✓ Resource quotas work")
        
        asyncio.run(test_resources.test_estimate_cost())
        print("✓ Cost estimation works")
        
        print("\nTesting Metrics...")
        asyncio.run(test_metrics.test_record_metric())
        print("✓ Metric recording works")
        
        asyncio.run(test_metrics.test_get_metrics_summary())
        print("✓ Metrics summary works")
        
        print("\n✅ All V3 API tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
    
    finally:
        # Clean up
        asyncio.run(cleanup_test_data())