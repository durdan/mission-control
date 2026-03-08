"""
V3 Enterprise Models for Mission Control
Multi-cluster, advanced workflows, and enterprise features
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, Text, JSON, Float, 
    ForeignKey, DateTime, Enum, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
import uuid
from datetime import datetime
from .base import Base, TimestampMixin

# ============================================
# Multi-Cluster Support
# ============================================

class ClusterStatus(enum.Enum):
    """Cluster operational status"""
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    DRAINING = "draining"
    MAINTENANCE = "maintenance"


class ClusterRegion(enum.Enum):
    """Geographic regions for clusters"""
    US_EAST = "us-east"
    US_WEST = "us-west"
    EU_WEST = "eu-west"
    EU_CENTRAL = "eu-central"
    ASIA_PACIFIC = "asia-pacific"
    ASIA_SOUTH = "asia-south"


class Cluster(Base, TimestampMixin):
    """OpenClaw cluster registration"""
    __tablename__ = "clusters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    gateway_url = Column(String(500), nullable=False)
    region = Column(Enum(ClusterRegion), nullable=False)
    status = Column(Enum(ClusterStatus), default=ClusterStatus.ONLINE)
    
    # Capacity and limits
    max_agents = Column(Integer, default=100)
    current_agents = Column(Integer, default=0)
    max_concurrent_tasks = Column(Integer, default=1000)
    
    # Health monitoring
    health_check_url = Column(String(500))
    last_heartbeat = Column(DateTime(timezone=True))
    health_metrics = Column(JSON, default={})
    
    # Cost tracking
    cost_per_hour = Column(Float, default=0.0)
    cost_center = Column(String(100))
    
    # Configuration
    config = Column(JSON, default={})
    tags = Column(JSON, default=[])
    
    # Relationships
    agents = relationship("ClusterAgent", back_populates="cluster")
    tasks = relationship("ClusterTask", back_populates="cluster")
    
    __table_args__ = (
        Index('idx_cluster_status', 'status'),
        Index('idx_cluster_region', 'region'),
        CheckConstraint('current_agents <= max_agents', name='check_agent_capacity'),
    )


class ClusterAgent(Base, TimestampMixin):
    """Agent-to-cluster mapping for multi-cluster deployments"""
    __tablename__ = "cluster_agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    cluster_id = Column(UUID(as_uuid=True), ForeignKey("clusters.id"), nullable=False)
    
    # Load balancing metrics
    current_load = Column(Float, default=0.0)
    task_count = Column(Integer, default=0)
    success_rate = Column(Float, default=100.0)
    avg_response_time = Column(Float)  # milliseconds
    
    # Cluster-specific configuration
    cluster_config = Column(JSON, default={})
    
    # Relationships
    cluster = relationship("Cluster", back_populates="agents")
    
    __table_args__ = (
        UniqueConstraint('agent_id', 'cluster_id', name='uq_agent_cluster'),
        Index('idx_cluster_agent_load', 'current_load'),
    )


class ClusterTask(Base, TimestampMixin):
    """Task distribution across clusters"""
    __tablename__ = "cluster_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    cluster_id = Column(UUID(as_uuid=True), ForeignKey("clusters.id"), nullable=False)
    
    # Distribution strategy
    strategy = Column(String, default="round_robin")  # round_robin, least_loaded, geo_nearest
    priority = Column(Integer, default=5)
    
    # Execution metrics
    assigned_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    execution_time = Column(Float)  # seconds
    
    # Relationships
    cluster = relationship("Cluster", back_populates="tasks")
    
    __table_args__ = (
        Index('idx_cluster_task_priority', 'priority'),
        Index('idx_cluster_task_status', 'assigned_at', 'completed_at'),
    )


# ============================================
# Advanced Approval Workflows
# ============================================

class WorkflowStatus(enum.Enum):
    """Workflow execution status"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ApprovalAction(enum.Enum):
    """Approval decision actions"""
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"
    DELEGATE = "delegate"
    REQUEST_INFO = "request_info"


class WorkflowTemplate(Base, TimestampMixin):
    """Reusable workflow templates"""
    __tablename__ = "workflow_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    category = Column(String(100))
    
    # Workflow definition (JSON schema)
    definition = Column(JSON, nullable=False)
    """
    Example definition:
    {
        "steps": [
            {
                "level": 1,
                "approvers": ["team_lead"],
                "timeout_hours": 2,
                "escalate_to": "manager"
            },
            {
                "level": 2,
                "approvers": ["security_team", "compliance_team"],
                "parallel": true,
                "required_approvals": 2
            }
        ],
        "conditions": [
            {
                "if": "cost > 10000",
                "add_step": {
                    "level": 3,
                    "approvers": ["cto"]
                }
            }
        ]
    }
    """
    
    # Template metadata
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(255))
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True))
    
    # Relationships
    workflows = relationship("WorkflowInstance", back_populates="template")


class WorkflowInstance(Base, TimestampMixin):
    """Active workflow execution instance"""
    __tablename__ = "workflow_instances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("workflow_templates.id"))
    
    # Workflow context
    entity_type = Column(String(100), nullable=False)  # task, provisioning, deployment
    entity_id = Column(String, nullable=False)
    
    # Execution state
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.ACTIVE)
    current_step = Column(Integer, default=1)
    
    # Runtime data
    context = Column(JSON, default={})  # Variables for conditions
    history = Column(JSON, default=[])  # Audit trail
    
    # Timing
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True))
    deadline = Column(DateTime(timezone=True))
    
    # Relationships
    template = relationship("WorkflowTemplate", back_populates="workflows")
    approval_steps = relationship("ApprovalStep", back_populates="workflow")
    
    __table_args__ = (
        Index('idx_workflow_status', 'status'),
        Index('idx_workflow_entity', 'entity_type', 'entity_id'),
    )


class ApprovalStep(Base, TimestampMixin):
    """Individual approval step in workflow"""
    __tablename__ = "approval_steps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflow_instances.id"), nullable=False)
    
    # Step configuration
    step_number = Column(Integer, nullable=False)
    approver_id = Column(String(255), nullable=False)
    approver_role = Column(String(100))
    
    # Decision
    action = Column(Enum(ApprovalAction))
    decision_at = Column(DateTime(timezone=True))
    comments = Column(Text)
    
    # Escalation
    escalated_from = Column(UUID(as_uuid=True), ForeignKey("approval_steps.id"))
    escalated_to = Column(String(255))
    escalation_reason = Column(String(500))
    
    # Timing
    assigned_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    deadline = Column(DateTime(timezone=True))
    reminder_sent_at = Column(DateTime(timezone=True))
    
    # Relationships
    workflow = relationship("WorkflowInstance", back_populates="approval_steps")
    
    __table_args__ = (
        Index('idx_approval_approver', 'approver_id'),
        Index('idx_approval_deadline', 'deadline'),
        UniqueConstraint('workflow_id', 'step_number', 'approver_id', name='uq_workflow_step_approver'),
    )


# ============================================
# Resource Provisioning
# ============================================

class ResourceType(enum.Enum):
    """Types of provisionable resources"""
    AGENT = "agent"
    WORKSPACE = "workspace"
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    DATABASE = "database"


class ProvisioningStatus(enum.Enum):
    """Provisioning request status"""
    PENDING = "pending"
    APPROVED = "approved"
    PROVISIONING = "provisioning"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResourceTemplate(Base, TimestampMixin):
    """Templates for resource provisioning"""
    __tablename__ = "resource_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    resource_type = Column(Enum(ResourceType), nullable=False)
    
    # Specification
    specifications = Column(JSON, nullable=False)
    """
    Example for agent:
    {
        "model": "gpt-4",
        "memory": "4Gi",
        "cpu": "2",
        "tools": ["web_search", "code_execution"],
        "permissions": ["read_workspace", "write_output"]
    }
    """
    
    # Cost estimation
    estimated_cost_hourly = Column(Float)
    estimated_cost_monthly = Column(Float)
    
    # Constraints
    max_instances = Column(Integer, default=10)
    requires_approval = Column(Boolean, default=True)
    approval_threshold = Column(Float)  # Cost threshold
    
    # Metadata
    tags = Column(JSON, default=[])
    is_active = Column(Boolean, default=True)


class ProvisioningRequest(Base, TimestampMixin):
    """Request to provision resources"""
    __tablename__ = "provisioning_requests_v3"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("resource_templates.id"))
    
    # Request details
    requester_id = Column(String(255), nullable=False)
    project_id = Column(String(255))
    cluster_id = Column(UUID(as_uuid=True), ForeignKey("clusters.id"))
    
    # Resource configuration
    resource_type = Column(Enum(ResourceType), nullable=False)
    specifications = Column(JSON, nullable=False)
    quantity = Column(Integer, default=1)
    
    # Status tracking
    status = Column(Enum(ProvisioningStatus), default=ProvisioningStatus.PENDING)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflow_instances.id"))
    
    # Cost tracking
    estimated_cost = Column(Float)
    actual_cost = Column(Float)
    cost_center = Column(String(100))
    
    # Provisioning results
    provisioned_resources = Column(JSON, default=[])  # List of created resource IDs
    provisioning_logs = Column(JSON, default=[])
    error_message = Column(Text)
    
    # Timing
    requested_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    approved_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))  # Auto-cleanup
    
    __table_args__ = (
        Index('idx_provisioning_status', 'status'),
        Index('idx_provisioning_requester', 'requester_id'),
        Index('idx_provisioning_project', 'project_id'),
    )


# ============================================
# RBAC Security
# ============================================

class Role(Base, TimestampMixin):
    """Security roles for access control"""
    __tablename__ = "roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    
    # Permissions (JSON array of permission strings)
    permissions = Column(JSON, nullable=False)
    """
    Example permissions:
    ["agents:read", "agents:write", "tasks:*", "approvals:approve"]
    """
    
    # Role hierarchy
    parent_role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"))
    
    # Metadata
    is_system = Column(Boolean, default=False)  # Built-in roles
    is_active = Column(Boolean, default=True)
    
    # Relationships
    parent_role = relationship("Role", remote_side=[id])
    user_roles = relationship("UserRole", back_populates="role")


class UserRole(Base, TimestampMixin):
    """User-to-role assignments"""
    __tablename__ = "user_roles"
    
    user_id = Column(String(255), primary_key=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True)
    
    # Assignment metadata
    granted_by = Column(String(255))
    granted_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True))
    
    # Scope limitations
    scope_type = Column(String(50))  # global, cluster, project
    scope_id = Column(String(255))  # ID of cluster/project
    
    # Relationships
    role = relationship("Role", back_populates="user_roles")
    
    __table_args__ = (
        Index('idx_user_role_user', 'user_id'),
        Index('idx_user_role_expires', 'expires_at'),
    )


class ApiKey(Base, TimestampMixin):
    """API key management"""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash = Column(String(255), unique=True, nullable=False)  # SHA256 hash
    
    # Owner
    user_id = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    
    # Permissions
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"))
    scopes = Column(JSON, default=[])  # Additional permission scopes
    
    # Security
    last_used_at = Column(DateTime(timezone=True))
    last_used_ip = Column(String(45))  # IPv6 support
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    
    # Rate limiting
    rate_limit = Column(Integer, default=1000)  # Requests per hour
    current_usage = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_api_key_user', 'user_id'),
        Index('idx_api_key_expires', 'expires_at'),
    )


# ============================================
# Monitoring & Metrics
# ============================================

class MetricType(enum.Enum):
    """Types of metrics collected"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class Metric(Base):
    """Time-series metrics storage"""
    __tablename__ = "metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Metric identification
    name = Column(String(255), nullable=False)
    type = Column(Enum(MetricType), nullable=False)
    
    # Source
    source_type = Column(String(100), nullable=False)  # agent, cluster, task
    source_id = Column(String(255), nullable=False)
    
    # Value
    value = Column(Float, nullable=False)
    unit = Column(String(50))  # seconds, bytes, percentage
    
    # Labels/tags for filtering
    labels = Column(JSON, default={})
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_metric_name_time', 'name', 'timestamp'),
        Index('idx_metric_source', 'source_type', 'source_id'),
        Index('idx_metric_timestamp', 'timestamp'),
    )


class SLADefinition(Base, TimestampMixin):
    """Service Level Agreement definitions"""
    __tablename__ = "sla_definitions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    
    # SLA target
    metric_name = Column(String(255), nullable=False)
    target_value = Column(Float, nullable=False)
    comparison = Column(String(10))  # >, <, >=, <=, ==
    
    # Measurement window
    window_minutes = Column(Integer, default=60)
    calculation = Column(String(50))  # avg, min, max, percentile_95
    
    # Alert configuration
    alert_enabled = Column(Boolean, default=True)
    alert_channels = Column(JSON, default=[])  # email, slack, pagerduty
    
    # Tracking
    is_active = Column(Boolean, default=True)
    last_evaluated = Column(DateTime(timezone=True))
    current_status = Column(String(50))  # meeting, warning, breaching
    
    __table_args__ = (
        Index('idx_sla_active', 'is_active'),
        Index('idx_sla_status', 'current_status'),
    )


# ============================================
# Audit & Compliance
# ============================================

class AuditLog(Base):
    """Comprehensive audit logging"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event details
    event_type = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    
    # Actor
    user_id = Column(String(255), nullable=False)
    user_role = Column(String(100))
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    # Target
    target_type = Column(String(100))
    target_id = Column(String(255))
    
    # Changes
    old_value = Column(JSON)
    new_value = Column(JSON)
    
    # Context
    request_id = Column(String(100))
    session_id = Column(String(100))
    
    # Result
    success = Column(Boolean, nullable=False)
    error_message = Column(Text)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_type', 'event_type'),
        Index('idx_audit_target', 'target_type', 'target_id'),
    )