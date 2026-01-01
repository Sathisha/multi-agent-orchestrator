"""Agent versioning service for managing agent versions and rollback capabilities."""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, or_
from sqlalchemy.orm import selectinload

from ..models.agent import Agent, AgentStatus
from .base import BaseService
from .id_generator import IDGeneratorService


class AgentVersioningService(BaseService):
    """Service for managing agent versions and rollback capabilities."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Agent)
    
    async def create_version(
        self,
        agent_id: str,
        version: str,
        changes: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None
    ) -> Agent:
        """
        Create a new version of an agent.
        
        Args:
            agent_id: The ID of the agent to version
            version: Version string (e.g., "1.1.0")
            changes: Dictionary of changes to apply
            created_by: User who created the version
            
        Returns:
            New agent version
        """
        # Get the current agent
        current_agent = await self.get_by_id(agent_id)
        if not current_agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Create new agent version
        new_agent = Agent(
            id=IDGeneratorService.generate_agent_id(),
            name=current_agent.name,
            description=current_agent.description,
            type=current_agent.type,
            template_id=current_agent.template_id,
            config=current_agent.config.copy() if current_agent.config else {},
            status=AgentStatus.DRAFT,
            version=version,
            parent_agent_id=current_agent.id,
            system_prompt=current_agent.system_prompt,
            llm_config=current_agent.llm_config.copy() if current_agent.llm_config else {},
            available_tools=current_agent.available_tools.copy() if current_agent.available_tools else [],
            capabilities=current_agent.capabilities.copy() if current_agent.capabilities else [],
            tags=current_agent.tags.copy() if current_agent.tags else [],
            agent_metadata=current_agent.agent_metadata.copy() if current_agent.agent_metadata else {},
            created_by=created_by
        )
        
        # Apply changes if provided
        if changes:
            for key, value in changes.items():
                if hasattr(new_agent, key):
                    setattr(new_agent, key, value)
        
        self.session.add(new_agent)
        await self.session.commit()
        await self.session.refresh(new_agent)
        return new_agent
    
    async def get_agent_versions(self, agent_id: str) -> List[Agent]:
        """
        Get all versions of an agent, including the original.
        
        Args:
            agent_id: The ID of any version of the agent
            
        Returns:
            List of all agent versions, ordered by creation date (newest first)
        """
        # First, find the root agent (the one without a parent)
        agent = await self.get_by_id(agent_id)
        if not agent:
            return []
        
        # If this agent has a parent, get the parent (root)
        root_agent_id = agent.parent_agent_id or agent_id
        
        # Get all versions (including root and all children)
        stmt = select(Agent).where(
            or_(
                Agent.id == root_agent_id,
                Agent.parent_agent_id == root_agent_id
            )
        ).order_by(desc(Agent.created_at))
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_version_by_number(self, agent_id: str, version: str) -> Optional[Agent]:
        """
        Get a specific version of an agent by version number.
        
        Args:
            agent_id: The ID of any version of the agent
            version: Version string to find
            
        Returns:
            Agent with the specified version, or None if not found
        """
        versions = await self.get_agent_versions(agent_id)
        for agent_version in versions:
            if agent_version.version == version:
                return agent_version
        return None
    
    async def rollback_to_version(
        self,
        agent_id: str,
        target_version: str,
        updated_by: Optional[str] = None
    ) -> Optional[Agent]:
        """
        Rollback an agent to a specific version.
        
        This creates a new version with the configuration from the target version.
        
        Args:
            agent_id: The ID of the current agent
            target_version: Version to rollback to
            updated_by: User performing the rollback
            
        Returns:
            New agent version with rolled back configuration
        """
        # Get the target version
        target_agent = await self.get_version_by_number(agent_id, target_version)
        if not target_agent:
            raise ValueError(f"Version {target_version} not found for agent {agent_id}")
        
        # Get current agent to determine next version number
        current_agent = await self.get_by_id(agent_id)
        if not current_agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Generate new version number (increment patch version)
        current_version_parts = current_agent.version.split('.')
        if len(current_version_parts) >= 3:
            patch = int(current_version_parts[2]) + 1
            new_version = f"{current_version_parts[0]}.{current_version_parts[1]}.{patch}"
        else:
            new_version = f"{current_agent.version}.1"
        
        # Create new version with target configuration
        rollback_changes = {
            'config': target_agent.config,
            'system_prompt': target_agent.system_prompt,
            'llm_config': target_agent.llm_config,
            'available_tools': target_agent.available_tools,
            'capabilities': target_agent.capabilities,
            'tags': target_agent.tags,
            'metadata': {
                **(target_agent.agent_metadata or {}),
                'rollback_from_version': current_agent.version,
                'rollback_to_version': target_version,
                'rollback_timestamp': datetime.utcnow().isoformat()
            }
        }
        
        return await self.create_version(
            agent_id=agent_id,
            version=new_version,
            changes=rollback_changes,
            created_by=updated_by
        )
    
    async def compare_versions(
        self,
        agent_id: str,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """
        Compare two versions of an agent.
        
        Args:
            agent_id: The ID of any version of the agent
            version1: First version to compare
            version2: Second version to compare
            
        Returns:
            Dictionary containing the differences between versions
        """
        agent1 = await self.get_version_by_number(agent_id, version1)
        agent2 = await self.get_version_by_number(agent_id, version2)
        
        if not agent1:
            raise ValueError(f"Version {version1} not found")
        if not agent2:
            raise ValueError(f"Version {version2} not found")
        
        # Compare key fields
        differences = {}
        
        # Compare configuration
        if agent1.config != agent2.config:
            differences['config'] = {
                'version1': agent1.config,
                'version2': agent2.config
            }
        
        # Compare system prompt
        if agent1.system_prompt != agent2.system_prompt:
            differences['system_prompt'] = {
                'version1': agent1.system_prompt,
                'version2': agent2.system_prompt
            }
        
        # Compare model config
        if agent1.llm_config != agent2.llm_config:
            differences['llm_config'] = {
                'version1': agent1.llm_config,
                'version2': agent2.llm_config
            }
        
        # Compare tools
        if agent1.available_tools != agent2.available_tools:
            differences['available_tools'] = {
                'version1': agent1.available_tools,
                'version2': agent2.available_tools
            }
        
        # Compare capabilities
        if agent1.capabilities != agent2.capabilities:
            differences['capabilities'] = {
                'version1': agent1.capabilities,
                'version2': agent2.capabilities
            }
        
        # Compare tags
        if agent1.tags != agent2.tags:
            differences['tags'] = {
                'version1': agent1.tags,
                'version2': agent2.tags
            }
        
        return {
            'version1': version1,
            'version2': version2,
            'differences': differences,
            'has_changes': len(differences) > 0
        }
    
    async def get_version_history(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get version history with metadata for an agent.
        
        Args:
            agent_id: The ID of any version of the agent
            
        Returns:
            List of version history entries with metadata
        """
        versions = await self.get_agent_versions(agent_id)
        
        history = []
        for version in versions:
            history.append({
                'id': version.id,
                'version': version.version,
                'created_at': version.created_at,
                'created_by': version.created_by,
                'status': version.status,
                'is_current': version.parent_agent_id is None,
                'metadata': version.agent_metadata or {}
            })
        
        return history
    
    async def activate_version(
        self,
        agent_id: str,
        version: str,
        updated_by: Optional[str] = None
    ) -> Optional[Agent]:
        """
        Activate a specific version of an agent.
        
        Args:
            agent_id: The ID of any version of the agent
            version: Version to activate
            updated_by: User performing the activation
            
        Returns:
            Activated agent version
        """
        target_agent = await self.get_version_by_number(agent_id, version)
        if not target_agent:
            raise ValueError(f"Version {version} not found for agent {agent_id}")
        
        # Deactivate all other versions
        versions = await self.get_agent_versions(agent_id)
        for agent_version in versions:
            if agent_version.id != target_agent.id and agent_version.status == AgentStatus.ACTIVE:
                agent_version.status = AgentStatus.INACTIVE
                agent_version.updated_by = updated_by
                agent_version.updated_at = datetime.utcnow()
        
        # Activate target version
        target_agent.status = AgentStatus.ACTIVE
        target_agent.updated_by = updated_by
        target_agent.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(target_agent)
        return target_agent