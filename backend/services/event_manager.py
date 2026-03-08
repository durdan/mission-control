"""
Event Manager Service
=====================
Manages event streaming and Server-Sent Events (SSE) for live updates.
Uses Redis for pub/sub to enable horizontal scaling.
"""

import asyncio
import json
import logging
from typing import Dict, Any, AsyncGenerator, Set
from datetime import datetime
import redis.asyncio as redis

from core.config import settings
from models.models import Event
from models.base import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class EventManager:
    """
    Manages event distribution and SSE streaming.
    Events flow from OpenClaw -> Mission Control -> Frontend.
    """
    
    def __init__(self):
        self.redis_client = None
        self.pubsub = None
        self.subscribers: Set[asyncio.Queue] = set()
        self.running = False
        self._listener_task = None
    
    async def start(self):
        """Start the event manager."""
        try:
            # Connect to Redis
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.pubsub = self.redis_client.pubsub()
            
            # Subscribe to event channels
            await self.pubsub.subscribe(
                "mission_control:events",
                "openclaw:events"  # Listen to OpenClaw events
            )
            
            # Start listener
            self.running = True
            self._listener_task = asyncio.create_task(self._listen_for_events())
            
            logger.info("Event manager started")
        except Exception as e:
            logger.error(f"Failed to start event manager: {e}")
            raise
    
    async def stop(self):
        """Stop the event manager."""
        self.running = False
        
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Event manager stopped")
    
    async def emit(self, event_data: Dict[str, Any]):
        """
        Emit an event to all subscribers.
        Also stores in database for audit trail.
        """
        try:
            # Add timestamp
            event_data["timestamp"] = datetime.utcnow().isoformat()
            
            # Store in database if it's a significant event
            if event_data.get("type") and event_data.get("type") != "heartbeat":
                await self._store_event(event_data)
            
            # Publish to Redis
            if self.redis_client:
                await self.redis_client.publish(
                    "mission_control:events",
                    json.dumps(event_data)
                )
            
            # Direct emit to local subscribers
            await self._broadcast_to_subscribers(event_data)
            
        except Exception as e:
            logger.error(f"Failed to emit event: {e}")
    
    async def _store_event(self, event_data: Dict[str, Any]):
        """Store event in database."""
        try:
            async for session in get_async_session(settings.DATABASE_URL):
                event = Event(
                    type=event_data.get("type"),
                    source_type=event_data.get("source_type"),
                    source_id=event_data.get("source_id"),
                    payload=event_data
                )
                session.add(event)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to store event: {e}")
    
    async def _listen_for_events(self):
        """Listen for events from Redis pub/sub."""
        logger.info("Starting event listener")
        
        while self.running:
            try:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )
                
                if message:
                    channel = message["channel"]
                    data = json.loads(message["data"])
                    
                    # Process based on channel
                    if channel == "openclaw:events":
                        # Events from OpenClaw
                        await self._handle_openclaw_event(data)
                    else:
                        # Internal events
                        await self._broadcast_to_subscribers(data)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in event listener: {e}")
                await asyncio.sleep(1)  # Brief pause before retry
    
    async def _handle_openclaw_event(self, event_data: Dict[str, Any]):
        """
        Handle events from OpenClaw.
        Transform and relay to frontend.
        """
        event_type = event_data.get("type")
        
        # Transform OpenClaw events to Mission Control format
        transformed = {
            "source": "openclaw",
            "type": event_type,
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Special handling for certain events
        if event_type == "agent_heartbeat":
            # Update agent status in cache/database
            pass
        elif event_type == "session_completed":
            # Update job status
            pass
        elif event_type == "artifact_created":
            # Register artifact
            pass
        
        # Broadcast to subscribers
        await self._broadcast_to_subscribers(transformed)
    
    async def _broadcast_to_subscribers(self, event_data: Dict[str, Any]):
        """Broadcast event to all SSE subscribers."""
        dead_queues = set()
        
        for queue in self.subscribers:
            try:
                await queue.put(event_data)
            except:
                # Queue is full or closed
                dead_queues.add(queue)
        
        # Clean up dead queues
        self.subscribers -= dead_queues
    
    async def subscribe(self) -> AsyncGenerator[str, None]:
        """
        Subscribe to SSE events.
        Returns an async generator for SSE streaming.
        """
        queue = asyncio.Queue(maxsize=100)
        self.subscribers.add(queue)
        
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            
            # Stream events
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f": keepalive\n\n"
                    
        finally:
            # Cleanup on disconnect
            self.subscribers.discard(queue)
    
    async def emit_agent_status(self, agent_id: str, status: str, metadata: Dict[str, Any] = None):
        """Emit agent status change event."""
        await self.emit({
            "type": "agent_status_changed",
            "source_type": "agent",
            "source_id": agent_id,
            "status": status,
            "metadata": metadata or {}
        })
    
    async def emit_task_update(self, task_id: str, update_type: str, data: Dict[str, Any]):
        """Emit task update event."""
        await self.emit({
            "type": f"task_{update_type}",
            "source_type": "task",
            "source_id": task_id,
            **data
        })
    
    async def emit_job_event(self, job_id: str, event_type: str, data: Dict[str, Any]):
        """Emit job-related event."""
        await self.emit({
            "type": f"job_{event_type}",
            "source_type": "job",
            "source_id": job_id,
            **data
        })
    
    async def emit_system_event(self, event_type: str, message: str, severity: str = "info"):
        """Emit system-level event."""
        await self.emit({
            "type": f"system_{event_type}",
            "source_type": "system",
            "source_id": "mission_control",
            "message": message,
            "severity": severity
        })


# Singleton instance
event_manager = EventManager()