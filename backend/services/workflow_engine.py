"""
Workflow Engine for V3
Advanced approval workflows with conditional routing and escalation
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

from models.v3_models import (
    WorkflowTemplate, WorkflowInstance, WorkflowStatus,
    ApprovalStep, ApprovalAction
)
from services.event_manager import event_manager
from core.config import settings

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Manages approval workflows with multi-level approvals,
    conditional routing, and time-based escalations
    """
    
    def __init__(self):
        self.active_workflows: Dict[str, Dict] = {}  # In-memory workflow cache
        self.escalation_check_interval = 60  # seconds
        self._escalation_task = None
        self._running = False
    
    async def start(self):
        """Start workflow engine services"""
        logger.info("Starting Workflow Engine")
        self._running = True
        
        # Load active workflows
        await self._load_active_workflows()
        
        # Start escalation monitor
        self._escalation_task = asyncio.create_task(self._escalation_monitor())
    
    async def stop(self):
        """Stop workflow engine services"""
        logger.info("Stopping Workflow Engine")
        self._running = False
        
        if self._escalation_task:
            self._escalation_task.cancel()
    
    # ========================================
    # Workflow Template Management
    # ========================================
    
    async def create_template(self, template_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a reusable workflow template
        """
        logger.info(f"Creating workflow template: {template_spec.get('name')}")
        
        # Validate template definition
        if not self._validate_template(template_spec['definition']):
            raise ValueError("Invalid workflow template definition")
        
        template = {
            "id": template_spec.get('id'),
            "name": template_spec['name'],
            "description": template_spec.get('description'),
            "category": template_spec.get('category'),
            "definition": template_spec['definition'],
            "version": 1,
            "is_active": True,
            "created_by": template_spec.get('created_by'),
            "created_at": datetime.utcnow()
        }
        
        # Emit event
        await event_manager.emit({
            "type": "workflow_template_created",
            "template_id": template['id'],
            "name": template['name']
        })
        
        return template
    
    def _validate_template(self, definition: Dict) -> bool:
        """Validate workflow template definition"""
        # Check required fields
        if 'steps' not in definition or not definition['steps']:
            return False
        
        # Validate each step
        for step in definition['steps']:
            if 'level' not in step or 'approvers' not in step:
                return False
        
        return True
    
    # ========================================
    # Workflow Execution
    # ========================================
    
    async def start_workflow(
        self,
        template_id: str,
        entity_type: str,
        entity_id: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Start a new workflow instance
        """
        logger.info(f"Starting workflow for {entity_type}/{entity_id}")
        
        # Get template (in production, from database)
        template = await self._get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # Create workflow instance
        workflow = {
            "id": f"wf_{datetime.utcnow().timestamp()}",
            "template_id": template_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "status": WorkflowStatus.ACTIVE,
            "current_step": 1,
            "context": context or {},
            "history": [],
            "started_at": datetime.utcnow(),
            "deadline": datetime.utcnow() + timedelta(hours=48)  # Default 48h deadline
        }
        
        # Store in cache
        self.active_workflows[workflow['id']] = workflow
        
        # Process first step
        await self._process_workflow_step(workflow['id'])
        
        # Emit event
        await event_manager.emit({
            "type": "workflow_started",
            "workflow_id": workflow['id'],
            "entity_type": entity_type,
            "entity_id": entity_id
        })
        
        return workflow
    
    async def _process_workflow_step(self, workflow_id: str):
        """Process current step of workflow"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return
        
        # Get template
        template = await self._get_template(workflow['template_id'])
        if not template:
            return
        
        definition = template['definition']
        current_step = workflow['current_step']
        
        # Check if we've completed all steps
        if current_step > len(definition['steps']):
            await self._complete_workflow(workflow_id)
            return
        
        # Get current step definition
        step_def = definition['steps'][current_step - 1]
        
        # Check conditions
        if 'conditions' in definition:
            step_def = await self._apply_conditions(workflow, step_def, definition['conditions'])
        
        # Create approval requests
        await self._create_approval_requests(workflow, step_def)
    
    async def _apply_conditions(
        self,
        workflow: Dict,
        step_def: Dict,
        conditions: List[Dict]
    ) -> Dict:
        """Apply conditional logic to workflow step"""
        context = workflow['context']
        
        for condition in conditions:
            # Evaluate condition
            if self._evaluate_condition(condition['if'], context):
                # Apply modifications
                if 'add_step' in condition:
                    # Add additional approval step
                    pass  # Implementation depends on requirements
                
                if 'skip_to' in condition:
                    # Skip to different step
                    workflow['current_step'] = condition['skip_to']
                
                if 'add_approvers' in condition:
                    # Add additional approvers
                    step_def['approvers'].extend(condition['add_approvers'])
        
        return step_def
    
    def _evaluate_condition(self, condition: str, context: Dict) -> bool:
        """Evaluate a condition string"""
        # Simple implementation - in production, use safe evaluation
        try:
            # Parse condition like "cost > 10000"
            parts = condition.split()
            if len(parts) == 3:
                field, operator, value = parts
                field_value = context.get(field)
                
                if field_value is None:
                    return False
                
                if operator == '>':
                    return float(field_value) > float(value)
                elif operator == '<':
                    return float(field_value) < float(value)
                elif operator == '==':
                    return str(field_value) == value
                elif operator == '>=':
                    return float(field_value) >= float(value)
                elif operator == '<=':
                    return float(field_value) <= float(value)
        except:
            pass
        
        return False
    
    async def _create_approval_requests(self, workflow: Dict, step_def: Dict):
        """Create approval requests for a workflow step"""
        approvers = step_def.get('approvers', [])
        parallel = step_def.get('parallel', False)
        timeout_hours = step_def.get('timeout_hours', 24)
        
        deadline = datetime.utcnow() + timedelta(hours=timeout_hours)
        
        for approver in approvers:
            approval = {
                "id": f"approval_{datetime.utcnow().timestamp()}",
                "workflow_id": workflow['id'],
                "step_number": workflow['current_step'],
                "approver_id": approver,
                "assigned_at": datetime.utcnow(),
                "deadline": deadline,
                "escalate_to": step_def.get('escalate_to')
            }
            
            # Store approval (in production, to database)
            # For now, add to workflow history
            workflow['history'].append({
                "type": "approval_requested",
                "step": workflow['current_step'],
                "approver": approver,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Notify approver
            await self._notify_approver(approver, workflow, approval)
        
        # Emit event
        await event_manager.emit({
            "type": "approvals_requested",
            "workflow_id": workflow['id'],
            "step": workflow['current_step'],
            "approvers": approvers
        })
    
    async def _notify_approver(self, approver: str, workflow: Dict, approval: Dict):
        """Send notification to approver"""
        # In production, this would send email/Slack/etc.
        logger.info(f"Notifying approver {approver} for workflow {workflow['id']}")
        
        await event_manager.emit({
            "type": "approval_notification",
            "approver": approver,
            "workflow_id": workflow['id'],
            "entity_type": workflow['entity_type'],
            "entity_id": workflow['entity_id'],
            "deadline": approval['deadline'].isoformat()
        })
    
    # ========================================
    # Approval Processing
    # ========================================
    
    async def process_approval(
        self,
        workflow_id: str,
        approver_id: str,
        action: ApprovalAction,
        comments: str = None
    ) -> Dict[str, Any]:
        """
        Process an approval decision
        """
        logger.info(f"Processing approval for workflow {workflow_id} by {approver_id}: {action.value}")
        
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        if workflow['status'] != WorkflowStatus.ACTIVE:
            raise ValueError(f"Workflow is not active: {workflow['status'].value}")
        
        # Record decision
        workflow['history'].append({
            "type": "approval_decision",
            "step": workflow['current_step'],
            "approver": approver_id,
            "action": action.value,
            "comments": comments,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Handle different actions
        if action == ApprovalAction.APPROVE:
            await self._handle_approval(workflow_id, approver_id)
        elif action == ApprovalAction.REJECT:
            await self._handle_rejection(workflow_id, approver_id, comments)
        elif action == ApprovalAction.ESCALATE:
            await self._handle_escalation(workflow_id, approver_id, comments)
        elif action == ApprovalAction.DELEGATE:
            await self._handle_delegation(workflow_id, approver_id, comments)
        elif action == ApprovalAction.REQUEST_INFO:
            await self._handle_info_request(workflow_id, approver_id, comments)
        
        # Emit event
        await event_manager.emit({
            "type": "approval_processed",
            "workflow_id": workflow_id,
            "approver": approver_id,
            "action": action.value
        })
        
        return {
            "workflow_id": workflow_id,
            "action": action.value,
            "status": workflow['status'].value
        }
    
    async def _handle_approval(self, workflow_id: str, approver_id: str):
        """Handle approval action"""
        workflow = self.active_workflows[workflow_id]
        
        # Check if all required approvals for current step are complete
        template = await self._get_template(workflow['template_id'])
        step_def = template['definition']['steps'][workflow['current_step'] - 1]
        
        required_approvals = step_def.get('required_approvals', len(step_def['approvers']))
        current_approvals = len([
            h for h in workflow['history']
            if h['type'] == 'approval_decision' and
            h['step'] == workflow['current_step'] and
            h['action'] == ApprovalAction.APPROVE.value
        ])
        
        if current_approvals >= required_approvals:
            # Move to next step
            workflow['current_step'] += 1
            await self._process_workflow_step(workflow_id)
    
    async def _handle_rejection(self, workflow_id: str, approver_id: str, reason: str):
        """Handle rejection action"""
        workflow = self.active_workflows[workflow_id]
        workflow['status'] = WorkflowStatus.CANCELLED
        
        # Notify requester
        await event_manager.emit({
            "type": "workflow_rejected",
            "workflow_id": workflow_id,
            "approver": approver_id,
            "reason": reason
        })
    
    async def _handle_escalation(self, workflow_id: str, from_approver: str, reason: str):
        """Handle escalation action"""
        workflow = self.active_workflows[workflow_id]
        
        # Get escalation target
        template = await self._get_template(workflow['template_id'])
        step_def = template['definition']['steps'][workflow['current_step'] - 1]
        escalate_to = step_def.get('escalate_to')
        
        if escalate_to:
            # Create new approval request for escalated approver
            await self._create_approval_requests(workflow, {
                'approvers': [escalate_to],
                'timeout_hours': 12  # Shorter timeout for escalations
            })
            
            # Notify escalation
            await event_manager.emit({
                "type": "approval_escalated",
                "workflow_id": workflow_id,
                "from": from_approver,
                "to": escalate_to,
                "reason": reason
            })
    
    async def _handle_delegation(self, workflow_id: str, from_approver: str, delegate_to: str):
        """Handle delegation action"""
        # Create approval request for delegate
        workflow = self.active_workflows[workflow_id]
        
        await self._create_approval_requests(workflow, {
            'approvers': [delegate_to],
            'timeout_hours': 24
        })
        
        # Notify delegation
        await event_manager.emit({
            "type": "approval_delegated",
            "workflow_id": workflow_id,
            "from": from_approver,
            "to": delegate_to
        })
    
    async def _handle_info_request(self, workflow_id: str, approver_id: str, info_needed: str):
        """Handle information request"""
        workflow = self.active_workflows[workflow_id]
        
        # Pause workflow
        workflow['status'] = WorkflowStatus.PAUSED
        
        # Notify requester
        await event_manager.emit({
            "type": "info_requested",
            "workflow_id": workflow_id,
            "approver": approver_id,
            "info_needed": info_needed
        })
    
    # ========================================
    # Escalation Management
    # ========================================
    
    async def _escalation_monitor(self):
        """Background task to check for timeout escalations"""
        while self._running:
            try:
                await asyncio.sleep(self.escalation_check_interval)
                await self._check_escalations()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Escalation monitor error: {e}")
    
    async def _check_escalations(self):
        """Check all active workflows for timeout escalations"""
        current_time = datetime.utcnow()
        
        for workflow_id, workflow in self.active_workflows.items():
            if workflow['status'] != WorkflowStatus.ACTIVE:
                continue
            
            # Check workflow deadline
            if workflow.get('deadline') and current_time > workflow['deadline']:
                await self._escalate_workflow(workflow_id, "Workflow deadline exceeded")
            
            # Check step deadlines
            # This would check individual approval deadlines
    
    async def _escalate_workflow(self, workflow_id: str, reason: str):
        """Escalate an entire workflow"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return
        
        logger.warning(f"Escalating workflow {workflow_id}: {reason}")
        
        # Get escalation path from template
        template = await self._get_template(workflow['template_id'])
        step_def = template['definition']['steps'][workflow['current_step'] - 1]
        
        if 'escalate_to' in step_def:
            await self._handle_escalation(workflow_id, "system", reason)
    
    # ========================================
    # Workflow Completion
    # ========================================
    
    async def _complete_workflow(self, workflow_id: str):
        """Mark workflow as completed"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return
        
        workflow['status'] = WorkflowStatus.COMPLETED
        workflow['completed_at'] = datetime.utcnow()
        
        # Calculate metrics
        duration = (workflow['completed_at'] - workflow['started_at']).total_seconds()
        
        # Emit completion event
        await event_manager.emit({
            "type": "workflow_completed",
            "workflow_id": workflow_id,
            "entity_type": workflow['entity_type'],
            "entity_id": workflow['entity_id'],
            "duration_seconds": duration
        })
        
        # Trigger post-approval actions
        await self._trigger_post_approval_actions(workflow)
    
    async def _trigger_post_approval_actions(self, workflow: Dict):
        """Trigger actions after workflow approval"""
        entity_type = workflow['entity_type']
        entity_id = workflow['entity_id']
        
        # Based on entity type, trigger appropriate action
        if entity_type == 'provisioning':
            # Trigger resource provisioning
            await event_manager.emit({
                "type": "provisioning_approved",
                "entity_id": entity_id
            })
        elif entity_type == 'task':
            # Start task execution
            await event_manager.emit({
                "type": "task_approved",
                "entity_id": entity_id
            })
    
    # ========================================
    # Utility Methods
    # ========================================
    
    async def _get_template(self, template_id: str) -> Optional[Dict]:
        """Get workflow template"""
        # In production, this would query the database
        # For now, return mock template
        return {
            "id": template_id,
            "name": "Standard Approval",
            "definition": {
                "steps": [
                    {
                        "level": 1,
                        "approvers": ["team_lead"],
                        "timeout_hours": 24,
                        "escalate_to": "manager"
                    },
                    {
                        "level": 2,
                        "approvers": ["manager"],
                        "timeout_hours": 12
                    }
                ],
                "conditions": []
            }
        }
    
    async def _load_active_workflows(self):
        """Load active workflows from database"""
        # In production, this would query the database
        self.active_workflows = {}
    
    def get_pending_approvals(self, approver_id: str) -> List[Dict]:
        """Get pending approvals for a specific approver"""
        pending = []
        
        for workflow in self.active_workflows.values():
            if workflow['status'] != WorkflowStatus.ACTIVE:
                continue
            
            # Check if approver has pending approval
            # This is simplified - in production, check database
            template = {
                "definition": {
                    "steps": [{"approvers": ["team_lead", "manager"]}]
                }
            }
            
            current_step = workflow.get('current_step', 1)
            if current_step <= len(template['definition']['steps']):
                step = template['definition']['steps'][current_step - 1]
                if approver_id in step.get('approvers', []):
                    # Check if already approved
                    already_approved = any(
                        h for h in workflow['history']
                        if h.get('type') == 'approval_decision' and
                        h.get('approver') == approver_id and
                        h.get('step') == current_step
                    )
                    
                    if not already_approved:
                        pending.append({
                            "workflow_id": workflow['id'],
                            "entity_type": workflow['entity_type'],
                            "entity_id": workflow['entity_id'],
                            "step": current_step,
                            "deadline": workflow.get('deadline')
                        })
        
        return pending
    
    def get_workflow_stats(self) -> Dict[str, Any]:
        """Get workflow statistics"""
        active = len([w for w in self.active_workflows.values() if w['status'] == WorkflowStatus.ACTIVE])
        completed = len([w for w in self.active_workflows.values() if w['status'] == WorkflowStatus.COMPLETED])
        cancelled = len([w for w in self.active_workflows.values() if w['status'] == WorkflowStatus.CANCELLED])
        
        return {
            "total_workflows": len(self.active_workflows),
            "active": active,
            "completed": completed,
            "cancelled": cancelled,
            "avg_completion_time": self._calculate_avg_completion_time()
        }
    
    def _calculate_avg_completion_time(self) -> float:
        """Calculate average workflow completion time"""
        completed_workflows = [
            w for w in self.active_workflows.values()
            if w['status'] == WorkflowStatus.COMPLETED and 'completed_at' in w
        ]
        
        if not completed_workflows:
            return 0
        
        total_time = sum(
            (w['completed_at'] - w['started_at']).total_seconds()
            for w in completed_workflows
        )
        
        return total_time / len(completed_workflows)


# Singleton instance
workflow_engine = WorkflowEngine()