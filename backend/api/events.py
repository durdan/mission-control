"""
Event API endpoints.
Events track all activity for audit and timeline.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from models.models import Event
from models.base import get_async_session
from core.config import settings

router = APIRouter()


@router.get("/", response_model=List[dict])
async def list_events(
    event_type: Optional[str] = None,
    source_type: Optional[str] = None,
    source_id: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0),
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """List events with optional filtering."""
    query = select(Event).order_by(desc(Event.created_at))
    
    if event_type:
        query = query.filter(Event.type == event_type)
    if source_type:
        query = query.filter(Event.source_type == source_type)
    if source_id:
        query = query.filter(Event.source_id == source_id)
    
    query = query.limit(limit).offset(offset)
    
    async with session:
        result = await session.execute(query)
        events = result.scalars().all()
        
        return [
            {
                "id": event.id,
                "type": event.type,
                "source_type": event.source_type,
                "source_id": event.source_id,
                "payload": event.payload,
                "created_at": event.created_at.isoformat() if event.created_at else None
            }
            for event in events
        ]


@router.get("/timeline")
async def get_timeline(
    hours: int = Query(default=24, le=168),  # Max 1 week
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Get event timeline for the specified time range."""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    query = select(Event).filter(
        Event.created_at >= since
    ).order_by(desc(Event.created_at))
    
    async with session:
        result = await session.execute(query)
        events = result.scalars().all()
        
        # Group events by hour for timeline visualization
        timeline = {}
        for event in events:
            hour_key = event.created_at.strftime("%Y-%m-%d %H:00")
            if hour_key not in timeline:
                timeline[hour_key] = []
            
            timeline[hour_key].append({
                "id": event.id,
                "type": event.type,
                "source": f"{event.source_type}/{event.source_id}",
                "time": event.created_at.strftime("%H:%M:%S")
            })
        
        return timeline


@router.get("/activity/{entity_type}/{entity_id}")
async def get_entity_activity(
    entity_type: str,
    entity_id: str,
    limit: int = Query(default=50),
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Get activity history for a specific entity."""
    query = select(Event).filter(
        Event.source_type == entity_type,
        Event.source_id == entity_id
    ).order_by(desc(Event.created_at)).limit(limit)
    
    async with session:
        result = await session.execute(query)
        events = result.scalars().all()
        
        return [
            {
                "type": event.type,
                "payload": event.payload,
                "created_at": event.created_at.isoformat()
            }
            for event in events
        ]


@router.post("/")
async def create_event(
    event_data: dict,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """
    Create a new event.
    Usually called internally or via webhooks.
    """
    event = Event(
        type=event_data.get("type"),
        source_type=event_data.get("source_type"),
        source_id=event_data.get("source_id"),
        payload=event_data.get("payload", {})
    )
    
    async with session:
        session.add(event)
        await session.commit()
        
        return {
            "id": event.id,
            "type": event.type,
            "created": True
        }


@router.get("/stats")
async def get_event_stats(
    hours: int = Query(default=24),
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Get event statistics for monitoring."""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    async with session:
        # Get total events
        total_result = await session.execute(
            select(Event).filter(Event.created_at >= since)
        )
        total_events = len(total_result.scalars().all())
        
        # Get events by type
        type_stats = {}
        for event_type in ["agent_created", "task_created", "job_started", "job_completed"]:
            type_result = await session.execute(
                select(Event).filter(
                    Event.type == event_type,
                    Event.created_at >= since
                )
            )
            type_stats[event_type] = len(type_result.scalars().all())
        
        return {
            "period_hours": hours,
            "total_events": total_events,
            "events_by_type": type_stats,
            "events_per_hour": round(total_events / hours, 2) if hours > 0 else 0
        }