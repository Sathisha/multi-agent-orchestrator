from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ..database.connection import get_async_db
from ..services.agent import AgentService, AgentDeploymentService, AgentExecutionService, AgentMemoryService
from ..models.agent import Agent, AgentType, AgentStatus, AgentDeployment, AgentExecution, AgentMemory

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

# Pydantic models for API requests/responses
class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    type: AgentType = AgentType.CONVERSATIONAL
    config: Dict[str, Any] = Field(default_factory=dict)
    system_prompt: Optional[str] = None
    llm_config: Optional[Dict[str, Any]] = None
    available_tools: Optional[List[str]] = None
    capabilities: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class AgentUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
    llm_config: Optional[Dict[str, Any]] = None
    available_tools: Optional[List[str]] = None
    capabilities: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class AgentResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    type: str
    status: str
    version: str
    config: Dict[str, Any]
    system_prompt: Optional[str] = None
    llm_config: Optional[Dict[str, Any]] = Field(None, validation_alias="model_config_dict")
    available_tools: Optional[List[str]] = None
    capabilities: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AgentDeploymentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    environment: str = Field(default="development")
    config: Optional[Dict[str, Any]] = None
    resource_limits: Optional[Dict[str, Any]] = None


class AgentDeploymentResponse(BaseModel):
    id: UUID
    agent_id: UUID
    name: str
    environment: str
    status: str
    config: Optional[Dict[str, Any]]
    resource_limits: Optional[Dict[str, Any]] = None
    deployed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AgentExecutionRequest(BaseModel):
    input_data: Dict[str, Any]
    deployment_id: Optional[UUID] = None
    session_id: Optional[str] = None


class AgentExecutionResponse(BaseModel):
    id: UUID
    agent_id: UUID
    deployment_id: Optional[UUID]
    session_id: Optional[str]
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    status: str
    error_message: Optional[str]
    tokens_used: Optional[int]
    execution_time_ms: Optional[int] = None
    cost: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AgentMemoryRequest(BaseModel):
    content: str = Field(..., min_length=1)
    memory_type: str = Field(default="conversation")
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    importance_score: Optional[float] = None


class AgentMemoryResponse(BaseModel):
    id: UUID
    agent_id: UUID
    session_id: Optional[str]
    memory_type: str
    content: str
    metadata: Optional[Dict[str, Any]]
    importance_score: Optional[float] = None
    access_count: int = 0
    last_accessed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AgentStatisticsResponse(BaseModel):
    agent_id: UUID
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_execution_time_ms: float
    total_tokens_used: int
    total_cost: float
    total_memories: int
    total_memory_size_bytes: int


# Agent CRUD endpoints
@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: AgentCreateRequest,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "00000000-0000-0000-0000-000000000000"})
):
    """Create a new agent"""
    service = AgentService(session)
    
    try:
        agent = await service.create_agent(
            name=request.name,
            description=request.description,
            agent_type=request.type,
            config=request.config,
            system_prompt=request.system_prompt,
            llm_config=request.llm_config,
            available_tools=request.available_tools,
            capabilities=request.capabilities,
            tags=request.tags,
            created_by=current_user["user_id"]
        )
        
        return agent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    agent_type: Optional[AgentType] = None,
    status_filter: Optional[AgentStatus] = None,
    tags: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_async_db)
):
    """List agents"""
    service = AgentService(session)
    
    # Parse tags if provided
    tag_list = tags.split(",") if tags else None
    
    agents = await service.list_agents(
        agent_type=agent_type,
        status=status_filter,
        tags=tag_list,
        limit=limit,
        offset=offset
    )
    
    return agents


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_async_db)
):
    """Get agent by ID"""
    service = AgentService(session)
    
    agent = await service.get_by_id(str(agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    request: AgentUpdateRequest,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "00000000-0000-0000-0000-000000000000"})
):
    """Update agent"""
    service = AgentService(session)
    
    agent = await service.update_agent(
        agent_id=str(agent_id),
        name=request.name,
        description=request.description,
        config=request.config,
        system_prompt=request.system_prompt,
        llm_config=request.llm_config,
        available_tools=request.available_tools,
        capabilities=request.capabilities,
        tags=request.tags,
        updated_by=current_user["user_id"]
    )
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent


@router.post("/{agent_id}/activate")
async def activate_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "00000000-0000-0000-0000-000000000000"})
):
    """Activate agent"""
    service = AgentService(session)
    
    agent = await service.activate_agent(str(agent_id), current_user["user_id"])
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"message": "Agent activated successfully"}


@router.post("/{agent_id}/deactivate")
async def deactivate_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "00000000-0000-0000-0000-000000000000"})
):
    """Deactivate agent"""
    service = AgentService(session)
    
    agent = await service.deactivate_agent(str(agent_id), current_user["user_id"])
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"message": "Agent deactivated successfully"}


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "00000000-0000-0000-0000-000000000000"})
):
    """Delete agent"""
    service = AgentService(session)
    
    success = await service.delete(str(agent_id))
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"message": "Agent deleted successfully"}


@router.get("/{agent_id}/statistics", response_model=AgentStatisticsResponse)
async def get_agent_statistics(
    agent_id: UUID,
    session: AsyncSession = Depends(get_async_db)
):
    """Get agent usage statistics"""
    service = AgentService(session)
    
    stats = await service.get_agent_statistics(str(agent_id))
    if not stats:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentStatisticsResponse(**stats)


# Agent deployment endpoints
@router.post("/{agent_id}/deployments", response_model=AgentDeploymentResponse)
async def create_deployment(
    agent_id: UUID,
    request: AgentDeploymentRequest,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "00000000-0000-0000-0000-000000000000"})
):
    """Create agent deployment"""
    service = AgentDeploymentService(session)
    
    try:
        deployment = await service.create_deployment(
            agent_id=str(agent_id),
            name=request.name,
            environment=request.environment,
            config=request.config,
            resource_limits=request.resource_limits,
            created_by=current_user["user_id"]
        )
        return deployment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/deployments", response_model=List[AgentDeploymentResponse])
async def list_deployments(
    agent_id: UUID,
    session: AsyncSession = Depends(get_async_db)
):
    """List agent deployments"""
    service = AgentDeploymentService(session)
    
    deployments = await service.list_by_agent(str(agent_id))
    return deployments


@router.post("/deployments/{deployment_id}/deploy")
async def deploy_agent(
    deployment_id: UUID,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "00000000-0000-0000-0000-000000000000"})
):
    """Deploy agent"""
    service = AgentDeploymentService(session)
    
    deployment = await service.deploy(str(deployment_id), current_user["user_id"])
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return {"message": "Agent deployed successfully"}


# Agent execution endpoints
@router.post("/{agent_id}/execute", response_model=AgentExecutionResponse)
async def execute_agent(
    agent_id: UUID,
    request: AgentExecutionRequest,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "00000000-0000-0000-0000-000000000000"})
):
    """Execute agent"""
    service = AgentExecutionService(session)
    
    try:
        execution = await service.create_execution(
            agent_id=str(agent_id),
            input_data=request.input_data,
            deployment_id=str(request.deployment_id) if request.deployment_id else None,
            session_id=request.session_id,
            created_by=current_user["user_id"]
        )
        
        return execution
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/executions", response_model=List[AgentExecutionResponse])
async def list_executions(
    agent_id: UUID,
    session_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_async_db)
):
    """List agent executions"""
    service = AgentExecutionService(session)
    
    executions = await service.list_by_agent(
        str(agent_id),
        session_id=session_id,
        status=status_filter,
        limit=limit,
        offset=offset
    )
    
    return executions


# Agent memory endpoints
@router.post("/{agent_id}/memories", response_model=AgentMemoryResponse)
async def create_memory(
    agent_id: UUID,
    request: AgentMemoryRequest,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "00000000-0000-0000-0000-000000000000"})
):
    """Create agent memory"""
    service = AgentMemoryService(session)
    
    try:
        memory = await service.create_memory(
            agent_id=str(agent_id),
            content=request.content,
            memory_type=request.memory_type,
            session_id=request.session_id,
            metadata=request.metadata,
            importance_score=request.importance_score,
            created_by=current_user["user_id"]
        )
        return memory
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/memories", response_model=List[AgentMemoryResponse])
async def list_memories(
    agent_id: UUID,
    session_id: Optional[str] = None,
    memory_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_async_db)
):
    """List agent memories"""
    service = AgentMemoryService(session)
    
    memories = await service.get_agent_memories(
        agent_id=str(agent_id),
        session_id=session_id,
        memory_type=memory_type,
        limit=limit,
        offset=offset
    )
    
    return memories


@router.get("/memories/{memory_id}", response_model=AgentMemoryResponse)
async def get_memory(
    memory_id: UUID,
    session: AsyncSession = Depends(get_async_db)
):
    """Get and access a specific memory"""
    service = AgentMemoryService(session)
    
    memory = await service.access_memory(str(memory_id))
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return memory
