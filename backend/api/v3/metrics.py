"""
V3 Metrics API
Provides metrics collection, aggregation, and monitoring endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime, timedelta

from services.metrics_collector import (
    metrics_collector,
    MetricCategory,
    AggregationType
)
from services.event_manager import event_manager

router = APIRouter()


# ========================================
# Request/Response Models
# ========================================

class MetricRecord(BaseModel):
    """Single metric record"""
    name: str
    value: float
    category: str
    tags: dict = {}
    timestamp: Optional[datetime] = None


class MetricBatch(BaseModel):
    """Batch of metrics"""
    metrics: List[MetricRecord]


class AlertThreshold(BaseModel):
    """Alert threshold configuration"""
    metric_name: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    sustained_duration: int = 60


class TimeSeriesQuery(BaseModel):
    """Time series query parameters"""
    name: str
    interval: str = "1m"  # 1m, 5m, 15m, 1h, 1d
    duration: str = "1h"  # 1h, 6h, 24h, 7d, 30d
    aggregation: str = "avg"  # sum, avg, min, max, count


# ========================================
# Metric Recording Endpoints
# ========================================

@router.post("/record")
async def record_metric(metric: MetricRecord):
    """
    Record a single metric data point
    """
    try:
        category = MetricCategory[metric.category.upper()]
        
        await metrics_collector.record_metric(
            name=metric.name,
            value=metric.value,
            category=category,
            tags=metric.tags,
            timestamp=metric.timestamp
        )
        
        return {
            "status": "recorded",
            "metric": metric.name,
            "value": metric.value
        }
        
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid metric category")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch")
async def record_metric_batch(batch: MetricBatch):
    """
    Record multiple metrics at once
    """
    try:
        metrics_data = [
            {
                "name": m.name,
                "value": m.value,
                "category": m.category,
                "tags": m.tags,
                "timestamp": m.timestamp
            }
            for m in batch.metrics
        ]
        
        await metrics_collector.record_batch(metrics_data)
        
        return {
            "status": "recorded",
            "count": len(batch.metrics)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========================================
# Metric Query Endpoints
# ========================================

@router.get("/")
async def get_metrics(
    name: Optional[str] = None,
    category: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(100, le=1000)
):
    """
    Query metrics with filters
    """
    try:
        category_enum = None
        if category:
            category_enum = MetricCategory[category.upper()]
        
        metrics = await metrics_collector.get_metrics(
            name=name,
            category=category_enum,
            start_time=start_time,
            end_time=end_time
        )
        
        # Apply limit
        metrics = metrics[:limit]
        
        return {
            "metrics": metrics,
            "count": len(metrics),
            "filters": {
                "name": name,
                "category": category,
                "start_time": start_time,
                "end_time": end_time
            }
        }
        
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid metric category")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/aggregated")
async def get_aggregated_metrics(
    name: Optional[str] = None,
    aggregation: str = "avg"
):
    """
    Get aggregated metrics
    """
    try:
        agg_type = AggregationType[aggregation.upper()]
        
        aggregated = await metrics_collector.get_aggregated_metrics(
            name=name,
            aggregation=agg_type
        )
        
        return {
            "aggregated": aggregated,
            "aggregation_type": aggregation
        }
        
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid aggregation type")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/timeseries")
async def get_time_series(query: TimeSeriesQuery):
    """
    Get time series data for a metric
    """
    try:
        agg_type = AggregationType[query.aggregation.upper()]
        
        series = await metrics_collector.get_time_series(
            name=query.name,
            interval=query.interval,
            duration=query.duration,
            aggregation=agg_type
        )
        
        return {
            "metric": query.name,
            "series": series,
            "interval": query.interval,
            "duration": query.duration,
            "aggregation": query.aggregation
        }
        
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid aggregation type")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========================================
# Dashboard Endpoints
# ========================================

@router.get("/dashboard")
async def get_dashboard_metrics():
    """
    Get comprehensive metrics for dashboard display
    """
    metrics = await metrics_collector.get_dashboard_metrics()
    return metrics


@router.get("/summary")
async def get_metrics_summary():
    """
    Get summary of current metrics
    """
    summary = {
        "agents": {
            "total": await metrics_collector._get_latest_metric("agents.total"),
            "active": await metrics_collector._get_latest_metric("agents.active")
        },
        "tasks": {
            "pending": await metrics_collector._get_latest_metric("tasks.pending"),
            "success_rate": await metrics_collector._get_latest_metric("tasks.success_rate")
        },
        "resources": {
            "cpu_usage": await metrics_collector._get_latest_metric("resources.cpu_usage"),
            "memory_usage": await metrics_collector._get_latest_metric("resources.memory_usage")
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return summary


# ========================================
# Alert Management Endpoints
# ========================================

@router.post("/alerts/thresholds")
async def set_alert_threshold(threshold: AlertThreshold):
    """
    Set alert threshold for a metric
    """
    try:
        await metrics_collector.set_alert_threshold(
            metric_name=threshold.metric_name,
            min_value=threshold.min_value,
            max_value=threshold.max_value,
            sustained_duration=threshold.sustained_duration
        )
        
        return {
            "status": "threshold_set",
            "metric": threshold.metric_name,
            "min": threshold.min_value,
            "max": threshold.max_value
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/alerts/thresholds")
async def get_alert_thresholds():
    """
    Get all configured alert thresholds
    """
    thresholds = []
    
    for metric_name, threshold in metrics_collector.alert_thresholds.items():
        thresholds.append({
            "metric": metric_name,
            "min": threshold.get('min'),
            "max": threshold.get('max'),
            "sustained_duration": threshold.get('sustained_duration'),
            "violations_count": len(threshold.get('violations', []))
        })
    
    return thresholds


@router.get("/alerts/active")
async def get_active_alerts():
    """
    Get currently active alerts
    """
    alerts = await metrics_collector._get_active_alerts()
    return {
        "alerts": alerts,
        "count": len(alerts),
        "timestamp": datetime.utcnow().isoformat()
    }


# ========================================
# Health & Status Endpoints
# ========================================

@router.get("/health")
async def get_metrics_health():
    """
    Get health status of metrics collector
    """
    return {
        "status": "healthy",
        "running": metrics_collector._running,
        "metrics_buffered": len(metrics_collector.metrics_buffer),
        "metrics_aggregated": len(metrics_collector.aggregated_metrics),
        "alert_thresholds": len(metrics_collector.alert_thresholds),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/stats")
async def get_metrics_stats():
    """
    Get statistics about metrics collection
    """
    total_metrics = sum(len(metrics) for metrics in metrics_collector.metrics_buffer.values())
    
    return {
        "total_metrics": total_metrics,
        "unique_metrics": len(metrics_collector.metrics_buffer),
        "aggregated_metrics": len(metrics_collector.aggregated_metrics),
        "alert_thresholds": len(metrics_collector.alert_thresholds),
        "collection_interval": metrics_collector.collection_interval
    }


# ========================================
# Export Endpoints
# ========================================

@router.get("/export")
async def export_metrics(
    format: str = Query("json", regex="^(json|csv|prometheus)$"),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
):
    """
    Export metrics in various formats
    """
    metrics = await metrics_collector.get_metrics(
        start_time=start_time,
        end_time=end_time
    )
    
    if format == "json":
        return {"metrics": metrics}
    
    elif format == "csv":
        # Convert to CSV format
        import csv
        import io
        
        output = io.StringIO()
        if metrics:
            writer = csv.DictWriter(output, fieldnames=metrics[0].keys())
            writer.writeheader()
            writer.writerows(metrics)
        
        return {
            "format": "csv",
            "data": output.getvalue()
        }
    
    elif format == "prometheus":
        # Convert to Prometheus format
        lines = []
        for metric in metrics:
            tags_str = ""
            if metric.get('tags'):
                tags_str = "{" + ",".join(f'{k}="{v}"' for k, v in metric['tags'].items()) + "}"
            
            lines.append(f"{metric['name']}{tags_str} {metric['value']} {int(metric['timestamp'].timestamp() * 1000)}")
        
        return {
            "format": "prometheus",
            "data": "\n".join(lines)
        }


# ========================================
# Initialization
# ========================================

@router.on_event("startup")
async def startup():
    """Initialize metrics collector on startup"""
    await metrics_collector.start()


@router.on_event("shutdown")
async def shutdown():
    """Cleanup metrics collector on shutdown"""
    await metrics_collector.stop()