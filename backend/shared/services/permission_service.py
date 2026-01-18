"""
Permission Service for Resource-Based Access Control

This module provides resource-level permission checking for agents and workflows.
It integrates with the role-based access control system to enforce fine-grained permissions.
"""

import logging
from typing import List, Optional, Set
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.user import User
from ..models.rbac import Role, Permission, UserRole
from ..models.resource_roles import AgentRole, WorkflowRole
from ..models.agent import Agent
from ..models.chain import Chain

logger = logging.getLogger(__name__)


class PermissionService:
    """Service for checking and managing resource-level permissions."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # Permission Check Logic
    
    async def has_permission(
        self,
        user: User,
        resource_type: str,
        action: str,
        resource_id: Optional[UUID] = None
    ) -> bool:
        """
        Check if a user has permission to perform an action on a resource.
        
        Args:
            user: The user attempting the action
            resource_type: Type of resource ('agent', 'workflow', 'user', etc.)
            action: Action being attempted ('view', 'execute', 'modify', 'delete')
            resource_id: Optional specific resource ID for resource-level checks
            
        Returns:
            bool: True if permission is granted, False otherwise
        """
        # Super admins have all permissions
        if user.is_superuser or user.is_system_admin:
            return True
        
        # Get user's roles
        user_roles = await self._get_user_roles_with_permissions(user.id)
        
        if not user_roles:
            return False
        
        # Map action to minimum required permission level
        action_permission_map = {
            'view': 1,      # View User or higher
            'execute': 2,   # Standard User or higher
            'create': 3,    # Service User or higher
            'modify': 3,    # Service User or higher
            'delete': 3,    # Service User or higher
            'manage': 3,    # Service User or higher
            'assign_role': 4,  # Super Admin only
        }
        
        required_level = action_permission_map.get(action, 3)
        
        # If no specific resource, check global permissions
        if not resource_id:
            return await self._check_global_permission(
                user_roles, resource_type, action, required_level
            )
        
        # Check resource-specific permissions
        return await self._check_resource_permission(
            user_roles, resource_type, action, resource_id, required_level
        )
    
    async def _get_user_roles_with_permissions(self, user_id: UUID) -> List[tuple]:
        """Get all roles with their permissions for a user."""
        query = select(UserRole).options(
            selectinload(UserRole.role).selectinload(Role.permissions)
        ).where(UserRole.user_id == user_id)
        
        result = await self.session.execute(query)
        user_roles = result.scalars().all()
        
        return [(ur.role, ur.role.permission_level or 0) for ur in user_roles if ur.role]
    
    async def _check_global_permission(
        self,
        user_roles: List[tuple],
        resource_type: str,
        action: str,
        required_level: int
    ) -> bool:
        """Check if user has global permission for resource type."""
        for role, permission_level in user_roles:
            # Check if role's permission level is sufficient
            if permission_level >= required_level:
                # Check if role has the specific permission
                permission_name = f"{resource_type}.{action}"
                for permission in role.permissions:
                    if permission.name == permission_name:
                        return True
                    # Also check resource.action format
                    if permission.resource == resource_type and permission.action == action:
                        return True
        
        return False
    
    async def _check_resource_permission(
        self,
        user_roles: List[tuple],
        resource_type: str,
        action: str,
        resource_id: UUID,
        required_level: int
    ) -> bool:
        """Check if user has permission for specific resource."""
        # First check global permissions
        if await self._check_global_permission(user_roles, resource_type, action, required_level):
            # User has global permission, now check resource assignment
            role_ids = [role.id for role, _ in user_roles]
            
            if resource_type == 'agent':
                return await self._has_agent_access(role_ids, resource_id, action)
            elif resource_type == 'workflow':
                return await self._has_workflow_access(role_ids, resource_id, action)
        
        return False
    
    async def _has_agent_access(self, role_ids: List[UUID], agent_id: UUID, action: str) -> bool:
        """Check if any of the user's roles has access to the agent."""
        query = select(AgentRole).where(
            and_(
                AgentRole.agent_id == agent_id,
                AgentRole.role_id.in_(role_ids)
            )
        )
        
        result = await self.session.execute(query)
        agent_roles = result.scalars().all()
        
        if not agent_roles:
            # No specific assignment, deny access
            return False
        
        # Check if access type matches action
        for agent_role in agent_roles:
            if self._is_access_type_sufficient(agent_role.access_type, action):
                return True
        
        return False
    
    async def _has_workflow_access(self, role_ids: List[UUID], workflow_id: UUID, action: str) -> bool:
        """Check if any of the user's roles has access to the workflow."""
        query = select(WorkflowRole).where(
            and_(
                WorkflowRole.workflow_id == workflow_id,
                WorkflowRole.role_id.in_(role_ids)
            )
        )
        
        result = await self.session.execute(query)
        workflow_roles = result.scalars().all()
        
        if not workflow_roles:
            # No specific assignment, deny access
            return False
        
        # Check if access type matches action
        for workflow_role in workflow_roles:
            if self._is_access_type_sufficient(workflow_role.access_type, action):
                return True
        
        return False
    
    def _is_access_type_sufficient(self, granted_access: str, requested_action: str) -> bool:
        """Check if granted access type is sufficient for requested action."""
        access_hierarchy = {
            'view': ['view'],
            'execute': ['view', 'execute'],
            'modify': ['view', 'execute', 'modify']
        }
        
        # Map actions to access types
        action_to_access = {
            'view': 'view',
            'execute': 'execute',
            'create': 'modify',  # Create requires modify access
            'modify': 'modify',
            'delete': 'modify',  # Delete requires modify access
        }
        
        required_access = action_to_access.get(requested_action, 'modify')
        allowed_actions = access_hierarchy.get(granted_access, [])
        
        return required_access in allowed_actions
    
    # Resource Role Assignment
    
    async def assign_resource_role(
        self,
        resource_type: str,
        resource_id: UUID,
        role_id: UUID,
        access_type: str,
        created_by: Optional[UUID] = None
    ) -> object:
        """Assign a role to a resource with specific access type."""
        if resource_type == 'agent':
            # Check if assignment already exists
            query = select(AgentRole).where(
                and_(
                    AgentRole.agent_id == resource_id,
                    AgentRole.role_id == role_id,
                    AgentRole.access_type == access_type
                )
            )
            result = await self.session.execute(query)
            existing = result.scalar_one_or_none()
            
            if existing:
                return existing
            
            assignment = AgentRole(
                agent_id=resource_id,
                role_id=role_id,
                access_type=access_type,
                created_by=created_by
            )
            self.session.add(assignment)
            await self.session.commit()
            await self.session.refresh(assignment)
            
            logger.info(f"Assigned role {role_id} to agent {resource_id} with {access_type} access")
            return assignment
            
        elif resource_type == 'workflow':
            # Check if assignment already exists
            query = select(WorkflowRole).where(
                and_(
                    WorkflowRole.workflow_id == resource_id,
                    WorkflowRole.role_id == role_id,
                    WorkflowRole.access_type == access_type
                )
            )
            result = await self.session.execute(query)
            existing = result.scalar_one_or_none()
            
            if existing:
                return existing
            
            assignment = WorkflowRole(
                workflow_id=resource_id,
                role_id=role_id,
                access_type=access_type,
                created_by=created_by
            )
            self.session.add(assignment)
            await self.session.commit()
            await self.session.refresh(assignment)
            
            logger.info(f"Assigned role {role_id} to workflow {resource_id} with {access_type} access")
            return assignment
        
        raise ValueError(f"Unsupported resource type: {resource_type}")
    
    async def revoke_resource_role(
        self,
        resource_type: str,
        resource_id: UUID,
        role_id: UUID,
        access_type: Optional[str] = None
    ) -> bool:
        """Remove a role from a resource."""
        if resource_type == 'agent':
            conditions = [
                AgentRole.agent_id == resource_id,
                AgentRole.role_id == role_id
            ]
            if access_type:
                conditions.append(AgentRole.access_type == access_type)
            
            query = select(AgentRole).where(and_(*conditions))
            result = await self.session.execute(query)
            assignments = result.scalars().all()
            
            for assignment in assignments:
                await self.session.delete(assignment)
            
            await self.session.commit()
            logger.info(f"Revoked role {role_id} from agent {resource_id}")
            return len(assignments) > 0
            
        elif resource_type == 'workflow':
            conditions = [
                WorkflowRole.workflow_id == resource_id,
                WorkflowRole.role_id == role_id
            ]
            if access_type:
                conditions.append(WorkflowRole.access_type == access_type)
            
            query = select(WorkflowRole).where(and_(*conditions))
            result = await self.session.execute(query)
            assignments = result.scalars().all()
            
            for assignment in assignments:
                await self.session.delete(assignment)
            
            await self.session.commit()
            logger.info(f"Revoked role {role_id} from workflow {resource_id}")
            return len(assignments) > 0
        
        return False
    
    async def get_resource_roles(
        self,
        resource_type: str,
        resource_id: UUID
    ) -> List[dict]:
        """Get all role assignments for a resource."""
        if resource_type == 'agent':
            query = select(AgentRole).options(
                selectinload(AgentRole.role)
            ).where(AgentRole.agent_id == resource_id)
            
            result = await self.session.execute(query)
            assignments = result.scalars().all()
            
            return [
                {
                    'role_id': a.role_id,
                    'role_name': a.role.name if a.role else None,
                    'access_type': a.access_type
                }
                for a in assignments
            ]
            
        elif resource_type == 'workflow':
            query = select(WorkflowRole).options(
                selectinload(WorkflowRole.role)
            ).where(WorkflowRole.workflow_id == resource_id)
            
            result = await self.session.execute(query)
            assignments = result.scalars().all()
            
            return [
                {
                    'role_id': a.role_id,
                    'role_name': a.role.name if a.role else None,
                    'access_type': a.access_type
                }
                for a in assignments
            ]
        
        return []
    
    async def get_user_accessible_resources(
        self,
        user: User,
        resource_type: str
    ) -> List[UUID]:
        """Get all resource IDs that a user can access."""
        # Super admins can access all resources
        if user.is_superuser or user.is_system_admin:
            if resource_type == 'agent':
                query = select(Agent.id)
                result = await self.session.execute(query)
                return [row[0] for row in result.all()]
            elif resource_type == 'workflow':
                query = select(Chain.id)
                result = await self.session.execute(query)
                return [row[0] for row in result.all()]
        
        # Get user's role IDs
        user_roles = await self._get_user_roles_with_permissions(user.id)
        role_ids = [role.id for role, _ in user_roles]
        
        if not role_ids:
            return []
        
        if resource_type == 'agent':
            query = select(AgentRole.agent_id).where(
                AgentRole.role_id.in_(role_ids)
            ).distinct()
            result = await self.session.execute(query)
            return [row[0] for row in result.all()]
            
        elif resource_type == 'workflow':
            query = select(WorkflowRole.workflow_id).where(
                WorkflowRole.role_id.in_(role_ids)
            ).distinct()
            result = await self.session.execute(query)
            return [row[0] for row in result.all()]
        
        return []

