# LLM Models API Endpoints
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

@router.post("/test", response_model=str) # Return type is str for now, can be a more complex schema
async def test_llm_model(
    test_request: LLMModelTestRequest,
    db: AsyncSession = Depends(get_async_db),
    ollama_service: OllamaService = Depends(get_ollama_service)
):
    """Test a specific LLM model with a sample prompt."""
    model_service = LLMModelService(db)
    llm_model = await model_service.get_llm_model(test_request.model_id)

    if not llm_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM model not found")

    # Generic provider handling using LLMProviderFactory
    from shared.services.llm_providers import (
        LLMProviderFactory, 
        CredentialManager, 
        LLMProviderType, 
        LLMRequest, 
        LLMMessage
    )

    try:
        # Determine provider type
        provider_type_str = llm_model.provider.lower()
        try:
            provider_enum = LLMProviderType(provider_type_str)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported LLM provider: {llm_model.provider}")

        # Setup temporary Credential Manager with this model's credentials
        cred_manager = CredentialManager()
        
        creds = {}
        if provider_enum == LLMProviderType.OPENAI:
             creds = {"api_key": llm_model.api_key}
             if llm_model.api_base:
                 creds["base_url"] = llm_model.api_base
        elif provider_enum == LLMProviderType.ANTHROPIC:
             creds = {"api_key": llm_model.api_key}
        elif provider_enum == LLMProviderType.OLLAMA:
             creds = {"base_url": llm_model.api_base or "http://ollama:11434"}
        elif provider_enum == LLMProviderType.AZURE_OPENAI:
             creds = {
                 "api_key": llm_model.api_key,
                 "endpoint": llm_model.api_base, # Assuming api_base maps to endpoint
                 "api_version": "2023-05-15" # Default or need a field for this
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
        return response.content

    except Exception as e:
        # If it's already an HTTPException, re-raise it
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error testing model: {str(e)}")

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
