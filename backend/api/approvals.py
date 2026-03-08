"""
Approval API endpoints.
Human-in-the-loop decision tracking.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.models import Approval, ApprovalStatus, ProvisioningRequest
from models.base import get_async_session
from services.event_manager import event_manager
from core.config import settings

router = APIRouter()


@router.get("/", response_model=List[dict])
async def list_approvals(
    status: Optional[ApprovalStatus] = None,
    entity_type: Optional[str] = None,
    requester: Optional[str] = None,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """List approvals with optional filtering."""
    query = select(Approval)
    
    if status:
        query = query.filter(Approval.status == status)
    if entity_type:
        query = query.filter(Approval.entity_type == entity_type)
    if requester:
        query = query.filter(Approval.requester == requester)
    
    async with session:
        result = await session.execute(query)
        approvals = result.scalars().all()
        
        return [
            {
                "id": approval.id,
                "entity_type": approval.entity_type,
                "entity_id": approval.entity_id,
                "action": approval.action,
                "status": approval.status.value,
                "requester": approval.requester,
                "approver": approval.approver,
                "reason": approval.reason,
                "requested_at": approval.requested_at.isoformat() if approval.requested_at else None,
                "expires_at": approval.expires_at.isoformat() if approval.expires_at else None
            }
            for approval in approvals
        ]


@router.get("/pending")
async def get_pending_approvals(
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Get all pending approvals that haven't expired."""
    now = datetime.utcnow()
    
    query = select(Approval).filter(
        Approval.status == ApprovalStatus.PENDING,
        (Approval.expires_at > now) | (Approval.expires_at == None)
    )
    
    async with session:
        result = await session.execute(query)
        approvals = result.scalars().all()
        
        return [
            {
                "id": approval.id,
                "entity_type": approval.entity_type,
                "entity_id": approval.entity_id,
                "action": approval.action,
                "requester": approval.requester,
                "metadata": approval.metadata,
                "requested_at": approval.requested_at.isoformat(),
                "expires_at": approval.expires_at.isoformat() if approval.expires_at else None
            }
            for approval in approvals
        ]


@router.get("/{approval_id}")
async def get_approval(
    approval_id: str,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Get approval details."""
    async with session:
        result = await session.execute(
            select(Approval).filter(Approval.id == approval_id)
        )
        approval = result.scalar_one_or_none()
        
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        
        return {
            "id": approval.id,
            "entity_type": approval.entity_type,
            "entity_id": approval.entity_id,
            "action": approval.action,
            "status": approval.status.value,
            "requester": approval.requester,
            "approver": approval.approver,
            "reason": approval.reason,
            "metadata": approval.metadata,
            "requested_at": approval.requested_at.isoformat() if approval.requested_at else None,
            "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
            "expires_at": approval.expires_at.isoformat() if approval.expires_at else None
        }


@router.post("/")
async def create_approval_request(
    approval_spec: dict,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Create a new approval request."""
    # Set expiration (default 24 hours)
    expires_at = datetime.utcnow() + timedelta(
        hours=approval_spec.get("expires_in_hours", 24)
    )
    
    approval = Approval(
        id=approval_spec.get("id", f"approval_{datetime.utcnow().timestamp()}"),
        entity_type=approval_spec.get("entity_type"),
        entity_id=approval_spec.get("entity_id"),
        action=approval_spec.get("action"),
        status=ApprovalStatus.PENDING,
        requester=approval_spec.get("requester"),
        metadata=approval_spec.get("metadata", {}),
        expires_at=expires_at
    )
    
    async with session:
        session.add(approval)
        await session.commit()
    
    # Emit event
    await event_manager.emit({
        "type": "approval_requested",
        "approval_id": approval.id,
        "entity_type": approval.entity_type,
        "action": approval.action
    })
    
    return {
        "id": approval.id,
        "status": approval.status.value,
        "expires_at": expires_at.isoformat()
    }


@router.post("/{approval_id}/approve")
async def approve_request(
    approval_id: str,
    decision_data: dict,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Approve a pending request."""
    async with session:
        result = await session.execute(
            select(Approval).filter(Approval.id == approval_id)
        )
        approval = result.scalar_one_or_none()
        
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        
        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve request in status: {approval.status.value}"
            )
        
        # Check expiration
        if approval.expires_at and approval.expires_at < datetime.utcnow():
            approval.status = ApprovalStatus.EXPIRED
            await session.commit()
            raise HTTPException(status_code=400, detail="Approval request has expired")
        
        # Update approval
        approval.status = ApprovalStatus.APPROVED
        approval.approver = decision_data.get("approver")
        approval.decided_at = datetime.utcnow()
        approval.reason = decision_data.get("reason")
        
        await session.commit()
        
        # Emit event
        await event_manager.emit({
            "type": "approval_granted",
            "approval_id": approval_id,
            "entity_type": approval.entity_type,
            "entity_id": approval.entity_id,
            "action": approval.action
        })
        
        # Trigger approved action (would be handled by event listener)
        # This is where OpenClaw would be notified to execute the approved action
        
        return {
            "id": approval_id,
            "status": approval.status.value,
            "approved_by": approval.approver
        }


@router.post("/{approval_id}/reject")
async def reject_request(
    approval_id: str,
    decision_data: dict,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Reject a pending request."""
    async with session:
        result = await session.execute(
            select(Approval).filter(Approval.id == approval_id)
        )
        approval = result.scalar_one_or_none()
        
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        
        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot reject request in status: {approval.status.value}"
            )
        
        # Update approval
        approval.status = ApprovalStatus.REJECTED
        approval.approver = decision_data.get("approver")
        approval.decided_at = datetime.utcnow()
        approval.reason = decision_data.get("reason")
        
        await session.commit()
        
        # Emit event
        await event_manager.emit({
            "type": "approval_rejected",
            "approval_id": approval_id,
            "entity_type": approval.entity_type,
            "entity_id": approval.entity_id,
            "reason": approval.reason
        })
        
        return {
            "id": approval_id,
            "status": approval.status.value,
            "rejected_by": approval.approver
        }


@router.post("/provisioning")
async def create_provisioning_request(
    provisioning_spec: dict,
    session: AsyncSession = Depends(lambda: get_async_session(settings.DATABASE_URL))
):
    """Create a provisioning request that requires approval."""
    # Create approval
    approval = Approval(
        id=f"approval_prov_{datetime.utcnow().timestamp()}",
        entity_type="provisioning",
        entity_id=provisioning_spec.get("id", f"prov_{datetime.utcnow().timestamp()}"),
        action="provision_resource",
        status=ApprovalStatus.PENDING,
        requester=provisioning_spec.get("requester"),
        metadata=provisioning_spec,
        expires_at=datetime.utcnow() + timedelta(hours=48)
    )
    
    # Create provisioning request
    provisioning = ProvisioningRequest(
        id=provisioning_spec.get("id", f"prov_{datetime.utcnow().timestamp()}"),
        resource_type=provisioning_spec.get("resource_type"),
        resource_spec=provisioning_spec.get("resource_spec"),
        status="pending",
        approval_id=approval.id
    )
    
    async with session:
        session.add(approval)
        session.add(provisioning)
        await session.commit()
    
    # Emit event
    await event_manager.emit({
        "type": "provisioning_requested",
        "provisioning_id": provisioning.id,
        "resource_type": provisioning.resource_type,
        "requires_approval": True
    })
    
    return {
        "provisioning_id": provisioning.id,
        "approval_id": approval.id,
        "status": "pending_approval"
    }