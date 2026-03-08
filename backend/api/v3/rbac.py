"""
V3 RBAC (Role-Based Access Control) API
Manages roles, permissions, and access control for Mission Control
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from datetime import datetime

from services.rbac_manager import (
    rbac_manager,
    PermissionScope,
    ResourceType
)
from services.event_manager import event_manager

router = APIRouter()


# ========================================
# Request/Response Models
# ========================================

class RoleCreateRequest(BaseModel):
    """Role creation request"""
    name: str
    description: str
    permissions: List[str]
    metadata: dict = {}


class RoleUpdateRequest(BaseModel):
    """Role update request"""
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    metadata: Optional[dict] = None


class RoleAssignmentRequest(BaseModel):
    """Role assignment request"""
    user_id: Optional[str] = None
    team_id: Optional[str] = None
    role_id: str
    expires_at: Optional[datetime] = None


class PermissionCheckRequest(BaseModel):
    """Permission check request"""
    user_id: str
    resource_type: str
    scope: str
    resource_id: Optional[str] = None


class TokenRequest(BaseModel):
    """Access token request"""
    user_id: str
    expires_in: int = 3600


# ========================================
# Dependencies
# ========================================

async def get_current_user(authorization: str = Header(None)):
    """Get current user from authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        # Extract token from "Bearer <token>"
        token = authorization.replace("Bearer ", "")
        payload = await rbac_manager.verify_access_token(token)
        return payload['user_id']
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


async def require_admin(current_user: str = Depends(get_current_user)):
    """Require admin permission"""
    has_permission = await rbac_manager.check_permission(
        current_user,
        ResourceType.ALL,
        PermissionScope.ADMIN
    )
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    return current_user


# ========================================
# Role Management Endpoints
# ========================================

@router.post("/roles")
async def create_role(
    request: RoleCreateRequest,
    current_user: str = Depends(require_admin)
):
    """
    Create a new role (admin only)
    """
    try:
        role = await rbac_manager.create_role(
            name=request.name,
            description=request.description,
            permissions=request.permissions,
            metadata=request.metadata
        )
        
        return {
            "role_id": role['id'],
            "name": role['name'],
            "description": role['description'],
            "permissions": role['permissions'],
            "created_at": role['created_at']
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/roles")
async def list_roles(current_user: str = Depends(get_current_user)):
    """
    List all available roles
    """
    roles = await rbac_manager.list_roles()
    
    return [
        {
            "role_id": role.get('id'),
            "name": role.get('name'),
            "description": role.get('description'),
            "permissions_count": len(role.get('permissions', [])),
            "is_system": role.get('is_system', False)
        }
        for role in roles
    ]


@router.get("/roles/{role_id}")
async def get_role(
    role_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get detailed information about a role
    """
    role = await rbac_manager.get_role(role_id)
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    return {
        "role_id": role['id'],
        "name": role['name'],
        "description": role['description'],
        "permissions": role['permissions'],
        "metadata": role.get('metadata', {}),
        "is_system": role.get('is_system', False),
        "created_at": role.get('created_at')
    }


@router.patch("/roles/{role_id}")
async def update_role(
    role_id: str,
    request: RoleUpdateRequest,
    current_user: str = Depends(require_admin)
):
    """
    Update an existing role (admin only)
    """
    try:
        updates = {}
        if request.description is not None:
            updates['description'] = request.description
        if request.permissions is not None:
            updates['permissions'] = request.permissions
        if request.metadata is not None:
            updates['metadata'] = request.metadata
        
        role = await rbac_manager.update_role(role_id, updates)
        
        return {
            "role_id": role['id'],
            "name": role['name'],
            "updated_at": role.get('updated_at')
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str,
    current_user: str = Depends(require_admin)
):
    """
    Delete a role (admin only)
    """
    try:
        await rbac_manager.delete_role(role_id)
        
        return {
            "role_id": role_id,
            "status": "deleted",
            "message": "Role deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========================================
# Role Assignment Endpoints
# ========================================

@router.post("/assignments")
async def assign_role(
    request: RoleAssignmentRequest,
    current_user: str = Depends(require_admin)
):
    """
    Assign a role to a user or team (admin only)
    """
    try:
        if request.user_id:
            await rbac_manager.assign_role_to_user(
                user_id=request.user_id,
                role_id=request.role_id,
                granted_by=current_user
            )
            
            return {
                "user_id": request.user_id,
                "role_id": request.role_id,
                "status": "assigned",
                "granted_by": current_user
            }
            
        elif request.team_id:
            await rbac_manager.assign_role_to_team(
                team_id=request.team_id,
                role_id=request.role_id,
                granted_by=current_user
            )
            
            return {
                "team_id": request.team_id,
                "role_id": request.role_id,
                "status": "assigned",
                "granted_by": current_user
            }
        else:
            raise ValueError("Either user_id or team_id must be provided")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/assignments")
async def revoke_role(
    user_id: Optional[str] = None,
    team_id: Optional[str] = None,
    role_id: str = None,
    current_user: str = Depends(require_admin)
):
    """
    Revoke a role from a user or team (admin only)
    """
    try:
        if user_id and role_id:
            await rbac_manager.revoke_role_from_user(
                user_id=user_id,
                role_id=role_id,
                revoked_by=current_user
            )
            
            return {
                "user_id": user_id,
                "role_id": role_id,
                "status": "revoked",
                "revoked_by": current_user
            }
        else:
            raise ValueError("user_id and role_id required")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/{user_id}/roles")
async def get_user_roles(
    user_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get all roles assigned to a user
    """
    # Check if user is requesting their own roles or is admin
    if user_id != current_user:
        has_permission = await rbac_manager.check_permission(
            current_user,
            ResourceType.USER,
            PermissionScope.READ
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied")
    
    role_ids = await rbac_manager.get_user_roles(user_id)
    
    roles = []
    for role_id in role_ids:
        role = await rbac_manager.get_role(role_id)
        if role:
            roles.append({
                "role_id": role['id'],
                "name": role['name'],
                "description": role['description']
            })
    
    return roles


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get all permissions for a user
    """
    # Check if user is requesting their own permissions or is admin
    if user_id != current_user:
        has_permission = await rbac_manager.check_permission(
            current_user,
            ResourceType.USER,
            PermissionScope.READ
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied")
    
    permissions = await rbac_manager.get_user_permissions(user_id)
    
    return {
        "user_id": user_id,
        "permissions": list(permissions),
        "total_count": len(permissions)
    }


# ========================================
# Permission Checking Endpoints
# ========================================

@router.post("/check")
async def check_permission(
    request: PermissionCheckRequest,
    current_user: str = Depends(get_current_user)
):
    """
    Check if a user has a specific permission
    """
    # Only allow checking own permissions or admin
    if request.user_id != current_user:
        has_permission = await rbac_manager.check_permission(
            current_user,
            ResourceType.USER,
            PermissionScope.READ
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied")
    
    try:
        resource_type = ResourceType[request.resource_type.upper()]
        scope = PermissionScope[request.scope.upper()]
        
        has_permission = await rbac_manager.check_permission(
            user_id=request.user_id,
            resource_type=resource_type,
            scope=scope,
            resource_id=request.resource_id
        )
        
        # Audit the check
        await rbac_manager.audit_permission_check(
            user_id=request.user_id,
            resource_type=resource_type,
            scope=scope,
            resource_id=request.resource_id,
            granted=has_permission
        )
        
        return {
            "user_id": request.user_id,
            "permission": f"{request.resource_type}:{request.scope}",
            "resource_id": request.resource_id,
            "granted": has_permission
        }
        
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid resource type or scope")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========================================
# Token Management Endpoints
# ========================================

@router.post("/tokens")
async def create_access_token(
    request: TokenRequest,
    current_user: str = Depends(require_admin)
):
    """
    Create an access token for a user (admin only)
    """
    try:
        token = await rbac_manager.create_access_token(
            user_id=request.user_id,
            expires_in=request.expires_in
        )
        
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": request.expires_in,
            "user_id": request.user_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tokens/verify")
async def verify_token(authorization: str = Header(None)):
    """
    Verify an access token
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        token = authorization.replace("Bearer ", "")
        payload = await rbac_manager.verify_access_token(token)
        
        return {
            "valid": True,
            "user_id": payload['user_id'],
            "roles": payload.get('roles', []),
            "expires_at": datetime.fromtimestamp(payload['exp'])
        }
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


# ========================================
# Audit Endpoints
# ========================================

@router.get("/audit/permissions")
async def get_permission_audit_log(
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: str = Depends(get_current_user)
):
    """
    Get permission check audit log
    """
    # Check permission
    has_permission = await rbac_manager.check_permission(
        current_user,
        ResourceType.AUDIT,
        PermissionScope.READ
    )
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="Audit permission required")
    
    logs = await rbac_manager.get_permission_audit_log(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return {
        "logs": logs,
        "count": len(logs),
        "filters": {
            "user_id": user_id,
            "start_date": start_date,
            "end_date": end_date
        }
    }


# ========================================
# Initialization
# ========================================

@router.on_event("startup")
async def startup():
    """Initialize RBAC manager on startup"""
    await rbac_manager.initialize()