# Agent Service
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import uuid

from ..models.agent import Agent, AgentDeployment, AgentExecution, AgentMemory, AgentType, AgentStatus
from ..models.tenant import Tenant
from .base import BaseService
from .validation import ValidationService
from .id_generator import IDGeneratorService


class AgentService(BaseService):
    """Service for managing AI agents with multi-tenant support"""
    
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(session, Agent, tenant_id)
        self.validation_service = ValidationService()

    async def create_agent(
        self,
        name: str,
        description: Optional[str] = None,
        agent_type: AgentType = AgentType.CONVERSATIONAL,
        config: Dict[str, Any] = None,
        system_prompt: Optional[str] = None,
        llm_config: Optional[Dict[str, Any]] = None,
        available_tools: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None
    ) -> Agent:
        """Create a new agent"""
        # Validate agent configuration
        if config is None:
            config = {
                "temperature": 0.7,
                "max_tokens": 1000,
                "model": "gpt-3.5-turbo"
            }

        # Validate required fields
        if not name or not name.strip():
            raise ValueError("Agent name is required")

        # Check if agent name already exists in tenant
        existing = await self.get_by_name(name)
        if existing:
            raise ValueError(f"Agent with name '{name}' already exists in this tenant")

        agent = Agent(
            id=IDGeneratorService.generate_agent_id(),
            tenant_id=self.tenant_id,
            name=name.strip(),
            description=description,
            type=agent_type,
            status=AgentStatus.DRAFT,
            version="1.0",
            config=config,
            system_prompt=system_prompt,
            model_config=model_config or {},
            available_tools=available_tools or [],
            capabilities=capabilities or [],
            tags=tags or [],
            agent_metadata={},
            created_by=created_by
        )

        self.session.add(agent)
        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def get_by_name(self, name: str) -> Optional[Agent]:
        """Get agent by name within tenant"""
        stmt = select(Agent).where(
            and_(
                Agent.tenant_id == self.tenant_id,
                Agent.name == name
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_agents(
        self,
        agent_type: Optional[AgentType] = None,
        status: Optional[AgentStatus] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Agent]:
        """List agents with filtering"""
        stmt = select(Agent).where(Agent.tenant_id == self.tenant_id)
        
        if agent_type:
            stmt = stmt.where(Agent.type == agent_type)
        if status:
            stmt = stmt.where(Agent.status == status)
        if tags:
            # Filter agents that have any of the specified tags
            for tag in tags:
                stmt = stmt.where(Agent.tags.contains([tag]))

        stmt = stmt.order_by(Agent.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_agent(
        self,
        agent_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        llm_config: Optional[Dict[str, Any]] = None,
        available_tools: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        updated_by: Optional[str] = None
    ) -> Optional[Agent]:
        """Update agent configuration"""
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None

        # Check if new name conflicts with existing agents
        if name and name != agent.name:
            existing = await self.get_by_name(name)
            if existing and existing.id != agent_id:
                raise ValueError(f"Agent with name '{name}' already exists in this tenant")
            agent.name = name.strip()

        if description is not None:
            agent.description = description
        if config is not None:
            agent.config = config
        if system_prompt is not None:
            agent.system_prompt = system_prompt
        if model_config is not None:
            agent.model_config = model_config
        if available_tools is not None:
            agent.available_tools = available_tools
        if capabilities is not None:
            agent.capabilities = capabilities
        if tags is not None:
            agent.tags = tags

        agent.updated_by = updated_by
        agent.updated_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def activate_agent(self, agent_id: str, updated_by: Optional[str] = None) -> Optional[Agent]:
        """Activate an agent"""
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None

        agent.status = AgentStatus.ACTIVE
        agent.updated_by = updated_by
        agent.updated_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def deactivate_agent(self, agent_id: str, updated_by: Optional[str] = None) -> Optional[Agent]:
        """Deactivate an agent"""
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None

        agent.status = AgentStatus.INACTIVE
        agent.updated_by = updated_by
        agent.updated_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def get_agent_with_deployments(self, agent_id: str) -> Optional[Agent]:
        """Get agent with all deployments"""
        stmt = select(Agent).options(
            selectinload(Agent.deployments)
        ).where(
            and_(
                Agent.id == agent_id,
                Agent.tenant_id == self.tenant_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_agent_statistics(self, agent_id: str) -> Dict[str, Any]:
        """Get agent usage statistics"""
        agent = await self.get_by_id(agent_id)
        if not agent:
            return {}

        # Get execution statistics
        exec_stats = await self.session.execute(
            select(
                func.count(AgentExecution.id).label('total_executions'),
                func.count(AgentExecution.id).filter(AgentExecution.status == 'completed').label('successful_executions'),
                func.count(AgentExecution.id).filter(AgentExecution.status == 'failed').label('failed_executions'),
                func.avg(AgentExecution.execution_time_ms).label('avg_execution_time'),
                func.sum(AgentExecution.tokens_used).label('total_tokens'),
                func.sum(AgentExecution.cost).label('total_cost')
            ).where(
                and_(
                    AgentExecution.agent_id == agent_id,
                    AgentExecution.tenant_id == self.tenant_id
                )
            )
        )
        stats = exec_stats.first()

        # Get memory statistics
        memory_stats = await self.session.execute(
            select(
                func.count(AgentMemory.id).label('total_memories'),
                func.sum(func.length(AgentMemory.content)).label('total_memory_size')
            ).where(
                and_(
                    AgentMemory.agent_id == agent_id,
                    AgentMemory.tenant_id == self.tenant_id
                )
            )
        )
        memory_data = memory_stats.first()

        return {
            'agent_id': agent_id,
            'total_executions': stats.total_executions or 0,
            'successful_executions': stats.successful_executions or 0,
            'failed_executions': stats.failed_executions or 0,
            'success_rate': (stats.successful_executions or 0) / max(stats.total_executions or 1, 1),
            'avg_execution_time_ms': float(stats.avg_execution_time or 0),
            'total_tokens_used': stats.total_tokens or 0,
            'total_cost': float(stats.total_cost or 0),
            'total_memories': memory_data.total_memories or 0,
            'total_memory_size_bytes': memory_data.total_memory_size or 0
        }


class AgentDeploymentService(BaseService):
    """Service for managing agent deployments"""
    
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(session, AgentDeployment, tenant_id)

    async def create_deployment(
        self,
        agent_id: str,
        name: str,
        environment: str = "development",
        config: Optional[Dict[str, Any]] = None,
        resource_limits: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None
    ) -> AgentDeployment:
        """Create a new agent deployment"""
        # Verify agent exists and belongs to tenant
        agent_service = AgentService(self.session, self.tenant_id)
        agent = await agent_service.get_by_id(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found in tenant {self.tenant_id}")

        deployment = AgentDeployment(
            id=IDGeneratorService.generate_deployment_id(),
            tenant_id=self.tenant_id,
            agent_id=agent_id,
            name=name,
            environment=environment,
            status="inactive",
            config=config or {},
            resource_limits=resource_limits or {},
            created_by=created_by
        )

        self.session.add(deployment)
        await self.session.commit()
        await self.session.refresh(deployment)
        return deployment

    async def list_by_agent(self, agent_id: str) -> List[AgentDeployment]:
        """List all deployments for an agent"""
        stmt = select(AgentDeployment).where(
            and_(
                AgentDeployment.tenant_id == self.tenant_id,
                AgentDeployment.agent_id == agent_id
            )
        ).order_by(AgentDeployment.created_at.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def deploy(self, deployment_id: str, updated_by: Optional[str] = None) -> Optional[AgentDeployment]:
        """Deploy an agent deployment"""
        deployment = await self.get_by_id(deployment_id)
        if not deployment:
            return None

        deployment.status = "active"
        deployment.deployed_at = datetime.utcnow()
        deployment.updated_by = updated_by
        deployment.updated_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(deployment)
        return deployment

    async def undeploy(self, deployment_id: str, updated_by: Optional[str] = None) -> Optional[AgentDeployment]:
        """Undeploy an agent deployment"""
        deployment = await self.get_by_id(deployment_id)
        if not deployment:
            return None

        deployment.status = "inactive"
        deployment.updated_by = updated_by
        deployment.updated_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(deployment)
        return deployment


class AgentExecutionService(BaseService):
    """Service for managing agent executions"""
    
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(session, AgentExecution, tenant_id)

    async def create_execution(
        self,
        agent_id: str,
        input_data: Dict[str, Any],
        deployment_id: Optional[str] = None,
        session_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> AgentExecution:
        """Create a new agent execution"""
        # Verify agent exists and belongs to tenant
        agent_service = AgentService(self.session, self.tenant_id)
        agent = await agent_service.get_by_id(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found in tenant {self.tenant_id}")

        execution = AgentExecution(
            id=IDGeneratorService.generate_execution_id(),
            tenant_id=self.tenant_id,
            agent_id=agent_id,
            deployment_id=deployment_id,
            session_id=session_id,
            input_data=input_data,
            status="running",
            started_at=datetime.utcnow(),
            created_by=created_by
        )

        self.session.add(execution)
        await self.session.commit()
        await self.session.refresh(execution)
        return execution

    async def list_by_agent(
        self,
        agent_id: str,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AgentExecution]:
        """List executions for an agent"""
        stmt = select(AgentExecution).where(
            and_(
                AgentExecution.tenant_id == self.tenant_id,
                AgentExecution.agent_id == agent_id
            )
        )
        
        if session_id:
            stmt = stmt.where(AgentExecution.session_id == session_id)
        if status:
            stmt = stmt.where(AgentExecution.status == status)
        
        stmt = stmt.order_by(AgentExecution.started_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def complete_execution(
        self,
        execution_id: str,
        output_data: Dict[str, Any],
        tokens_used: Optional[int] = None,
        execution_time_ms: Optional[int] = None,
        cost: Optional[float] = None
    ) -> Optional[AgentExecution]:
        """Complete an agent execution"""
        execution = await self.get_by_id(execution_id)
        if not execution:
            return None

        execution.status = "completed"
        execution.output_data = output_data
        execution.tokens_used = tokens_used
        execution.execution_time_ms = execution_time_ms
        execution.cost = cost
        execution.completed_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(execution)
        return execution

    async def fail_execution(
        self,
        execution_id: str,
        error_message: str,
        tokens_used: Optional[int] = None,
        execution_time_ms: Optional[int] = None
    ) -> Optional[AgentExecution]:
        """Mark an agent execution as failed"""
        execution = await self.get_by_id(execution_id)
        if not execution:
            return None

        execution.status = "failed"
        execution.error_message = error_message
        execution.tokens_used = tokens_used
        execution.execution_time_ms = execution_time_ms
        execution.completed_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(execution)
        return execution


class AgentMemoryService(BaseService):
    """Service for managing agent memories"""
    
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(session, AgentMemory, tenant_id)

    async def create_memory(
        self,
        agent_id: str,
        content: str,
        memory_type: str = "conversation",
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance_score: Optional[float] = None,
        expires_at: Optional[datetime] = None,
        created_by: Optional[str] = None
    ) -> AgentMemory:
        """Create a new agent memory"""
        # Verify agent exists and belongs to tenant
        agent_service = AgentService(self.session, self.tenant_id)
        agent = await agent_service.get_by_id(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found in tenant {self.tenant_id}")

        memory = AgentMemory(
            id=IDGeneratorService.generate_memory_id(),
            tenant_id=self.tenant_id,
            agent_id=agent_id,
            session_id=session_id,
            memory_type=memory_type,
            content=content,
            memory_metadata=metadata or {},
            importance_score=importance_score,
            access_count=0,
            expires_at=expires_at,
            created_by=created_by
        )

        self.session.add(memory)
        await self.session.commit()
        await self.session.refresh(memory)
        return memory

    async def get_agent_memories(
        self,
        agent_id: str,
        session_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AgentMemory]:
        """Get memories for an agent"""
        stmt = select(AgentMemory).where(
            and_(
                AgentMemory.tenant_id == self.tenant_id,
                AgentMemory.agent_id == agent_id
            )
        )

        if session_id:
            stmt = stmt.where(AgentMemory.session_id == session_id)
        if memory_type:
            stmt = stmt.where(AgentMemory.memory_type == memory_type)

        # Filter out expired memories
        stmt = stmt.where(
            or_(
                AgentMemory.expires_at.is_(None),
                AgentMemory.expires_at > datetime.utcnow()
            )
        )

        stmt = stmt.order_by(AgentMemory.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def access_memory(self, memory_id: str) -> Optional[AgentMemory]:
        """Access a memory and increment access count"""
        memory = await self.get_by_id(memory_id)
        if not memory:
            return None

        memory.access_count += 1
        memory.last_accessed = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(memory)
        return memory

    async def cleanup_expired_memories(self) -> int:
        """Clean up expired memories for the tenant"""
        from sqlalchemy import delete
        
        stmt = delete(AgentMemory).where(
            and_(
                AgentMemory.tenant_id == self.tenant_id,
                AgentMemory.expires_at <= datetime.utcnow()
            )
        )
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount