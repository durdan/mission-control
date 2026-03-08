"""
Metrics Collector Service for V3
Collects, aggregates, and stores performance metrics for Mission Control
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import statistics
from collections import defaultdict, deque

from models.v3_models import Metric, MetricType
from services.event_manager import event_manager
from services.cluster_manager import cluster_manager
from core.config import settings

logger = logging.getLogger(__name__)


class MetricCategory(Enum):
    """Metric categories"""
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    CAPACITY = "capacity"
    COST = "cost"
    HEALTH = "health"
    USAGE = "usage"


class AggregationType(Enum):
    """Metric aggregation types"""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    P50 = "p50"
    P95 = "p95"
    P99 = "p99"


class MetricsCollector:
    """
    Collects and manages metrics for Mission Control
    Provides real-time and historical metrics analysis
    """
    
    def __init__(self):
        self.metrics_buffer: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.aggregated_metrics: Dict[str, Dict] = {}
        self.alert_thresholds: Dict[str, Dict] = {}
        self.collection_interval = 10  # seconds
        self._collection_task = None
        self._aggregation_task = None
        self._running = False
    
    async def start(self):
        """Start metrics collection services"""
        logger.info("Starting Metrics Collector")
        self._running = True
        
        # Load alert thresholds
        await self._load_alert_thresholds()
        
        # Start collection and aggregation tasks
        self._collection_task = asyncio.create_task(self._collect_metrics())
        self._aggregation_task = asyncio.create_task(self._aggregate_metrics())
        
        # Subscribe to events for metrics
        await self._subscribe_to_events()
    
    async def stop(self):
        """Stop metrics collection services"""
        logger.info("Stopping Metrics Collector")
        self._running = False
        
        if self._collection_task:
            self._collection_task.cancel()
        
        if self._aggregation_task:
            self._aggregation_task.cancel()
    
    # ========================================
    # Metric Recording
    # ========================================
    
    async def record_metric(
        self,
        name: str,
        value: float,
        category: MetricCategory,
        tags: Dict[str, str] = None,
        timestamp: datetime = None
    ):
        """Record a single metric data point"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        metric = {
            "name": name,
            "value": value,
            "category": category.value,
            "tags": tags or {},
            "timestamp": timestamp
        }
        
        # Add to buffer
        key = self._get_metric_key(name, tags)
        self.metrics_buffer[key].append(metric)
        
        # Check alerts
        await self._check_alert_threshold(name, value, tags)
        
        # Emit metric event for real-time monitoring
        if self._should_emit_realtime(name):
            await event_manager.emit({
                "type": "metric_recorded",
                "metric": metric
            })
    
    async def record_batch(self, metrics: List[Dict[str, Any]]):
        """Record multiple metrics at once"""
        for metric in metrics:
            await self.record_metric(
                name=metric['name'],
                value=metric['value'],
                category=MetricCategory[metric['category'].upper()],
                tags=metric.get('tags'),
                timestamp=metric.get('timestamp')
            )
    
    # ========================================
    # System Metrics Collection
    # ========================================
    
    async def _collect_metrics(self):
        """Background task to collect system metrics"""
        while self._running:
            try:
                await asyncio.sleep(self.collection_interval)
                
                # Collect various system metrics
                await self._collect_agent_metrics()
                await self._collect_task_metrics()
                await self._collect_cluster_metrics()
                await self._collect_resource_metrics()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
    
    async def _collect_agent_metrics(self):
        """Collect agent-related metrics"""
        # Would query actual agent data
        await self.record_metric(
            "agents.total",
            0,  # Would get from database
            MetricCategory.CAPACITY
        )
        
        await self.record_metric(
            "agents.active",
            0,  # Would get from database
            MetricCategory.USAGE
        )
    
    async def _collect_task_metrics(self):
        """Collect task-related metrics"""
        # Would query actual task data
        await self.record_metric(
            "tasks.pending",
            0,  # Would get from database
            MetricCategory.PERFORMANCE
        )
        
        await self.record_metric(
            "tasks.success_rate",
            100.0,  # Would calculate from database
            MetricCategory.RELIABILITY
        )
    
    async def _collect_cluster_metrics(self):
        """Collect cluster metrics"""
        if cluster_manager.clusters:
            for cluster_id, cluster in cluster_manager.clusters.items():
                # Cluster utilization
                utilization = 0
                if cluster['max_agents'] > 0:
                    utilization = (cluster['current_agents'] / cluster['max_agents']) * 100
                
                await self.record_metric(
                    "cluster.utilization",
                    utilization,
                    MetricCategory.CAPACITY,
                    tags={"cluster_id": cluster_id}
                )
                
                # Cluster health
                health_score = 100 if cluster['status'].value == 'online' else 0
                await self.record_metric(
                    "cluster.health",
                    health_score,
                    MetricCategory.HEALTH,
                    tags={"cluster_id": cluster_id}
                )
    
    async def _collect_resource_metrics(self):
        """Collect resource utilization metrics"""
        # Would query actual resource usage
        await self.record_metric(
            "resources.cpu_usage",
            0.0,  # Would get from system
            MetricCategory.USAGE
        )
        
        await self.record_metric(
            "resources.memory_usage",
            0.0,  # Would get from system
            MetricCategory.USAGE
        )
    
    # ========================================
    # Metric Aggregation
    # ========================================
    
    async def _aggregate_metrics(self):
        """Background task to aggregate metrics"""
        while self._running:
            try:
                await asyncio.sleep(60)  # Aggregate every minute
                
                for key, metrics in self.metrics_buffer.items():
                    if metrics:
                        await self._aggregate_metric_data(key, list(metrics))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics aggregation error: {e}")
    
    async def _aggregate_metric_data(self, key: str, metrics: List[Dict]):
        """Aggregate metric data points"""
        values = [m['value'] for m in metrics]
        
        if not values:
            return
        
        aggregated = {
            "key": key,
            "count": len(values),
            "sum": sum(values),
            "avg": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "timestamp": datetime.utcnow()
        }
        
        # Calculate percentiles for larger datasets
        if len(values) >= 10:
            sorted_values = sorted(values)
            aggregated["p50"] = self._percentile(sorted_values, 50)
            aggregated["p95"] = self._percentile(sorted_values, 95)
            aggregated["p99"] = self._percentile(sorted_values, 99)
        
        self.aggregated_metrics[key] = aggregated
    
    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values"""
        index = (len(sorted_values) - 1) * (percentile / 100)
        lower = int(index)
        upper = lower + 1
        
        if upper >= len(sorted_values):
            return sorted_values[lower]
        
        weight = index - lower
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
    
    # ========================================
    # Metric Queries
    # ========================================
    
    async def get_metrics(
        self,
        name: Optional[str] = None,
        category: Optional[MetricCategory] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Query metrics with filters"""
        results = []
        
        for key, metrics in self.metrics_buffer.items():
            for metric in metrics:
                # Apply filters
                if name and metric['name'] != name:
                    continue
                
                if category and metric['category'] != category.value:
                    continue
                
                if start_time and metric['timestamp'] < start_time:
                    continue
                
                if end_time and metric['timestamp'] > end_time:
                    continue
                
                if tags:
                    if not all(metric.get('tags', {}).get(k) == v for k, v in tags.items()):
                        continue
                
                results.append(metric)
        
        return sorted(results, key=lambda x: x['timestamp'])
    
    async def get_aggregated_metrics(
        self,
        name: Optional[str] = None,
        aggregation: AggregationType = AggregationType.AVG
    ) -> Dict[str, Any]:
        """Get aggregated metrics"""
        results = {}
        
        for key, aggregated in self.aggregated_metrics.items():
            if name and not key.startswith(name):
                continue
            
            if aggregation == AggregationType.SUM:
                value = aggregated.get('sum')
            elif aggregation == AggregationType.AVG:
                value = aggregated.get('avg')
            elif aggregation == AggregationType.MIN:
                value = aggregated.get('min')
            elif aggregation == AggregationType.MAX:
                value = aggregated.get('max')
            elif aggregation == AggregationType.COUNT:
                value = aggregated.get('count')
            elif aggregation == AggregationType.P50:
                value = aggregated.get('p50')
            elif aggregation == AggregationType.P95:
                value = aggregated.get('p95')
            elif aggregation == AggregationType.P99:
                value = aggregated.get('p99')
            else:
                value = aggregated.get('avg')
            
            results[key] = {
                "value": value,
                "timestamp": aggregated.get('timestamp')
            }
        
        return results
    
    async def get_time_series(
        self,
        name: str,
        interval: str = "1m",
        duration: str = "1h",
        aggregation: AggregationType = AggregationType.AVG
    ) -> List[Dict[str, Any]]:
        """Get time series data for a metric"""
        # Parse duration
        duration_map = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30)
        }
        
        duration_delta = duration_map.get(duration, timedelta(hours=1))
        start_time = datetime.utcnow() - duration_delta
        
        # Parse interval
        interval_map = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "1d": timedelta(days=1)
        }
        
        interval_delta = interval_map.get(interval, timedelta(minutes=1))
        
        # Get metrics
        metrics = await self.get_metrics(name=name, start_time=start_time)
        
        # Group by interval
        time_series = []
        current_time = start_time
        
        while current_time < datetime.utcnow():
            interval_end = current_time + interval_delta
            interval_metrics = [
                m for m in metrics
                if current_time <= m['timestamp'] < interval_end
            ]
            
            if interval_metrics:
                values = [m['value'] for m in interval_metrics]
                
                if aggregation == AggregationType.SUM:
                    value = sum(values)
                elif aggregation == AggregationType.AVG:
                    value = statistics.mean(values)
                elif aggregation == AggregationType.MIN:
                    value = min(values)
                elif aggregation == AggregationType.MAX:
                    value = max(values)
                elif aggregation == AggregationType.COUNT:
                    value = len(values)
                else:
                    value = statistics.mean(values)
                
                time_series.append({
                    "timestamp": current_time,
                    "value": value
                })
            else:
                time_series.append({
                    "timestamp": current_time,
                    "value": None
                })
            
            current_time = interval_end
        
        return time_series
    
    # ========================================
    # Alerting
    # ========================================
    
    async def set_alert_threshold(
        self,
        metric_name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        sustained_duration: int = 60  # seconds
    ):
        """Set alert threshold for a metric"""
        self.alert_thresholds[metric_name] = {
            "min": min_value,
            "max": max_value,
            "sustained_duration": sustained_duration,
            "violations": []
        }
    
    async def _check_alert_threshold(
        self,
        metric_name: str,
        value: float,
        tags: Dict[str, str] = None
    ):
        """Check if metric violates alert threshold"""
        if metric_name not in self.alert_thresholds:
            return
        
        threshold = self.alert_thresholds[metric_name]
        violated = False
        
        if threshold['min'] is not None and value < threshold['min']:
            violated = True
            violation_type = "below_minimum"
        elif threshold['max'] is not None and value > threshold['max']:
            violated = True
            violation_type = "above_maximum"
        
        if violated:
            # Track violation
            threshold['violations'].append({
                "timestamp": datetime.utcnow(),
                "value": value,
                "type": violation_type
            })
            
            # Check if sustained
            cutoff_time = datetime.utcnow() - timedelta(seconds=threshold['sustained_duration'])
            recent_violations = [
                v for v in threshold['violations']
                if v['timestamp'] > cutoff_time
            ]
            
            if len(recent_violations) >= 3:  # At least 3 violations in duration
                await self._trigger_alert(metric_name, value, violation_type, tags)
        else:
            # Clear violations if metric returns to normal
            threshold['violations'] = []
    
    async def _trigger_alert(
        self,
        metric_name: str,
        value: float,
        violation_type: str,
        tags: Dict[str, str] = None
    ):
        """Trigger an alert for metric threshold violation"""
        logger.warning(f"Alert: {metric_name} = {value} ({violation_type})")
        
        await event_manager.emit({
            "type": "metric_alert",
            "metric_name": metric_name,
            "value": value,
            "violation_type": violation_type,
            "tags": tags,
            "timestamp": datetime.utcnow()
        })
    
    # ========================================
    # Dashboard Support
    # ========================================
    
    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get metrics for dashboard display"""
        return {
            "summary": {
                "agents_total": await self._get_latest_metric("agents.total"),
                "agents_active": await self._get_latest_metric("agents.active"),
                "tasks_pending": await self._get_latest_metric("tasks.pending"),
                "success_rate": await self._get_latest_metric("tasks.success_rate"),
                "cpu_usage": await self._get_latest_metric("resources.cpu_usage"),
                "memory_usage": await self._get_latest_metric("resources.memory_usage")
            },
            "clusters": await self._get_cluster_metrics(),
            "performance": await self.get_time_series("tasks.success_rate", "5m", "1h"),
            "capacity": await self.get_time_series("agents.active", "5m", "1h"),
            "alerts": await self._get_active_alerts()
        }
    
    async def _get_latest_metric(self, name: str) -> Optional[float]:
        """Get latest value for a metric"""
        metrics = await self.get_metrics(name=name)
        if metrics:
            return metrics[-1]['value']
        return None
    
    async def _get_cluster_metrics(self) -> List[Dict[str, Any]]:
        """Get metrics for all clusters"""
        cluster_metrics = []
        
        for cluster_id in cluster_manager.clusters:
            utilization = await self._get_latest_metric_with_tags(
                "cluster.utilization",
                {"cluster_id": cluster_id}
            )
            
            health = await self._get_latest_metric_with_tags(
                "cluster.health",
                {"cluster_id": cluster_id}
            )
            
            cluster_metrics.append({
                "cluster_id": cluster_id,
                "utilization": utilization,
                "health": health
            })
        
        return cluster_metrics
    
    async def _get_latest_metric_with_tags(
        self,
        name: str,
        tags: Dict[str, str]
    ) -> Optional[float]:
        """Get latest value for a metric with specific tags"""
        metrics = await self.get_metrics(name=name, tags=tags)
        if metrics:
            return metrics[-1]['value']
        return None
    
    async def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts"""
        active_alerts = []
        
        for metric_name, threshold in self.alert_thresholds.items():
            if threshold['violations']:
                latest_violation = threshold['violations'][-1]
                active_alerts.append({
                    "metric": metric_name,
                    "violation": latest_violation['type'],
                    "value": latest_violation['value'],
                    "timestamp": latest_violation['timestamp']
                })
        
        return active_alerts
    
    # ========================================
    # Helper Methods
    # ========================================
    
    def _get_metric_key(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Generate unique key for metric"""
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            return f"{name}:{tag_str}"
        return name
    
    def _should_emit_realtime(self, metric_name: str) -> bool:
        """Check if metric should emit real-time events"""
        # Emit real-time for critical metrics
        critical_metrics = [
            "cluster.health",
            "tasks.success_rate",
            "agents.failures"
        ]
        return metric_name in critical_metrics
    
    async def _load_alert_thresholds(self):
        """Load default alert thresholds"""
        # Default thresholds
        await self.set_alert_threshold("tasks.success_rate", min_value=95.0)
        await self.set_alert_threshold("cluster.utilization", max_value=90.0)
        await self.set_alert_threshold("resources.cpu_usage", max_value=80.0)
        await self.set_alert_threshold("resources.memory_usage", max_value=85.0)
    
    async def _subscribe_to_events(self):
        """Subscribe to events for metric collection"""
        # Would subscribe to event manager for various events
        pass


# Singleton instance
metrics_collector = MetricsCollector()