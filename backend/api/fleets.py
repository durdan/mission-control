"""
Fleet API endpoints.
Fleets are logical groupings of agents.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.models import Fleet, Agent
from models.base import get_async_session
from services.event_manager import event_manager
from core.config import settings

router = APIRouter()


@router.get("/", response_model=List[dict])
async def list_fleets(
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """List all fleets."""
    async with session:
        result = await session.execute(select(Fleet))
        fleets = result.scalars().all()
        
        # Get agent counts
        fleet_data = []
        for fleet in fleets:
            agent_count_result = await session.execute(
                select(Agent).filter(Agent.fleet_id == fleet.id)
            )
            agent_count = len(agent_count_result.scalars().all())
            
            fleet_data.append({
                "id": fleet.id,
                "name": fleet.name,
                "description": fleet.description,
                "agent_count": agent_count,
                "created_at": fleet.created_at.isoformat() if fleet.created_at else None
            })
        
        return fleet_data


@router.get("/{fleet_id}")
async def get_fleet(
    fleet_id: str,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Get fleet details with agents."""
    async with session:
        # Get fleet
        result = await session.execute(
            select(Fleet).filter(Fleet.id == fleet_id)
        )
        fleet = result.scalar_one_or_none()
        
        if not fleet:
            raise HTTPException(status_code=404, detail="Fleet not found")
        
        # Get agents in fleet
        agents_result = await session.execute(
            select(Agent).filter(Agent.fleet_id == fleet_id)
        )
        agents = agents_result.scalars().all()
        
        return {
            "id": fleet.id,
            "name": fleet.name,
            "description": fleet.description,
            "metadata": fleet.metadata,
            "agents": [
                {
                    "id": agent.id,
                    "name": agent.name,
                    "role": agent.role,
                    "status": agent.status.value
                }
                for agent in agents
            ],
            "created_at": fleet.created_at.isoformat() if fleet.created_at else None,
            "updated_at": fleet.updated_at.isoformat() if fleet.updated_at else None
        }


@router.post("/")
async def create_fleet(
    fleet_spec: dict,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Create a new fleet."""
    fleet = Fleet(
        id=fleet_spec.get("id"),
        name=fleet_spec.get("name"),
        description=fleet_spec.get("description"),
        metadata=fleet_spec.get("metadata", {})
    )
    
    async with session:
        session.add(fleet)
        await session.commit()
    
    # Emit event
    await event_manager.emit({
        "type": "fleet_created",
        "fleet_id": fleet.id
    })
    
    return {
        "id": fleet.id,
        "name": fleet.name,
        "created": True
    }


@router.put("/{fleet_id}")
async def update_fleet(
    fleet_id: str,
    update_data: dict,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Update fleet metadata."""
    async with session:
        result = await session.execute(
            select(Fleet).filter(Fleet.id == fleet_id)
        )
        fleet = result.scalar_one_or_none()
        
        if not fleet:
            raise HTTPException(status_code=404, detail="Fleet not found")
        
        # Update fields
        if "name" in update_data:
            fleet.name = update_data["name"]
        if "description" in update_data:
            fleet.description = update_data["description"]
        if "metadata" in update_data:
            fleet.metadata = update_data["metadata"]
        
        await session.commit()
        
        return {"id": fleet_id, "updated": True}


@router.delete("/{fleet_id}")
async def delete_fleet(
    fleet_id: str,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Delete a fleet (if no agents assigned)."""
    async with session:
        # Check for agents
        agents_result = await session.execute(
            select(Agent).filter(Agent.fleet_id == fleet_id)
        )
        if agents_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Cannot delete fleet with assigned agents"
            )
        
        # Delete fleet
        result = await session.execute(
            select(Fleet).filter(Fleet.id == fleet_id)
        )
        fleet = result.scalar_one_or_none()
        
        if not fleet:
            raise HTTPException(status_code=404, detail="Fleet not found")
        
        await session.delete(fleet)
        await session.commit()
        
        return {"id": fleet_id, "deleted": True}