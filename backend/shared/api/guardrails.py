# Guardrails API Endpoints
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import logging

from ..database.connection import get_async_db
from ..services.guardrails import (
    GuardrailsService,
    ValidationResult,
    PolicyResult,
    ContentCategory,
    ViolationType,
    RiskLevel
)
from ..middleware.tenant import get_tenant_context
from ..api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/guardrails", tags=["guardrails"])


# Request/Response Models
class ValidateContentRequest(BaseModel):
    """Request model for content validation"""
    content: str = Field(..., description="Content to validate")
    agent_id: Optional[str] = Field(None, description="Agent ID if applicable")
    session_id: Optional[str] = Field(None, description="Session ID if applicable")
    content_category: Optional[str] = Field("general", description="Content category")


class ValidationResultResponse(BaseModel):
    """Response model for validation result"""
    is_valid: bool
    violations: list[str]
    violation_types: list[str]
    risk_score: float
    risk_level: str
    sanitized_content: Optional[str]
    blocked_phrases: list[str]
    confidence: float
    processing_time_ms: float
    metadata: Dict[str, Any]


class CheckPolicyRequest(BaseModel):
    """Request model for policy check"""
    action: str = Field(..., description="Action to check")
    resource: str = Field(..., description="Resource being accessed")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")


class PolicyResultResponse(BaseModel):
    """Response model for policy check"""
    allowed: bool
    policy_name: str
    reason: str
    risk_score: float
    metadata: Dict[str, Any]


class ViolationStatsResponse(BaseModel):
    """Response model for violation statistics"""
    tenant_id: str
    period: Dict[str, str]
    total_violations: int
    critical_violations: int
    high_violations: int
    medium_violations: int


@router.post("/validate/input", response_model=ValidationResultResponse)
async def validate_input(
    request: ValidateContentRequest,
    current_request: Request,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Validate input content against guardrails
    
    This endpoint checks user input for:
    - Harmful content
    - PII exposure
    - Prompt injection attempts
    - Toxic content
    - Policy violations
    """
    try:
        tenant_context = get_tenant_context(current_request)
        tenant_id = tenant_context.get('tenant_id')
        user_id = current_user.get('user_id')
        
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant context not found"
            )
        
        guardrails_service = GuardrailsService(session)
        
        result = await guardrails_service.validate_agent_input(
            tenant_id=tenant_id,
            agent_id=request.agent_id,
            user_id=user_id,
            content=request.content,
            session_id=request.session_id
        )
        
        return ValidationResultResponse(
            is_valid=result.is_valid,
            violations=result.violations,
            violation_types=[vt.value for vt in result.violation_types],
            risk_score=result.risk_score,
            risk_level=result.risk_level.value,
            sanitized_content=result.sanitized_content,
            blocked_phrases=result.blocked_phrases,
            confidence=result.confidence,
            processing_time_ms=result.processing_time_ms,
            metadata=result.metadata
        )
        
    except Exception as e:
        logger.error(f"Error validating input: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating input: {str(e)}"
        )


@router.post("/validate/output", response_model=ValidationResultResponse)
async def validate_output(
    request: ValidateContentRequest,
    current_request: Request,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Validate output content against guardrails
    
    This endpoint checks agent output for:
    - Harmful content
    - PII exposure
    - Inappropriate responses
    - Policy violations
    """
    try:
        tenant_context = get_tenant_context(current_request)
        tenant_id = tenant_context.get('tenant_id')
        user_id = current_user.get('user_id')
        
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant context not found"
            )
        
        guardrails_service = GuardrailsService(session)
        
        result = await guardrails_service.validate_agent_output(
            tenant_id=tenant_id,
            agent_id=request.agent_id,
            user_id=user_id,
            content=request.content,
            session_id=request.session_id
        )
        
        return ValidationResultResponse(
            is_valid=result.is_valid,
            violations=result.violations,
            violation_types=[vt.value for vt in result.violation_types],
            risk_score=result.risk_score,
            risk_level=result.risk_level.value,
            sanitized_content=result.sanitized_content,
            blocked_phrases=result.blocked_phrases,
            confidence=result.confidence,
            processing_time_ms=result.processing_time_ms,
            metadata=result.metadata
        )
        
    except Exception as e:
        logger.error(f"Error validating output: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating output: {str(e)}"
        )


@router.post("/policy/check", response_model=PolicyResultResponse)
async def check_policy(
    request: CheckPolicyRequest,
    current_request: Request,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Check if an action is allowed by tenant policies
    
    This endpoint validates actions against:
    - Tenant-specific policies
    - Resource access controls
    - Rate limiting policies
    - Security policies
    """
    try:
        tenant_context = get_tenant_context(current_request)
        tenant_id = tenant_context.get('tenant_id')
        user_id = current_user.get('user_id')
        
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant context not found"
            )
        
        guardrails_service = GuardrailsService(session)
        
        result = await guardrails_service.check_agent_policy(
            tenant_id=tenant_id,
            user_id=user_id,
            action=request.action,
            resource=request.resource,
            context=request.context
        )
        
        return PolicyResultResponse(
            allowed=result.allowed,
            policy_name=result.policy_name,
            reason=result.reason,
            risk_score=result.risk_score,
            metadata=result.metadata
        )
        
    except Exception as e:
        logger.error(f"Error checking policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking policy: {str(e)}"
        )


@router.get("/violations/stats", response_model=ViolationStatsResponse)
async def get_violation_stats(
    current_request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get violation statistics for the tenant
    
    Returns statistics about guardrail violations including:
    - Total violations
    - Violations by risk level
    - Violation trends over time
    """
    try:
        tenant_context = get_tenant_context(current_request)
        tenant_id = tenant_context.get('tenant_id')
        
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant context not found"
            )
        
        # Parse dates if provided
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        guardrails_service = GuardrailsService(session)
        
        stats = await guardrails_service.get_violation_stats(
            tenant_id=tenant_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        return ViolationStatsResponse(**stats)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting violation stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting violation stats: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for guardrails service"""
    return {
        "status": "healthy",
        "service": "guardrails",
        "timestamp": datetime.utcnow().isoformat()
    }
