import os
from datetime import datetime
from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_async_db
from shared.schemas.llm_model import LLMModelCreate, LLMModelResponse, LLMModelUpdate, LLMModelTestRequest
from shared.services.llm_model import LLMModelService
from shared.services.ollama_service import OllamaService, get_ollama_service

router = APIRouter(prefix="/api/v1/llm-models", tags=["llm-models"])

@router.post("/", response_model=LLMModelResponse, status_code=status.HTTP_201_CREATED)
async def create_llm_model(
    model_data: LLMModelCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new LLM model."""
    service = LLMModelService(db)
    try:
        model = await service.create_llm_model(model_data)
        return model
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[LLMModelResponse])
async def list_llm_models(
    db: AsyncSession = Depends(get_async_db),
):
    """List all LLM models."""
    service = LLMModelService(db)
    models = await service.list_llm_models()
    return models

@router.get("/discover-ollama", response_model=List[Dict[str, Any]])
async def discover_ollama_models(
    ollama_service: OllamaService = Depends(get_ollama_service)
):
    """Discover LLM models available via Ollama."""
    models = await ollama_service.list_local_models()
    return models

# In-memory job store for test results (transient)
TEST_JOBS: Dict[str, Dict[str, Any]] = {}

import asyncio
import uuid
from fastapi import BackgroundTasks

async def run_test_bg_task(job_id: str, test_request: LLMModelTestRequest, db_session_maker, ollama_service):
    """Background task to run the LLM test."""
    TEST_JOBS[job_id]["status"] = "running"
    
    # Create a new session for the background task
    async with db_session_maker() as session:
        try:
            model_service = LLMModelService(session)
            llm_model = await model_service.get_llm_model(test_request.model_id)

            if not llm_model:
                TEST_JOBS[job_id]["status"] = "failed"
                TEST_JOBS[job_id]["error"] = "LLM model not found"
                return

            # Generic provider handling using LLMProviderFactory
            from shared.services.llm_providers import (
                LLMProviderFactory, 
                CredentialManager, 
                LLMProviderType, 
                LLMRequest, 
                LLMMessage
            )

            # Determine provider type
            provider_type_str = llm_model.provider.lower()
            try:
                provider_enum = LLMProviderType(provider_type_str)
            except ValueError:
                TEST_JOBS[job_id]["status"] = "failed"
                TEST_JOBS[job_id]["error"] = f"Unsupported LLM provider: {llm_model.provider}"
                return

            # Setup temporary Credential Manager
            cred_manager = CredentialManager()
            
            creds = {}
            if provider_enum == LLMProviderType.OPENAI:
                 creds = {"api_key": llm_model.api_key}
                 if llm_model.api_base:
                     creds["base_url"] = llm_model.api_base
            elif provider_enum == LLMProviderType.ANTHROPIC:
                 creds = {"api_key": llm_model.api_key}
            elif provider_enum == LLMProviderType.OLLAMA:
                 # Handle Ollama connection - prioritize internal networking if available
                 base_url = llm_model.api_base
                 env_ollama_url = os.environ.get("OLLAMA_BASE_URL")
                 
                 # If we are in Docker and the DB says localhost, switch to the internal service
                 if base_url and ("localhost" in base_url or "127.0.0.1" in base_url) and env_ollama_url:
                     base_url = env_ollama_url
                 
                 # Fallback to env var or default if not in DB
                 if not base_url:
                     base_url = env_ollama_url or "http://ollama:11434"
                     
                 creds = {"base_url": base_url}
            elif provider_enum == LLMProviderType.AZURE_OPENAI:
                 creds = {
                     "api_key": llm_model.api_key,
                     "endpoint": llm_model.api_base,
                     "api_version": "2023-05-15"
                 }
            
            await cred_manager.store_credentials(provider_enum, creds)
            
            # Create Factory & Provider
            factory = LLMProviderFactory(cred_manager)
            provider = await factory.get_or_create_provider(provider_enum)
            
            # Create Request
            messages = []
            if test_request.system_prompt:
                 messages.append(LLMMessage(role="system", content=test_request.system_prompt))
            messages.append(LLMMessage(role="user", content=test_request.prompt))

            request = LLMRequest(
                messages=messages,
                model=llm_model.name,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Generate Response
            response = await provider.generate_response(request)
            
            TEST_JOBS[job_id]["status"] = "completed"
            TEST_JOBS[job_id]["result"] = response.content
            
        except Exception as e:
            TEST_JOBS[job_id]["status"] = "failed"
            TEST_JOBS[job_id]["error"] = str(e)


@router.post("/test", response_model=Dict[str, str])
async def test_llm_model(
    test_request: LLMModelTestRequest,
    background_tasks: BackgroundTasks,
    ollama_service: OllamaService = Depends(get_ollama_service),
):
    """Start a background test for a specific LLM model."""
    job_id = str(uuid.uuid4())
    TEST_JOBS[job_id] = {"status": "pending", "created_at": str(datetime.now())}
    
    # We need to pass the session maker to the background task, not the session itself
    # because the session will be closed when this request finishes.
    from shared.database.connection import AsyncSessionLocal
    
    background_tasks.add_task(
        run_test_bg_task, 
        job_id, 
        test_request, 
        AsyncSessionLocal, 
        ollama_service
    )
    
    return {"job_id": job_id, "status": "pending"}


@router.get("/test/{job_id}", response_model=Dict[str, Any])
async def get_test_status(job_id: str):
    """Get the status and result of a test job."""
    if job_id not in TEST_JOBS:
        raise HTTPException(status_code=404, detail="Test job not found")
        
    return TEST_JOBS[job_id]


@router.get("/{model_id}", response_model=LLMModelResponse)
async def get_llm_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """Get a specific LLM model by ID."""
    service = LLMModelService(db)
    model = await service.get_llm_model(model_id)
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM model not found")
    return model

@router.put("/{model_id}", response_model=LLMModelResponse)
async def update_llm_model(
    model_id: UUID,
    model_data: LLMModelUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    """Update an LLM model."""
    service = LLMModelService(db)
    try:
        model = await service.update_llm_model(model_id, model_data)
        if not model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM model not found")
        return model
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """Delete an LLM model."""
    service = LLMModelService(db)
    success = await service.delete_llm_model(model_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM model not found")
