"""
Cluster Manager Service for V3
Manages multiple OpenClaw clusters with load balancing and failover
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import httpx
import websockets
from enum import Enum

from models.v3_models import (
    Cluster, ClusterStatus, ClusterRegion,
    ClusterAgent, ClusterTask
)
from services.event_manager import event_manager
from core.config import settings

logger = logging.getLogger(__name__)


class DistributionStrategy(Enum):
    """Task distribution strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    GEO_NEAREST = "geo_nearest"
    COST_OPTIMIZED = "cost_optimized"
    PERFORMANCE_OPTIMIZED = "performance_optimized"


class ClusterManager:
    """
    Manages multiple OpenClaw clusters
    Handles registration, health checks, and task distribution
    """
    
    def __init__(self):
        self.clusters: Dict[str, Dict] = {}  # In-memory cluster cache
        self.health_check_interval = 30  # seconds
        self.connections: Dict[str, websockets.WebSocketClientProtocol] = {}
        self._health_check_task = None
        self._running = False
    
    async def start(self):
        """Start cluster manager services"""
        logger.info("Starting Cluster Manager")
        self._running = True
        
        # Load clusters from database
        await self._load_clusters()
        
        # Start health monitoring
        self._health_check_task = asyncio.create_task(self._health_monitor())
        
        # Connect to cluster websockets
        for cluster_id in self.clusters:
            asyncio.create_task(self._connect_to_cluster(cluster_id))
    
    async def stop(self):
        """Stop cluster manager services"""
        logger.info("Stopping Cluster Manager")
        self._running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
        
        # Close all websocket connections
        for ws in self.connections.values():
            await ws.close()
    
    # ========================================
    # Cluster Registration & Management
    # ========================================
    
    async def register_cluster(self, cluster_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new OpenClaw cluster
        """
        logger.info(f"Registering cluster: {cluster_spec.get('name')}")
        
        # Validate cluster connectivity
        if not await self._validate_cluster(cluster_spec['gateway_url']):
            raise ValueError(f"Cannot connect to cluster at {cluster_spec['gateway_url']}")
        
        # Create cluster record
        cluster = {
            "id": cluster_spec.get('id'),
            "name": cluster_spec['name'],
            "gateway_url": cluster_spec['gateway_url'],
            "region": cluster_spec.get('region', ClusterRegion.US_EAST),
            "status": ClusterStatus.ONLINE,
            "max_agents": cluster_spec.get('max_agents', 100),
            "current_agents": 0,
            "health_metrics": {},
            "last_heartbeat": datetime.utcnow()
        }
        
        # Store in cache
        self.clusters[cluster['id']] = cluster
        
        # Connect to cluster
        asyncio.create_task(self._connect_to_cluster(cluster['id']))
        
        # Emit event
        await event_manager.emit({
            "type": "cluster_registered",
            "cluster_id": cluster['id'],
            "name": cluster['name'],
            "region": cluster['region']
        })
        
        return cluster
    
    async def unregister_cluster(self, cluster_id: str, drain: bool = True):
        """
        Remove a cluster from management
        """
        logger.info(f"Unregistering cluster: {cluster_id}")
        
        if cluster_id not in self.clusters:
            raise ValueError(f"Cluster {cluster_id} not found")
        
        if drain:
            # Drain tasks from cluster
            await self.drain_cluster(cluster_id)
        
        # Close websocket connection
        if cluster_id in self.connections:
            await self.connections[cluster_id].close()
            del self.connections[cluster_id]
        
        # Remove from cache
        del self.clusters[cluster_id]
        
        # Emit event
        await event_manager.emit({
            "type": "cluster_unregistered",
            "cluster_id": cluster_id
        })
    
    async def drain_cluster(self, cluster_id: str):
        """
        Drain all tasks from a cluster (for maintenance)
        """
        logger.info(f"Draining cluster: {cluster_id}")
        
        cluster = self.clusters.get(cluster_id)
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")
        
        # Update status
        cluster['status'] = ClusterStatus.DRAINING
        
        # TODO: Migrate running tasks to other clusters
        # This would involve:
        # 1. Getting list of running tasks
        # 2. Finding alternative clusters
        # 3. Migrating each task
        
        await event_manager.emit({
            "type": "cluster_draining",
            "cluster_id": cluster_id
        })
    
    # ========================================
    # Health Monitoring
    # ========================================
    
    async def _health_monitor(self):
        """Background task to monitor cluster health"""
        while self._running:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                for cluster_id in list(self.clusters.keys()):
                    await self._check_cluster_health(cluster_id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
    
    async def _check_cluster_health(self, cluster_id: str):
        """Check health of a specific cluster"""
        cluster = self.clusters.get(cluster_id)
        if not cluster:
            return
        
        try:
            async with httpx.AsyncClient() as client:
                # Attempt health check
                health_url = cluster.get('health_check_url') or f"{cluster['gateway_url']}/health"
                response = await client.get(health_url, timeout=5.0)
                
                if response.status_code == 200:
                    health_data = response.json()
                    
                    # Update cluster metrics
                    cluster['health_metrics'] = health_data
                    cluster['last_heartbeat'] = datetime.utcnow()
                    cluster['current_agents'] = health_data.get('agent_count', 0)
                    
                    # Update status based on health
                    if cluster['status'] == ClusterStatus.OFFLINE:
                        cluster['status'] = ClusterStatus.ONLINE
                        await self._handle_cluster_recovery(cluster_id)
                else:
                    await self._handle_cluster_degraded(cluster_id)
                    
        except Exception as e:
            logger.error(f"Health check failed for cluster {cluster_id}: {e}")
            await self._handle_cluster_failure(cluster_id)
    
    async def _handle_cluster_failure(self, cluster_id: str):
        """Handle cluster failure detection"""
        cluster = self.clusters.get(cluster_id)
        if not cluster:
            return
        
        # Check if cluster has been down too long
        last_heartbeat = cluster.get('last_heartbeat')
        if last_heartbeat:
            downtime = datetime.utcnow() - last_heartbeat
            
            if downtime > timedelta(minutes=5):
                cluster['status'] = ClusterStatus.OFFLINE
                
                # Trigger failover
                await self._initiate_failover(cluster_id)
            else:
                cluster['status'] = ClusterStatus.DEGRADED
        
        await event_manager.emit({
            "type": "cluster_health_changed",
            "cluster_id": cluster_id,
            "status": cluster['status'].value
        })
    
    async def _handle_cluster_recovery(self, cluster_id: str):
        """Handle cluster recovery"""
        logger.info(f"Cluster {cluster_id} recovered")
        
        await event_manager.emit({
            "type": "cluster_recovered",
            "cluster_id": cluster_id
        })
    
    async def _handle_cluster_degraded(self, cluster_id: str):
        """Handle degraded cluster"""
        cluster = self.clusters.get(cluster_id)
        if cluster:
            cluster['status'] = ClusterStatus.DEGRADED
    
    # ========================================
    # Task Distribution
    # ========================================
    
    async def get_optimal_cluster(
        self,
        requirements: Dict[str, Any],
        strategy: DistributionStrategy = DistributionStrategy.LEAST_LOADED
    ) -> Optional[str]:
        """
        Select the best cluster for a task based on requirements and strategy
        """
        available_clusters = [
            c for c in self.clusters.values()
            if c['status'] == ClusterStatus.ONLINE
        ]
        
        if not available_clusters:
            logger.error("No available clusters")
            return None
        
        if strategy == DistributionStrategy.ROUND_ROBIN:
            # Simple round-robin
            return self._round_robin_select(available_clusters)
            
        elif strategy == DistributionStrategy.LEAST_LOADED:
            # Select cluster with lowest load
            return self._least_loaded_select(available_clusters)
            
        elif strategy == DistributionStrategy.GEO_NEAREST:
            # Select geographically nearest cluster
            return self._geo_nearest_select(available_clusters, requirements)
            
        elif strategy == DistributionStrategy.COST_OPTIMIZED:
            # Select most cost-effective cluster
            return self._cost_optimized_select(available_clusters)
            
        elif strategy == DistributionStrategy.PERFORMANCE_OPTIMIZED:
            # Select highest performance cluster
            return self._performance_optimized_select(available_clusters)
        
        # Default to first available
        return available_clusters[0]['id']
    
    def _round_robin_select(self, clusters: List[Dict]) -> str:
        """Round-robin cluster selection"""
        # Simple implementation - could be improved with persistent counter
        import random
        return random.choice(clusters)['id']
    
    def _least_loaded_select(self, clusters: List[Dict]) -> str:
        """Select least loaded cluster"""
        return min(
            clusters,
            key=lambda c: c['current_agents'] / c['max_agents']
        )['id']
    
    def _geo_nearest_select(self, clusters: List[Dict], requirements: Dict) -> str:
        """Select geographically nearest cluster"""
        target_region = requirements.get('region', ClusterRegion.US_EAST)
        
        # Prefer same region
        same_region = [c for c in clusters if c['region'] == target_region]
        if same_region:
            return self._least_loaded_select(same_region)
        
        # Otherwise, use any available
        return self._least_loaded_select(clusters)
    
    def _cost_optimized_select(self, clusters: List[Dict]) -> str:
        """Select most cost-effective cluster"""
        return min(
            clusters,
            key=lambda c: c.get('cost_per_hour', 0)
        )['id']
    
    def _performance_optimized_select(self, clusters: List[Dict]) -> str:
        """Select highest performance cluster"""
        # Could consider metrics like response time, success rate, etc.
        return max(
            clusters,
            key=lambda c: c.get('health_metrics', {}).get('performance_score', 0)
        )['id']
    
    async def distribute_task(
        self,
        task: Dict[str, Any],
        strategy: DistributionStrategy = DistributionStrategy.LEAST_LOADED
    ) -> Dict[str, Any]:
        """
        Distribute a task to the optimal cluster
        """
        # Select cluster
        cluster_id = await self.get_optimal_cluster(task.get('requirements', {}), strategy)
        
        if not cluster_id:
            raise ValueError("No available clusters for task distribution")
        
        cluster = self.clusters[cluster_id]
        
        # Send task to cluster via OpenClaw adapter
        # This would integrate with the existing OpenClawAdapter
        
        logger.info(f"Distributing task {task['id']} to cluster {cluster_id}")
        
        # Track distribution
        await event_manager.emit({
            "type": "task_distributed",
            "task_id": task['id'],
            "cluster_id": cluster_id,
            "strategy": strategy.value
        })
        
        return {
            "task_id": task['id'],
            "cluster_id": cluster_id,
            "cluster_name": cluster['name'],
            "status": "distributed"
        }
    
    # ========================================
    # Failover & Recovery
    # ========================================
    
    async def _initiate_failover(self, failed_cluster_id: str):
        """
        Initiate failover from a failed cluster
        """
        logger.warning(f"Initiating failover for cluster {failed_cluster_id}")
        
        # Get tasks assigned to failed cluster
        # In production, this would query the database
        failed_tasks = []  # TODO: Get from database
        
        # Redistribute tasks to healthy clusters
        for task in failed_tasks:
            try:
                # Find alternative cluster
                new_cluster_id = await self.get_optimal_cluster(
                    task.get('requirements', {}),
                    DistributionStrategy.LEAST_LOADED
                )
                
                if new_cluster_id:
                    await self.distribute_task(task, DistributionStrategy.LEAST_LOADED)
                    
            except Exception as e:
                logger.error(f"Failed to redistribute task {task['id']}: {e}")
        
        await event_manager.emit({
            "type": "cluster_failover_completed",
            "failed_cluster": failed_cluster_id,
            "redistributed_tasks": len(failed_tasks)
        })
    
    # ========================================
    # WebSocket Management
    # ========================================
    
    async def _connect_to_cluster(self, cluster_id: str):
        """Establish WebSocket connection to cluster"""
        cluster = self.clusters.get(cluster_id)
        if not cluster:
            return
        
        try:
            ws_url = cluster['gateway_url'].replace('http', 'ws')
            websocket = await websockets.connect(ws_url)
            self.connections[cluster_id] = websocket
            
            # Listen for events
            asyncio.create_task(self._listen_to_cluster(cluster_id, websocket))
            
            logger.info(f"Connected to cluster {cluster_id}")
            
        except Exception as e:
            logger.error(f"Failed to connect to cluster {cluster_id}: {e}")
    
    async def _listen_to_cluster(self, cluster_id: str, websocket):
        """Listen for events from cluster"""
        try:
            async for message in websocket:
                # Process cluster events
                await self._process_cluster_event(cluster_id, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Connection to cluster {cluster_id} closed")
            await self._handle_cluster_failure(cluster_id)
    
    async def _process_cluster_event(self, cluster_id: str, message: str):
        """Process event from cluster"""
        try:
            event = json.loads(message)
            
            # Update cluster metrics based on events
            if event.get('type') == 'metrics':
                cluster = self.clusters.get(cluster_id)
                if cluster:
                    cluster['health_metrics'] = event.get('data', {})
            
            # Forward to event manager
            await event_manager.emit({
                "type": "cluster_event",
                "cluster_id": cluster_id,
                "event": event
            })
            
        except Exception as e:
            logger.error(f"Error processing cluster event: {e}")
    
    # ========================================
    # Utility Methods
    # ========================================
    
    async def _validate_cluster(self, gateway_url: str) -> bool:
        """Validate cluster connectivity"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{gateway_url}/health", timeout=5.0)
                return response.status_code == 200
        except:
            return False
    
    async def _load_clusters(self):
        """Load clusters from database"""
        # In production, this would query the database
        # For now, using empty dict
        self.clusters = {}
    
    def get_cluster_stats(self) -> Dict[str, Any]:
        """Get statistics about all clusters"""
        total_capacity = sum(c['max_agents'] for c in self.clusters.values())
        total_used = sum(c['current_agents'] for c in self.clusters.values())
        
        return {
            "total_clusters": len(self.clusters),
            "online_clusters": len([c for c in self.clusters.values() if c['status'] == ClusterStatus.ONLINE]),
            "total_capacity": total_capacity,
            "total_used": total_used,
            "utilization": (total_used / total_capacity * 100) if total_capacity > 0 else 0,
            "clusters": [
                {
                    "id": c['id'],
                    "name": c['name'],
                    "status": c['status'].value,
                    "region": c['region'].value,
                    "utilization": (c['current_agents'] / c['max_agents'] * 100) if c['max_agents'] > 0 else 0
                }
                for c in self.clusters.values()
            ]
        }


# Singleton instance
cluster_manager = ClusterManager()