"""Audit and compliance API endpoints for the AI Agent Framework."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from ..database import get_async_db
from ..middleware.security import get_current_user, require_permissions
from ..models.audit import (
    AuditLogRequest, AuditLogResponse,
    AuditStatistics, ComplianceReport, AuditEventType, AuditSeverity, AuditOutcome
)
# Define AuditLogCreateRequest locally to ensure fields exist
class AuditLogCreateRequest(BaseModel):
    event_type: AuditEventType
    action: str
    message: str
    outcome: AuditOutcome = AuditOutcome.SUCCESS
    severity: AuditSeverity = AuditSeverity.LOW
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    compliance_tags: Optional[List[str]] = None
    correlation_id: Optional[str] = None

from ..models.user import User
from ..services.audit import AuditService
from ..services.rbac import StandardPermissions
import json
import csv
import io


router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogListResponse(BaseModel):
    """Response model for audit log list."""
    
    logs: List[AuditLogResponse] = Field(..., description="List of audit logs")
    total: int = Field(..., description="Total number of logs")
    page: int = Field(..., description="Current page")
    size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total number of pages")


class IntegrityVerificationResponse(BaseModel):
    """Response model for integrity verification."""
    
    verification_id: str = Field(..., description="Verification ID")
    verified_at: str = Field(..., description="Verification timestamp")
    total_records: int = Field(..., description="Total records verified")
    verified_records: int = Field(..., description="Successfully verified records")
    corrupted_records: int = Field(..., description="Corrupted records found")
    missing_checksums: int = Field(..., description="Records missing checksums")
    corrupted_entries: List[Dict[str, Any]] = Field(..., description="Details of corrupted entries")


@router.get("/logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    event_types: Optional[List[AuditEventType]] = Query(None, description="Filter by event types"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    username: Optional[str] = Query(None, description="Filter by username"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    action: Optional[str] = Query(None, description="Filter by action"),
    outcome: Optional[AuditOutcome] = Query(None, description="Filter by outcome"),
    severity: Optional[AuditSeverity] = Query(None, description="Filter by severity"),
    source_ip: Optional[str] = Query(None, description="Filter by source IP"),
    start_date: Optional[datetime] = Query(None, description="Start date for time range"),
    end_date: Optional[datetime] = Query(None, description="End date for time range"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    compliance_tags: Optional[List[str]] = Query(None, description="Filter by compliance tags"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=1000, description="Items per page"),
    sort_by: str = Query("timestamp", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    current_user: User = Depends(get_current_user),
    session = Depends(get_async_db),
    _: None = Depends(require_permissions([StandardPermissions.AUDIT_READ]))
):
    """
    Retrieve audit logs with filtering, pagination, and search capabilities.
    """
    try:
        # Create audit service
        audit_service = AuditService(session, str(current_user.id))
        
        # Create request object
        request = AuditLogRequest(
            event_types=event_types,
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            outcome=outcome,
            severity=severity,
            source_ip=source_ip,
            start_date=start_date,
            end_date=end_date,
            correlation_id=correlation_id,
            compliance_tags=compliance_tags,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Get audit logs
        logs, total = await audit_service.get_audit_logs(request)
        
        # Calculate pagination info
        total_pages = (total + size - 1) // size
        
        # Log the audit log access
        await audit_service.log_event(
            event_type=AuditEventType.DATA_ACCESSED,
            action="audit_logs_accessed",
            message=f"User accessed audit logs (page {page}, {len(logs)} records)",
            outcome=AuditOutcome.SUCCESS,
            severity=AuditSeverity.LOW,
            resource_type="audit_logs",
            details={
                'page': page,
                'size': size,
                'total_records': total,
                'filters_applied': request.dict(exclude_none=True)
            },
            compliance_tags=['audit_access']
        )
        
        return AuditLogListResponse(
            logs=logs,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit logs: {str(e)}")


@router.get("/logs/{event_id}", response_model=AuditLogResponse)
async def get_audit_log(
    event_id: str,
    current_user: User = Depends(get_current_user),
    session = Depends(get_async_db),
    _: None = Depends(require_permissions([StandardPermissions.AUDIT_READ]))
):
    """
    Retrieve a specific audit log entry by event ID.
    """
    try:
        # Create audit service
        audit_service = AuditService(session, str(current_user.id))
        
        # Create request to find specific event
        request = AuditLogRequest(
            page=1,
            size=1,
            sort_by="timestamp",
            sort_order="desc"
        )
        
        # Get all logs and filter by event_id (since we can't filter by event_id in the request model)
        logs, total = await audit_service.get_audit_logs(request)
        
        target_log = None
        for log in logs:
            if log.event_id == event_id:
                target_log = log
                break
        
        if not target_log:
            raise HTTPException(status_code=404, detail="Audit log entry not found")
        
        # Log the specific audit log access
        await audit_service.log_event(
            event_type=AuditEventType.DATA_ACCESSED,
            action="audit_log_accessed",
            message=f"User accessed specific audit log entry: {event_id}",
            outcome=AuditOutcome.SUCCESS,
            severity=AuditSeverity.LOW,
            resource_type="audit_log",
            resource_id=event_id,
            compliance_tags=['audit_access', 'detailed_access']
        )
        
        return target_log
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit log: {str(e)}")


@router.get("/statistics", response_model=AuditStatistics)
async def get_audit_statistics(
    start_date: Optional[datetime] = Query(None, description="Start date for statistics"),
    end_date: Optional[datetime] = Query(None, description="End date for statistics"),
    current_user: User = Depends(get_current_user),
    session = Depends(get_async_db),
    _: None = Depends(require_permissions([StandardPermissions.AUDIT_READ]))
):
    """
    Get audit log statistics and analytics.
    """
    try:
        # Create audit service
        audit_service = AuditService(session, str(current_user.id))
        
        # Get statistics
        statistics = await audit_service.get_audit_statistics(start_date, end_date)
        
        # Log the statistics access
        await audit_service.log_event(
            event_type=AuditEventType.DATA_ACCESSED,
            action="audit_statistics_accessed",
            message="User accessed audit statistics",
            outcome=AuditOutcome.SUCCESS,
            severity=AuditSeverity.LOW,
            resource_type="audit_statistics",
            details={
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'total_events': statistics.total_events
            },
            compliance_tags=['audit_access', 'statistics']
        )
        
        return statistics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit statistics: {str(e)}")


@router.post("/reports/compliance", response_model=ComplianceReport)
async def generate_compliance_report(
    start_date: datetime,
    end_date: datetime,
    report_type: str = "general",
    current_user: User = Depends(get_current_user),
    session = Depends(get_async_db),
    _: None = Depends(require_permissions([StandardPermissions.AUDIT_EXPORT]))
):
    """
    Generate a comprehensive compliance report.
    """
    try:
        # Validate date range
        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        # Create audit service
        audit_service = AuditService(session, str(current_user.id))
        
        # Generate compliance report
        report = await audit_service.generate_compliance_report(start_date, end_date, report_type)
        
        # Log the report generation
        await audit_service.log_event(
            event_type=AuditEventType.DATA_EXPORTED,
            action="compliance_report_generated",
            message=f"Generated compliance report for period {start_date} to {end_date}",
            outcome=AuditOutcome.SUCCESS,
            severity=AuditSeverity.MEDIUM,
            resource_type="compliance_report",
            resource_id=report.report_id,
            details={
                'report_type': report_type,
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'total_events': report.total_events
            },
            compliance_tags=['compliance_report', 'data_export']
        )
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate compliance report: {str(e)}")


@router.post("/export")
async def export_audit_logs(
    format: str = Query("json", description="Export format: json, csv"),
    event_types: Optional[List[AuditEventType]] = Query(None, description="Filter by event types"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    username: Optional[str] = Query(None, description="Filter by username"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    action: Optional[str] = Query(None, description="Filter by action"),
    outcome: Optional[AuditOutcome] = Query(None, description="Filter by outcome"),
    severity: Optional[AuditSeverity] = Query(None, description="Filter by severity"),
    source_ip: Optional[str] = Query(None, description="Filter by source IP"),
    start_date: Optional[datetime] = Query(None, description="Start date for time range"),
    end_date: Optional[datetime] = Query(None, description="End date for time range"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    compliance_tags: Optional[List[str]] = Query(None, description="Filter by compliance tags"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(1000, ge=1, le=10000, description="Items per page"),
    sort_by: str = Query("timestamp", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    current_user: User = Depends(get_current_user),
    session = Depends(get_async_db),
    _: None = Depends(require_permissions([StandardPermissions.AUDIT_EXPORT]))
):
    """
    Export audit logs in various formats for compliance and analysis.
    """
    try:
        # Validate format
        if format not in ["json", "csv"]:
            raise HTTPException(status_code=400, detail="Unsupported export format. Use 'json' or 'csv'")
        
        # Create audit service
        audit_service = AuditService(session, str(current_user.id))
        
        # Create request object
        request = AuditLogRequest(
            event_types=event_types,
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            outcome=outcome,
            severity=severity,
            source_ip=source_ip,
            start_date=start_date,
            end_date=end_date,
            correlation_id=correlation_id,
            compliance_tags=compliance_tags,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Export audit logs
        export_data = await audit_service.export_audit_logs(request, format)
        
        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"audit_logs_{timestamp}.{format}"
        
        if format == "json":
            # Return JSON export
            content = json.dumps(export_data, indent=2, default=str)
            media_type = "application/json"
        else:  # CSV
            # Convert to CSV
            output = io.StringIO()
            if export_data['data']:
                # Get field names from first record
                fieldnames = list(export_data['data'][0].keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for record in export_data['data']:
                    # Convert complex fields to strings
                    csv_record = {}
                    for key, value in record.items():
                        if isinstance(value, (dict, list)):
                            csv_record[key] = json.dumps(value)
                        else:
                            csv_record[key] = str(value) if value is not None else ""
                    writer.writerow(csv_record)
            
            content = output.getvalue()
            media_type = "text/csv"
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(content.encode('utf-8')),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export audit logs: {str(e)}")


@router.post("/verify-integrity", response_model=IntegrityVerificationResponse)
async def verify_audit_integrity(
    start_date: Optional[datetime] = Query(None, description="Start date for verification"),
    end_date: Optional[datetime] = Query(None, description="End date for verification"),
    current_user: User = Depends(get_current_user),
    session = Depends(get_async_db),
    _: None = Depends(require_permissions([StandardPermissions.AUDIT_MANAGE]))
):
    """
    Verify the cryptographic integrity of audit logs.
    """
    try:
        # Create audit service
        audit_service = AuditService(session, str(current_user.id))
        
        # Verify integrity
        verification_results = await audit_service.verify_audit_integrity(start_date, end_date)
        
        return IntegrityVerificationResponse(**verification_results)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify audit integrity: {str(e)}")


@router.post("/logs", response_model=Dict[str, str])
async def create_audit_log(
    request: AuditLogCreateRequest,
    source_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session = Depends(get_async_db),
    _: None = Depends(require_permissions([StandardPermissions.AUDIT_MANAGE]))
):
    """
    Create a custom audit log entry.
    """
    try:
        # Create audit service
        audit_service = AuditService(session, str(current_user.id))
        
        # Create audit log
        audit_log = await audit_service.log_event(
            event_type=request.event_type,
            action=request.action,
            message=request.message,
            outcome=request.outcome,
            severity=request.severity,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            resource_name=request.resource_name,
            details=request.details,
            request_data=request.request_data,
            response_data=request.response_data,
            error_code=request.error_code,
            error_message=request.error_message,
            compliance_tags=request.compliance_tags,
            source_ip=source_ip,
            user_agent=user_agent,
            session_id=session_id,
            correlation_id=request.correlation_id
        )
        
        return {"event_id": audit_log.event_id, "message": "Audit log created successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create audit log: {str(e)}")


@router.get("/health")
async def audit_health_check():
    """
    Health check endpoint for the audit service.
    """
    return {
        "status": "healthy",
        "service": "audit",
        "timestamp": datetime.utcnow().isoformat()
    }
