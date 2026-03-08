"""
RBAC (Role-Based Access Control) Manager for V3
Manages roles, permissions, and access control for Mission Control
"""

import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from enum import Enum
import jwt
import hashlib

from models.v3_models import Role, Permission, User, Team
from services.event_manager import event_manager
from core.config import settings

logger = logging.getLogger(__name__)


class PermissionScope(Enum):
    """Permission scopes"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"


class ResourceType(Enum):
    """Resource types for permissions"""
    AGENT = "agent"
    TASK = "task"
    JOB = "job"
    CLUSTER = "cluster"
    WORKFLOW = "workflow"
    RESOURCE = "resource"
    APPROVAL = "approval"
    METRIC = "metric"
    AUDIT = "audit"
    USER = "user"
    ROLE = "role"
    ALL = "*"


class RBACManager:
    """
    Manages role-based access control for Mission Control
    """
    
    def __init__(self):
        self.roles_cache: Dict[str, Dict] = {}
        self.permissions_cache: Dict[str, Set[str]] = {}
        self.user_roles_cache: Dict[str, Set[str]] = {}
        self.team_roles_cache: Dict[str, Set[str]] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize RBAC manager with default roles"""
        if self._initialized:
            return
        
        logger.info("Initializing RBAC Manager")
        
        # Create default roles
        await self._create_default_roles()
        
        # Load roles and permissions from database
        await self._load_roles()
        
        self._initialized = True
    
    # ========================================
    # Role Management
    # ========================================
    
    async def create_role(
        self,
        name: str,
        description: str,
        permissions: List[str],
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a new role"""
        logger.info(f"Creating role: {name}")
        
        # Validate permissions
        for permission in permissions:
            if not self._validate_permission(permission):
                raise ValueError(f"Invalid permission: {permission}")
        
        # Create role
        role = {
            "id": self._generate_role_id(name),
            "name": name,
            "description": description,
            "permissions": permissions,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "is_system": False
        }
        
        # Cache role
        self.roles_cache[role['id']] = role
        self.permissions_cache[role['id']] = set(permissions)
        
        # Emit event
        await event_manager.emit({
            "type": "role_created",
            "role_id": role['id'],
            "name": name
        })
        
        return role
    
    async def update_role(
        self,
        role_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing role"""
        role = self.roles_cache.get(role_id)
        
        if not role:
            raise ValueError(f"Role {role_id} not found")
        
        if role.get('is_system'):
            raise ValueError("Cannot modify system role")
        
        # Update role
        if 'permissions' in updates:
            for permission in updates['permissions']:
                if not self._validate_permission(permission):
                    raise ValueError(f"Invalid permission: {permission}")
            
            self.permissions_cache[role_id] = set(updates['permissions'])
            role['permissions'] = updates['permissions']
        
        if 'description' in updates:
            role['description'] = updates['description']
        
        if 'metadata' in updates:
            role['metadata'].update(updates['metadata'])
        
        role['updated_at'] = datetime.utcnow()
        
        # Emit event
        await event_manager.emit({
            "type": "role_updated",
            "role_id": role_id,
            "updates": updates
        })
        
        return role
    
    async def delete_role(self, role_id: str):
        """Delete a role"""
        role = self.roles_cache.get(role_id)
        
        if not role:
            raise ValueError(f"Role {role_id} not found")
        
        if role.get('is_system'):
            raise ValueError("Cannot delete system role")
        
        # Remove role assignments
        for user_id, roles in list(self.user_roles_cache.items()):
            if role_id in roles:
                roles.remove(role_id)
        
        # Remove from cache
        del self.roles_cache[role_id]
        del self.permissions_cache[role_id]
        
        # Emit event
        await event_manager.emit({
            "type": "role_deleted",
            "role_id": role_id
        })
    
    async def get_role(self, role_id: str) -> Optional[Dict[str, Any]]:
        """Get role details"""
        return self.roles_cache.get(role_id)
    
    async def list_roles(self) -> List[Dict[str, Any]]:
        """List all roles"""
        return list(self.roles_cache.values())
    
    # ========================================
    # User-Role Assignment
    # ========================================
    
    async def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        granted_by: str = None
    ):
        """Assign a role to a user"""
        if role_id not in self.roles_cache:
            raise ValueError(f"Role {role_id} not found")
        
        if user_id not in self.user_roles_cache:
            self.user_roles_cache[user_id] = set()
        
        self.user_roles_cache[user_id].add(role_id)
        
        logger.info(f"Assigned role {role_id} to user {user_id}")
        
        # Emit event
        await event_manager.emit({
            "type": "role_assigned",
            "user_id": user_id,
            "role_id": role_id,
            "granted_by": granted_by
        })
    
    async def revoke_role_from_user(
        self,
        user_id: str,
        role_id: str,
        revoked_by: str = None
    ):
        """Revoke a role from a user"""
        if user_id in self.user_roles_cache:
            self.user_roles_cache[user_id].discard(role_id)
        
        logger.info(f"Revoked role {role_id} from user {user_id}")
        
        # Emit event
        await event_manager.emit({
            "type": "role_revoked",
            "user_id": user_id,
            "role_id": role_id,
            "revoked_by": revoked_by
        })
    
    async def get_user_roles(self, user_id: str) -> List[str]:
        """Get all roles assigned to a user"""
        return list(self.user_roles_cache.get(user_id, set()))
    
    async def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get all permissions for a user"""
        permissions = set()
        
        # Get permissions from user roles
        for role_id in self.user_roles_cache.get(user_id, set()):
            permissions.update(self.permissions_cache.get(role_id, set()))
        
        # Get permissions from team roles
        user_teams = await self._get_user_teams(user_id)
        for team_id in user_teams:
            for role_id in self.team_roles_cache.get(team_id, set()):
                permissions.update(self.permissions_cache.get(role_id, set()))
        
        return permissions
    
    # ========================================
    # Team-Role Assignment
    # ========================================
    
    async def assign_role_to_team(
        self,
        team_id: str,
        role_id: str,
        granted_by: str = None
    ):
        """Assign a role to a team"""
        if role_id not in self.roles_cache:
            raise ValueError(f"Role {role_id} not found")
        
        if team_id not in self.team_roles_cache:
            self.team_roles_cache[team_id] = set()
        
        self.team_roles_cache[team_id].add(role_id)
        
        logger.info(f"Assigned role {role_id} to team {team_id}")
        
        # Emit event
        await event_manager.emit({
            "type": "role_assigned_to_team",
            "team_id": team_id,
            "role_id": role_id,
            "granted_by": granted_by
        })
    
    async def get_team_roles(self, team_id: str) -> List[str]:
        """Get all roles assigned to a team"""
        return list(self.team_roles_cache.get(team_id, set()))
    
    # ========================================
    # Permission Checking
    # ========================================
    
    async def check_permission(
        self,
        user_id: str,
        resource_type: ResourceType,
        scope: PermissionScope,
        resource_id: Optional[str] = None
    ) -> bool:
        """Check if user has permission for resource"""
        # Get user permissions
        permissions = await self.get_user_permissions(user_id)
        
        # Check for admin permission
        if f"{ResourceType.ALL.value}:{PermissionScope.ADMIN.value}" in permissions:
            return True
        
        # Check specific permission
        permission = f"{resource_type.value}:{scope.value}"
        if permission in permissions:
            return True
        
        # Check wildcard permissions
        if f"{resource_type.value}:{PermissionScope.ADMIN.value}" in permissions:
            return True
        
        if f"{ResourceType.ALL.value}:{scope.value}" in permissions:
            return True
        
        # Check resource-specific permission if provided
        if resource_id:
            specific_permission = f"{resource_type.value}:{resource_id}:{scope.value}"
            if specific_permission in permissions:
                return True
        
        return False
    
    async def enforce_permission(
        self,
        user_id: str,
        resource_type: ResourceType,
        scope: PermissionScope,
        resource_id: Optional[str] = None
    ):
        """Enforce permission check, raise exception if denied"""
        if not await self.check_permission(user_id, resource_type, scope, resource_id):
            raise PermissionError(
                f"User {user_id} lacks permission {resource_type.value}:{scope.value}"
            )
    
    # ========================================
    # Token Management
    # ========================================
    
    async def create_access_token(
        self,
        user_id: str,
        expires_in: int = 3600
    ) -> str:
        """Create JWT access token for user"""
        # Get user permissions
        permissions = await self.get_user_permissions(user_id)
        roles = await self.get_user_roles(user_id)
        
        # Create token payload
        payload = {
            "user_id": user_id,
            "roles": roles,
            "permissions": list(permissions),
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow()
        }
        
        # Sign token
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        
        return token
    
    async def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode access token"""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
    
    # ========================================
    # Audit and Compliance
    # ========================================
    
    async def audit_permission_check(
        self,
        user_id: str,
        resource_type: ResourceType,
        scope: PermissionScope,
        resource_id: Optional[str],
        granted: bool
    ):
        """Log permission check for audit"""
        await event_manager.emit({
            "type": "permission_check",
            "user_id": user_id,
            "resource_type": resource_type.value,
            "scope": scope.value,
            "resource_id": resource_id,
            "granted": granted,
            "timestamp": datetime.utcnow()
        })
    
    async def get_permission_audit_log(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get permission audit log"""
        # Would query from database
        return []
    
    # ========================================
    # Default Roles and Permissions
    # ========================================
    
    async def _create_default_roles(self):
        """Create default system roles"""
        default_roles = [
            {
                "id": "admin",
                "name": "Administrator",
                "description": "Full system access",
                "permissions": [f"{ResourceType.ALL.value}:{PermissionScope.ADMIN.value}"],
                "is_system": True
            },
            {
                "id": "operator",
                "name": "Operator",
                "description": "Can manage agents and tasks",
                "permissions": [
                    f"{ResourceType.AGENT.value}:{PermissionScope.WRITE.value}",
                    f"{ResourceType.AGENT.value}:{PermissionScope.EXECUTE.value}",
                    f"{ResourceType.TASK.value}:{PermissionScope.WRITE.value}",
                    f"{ResourceType.TASK.value}:{PermissionScope.EXECUTE.value}",
                    f"{ResourceType.JOB.value}:{PermissionScope.READ.value}",
                    f"{ResourceType.CLUSTER.value}:{PermissionScope.READ.value}"
                ],
                "is_system": True
            },
            {
                "id": "developer",
                "name": "Developer",
                "description": "Can create and manage workflows",
                "permissions": [
                    f"{ResourceType.WORKFLOW.value}:{PermissionScope.WRITE.value}",
                    f"{ResourceType.WORKFLOW.value}:{PermissionScope.EXECUTE.value}",
                    f"{ResourceType.AGENT.value}:{PermissionScope.READ.value}",
                    f"{ResourceType.TASK.value}:{PermissionScope.READ.value}",
                    f"{ResourceType.JOB.value}:{PermissionScope.READ.value}",
                    f"{ResourceType.METRIC.value}:{PermissionScope.READ.value}"
                ],
                "is_system": True
            },
            {
                "id": "viewer",
                "name": "Viewer",
                "description": "Read-only access",
                "permissions": [
                    f"{ResourceType.AGENT.value}:{PermissionScope.READ.value}",
                    f"{ResourceType.TASK.value}:{PermissionScope.READ.value}",
                    f"{ResourceType.JOB.value}:{PermissionScope.READ.value}",
                    f"{ResourceType.CLUSTER.value}:{PermissionScope.READ.value}",
                    f"{ResourceType.WORKFLOW.value}:{PermissionScope.READ.value}",
                    f"{ResourceType.METRIC.value}:{PermissionScope.READ.value}"
                ],
                "is_system": True
            },
            {
                "id": "approver",
                "name": "Approver",
                "description": "Can approve or reject requests",
                "permissions": [
                    f"{ResourceType.APPROVAL.value}:{PermissionScope.WRITE.value}",
                    f"{ResourceType.APPROVAL.value}:{PermissionScope.EXECUTE.value}",
                    f"{ResourceType.WORKFLOW.value}:{PermissionScope.READ.value}",
                    f"{ResourceType.TASK.value}:{PermissionScope.READ.value}"
                ],
                "is_system": True
            },
            {
                "id": "auditor",
                "name": "Auditor",
                "description": "Can view audit logs and compliance data",
                "permissions": [
                    f"{ResourceType.AUDIT.value}:{PermissionScope.READ.value}",
                    f"{ResourceType.ALL.value}:{PermissionScope.READ.value}"
                ],
                "is_system": True
            }
        ]
        
        for role in default_roles:
            self.roles_cache[role['id']] = role
            self.permissions_cache[role['id']] = set(role['permissions'])
    
    # ========================================
    # Helper Methods
    # ========================================
    
    def _validate_permission(self, permission: str) -> bool:
        """Validate permission format"""
        parts = permission.split(':')
        
        if len(parts) < 2 or len(parts) > 3:
            return False
        
        # Validate resource type
        resource_type = parts[0]
        valid_types = [rt.value for rt in ResourceType]
        if resource_type not in valid_types:
            return False
        
        # Validate scope
        scope = parts[-1]
        valid_scopes = [ps.value for ps in PermissionScope]
        if scope not in valid_scopes:
            return False
        
        return True
    
    def _generate_role_id(self, name: str) -> str:
        """Generate role ID from name"""
        return name.lower().replace(' ', '_').replace('-', '_')
    
    async def _load_roles(self):
        """Load roles from database"""
        # In production, would load from database
        pass
    
    async def _get_user_teams(self, user_id: str) -> List[str]:
        """Get teams that user belongs to"""
        # In production, would query from database
        return []


# Singleton instance
rbac_manager = RBACManager()