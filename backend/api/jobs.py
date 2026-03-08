"""
Job API endpoints.
Jobs are execution attempts of tasks via OpenClaw.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.models import Job, JobStatus, Task, Agent, Session as AgentSession
from models.base import get_async_session
from services.openclaw_adapter import openclaw_adapter
from services.event_manager import event_manager
from core.config import settings

router = APIRouter()


@router.get("/", response_model=List[dict])
async def list_jobs(
    task_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    status: Optional[JobStatus] = None,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """List jobs with optional filtering."""
    query = select(Job)
    
    if task_id:
        query = query.filter(Job.task_id == task_id)
    if agent_id:
        query = query.filter(Job.agent_id == agent_id)
    if status:
        query = query.filter(Job.status == status)
    
    async with session:
        result = await session.execute(query)
        jobs = result.scalars().all()
        
        return [
            {
                "id": job.id,
                "task_id": job.task_id,
                "agent_id": job.agent_id,
                "status": job.status.value,
                "openclaw_session_ref": job.openclaw_session_ref,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
            for job in jobs
        ]


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Get job details with sessions and artifacts."""
    async with session:
        result = await session.execute(
            select(Job).filter(Job.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get sessions
        sessions_result = await session.execute(
            select(AgentSession).filter(AgentSession.job_id == job_id)
        )
        sessions = sessions_result.scalars().all()
        
        return {
            "id": job.id,
            "task_id": job.task_id,
            "agent_id": job.agent_id,
            "status": job.status.value,
            "openclaw_session_ref": job.openclaw_session_ref,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "output": job.output,
            "error": job.error,
            "sessions": [
                {
                    "id": sess.id,
                    "openclaw_session_ref": sess.openclaw_session_ref,
                    "started_at": sess.started_at.isoformat() if sess.started_at else None,
                    "ended_at": sess.ended_at.isoformat() if sess.ended_at else None
                }
                for sess in sessions
            ]
        }


@router.post("/")
async def create_job(
    job_spec: dict,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """
    Create a job to execute a task.
    Requests OpenClaw to start the actual execution.
    """
    # Validate task and agent exist
    async with session:
        task_result = await session.execute(
            select(Task).filter(Task.id == job_spec.get("task_id"))
        )
        task = task_result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        agent_result = await session.execute(
            select(Agent).filter(Agent.id == job_spec.get("agent_id"))
        )
        agent = agent_result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Create job record
        job = Job(
            id=job_spec.get("id", f"job_{datetime.utcnow().timestamp()}"),
            task_id=task.id,
            agent_id=agent.id,
            status=JobStatus.QUEUED
        )
        
        session.add(job)
        await session.commit()
        
        # Request OpenClaw to start session
        if agent.openclaw_agent_ref:
            openclaw_session = await openclaw_adapter.start_session(
                agent_ref=agent.openclaw_agent_ref,
                job_id=job.id,
                task_description=task.description or task.title
            )
            
            # Update job with session reference
            job.openclaw_session_ref = openclaw_session.get("openclaw_session_ref")
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            
            # Create session record
            agent_session = AgentSession(
                id=f"session_{job.id}",
                job_id=job.id,
                openclaw_session_ref=openclaw_session.get("openclaw_session_ref"),
                started_at=datetime.utcnow()
            )
            session.add(agent_session)
            
            # Update task status
            task.status = TaskStatus.IN_PROGRESS
            
            await session.commit()
        
        # Emit event
        await event_manager.emit({
            "type": "job_started",
            "job_id": job.id,
            "task_id": task.id,
            "agent_id": agent.id
        })
        
        return {
            "id": job.id,
            "status": job.status.value,
            "openclaw_session_ref": job.openclaw_session_ref
        }


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Cancel a running job."""
    async with session:
        result = await session.execute(
            select(Job).filter(Job.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status not in [JobStatus.QUEUED, JobStatus.RUNNING]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job in status: {job.status.value}"
            )
        
        # Request OpenClaw to end session
        if job.openclaw_session_ref:
            await openclaw_adapter.end_session(job.openclaw_session_ref)
        
        # Update job status
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        
        await session.commit()
        
        # Emit event
        await event_manager.emit({
            "type": "job_cancelled",
            "job_id": job_id
        })
        
        return {
            "id": job_id,
            "status": job.status.value,
            "cancelled": True
        }


@router.post("/{job_id}/complete")
async def complete_job(
    job_id: str,
    completion_data: dict,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """
    Mark job as completed (called by OpenClaw via webhook).
    We don't complete jobs, OpenClaw does.
    """
    async with session:
        result = await session.execute(
            select(Job).filter(Job.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Update job with results
        job.status = JobStatus.SUCCEEDED if not completion_data.get("error") else JobStatus.FAILED
        job.completed_at = datetime.utcnow()
        job.output = completion_data.get("output", {})
        job.error = completion_data.get("error")
        
        # Update task status
        task_result = await session.execute(
            select(Task).filter(Task.id == job.task_id)
        )
        task = task_result.scalar_one_or_none()
        if task:
            if job.status == JobStatus.SUCCEEDED:
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.BLOCKED
        
        await session.commit()
        
        # Emit event
        await event_manager.emit({
            "type": "job_completed",
            "job_id": job_id,
            "status": job.status.value
        })
        
        return {
            "id": job_id,
            "status": job.status.value,
            "completed": True
        }