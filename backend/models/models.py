"""
Core domain models for Mission Control V2/V3.
These models store METADATA ONLY. OpenClaw owns runtime.
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, Text, JSON, 
    ForeignKey, DateTime, Enum, Index, UniqueConstraint, func
)
from sqlalchemy.orm import relationship
import enum
from .base import Base, TimestampMixin, OpenClawReferenceMixin


class AgentStatus(enum.Enum):
    """Agent status - metadata only, real status in OpenClaw."""
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    BUSY = "busy"
    IDLE = "idle"
    ERROR = "error"
    OFFLINE = "offline"


class TaskStatus(enum.Enum):
    """Task lifecycle status."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class JobStatus(enum.Enum):
    """Job execution status."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalStatus(enum.Enum):
    """Approval decision status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ===========================================
# Fleet & Agent Models
# ===========================================

class Fleet(Base, TimestampMixin):
    """Fleet represents a group of agents."""
    __tablename__ = "fleets"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    metadata = Column(JSON, default={})
    
    # Relationships
    agents = relationship("Agent", back_populates="fleet")


class Agent(Base, TimestampMixin, OpenClawReferenceMixin):
    """
    Agent metadata record.
    The actual agent runs in OpenClaw, we just track metadata.
    """
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    fleet_id = Column(String, ForeignKey("fleets.id"))
    parent_agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    
    # Metadata
    role = Column(String)
    model = Column(String)
    status = Column(Enum(AgentStatus), default=AgentStatus.PROVISIONING)
    prompt_template_id = Column(String, ForeignKey("prompt_templates.id"), nullable=True)
    
    # OpenClaw references inherited from mixin
    # openclaw_agent_ref, openclaw_session_ref, workspace_path
    
    # Relationships
    fleet = relationship("Fleet", back_populates="agents")
    parent_agent = relationship("Agent", remote_side=[id], backref="sub_agents")
    prompt_template = relationship("PromptTemplate", back_populates="agents")
    jobs = relationship("Job", back_populates="agent")
    
    __table_args__ = (
        Index('idx_agent_fleet', 'fleet_id'),
        Index('idx_agent_parent', 'parent_agent_id'),
        UniqueConstraint('openclaw_agent_ref', name='uq_openclaw_agent_ref'),
    )


class PromptTemplate(Base, TimestampMixin):
    """Prompt templates for agents - configuration only."""
    __tablename__ = "prompt_templates"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    template = Column(Text, nullable=False)
    variables = Column(JSON, default=[])
    metadata = Column(JSON, default={})
    
    # Relationships
    agents = relationship("Agent", back_populates="prompt_template")


# ===========================================
# Task Management Models
# ===========================================

class Board(Base, TimestampMixin):
    """Kanban board for task organization."""
    __tablename__ = "boards"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    fleet_id = Column(String, ForeignKey("fleets.id"))
    metadata = Column(JSON, default={})
    
    # Relationships
    columns = relationship("BoardColumn", back_populates="board", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="board")


class BoardColumn(Base, TimestampMixin):
    """Column within a Kanban board."""
    __tablename__ = "columns"
    
    id = Column(String, primary_key=True)
    board_id = Column(String, ForeignKey("boards.id"), nullable=False)
    name = Column(String, nullable=False)
    position = Column(Integer, nullable=False)
    status_mapping = Column(JSON, default=[])  # List of TaskStatus values
    
    # Relationships
    board = relationship("Board", back_populates="columns")
    tasks = relationship("Task", back_populates="column")
    
    __table_args__ = (
        UniqueConstraint('board_id', 'position', name='uq_board_column_position'),
    )


class Task(Base, TimestampMixin):
    """
    Task represents work to be done.
    Task -> Job -> Session (OpenClaw execution)
    """
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    board_id = Column(String, ForeignKey("boards.id"))
    column_id = Column(String, ForeignKey("columns.id"))
    
    # Task details
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    priority = Column(String, default="P2")  # P0, P1, P2, P3
    
    # Assignment
    assigned_agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    
    # Metadata
    metadata = Column(JSON, default={})
    
    # Relationships
    board = relationship("Board", back_populates="tasks")
    column = relationship("BoardColumn", back_populates="tasks")
    assigned_agent = relationship("Agent")
    jobs = relationship("Job", back_populates="task", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_task_status', 'status'),
        Index('idx_task_board', 'board_id'),
    )


# ===========================================
# Execution Models
# ===========================================

class Job(Base, TimestampMixin, OpenClawReferenceMixin):
    """
    Job represents an execution attempt of a task.
    Links to OpenClaw session for actual execution.
    """
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    
    # Job details
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Results
    output = Column(JSON, default={})
    error = Column(Text)
    
    # OpenClaw references inherited from mixin
    
    # Relationships
    task = relationship("Task", back_populates="jobs")
    agent = relationship("Agent", back_populates="jobs")
    sessions = relationship("Session", back_populates="job", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="job")
    
    __table_args__ = (
        Index('idx_job_task', 'task_id'),
        Index('idx_job_agent', 'agent_id'),
        Index('idx_job_status', 'status'),
    )


class Session(Base, TimestampMixin, OpenClawReferenceMixin):
    """
    Session represents an OpenClaw agent session.
    We track metadata, OpenClaw owns the actual session.
    """
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    
    # Session metadata
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    metrics = Column(JSON, default={})
    
    # OpenClaw references inherited from mixin
    
    # Relationships
    job = relationship("Job", back_populates="sessions")
    
    __table_args__ = (
        Index('idx_session_job', 'job_id'),
    )


class Artifact(Base, TimestampMixin):
    """Artifact metadata - actual files may be in OpenClaw workspace."""
    __tablename__ = "artifacts"
    
    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    
    # Artifact details
    name = Column(String, nullable=False)
    type = Column(String)  # file, code, document, etc.
    path = Column(String)  # Reference to file location
    size = Column(Integer)
    mime_type = Column(String)
    metadata = Column(JSON, default={})
    
    # Relationships
    job = relationship("Job", back_populates="artifacts")
    
    __table_args__ = (
        Index('idx_artifact_job', 'job_id'),
    )


# ===========================================
# Operational Models
# ===========================================

class Event(Base):
    """
    Generic event table for activity tracking.
    Powers activity timeline and audit trail.
    """
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String, nullable=False)  # agent_registered, task_created, etc.
    source_type = Column(String)  # agent, task, job, etc.
    source_id = Column(String)  # ID of the source entity
    payload = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_event_type', 'type'),
        Index('idx_event_source', 'source_type', 'source_id'),
        Index('idx_event_created', 'created_at'),
    )


class Approval(Base, TimestampMixin):
    """
    Approval for human-in-the-loop decisions.
    Does NOT execute actions, only tracks decisions.
    """
    __tablename__ = "approvals"
    
    id = Column(String, primary_key=True)
    
    # What needs approval
    entity_type = Column(String, nullable=False)  # task, job, provisioning, etc.
    entity_id = Column(String, nullable=False)
    action = Column(String, nullable=False)  # start_job, provision_agent, etc.
    
    # Approval details
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    requester = Column(String)
    approver = Column(String)
    reason = Column(Text)
    metadata = Column(JSON, default={})
    
    # Timing
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    decided_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index('idx_approval_status', 'status'),
        Index('idx_approval_entity', 'entity_type', 'entity_id'),
    )


class ProvisioningRequest(Base, TimestampMixin):
    """
    Request to provision new resources via OpenClaw.
    Mission Control creates the request, OpenClaw executes it.
    """
    __tablename__ = "provisioning_requests"
    
    id = Column(String, primary_key=True)
    
    # Request details
    resource_type = Column(String, nullable=False)  # agent, workspace, etc.
    resource_spec = Column(JSON, nullable=False)  # Configuration for resource
    status = Column(String, default="pending")  # pending, approved, provisioning, completed, failed
    
    # Approval link
    approval_id = Column(String, ForeignKey("approvals.id"), nullable=True)
    
    # Results
    provisioned_resource_ref = Column(String)  # Reference to created resource in OpenClaw
    error = Column(Text)
    
    # Relationships
    approval = relationship("Approval")
    
    __table_args__ = (
        Index('idx_provisioning_status', 'status'),
    )