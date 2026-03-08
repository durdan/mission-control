"""
V3 Workflow API
Provides workflow management endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

from services.workflow_engine import workflow_engine
from services.event_manager import event_manager

router = APIRouter()


# ========================================
# Request/Response Models
# ========================================

class WorkflowStart(BaseModel):
    """Workflow start request"""
    template_id: str
    entity_type: str
    entity_id: str
    context: dict = {}


class WorkflowAction(BaseModel):
    """Workflow action request"""
    action: str  # approve, reject, escalate
    comment: Optional[str] = None
    actor_id: str


# ========================================
# Workflow Management Endpoints
# ========================================

@router.get("/active")
async def get_active_workflows():
    """
    Get all active workflows
    """
    workflows = []
    
    for workflow_id, workflow in workflow_engine.active_workflows.items():
        workflows.append({
            "id": workflow_id,
            "template": workflow.get('template_id', 'unknown'),
            "status": workflow.get('status', 'unknown'),
            "current_step": workflow.get('current_step', 0),
            "started_at": workflow.get('started_at', datetime.utcnow()).isoformat(),
            "steps_completed": len(workflow.get('completed_steps', [])),
            "steps_total": len(workflow.get('steps', []))
        })
    
    return {
        "workflows": workflows,
        "count": len(workflows)
    }


@router.get("/templates")
async def get_workflow_templates():
    """
    Get available workflow templates
    """
    # Return predefined templates
    templates = [
        {
            "id": "resource-approval",
            "name": "resource-approval",
            "description": "Multi-level approval for resource provisioning",
            "steps": 3,
            "approvers": ["team-lead", "manager", "director"]
        },
        {
            "id": "deployment-approval",
            "name": "deployment-approval",
            "description": "Approval workflow for production deployments",
            "steps": 4,
            "approvers": ["dev-lead", "ops-lead", "security", "release-manager"]
        },
        {
            "id": "emergency-change",
            "name": "emergency-change",
            "description": "Fast-track approval for emergency changes",
            "steps": 2,
            "approvers": ["on-call", "incident-commander"]
        },
        {
            "id": "budget-approval",
            "name": "budget-approval",
            "description": "Budget approval with conditional escalation",
            "steps": 3,
            "approvers": ["finance", "department-head", "cfo"]
        }
    ]
    
    return {
        "templates": templates,
        "count": len(templates)
    }


@router.post("/start")
async def start_workflow(request: WorkflowStart):
    """
    Start a new workflow
    """
    try:
        workflow = await workflow_engine.start_workflow(
            template_id=request.template_id,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            context=request.context
        )
        
        return {
            "workflow_id": workflow["id"],
            "status": workflow["status"],
            "current_step": workflow.get("current_step", 0),
            "message": "Workflow started successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    """
    Get workflow details
    """
    workflow = workflow_engine.active_workflows.get(workflow_id)
    
    if not workflow:
        # Check completed workflows
        workflow = workflow_engine.completed_workflows.get(workflow_id)
        
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {
        "id": workflow_id,
        "template_id": workflow.get("template_id"),
        "entity_type": workflow.get("entity_type"),
        "entity_id": workflow.get("entity_id"),
        "status": workflow.get("status"),
        "current_step": workflow.get("current_step"),
        "steps": workflow.get("steps", []),
        "completed_steps": workflow.get("completed_steps", []),
        "started_at": workflow.get("started_at"),
        "completed_at": workflow.get("completed_at"),
        "context": workflow.get("context", {})
    }


@router.post("/{workflow_id}/action")
async def perform_workflow_action(workflow_id: str, action: WorkflowAction):
    """
    Perform an action on a workflow (approve, reject, escalate)
    """
    workflow = workflow_engine.active_workflows.get(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found or not active")
    
    try:
        if action.action == "approve":
            await workflow_engine.approve_step(
                workflow_id,
                action.actor_id,
                action.comment
            )
            message = "Workflow step approved"
            
        elif action.action == "reject":
            await workflow_engine.reject_workflow(
                workflow_id,
                action.actor_id,
                action.comment or "Rejected"
            )
            message = "Workflow rejected"
            
        elif action.action == "escalate":
            current_step = workflow.get("current_step", 0)
            await workflow_engine._escalate_step(workflow, current_step)
            message = "Workflow escalated"
            
        else:
            raise ValueError(f"Invalid action: {action.action}")
        
        # Get updated workflow
        workflow = workflow_engine.active_workflows.get(
            workflow_id,
            workflow_engine.completed_workflows.get(workflow_id)
        )
        
        return {
            "workflow_id": workflow_id,
            "status": workflow.get("status"),
            "current_step": workflow.get("current_step"),
            "message": message
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{workflow_id}")
async def cancel_workflow(workflow_id: str, reason: str = Query(...)):
    """
    Cancel an active workflow
    """
    workflow = workflow_engine.active_workflows.get(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found or not active")
    
    try:
        # Move to completed with cancelled status
        workflow["status"] = "cancelled"
        workflow["completed_at"] = datetime.utcnow()
        workflow["cancellation_reason"] = reason
        
        workflow_engine.completed_workflows[workflow_id] = workflow
        del workflow_engine.active_workflows[workflow_id]
        
        # Emit event
        await event_manager.emit({
            "type": "workflow_cancelled",
            "workflow_id": workflow_id,
            "reason": reason
        })
        
        return {
            "workflow_id": workflow_id,
            "status": "cancelled",
            "message": "Workflow cancelled successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========================================
# Workflow Statistics Endpoints
# ========================================

@router.get("/stats/overview")
async def get_workflow_statistics():
    """
    Get workflow statistics
    """
    total_active = len(workflow_engine.active_workflows)
    total_completed = len(workflow_engine.completed_workflows)
    
    # Calculate completion stats
    approved = sum(
        1 for w in workflow_engine.completed_workflows.values()
        if w.get("status") == "completed"
    )
    rejected = sum(
        1 for w in workflow_engine.completed_workflows.values()
        if w.get("status") == "rejected"
    )
    cancelled = sum(
        1 for w in workflow_engine.completed_workflows.values()
        if w.get("status") == "cancelled"
    )
    
    success_rate = 0
    if total_completed > 0:
        success_rate = (approved / total_completed) * 100
    
    return {
        "total_workflows": total_active + total_completed,
        "active_workflows": total_active,
        "completed_workflows": total_completed,
        "approved": approved,
        "rejected": rejected,
        "cancelled": cancelled,
        "success_rate": round(success_rate, 2),
        "pending_approvals": sum(
            1 for w in workflow_engine.active_workflows.values()
            if w.get("status") == "waiting_approval"
        )
    }


@router.get("/pending-approvals")
async def get_pending_approvals(approver_id: str = Query(...)):
    """
    Get workflows pending approval for a specific approver
    """
    pending = []
    
    for workflow_id, workflow in workflow_engine.active_workflows.items():
        if workflow.get("status") != "waiting_approval":
            continue
        
        current_step = workflow.get("current_step", 0)
        steps = workflow.get("steps", [])
        
        if current_step < len(steps):
            step = steps[current_step]
            approvers = step.get("approvers", [])
            
            if approver_id in approvers:
                pending.append({
                    "workflow_id": workflow_id,
                    "template": workflow.get("template_id"),
                    "entity_type": workflow.get("entity_type"),
                    "entity_id": workflow.get("entity_id"),
                    "step_name": step.get("name", f"Step {current_step + 1}"),
                    "waiting_since": step.get("started_at", datetime.utcnow()).isoformat(),
                    "context": workflow.get("context", {})
                })
    
    return {
        "pending_approvals": pending,
        "count": len(pending)
    }