# Agent Management API Endpoints with Multi-Tenant Support
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ..database.connection import get_async_db
from ..services.agent import AgentService, AgentDeploymentService, AgentExecutionService, AgentMemoryService
from ..middleware.tenant import (
    get_tenant_context,
    get_tenant_aware_session,
    get_tenant_context_dependency,
    require_tenant_context_dependency
)
from ..api.auth import require_tenant_authentication
from ..models.tenant import TenantContext
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
    tenant_id: UUID
    name: str
    description: Optional[str]
    type: str
    status: str
    version: str
    config: Dict[str, Any]
    system_prompt: Optional[str]
    llm_config: Optional[Dict[str, Any]]
    available_tools: Optional[List[str]]
    capabilities: Optional[List[str]]
    tags: Optional[List[str]]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class AgentDeploymentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    environment: str = Field(default="development")
    config: Optional[Dict[str, Any]] = None
    resource_limits: Optional[Dict[str, Any]] = None


class AgentDeploymentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    agent_id: UUID
    name: str
    environment: str
    status: str
    config: Optional[Dict[str, Any]]
    resource_limits: Optional[Dict[str, Any]]
    deployed_at: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


class AgentExecutionRequest(BaseModel):
    input_data: Dict[str, Any]
    deployment_id: Optional[UUID] = None
    session_id: Optional[str] = None


class AgentExecutionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    agent_id: UUID
    deployment_id: Optional[UUID]
    session_id: Optional[str]
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    status: str
    error_message: Optional[str]
    tokens_used: Optional[int]
    execution_time_ms: Optional[int]
    cost: Optional[float]
    started_at: Optional[str]
    completed_at: Optional[str]
    
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
    tenant_id: UUID
    agent_id: UUID
    session_id: Optional[str]
    memory_type: str
    content: str
    metadata: Optional[Dict[str, Any]]
    importance_score: Optional[float]
    access_count: int
    last_accessed: Optional[str]
    created_at: str
    
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
@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: AgentCreateRequest,
    session_and_context = Depends(get_tenant_aware_session),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Create a new agent"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentService(session, tenant_context.tenant_id)
    
    try:
        agent = await service.create_agent(
            name=request.name,
            description=request.description,
            agent_type=request.type,
            config=request.config,
            system_prompt=request.system_prompt,
            model_config=request.model_config,
            available_tools=request.available_tools,
            capabilities=request.capabilities,
            tags=request.tags,
            created_by=current_user["user_id"]
        )
        
        return AgentResponse.from_orm(agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    agent_type: Optional[AgentType] = None,
    status_filter: Optional[AgentStatus] = None,
    tags: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    session_and_context = Depends(get_tenant_aware_session)
):
    """List agents for the current tenant"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentService(session, tenant_context.tenant_id)
    
    # Parse tags if provided
    tag_list = tags.split(",") if tags else None
    
    agents = await service.list_agents(
        agent_type=agent_type,
        status=status_filter,
        tags=tag_list,
        limit=limit,
        offset=offset
    )
    
    return [AgentResponse.from_orm(agent) for agent in agents]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    session_and_context = Depends(get_tenant_aware_session)
):
    """Get agent by ID"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentService(session, tenant_context.tenant_id)
    
    agent = await service.get_by_id(str(agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentResponse.from_orm(agent)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    request: AgentUpdateRequest,
    session_and_context = Depends(get_tenant_aware_session),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Update agent"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentService(session, tenant_context.tenant_id)
    
    agent = await service.update_agent(
        agent_id=str(agent_id),
        name=request.name,
        description=request.description,
        config=request.config,
        system_prompt=request.system_prompt,
        model_config=request.model_config,
        available_tools=request.available_tools,
        capabilities=request.capabilities,
        tags=request.tags,
        updated_by=current_user["user_id"]
    )
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentResponse.from_orm(agent)


@router.post("/{agent_id}/activate")
async def activate_agent(
    agent_id: UUID,
    session_and_context = Depends(get_tenant_aware_session),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Activate agent"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentService(session, tenant_context.tenant_id)
    
    agent = await service.activate_agent(str(agent_id), current_user["user_id"])
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"message": "Agent activated successfully"}


@router.post("/{agent_id}/deactivate")
async def deactivate_agent(
    agent_id: UUID,
    session_and_context = Depends(get_tenant_aware_session),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Deactivate agent"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentService(session, tenant_context.tenant_id)
    
    agent = await service.deactivate_agent(str(agent_id), current_user["user_id"])
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"message": "Agent deactivated successfully"}


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: UUID,
    session_and_context = Depends(get_tenant_aware_session),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Delete agent"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentService(session, tenant_context.tenant_id)
    
    success = await service.delete(str(agent_id))
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"message": "Agent deleted successfully"}


@router.get("/{agent_id}/statistics", response_model=AgentStatisticsResponse)
async def get_agent_statistics(
    agent_id: UUID,
    session_and_context = Depends(get_tenant_aware_session)
):
    """Get agent usage statistics"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentService(session, tenant_context.tenant_id)
    
    stats = await service.get_agent_statistics(str(agent_id))
    if not stats:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentStatisticsResponse(**stats)


# Agent deployment endpoints
@router.post("/{agent_id}/deployments", response_model=AgentDeploymentResponse)
async def create_deployment(
    agent_id: UUID,
    request: AgentDeploymentRequest,
    session_and_context = Depends(get_tenant_aware_session),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Create agent deployment"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentDeploymentService(session, tenant_context.tenant_id)
    
    try:
        deployment = await service.create_deployment(
            agent_id=str(agent_id),
            name=request.name,
            environment=request.environment,
            config=request.config,
            resource_limits=request.resource_limits,
            created_by=current_user["user_id"]
        )
        return AgentDeploymentResponse.from_orm(deployment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/deployments", response_model=List[AgentDeploymentResponse])
async def list_deployments(
    agent_id: UUID,
    session_and_context = Depends(get_tenant_aware_session)
):
    """List agent deployments"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentDeploymentService(session, tenant_context.tenant_id)
    
    deployments = await service.list_by_agent(str(agent_id))
    return [AgentDeploymentResponse.from_orm(dep) for dep in deployments]


@router.post("/deployments/{deployment_id}/deploy")
async def deploy_agent(
    deployment_id: UUID,
    session_and_context = Depends(get_tenant_aware_session),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Deploy agent"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentDeploymentService(session, tenant_context.tenant_id)
    
    deployment = await service.deploy(str(deployment_id), current_user["user_id"])
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return {"message": "Agent deployed successfully"}


# Agent execution endpoints
@router.post("/{agent_id}/execute", response_model=AgentExecutionResponse)
async def execute_agent(
    agent_id: UUID,
    request: AgentExecutionRequest,
    session_and_context = Depends(get_tenant_aware_session),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Execute agent"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentExecutionService(session, tenant_context.tenant_id)
    
    try:
        execution = await service.create_execution(
            agent_id=str(agent_id),
            input_data=request.input_data,
            deployment_id=str(request.deployment_id) if request.deployment_id else None,
            session_id=request.session_id,
            created_by=current_user["user_id"]
        )
        
        return AgentExecutionResponse.from_orm(execution)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/executions", response_model=List[AgentExecutionResponse])
async def list_executions(
    agent_id: UUID,
    session_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    session_and_context = Depends(get_tenant_aware_session)
):
    """List agent executions"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentExecutionService(session, tenant_context.tenant_id)
    
    executions = await service.list_by_agent(
        str(agent_id),
        session_id=session_id,
        status=status_filter,
        limit=limit,
        offset=offset
    )
    
    return [AgentExecutionResponse.from_orm(exec) for exec in executions]


# Agent memory endpoints
@router.post("/{agent_id}/memories", response_model=AgentMemoryResponse)
async def create_memory(
    agent_id: UUID,
    request: AgentMemoryRequest,
    session_and_context = Depends(get_tenant_aware_session),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Create agent memory"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentMemoryService(session, tenant_context.tenant_id)
    
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
        return AgentMemoryResponse.from_orm(memory)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/memories", response_model=List[AgentMemoryResponse])
async def list_memories(
    agent_id: UUID,
    session_id: Optional[str] = None,
    memory_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    session_and_context = Depends(get_tenant_aware_session)
):
    """List agent memories"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentMemoryService(session, tenant_context.tenant_id)
    
    memories = await service.get_agent_memories(
        agent_id=str(agent_id),
        session_id=session_id,
        memory_type=memory_type,
        limit=limit,
        offset=offset
    )
    
    return [AgentMemoryResponse.from_orm(memory) for memory in memories]


@router.get("/memories/{memory_id}", response_model=AgentMemoryResponse)
async def get_memory(
    memory_id: UUID,
    session_and_context = Depends(get_tenant_aware_session)
):
    """Get and access a specific memory"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentMemoryService(session, tenant_context.tenant_id)
    
    memory = await service.access_memory(str(memory_id))
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return AgentMemoryResponse.from_orm(memory)