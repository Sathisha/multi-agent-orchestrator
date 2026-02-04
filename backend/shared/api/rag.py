

from datetime import datetime
from typing import List, Optional, Any, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_async_db
from shared.api.auth import get_current_user
from shared.models.user import User
from shared.models.rag import RAGSource, RAGSourceType, RAGStatus
from shared.services.rag_service import RAGService
from shared.services.memory_manager import get_memory_manager

router = APIRouter(prefix="/rag", tags=["RAG Management"])

# Pydantic Models
class RAGSourceCreateRequest(BaseModel):
    name: str
    url: HttpUrl
    is_public: bool = False

class RAGSourceResponse(BaseModel):
    id: UUID
    name: str
    source_type: RAGSourceType
    content_source: str
    status: RAGStatus
    owner_id: UUID
    is_public: bool
    processing_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True



# Dependency
async def get_rag_service(
    session: AsyncSession = Depends(get_async_db)
) -> RAGService:
    memory_manager = await get_memory_manager()
    return RAGService(session, memory_manager)

@router.post("/sources/website", response_model=RAGSourceResponse)
async def add_website_source(
    request: RAGSourceCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Add a website as a RAG source."""
    # We pass the URL as a string
    source = await rag_service.create_source(
        name=request.name,
        source_type=RAGSourceType.WEBSITE,
        content_source=str(request.url),
        owner_id=current_user.id,
        is_public=request.is_public
    )
    # Processing is triggered inside create_source (awaited) in current implementation of RAGService
    # If we wanted to background it strictly in API layer:
    # We would change RAGService.create_source to NOT process, and then add task here.
    # But current RAGService.create_source awaits process_source. 
    # To make it truly async if it takes time, we should modify RAGService to offload valid work.
    # For now, let's keep it simple as implemented in service (it awaits).
    
    return source

@router.post("/sources/pdf", response_model=RAGSourceResponse)
async def upload_pdf_source(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Upload a PDF as a RAG source."""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    content = await file.read()
    source_name = name or file.filename
    
    source = await rag_service.create_source(
        name=source_name,
        source_type=RAGSourceType.PDF,
        content_source=file.filename, # We might want to store the actual file path if we saved it to disk
        owner_id=current_user.id,
        file_content=content
    )
    
    return source

@router.get("/sources", response_model=List[RAGSourceResponse])
async def list_rag_sources(
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """List all RAG sources accessible to the current user (owned, public, or role-granted)."""
    # Get user's roles
    user_roles = [role.role_id for role in current_user.user_roles] if hasattr(current_user, 'user_roles') else []
    return await rag_service.get_accessible_sources(current_user.id, user_roles)

@router.delete("/sources/{source_id}", status_code=204)
async def delete_rag_source(
    source_id: UUID,
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Delete a RAG source."""
    success = await rag_service.delete_source(source_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Source not found")

class QueryRequest(BaseModel):
    query: str
    limit: int = 5

@router.post("/query")
async def query_rag(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Test query against user's RAG sources."""
    results = await rag_service.query(request.query, current_user.id, request.limit)
    return results

@router.get("/agents/{agent_id}/sources", response_model=List[RAGSourceResponse])
async def list_agent_sources(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """List RAG sources assigned to an agent."""
    # Add check if user owns agent? For now assumtion is if they can see agent, they can see sources options.
    return await rag_service.get_agent_sources(agent_id)

@router.post("/agents/{agent_id}/sources/{source_id}")
async def assign_source(
    agent_id: UUID,
    source_id: UUID,
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Assign a RAG source to an agent."""
    try:
        await rag_service.assign_source_to_agent(agent_id, source_id, current_user.id)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/agents/{agent_id}/sources/{source_id}")
async def remove_assignment(
    agent_id: UUID,
    source_id: UUID,
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Remove a RAG source assignment from an agent."""
    await rag_service.remove_source_from_agent(agent_id, source_id, current_user.id)
    return {"status": "success"}

# ===== RBAC Endpoints =====

@router.get("/sources/{source_id}/roles")
async def get_source_roles(
    source_id: UUID,
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Get role assignments for a RAG source (owner only)."""
    source = await rag_service.session.get(RAGSource, source_id)
    if not source or source.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return await rag_service.get_source_roles(source_id)

@router.post("/sources/{source_id}/roles/{role_id}")
async def assign_role_to_source(
    source_id: UUID,
    role_id: UUID,
    access_type: str = "view",
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Assign a role to a RAG source (owner only)."""
    if access_type not in ['view', 'query', 'modify']:
        raise HTTPException(status_code=400, detail="Invalid access type")
    
    try:
        await rag_service.assign_role_to_source(source_id, role_id, access_type, current_user.id)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.delete("/sources/{source_id}/roles/{role_id}")
async def remove_role_from_source(
    source_id: UUID,
    role_id: UUID,
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Remove a role from a RAG source (owner only)."""
    try:
        await rag_service.remove_role_from_source(source_id, role_id, current_user.id)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.patch("/sources/{source_id}/visibility")
async def update_source_visibility(
    source_id: UUID,
    is_public: bool,
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Toggle public/private status of a RAG source (owner only)."""
    source = await rag_service.session.get(RAGSource, source_id)
    if not source or source.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can change visibility")
    
    source.is_public = is_public
    await rag_service.session.commit()
    await rag_service.session.refresh(source)
    
    return RAGSourceResponse.model_validate(source)

