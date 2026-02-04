from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from ..services.llm_service import LLMService
from ..services.llm_providers import LLMError, LLMProviderType
from ..services.auth import get_current_user
from ..models.user import User

router = APIRouter(prefix="/llm-providers", tags=["llm-providers"])


class CredentialsRequest(BaseModel):
    """Request model for storing LLM provider credentials."""
    
    provider_type: str = Field(..., description="LLM provider type")
    credentials: Dict[str, Any] = Field(..., description="Provider credentials")


class CredentialsResponse(BaseModel):
    """Response model for credential operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation message")
    is_valid: Optional[bool] = Field(None, description="Credential validation status")


class ProviderHealthResponse(BaseModel):
    """Response model for provider health check."""
    
    provider: str = Field(..., description="Provider name")
    status: str = Field(..., description="Health status")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    available_models: Optional[int] = Field(None, description="Number of available models")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ProviderListResponse(BaseModel):
    """Response model for listing providers."""
    
    providers: List[Dict[str, Any]] = Field(..., description="List of provider information")


class ModelsResponse(BaseModel):
    """Response model for available models."""
    
    provider: str = Field(..., description="Provider name")
    models: List[str] = Field(..., description="Available model names")


class TestRequest(BaseModel):
    """Request model for testing LLM provider."""
    
    provider_type: str = Field(..., description="LLM provider type")
    model: str = Field(..., description="Model name to test")
    message: str = Field("Hello, this is a test message.", description="Test message")


class TestResponse(BaseModel):
    """Response model for LLM provider test."""
    
    success: bool = Field(..., description="Test success status")
    response: Optional[str] = Field(None, description="LLM response content")
    response_time_ms: Optional[int] = Field(None, description="Response time")
    tokens_used: Optional[int] = Field(None, description="Tokens used")
    error: Optional[str] = Field(None, description="Error message if failed")


# Initialize LLM service
llm_service = LLMService()


@router.post("/credentials", response_model=CredentialsResponse)
async def store_credentials(
    request: CredentialsRequest
):
    """Store LLM provider credentials.
    
    Args:
        request: Credentials request
        
    Returns:
        Credentials response with validation status
        
    Raises:
        HTTPException: If credential storage fails
    """
    try:
        # Validate provider type
        if request.provider_type not in [p.value for p in LLMProviderType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid provider type: {request.provider_type}"
            )
        
        # Store credentials
        is_valid = await llm_service.store_credentials(
            request.provider_type,
            request.credentials
        )
        
        return CredentialsResponse(
            success=True,
            message=f"Credentials stored for {request.provider_type}",
            is_valid=is_valid
        )
        
    except LLMError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to store credentials: {e.message}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )


@router.post("/credentials/{provider_type}/validate", response_model=CredentialsResponse)
async def validate_credentials(
    provider_type: str
):
    """Validate stored LLM provider credentials.
    
    Args:
        provider_type: LLM provider type
        
    Returns:
        Validation response
        
    Raises:
        HTTPException: If validation fails
    """
    try:
        # Validate provider type
        if provider_type not in [p.value for p in LLMProviderType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid provider type: {provider_type}"
            )
        
        # Validate credentials
        is_valid = await llm_service.validate_credentials(
            provider_type
        )
        
        return CredentialsResponse(
            success=True,
            message=f"Credentials validation completed for {provider_type}",
            is_valid=is_valid
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation error: {str(e)}"
        )


@router.get("/", response_model=ProviderListResponse)
async def list_providers(
):
    """List all available LLM providers with their status.
    
    Returns:
        List of provider information
    """
    try:
        providers = await llm_service.list_providers()
        
        return ProviderListResponse(providers=providers)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list providers: {str(e)}"
        )


@router.get("/{provider_type}/models", response_model=ModelsResponse)
async def get_available_models(
    provider_type: str
):
    """Get available models for a specific provider.
    
    Args:
        provider_type: LLM provider type
        
    Returns:
        Available models response
        
    Raises:
        HTTPException: If model retrieval fails
    """
    try:
        # Validate provider type
        if provider_type not in [p.value for p in LLMProviderType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid provider type: {provider_type}"
            )
        
        # Get available models
        models = await llm_service.get_available_models(
            provider_type
        )
        
        return ModelsResponse(
            provider=provider_type,
            models=models
        )
        
    except LLMError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get models: {e.message}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )


@router.get("/health", response_model=Dict[str, Any])
async def get_provider_health(
    provider_type: Optional[str] = None
):
    """Get health status for LLM providers.
    
    Args:
        provider_type: Optional specific provider type to check
        
    Returns:
        Health status information
    """
    try:
        if provider_type and provider_type not in [p.value for p in LLMProviderType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid provider type: {provider_type}"
            )
        
        health_status = await llm_service.get_provider_health(
            provider_type
        )
        
        return health_status
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.post("/test", response_model=TestResponse)
async def test_provider(
    request: TestRequest
):
    """Test LLM provider with a simple request.
    
    Args:
        request: Test request
        
    Returns:
        Test response
    """
    try:
        # Validate provider type
        if request.provider_type not in [p.value for p in LLMProviderType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid provider type: {request.provider_type}"
            )
        
        # Create a simple agent config for testing
        from ..models.agent import AgentConfig, LLMProvider
        
        test_config = AgentConfig(
            llm_provider=LLMProvider(request.provider_type),
            model_name=request.model,
            system_prompt="You are a helpful assistant.",
            temperature=0.7,
            max_tokens=100
        )
        
        # Generate test response
        messages = [{"role": "user", "content": request.message}]
        
        response = await llm_service.generate_response(
            messages,
            test_config
        )
        
        return TestResponse(
            success=True,
            response=response.content,
            response_time_ms=response.response_time_ms,
            tokens_used=response.usage.total_tokens
        )
        
    except LLMError as e:
        return TestResponse(
            success=False,
            error=e.message
        )
    except Exception as e:
        return TestResponse(
            success=False,
            error=str(e)
        )


@router.get("/statistics", response_model=Dict[str, Any])
async def get_request_statistics():
    """Get LLM request statistics for monitoring.
    
    Returns:
        Request statistics
    """
    try:
        stats = llm_service.get_request_statistics()
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )
