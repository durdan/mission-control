"""
Agent API endpoints.
We manage metadata, OpenClaw owns runtime.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.models import Agent, AgentStatus
from models.base import get_async_session
from services.openclaw_adapter import openclaw_adapter
from services.event_manager import event_manager
from core.config import settings

router = APIRouter()


@router.get("/", response_model=List[dict])
async def list_agents(
    fleet_id: Optional[str] = None,
    status: Optional[AgentStatus] = None,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """List all agents with optional filtering."""
    query = select(Agent)
    
    if fleet_id:
        query = query.filter(Agent.fleet_id == fleet_id)
    if status:
        query = query.filter(Agent.status == status)
    
    async with session:
        result = await session.execute(query)
        agents = result.scalars().all()
        
        return [
            {
                "id": agent.id,
                "name": agent.name,
                "role": agent.role,
                "model": agent.model,
                "status": agent.status.value,
                "fleet_id": agent.fleet_id,
                "openclaw_ref": agent.openclaw_agent_ref,
                "workspace_path": agent.workspace_path
            }
            for agent in agents
        ]


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Get agent metadata and current status."""
    async with session:
        result = await session.execute(
            select(Agent).filter(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get live status from OpenClaw if available
        live_status = None
        if agent.openclaw_agent_ref:
            live_status = await openclaw_adapter.get_agent_status(agent.openclaw_agent_ref)
        
        return {
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "model": agent.model,
            "status": agent.status.value,
            "fleet_id": agent.fleet_id,
            "openclaw_ref": agent.openclaw_agent_ref,
            "workspace_path": agent.workspace_path,
            "live_status": live_status,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "updated_at": agent.updated_at.isoformat() if agent.updated_at else None
        }


@router.post("/")
async def create_agent(
    agent_spec: dict,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """
    Request creation of a new agent.
    OpenClaw creates the agent, we store the reference.
    """
    # Request OpenClaw to create the agent
    openclaw_result = await openclaw_adapter.create_agent(agent_spec)
    
    # Store metadata reference
    agent = Agent(
        id=agent_spec.get("id"),
        name=agent_spec.get("name"),
        role=agent_spec.get("role"),
        model=agent_spec.get("model"),
        fleet_id=agent_spec.get("fleet_id"),
        status=AgentStatus.PROVISIONING,
        openclaw_agent_ref=openclaw_result.get("openclaw_agent_ref"),
        workspace_path=openclaw_result.get("workspace_path")
    )
    
    async with session:
        session.add(agent)
        await session.commit()
    
    # Emit event
    await event_manager.emit({
        "type": "agent_created",
        "agent_id": agent.id,
        "openclaw_ref": agent.openclaw_agent_ref
    })
    
    return {
        "id": agent.id,
        "openclaw_ref": agent.openclaw_agent_ref,
        "status": "provisioning"
    }


@router.post("/{agent_id}/register")
async def register_existing_agent(
    agent_id: str,
    metadata: dict,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """
    Register an existing OpenClaw agent with Mission Control.
    For agents created outside Mission Control.
    """
    # Verify with OpenClaw
    success = await openclaw_adapter.register_agent(agent_id, metadata)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to verify agent in OpenClaw")
    
    # Store metadata
    agent = Agent(
        id=agent_id,
        name=metadata.get("name", agent_id),
        role=metadata.get("role"),
        model=metadata.get("model"),
        fleet_id=metadata.get("fleet_id"),
        status=AgentStatus.ACTIVE,
        openclaw_agent_ref=metadata.get("openclaw_ref", f"oclaw_agent_{agent_id}"),
        workspace_path=metadata.get("workspace_path")
    )
    
    async with session:
        session.add(agent)
        await session.commit()
    
    return {"id": agent_id, "registered": True}


@router.get("/{agent_id}/heartbeat")
async def get_agent_heartbeat(agent_id: str):
    """Get latest heartbeat data for an agent."""
    # This would fetch from event store or cache
    return {
        "agent_id": agent_id,
        "last_heartbeat": "2024-01-15T10:30:00Z",
        "status": "active"
    }


@router.get("/{agent_id}/sub-agents")
async def get_sub_agents(
    agent_id: str,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Get sub-agents for a parent agent."""
    async with session:
        # Get parent agent
        result = await session.execute(
            select(Agent).filter(Agent.id == agent_id)
        )
        parent = result.scalar_one_or_none()
        
        if not parent:
            raise HTTPException(status_code=404, detail="Parent agent not found")
        
        # Sync sub-agents from OpenClaw
        if parent.openclaw_agent_ref:
            sub_agent_refs = await openclaw_adapter.sync_subagents(parent.openclaw_agent_ref)
            # Here we would update our database with the sub-agents
        
        # Return sub-agents from our database
        result = await session.execute(
            select(Agent).filter(Agent.parent_agent_id == agent_id)
        )
        sub_agents = result.scalars().all()
        
        return [
            {
                "id": agent.id,
                "name": agent.name,
                "role": agent.role,
                "status": agent.status.value
            }
            for agent in sub_agents
        ]