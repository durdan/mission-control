"""
Task API endpoints.
Tasks represent work to be done, executed via OpenClaw jobs.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.models import Task, TaskStatus, Board, BoardColumn, Job
from models.base import get_async_session
from services.event_manager import event_manager
from core.config import settings

router = APIRouter()


@router.get("/", response_model=List[dict])
async def list_tasks(
    board_id: Optional[str] = None,
    status: Optional[TaskStatus] = None,
    assigned_agent_id: Optional[str] = None,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """List tasks with optional filtering."""
    query = select(Task)
    
    if board_id:
        query = query.filter(Task.board_id == board_id)
    if status:
        query = query.filter(Task.status == status)
    if assigned_agent_id:
        query = query.filter(Task.assigned_agent_id == assigned_agent_id)
    
    async with session:
        result = await session.execute(query)
        tasks = result.scalars().all()
        
        return [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status.value,
                "priority": task.priority,
                "board_id": task.board_id,
                "column_id": task.column_id,
                "assigned_agent_id": task.assigned_agent_id,
                "created_at": task.created_at.isoformat() if task.created_at else None
            }
            for task in tasks
        ]


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Get task details with jobs."""
    async with session:
        result = await session.execute(
            select(Task).filter(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Get jobs for task
        jobs_result = await session.execute(
            select(Job).filter(Job.task_id == task_id)
        )
        jobs = jobs_result.scalars().all()
        
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority,
            "board_id": task.board_id,
            "column_id": task.column_id,
            "assigned_agent_id": task.assigned_agent_id,
            "metadata": task.metadata,
            "jobs": [
                {
                    "id": job.id,
                    "status": job.status.value,
                    "agent_id": job.agent_id,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None
                }
                for job in jobs
            ],
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None
        }


@router.post("/")
async def create_task(
    task_spec: dict,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Create a new task."""
    task = Task(
        id=task_spec.get("id"),
        board_id=task_spec.get("board_id"),
        column_id=task_spec.get("column_id"),
        title=task_spec.get("title"),
        description=task_spec.get("description"),
        status=TaskStatus.PENDING,
        priority=task_spec.get("priority", "P2"),
        assigned_agent_id=task_spec.get("assigned_agent_id"),
        metadata=task_spec.get("metadata", {})
    )
    
    async with session:
        session.add(task)
        await session.commit()
    
    # Emit event
    await event_manager.emit({
        "type": "task_created",
        "task_id": task.id,
        "board_id": task.board_id
    })
    
    return {
        "id": task.id,
        "status": task.status.value,
        "created": True
    }


@router.put("/{task_id}/status")
async def update_task_status(
    task_id: str,
    status_update: dict,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Update task status."""
    async with session:
        result = await session.execute(
            select(Task).filter(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        new_status = TaskStatus[status_update.get("status").upper()]
        old_status = task.status
        task.status = new_status
        
        # Update column if status maps to different column
        if "column_id" in status_update:
            task.column_id = status_update["column_id"]
        
        await session.commit()
        
        # Emit event
        await event_manager.emit({
            "type": "task_status_changed",
            "task_id": task_id,
            "old_status": old_status.value,
            "new_status": new_status.value
        })
        
        return {
            "id": task_id,
            "status": new_status.value,
            "updated": True
        }


@router.post("/{task_id}/assign")
async def assign_task(
    task_id: str,
    assignment: dict,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Assign task to an agent."""
    async with session:
        result = await session.execute(
            select(Task).filter(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task.assigned_agent_id = assignment.get("agent_id")
        task.status = TaskStatus.ASSIGNED
        
        await session.commit()
        
        # Emit event
        await event_manager.emit({
            "type": "task_assigned",
            "task_id": task_id,
            "agent_id": task.assigned_agent_id
        })
        
        return {
            "id": task_id,
            "assigned_to": task.assigned_agent_id,
            "status": task.status.value
        }


@router.get("/boards/", response_model=List[dict])
async def list_boards(
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """List all boards."""
    async with session:
        result = await session.execute(select(Board))
        boards = result.scalars().all()
        
        return [
            {
                "id": board.id,
                "name": board.name,
                "description": board.description,
                "fleet_id": board.fleet_id
            }
            for board in boards
        ]


@router.post("/boards/")
async def create_board(
    board_spec: dict,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Create a new board with default columns."""
    board = Board(
        id=board_spec.get("id"),
        name=board_spec.get("name"),
        description=board_spec.get("description"),
        fleet_id=board_spec.get("fleet_id"),
        metadata=board_spec.get("metadata", {})
    )
    
    # Create default columns
    default_columns = [
        BoardColumn(
            id=f"{board.id}_backlog",
            board_id=board.id,
            name="Backlog",
            position=0,
            status_mapping=[TaskStatus.PENDING]
        ),
        BoardColumn(
            id=f"{board.id}_todo",
            board_id=board.id,
            name="To Do",
            position=1,
            status_mapping=[TaskStatus.ASSIGNED]
        ),
        BoardColumn(
            id=f"{board.id}_progress",
            board_id=board.id,
            name="In Progress",
            position=2,
            status_mapping=[TaskStatus.IN_PROGRESS]
        ),
        BoardColumn(
            id=f"{board.id}_review",
            board_id=board.id,
            name="Review",
            position=3,
            status_mapping=[TaskStatus.REVIEW]
        ),
        BoardColumn(
            id=f"{board.id}_done",
            board_id=board.id,
            name="Done",
            position=4,
            status_mapping=[TaskStatus.COMPLETED]
        )
    ]
    
    async with session:
        session.add(board)
        for column in default_columns:
            session.add(column)
        await session.commit()
    
    return {
        "id": board.id,
        "name": board.name,
        "columns": len(default_columns)
    }