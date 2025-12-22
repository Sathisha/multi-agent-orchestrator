"""Comprehensive audit and compliance service for the AI Agent Framework."""

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from uuid import UUID

from sqlalchemy import select, func, and_, or_, desc, asc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_database_session
from ..models.audit import (
    AuditLog, AuditEventType, AuditSeverity, AuditOutcome,
    AuditLogRequest, AuditLogResponse, AuditLogCreateRequest,
    AuditStatistics, ComplianceReport
)
from ..models.user import User
from .base import BaseService


class AuditService(BaseService):
    """Comprehensive audit logging and compliance service."""
    
    def __init__(self, session: AsyncSession, tenant_id: str, user_id: Optional[str] = None):
        # Don't call super().__init__ since AuditService has different parameters
        self.session = session
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.correlation_id = str(uuid.uuid4())
    
    async def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        message: str,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        severity: AuditSeverity = AuditSeverity.LOW,
        resource_type: Optional[str] = None,
        resource_id: Optional[Union[str, UUID]] = None,
        resource_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        compliance_tags: Optional[List[str]] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        source_service: Optional[str] = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> AuditLog:
        """
        Log an audit event with comprehensive details.
        
        Args:
            event_type: Type of event being logged
            action: Action that was performed
            message: Human-readable description of the event
            outcome: Success/failure outcome
            severity: Event severity level
            resource_type: Type of resource affected
            resource_id: ID of the resource affected
            resource_name: Name of the resource affected
            details: Additional structured details
            request_data: Request data for API calls
            response_data: Response data for API calls
            error_code: Error code if applicable
            error_message: Error message if applicable
            compliance_tags: Tags for compliance categorization
            source_ip: Source IP address
            user_agent: User agent string
            source_service: Source service name
            session_id: User session ID
            correlation_id: Correlation ID for tracing
            
        Returns:
            Created audit log entry
        """
        try:
            # Generate unique event ID
            event_id = str(uuid.uuid4())
            
            # Get user information if available
            username = None
            if self.user_id:
                user_result = await self.session.execute(
                    select(User.username).where(User.id == self.user_id)
                )
                user_row = user_result.first()
                if user_row:
                    username = user_row.username
            
            # Create audit log entry
            audit_log = AuditLog(
                tenant_id=self.tenant_id,
                event_type=event_type,
                event_id=event_id,
                correlation_id=correlation_id or self.correlation_id,
                timestamp=datetime.utcnow(),
                user_id=self.user_id,
                username=username,
                session_id=session_id,
                source_ip=source_ip,
                user_agent=user_agent,
                source_service=source_service,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                action=action,
                outcome=outcome,
                severity=severity,
                message=message,
                details=details or {},
                request_data=request_data or {},
                response_data=response_data or {},
                error_code=error_code,
                error_message=error_message,
                compliance_tags=compliance_tags or [],
                retention_date=self._calculate_retention_date(event_type, severity)
            )
            
            # Calculate and set checksum for integrity
            audit_log.checksum = audit_log.calculate_checksum()
            
            # Add to session and commit
            self.session.add(audit_log)
            await self.session.commit()
            await self.session.refresh(audit_log)
            
            return audit_log
            
        except Exception as e:
            await self.session.rollback()
            # Log the audit logging failure (meta-audit)
            print(f"Failed to log audit event: {e}")
            raise
    
    async def get_audit_logs(
        self,
        request: AuditLogRequest
    ) -> tuple[List[AuditLogResponse], int]:
        """
        Retrieve audit logs with filtering, pagination, and search.
        
        Args:
            request: Audit log query request
            
        Returns:
            Tuple of (audit logs, total count)
        """
        # Build base query
        query = select(AuditLog).where(AuditLog.tenant_id == self.tenant_id)
        count_query = select(func.count(AuditLog.id)).where(AuditLog.tenant_id == self.tenant_id)
        
        # Apply filters
        if request.event_types:
            query = query.where(AuditLog.event_type.in_(request.event_types))
            count_query = count_query.where(AuditLog.event_type.in_(request.event_types))
        
        if request.user_id:
            query = query.where(AuditLog.user_id == request.user_id)
            count_query = count_query.where(AuditLog.user_id == request.user_id)
        
        if request.username:
            query = query.where(AuditLog.username.ilike(f"%{request.username}%"))
            count_query = count_query.where(AuditLog.username.ilike(f"%{request.username}%"))
        
        if request.resource_type:
            query = query.where(AuditLog.resource_type == request.resource_type)
            count_query = count_query.where(AuditLog.resource_type == request.resource_type)
        
        if request.resource_id:
            query = query.where(AuditLog.resource_id == request.resource_id)
            count_query = count_query.where(AuditLog.resource_id == request.resource_id)
        
        if request.action:
            query = query.where(AuditLog.action.ilike(f"%{request.action}%"))
            count_query = count_query.where(AuditLog.action.ilike(f"%{request.action}%"))
        
        if request.outcome:
            query = query.where(AuditLog.outcome == request.outcome)
            count_query = count_query.where(AuditLog.outcome == request.outcome)
        
        if request.severity:
            query = query.where(AuditLog.severity == request.severity)
            count_query = count_query.where(AuditLog.severity == request.severity)
        
        if request.source_ip:
            query = query.where(AuditLog.source_ip == request.source_ip)
            count_query = count_query.where(AuditLog.source_ip == request.source_ip)
        
        if request.correlation_id:
            query = query.where(AuditLog.correlation_id == request.correlation_id)
            count_query = count_query.where(AuditLog.correlation_id == request.correlation_id)
        
        if request.start_date:
            query = query.where(AuditLog.timestamp >= request.start_date)
            count_query = count_query.where(AuditLog.timestamp >= request.start_date)
        
        if request.end_date:
            query = query.where(AuditLog.timestamp <= request.end_date)
            count_query = count_query.where(AuditLog.timestamp <= request.end_date)
        
        if request.compliance_tags:
            # Filter by compliance tags using JSONB contains
            for tag in request.compliance_tags:
                query = query.where(AuditLog.compliance_tags.contains([tag]))
                count_query = count_query.where(AuditLog.compliance_tags.contains([tag]))
        
        # Apply sorting
        sort_column = getattr(AuditLog, request.sort_by, AuditLog.timestamp)
        if request.sort_order == 'asc':
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))
        
        # Apply pagination
        offset = (request.page - 1) * request.size
        query = query.offset(offset).limit(request.size)
        
        # Execute queries
        result = await self.session.execute(query)
        audit_logs = result.scalars().all()
        
        count_result = await self.session.execute(count_query)
        total_count = count_result.scalar()
        
        # Convert to response models
        response_logs = [
            AuditLogResponse(
                event_type=log.event_type,
                event_id=log.event_id,
                correlation_id=log.correlation_id,
                timestamp=log.timestamp,
                user_id=str(log.user_id) if log.user_id else None,
                username=log.username,
                session_id=log.session_id,
                source_ip=str(log.source_ip) if log.source_ip else None,
                user_agent=log.user_agent,
                source_service=log.source_service,
                resource_type=log.resource_type,
                resource_id=str(log.resource_id) if log.resource_id else None,
                resource_name=log.resource_name,
                action=log.action,
                outcome=log.outcome,
                severity=log.severity,
                message=log.message,
                details=log.details,
                error_code=log.error_code,
                error_message=log.error_message,
                compliance_tags=log.compliance_tags
            )
            for log in audit_logs
        ]
        
        return response_logs, total_count
    
    async def get_audit_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> AuditStatistics:
        """
        Get audit log statistics for the tenant.
        
        Args:
            start_date: Start date for statistics
            end_date: End date for statistics
            
        Returns:
            Audit statistics
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Base query conditions
        conditions = [
            AuditLog.tenant_id == self.tenant_id,
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date
        ]
        
        # Total events
        total_result = await self.session.execute(
            select(func.count(AuditLog.id)).where(and_(*conditions))
        )
        total_events = total_result.scalar()
        
        # Events by type
        type_result = await self.session.execute(
            select(
                AuditLog.event_type,
                func.count(AuditLog.id).label('count')
            ).where(and_(*conditions)).group_by(AuditLog.event_type)
        )
        events_by_type = {row.event_type.value: row.count for row in type_result}
        
        # Events by outcome
        outcome_result = await self.session.execute(
            select(
                AuditLog.outcome,
                func.count(AuditLog.id).label('count')
            ).where(and_(*conditions)).group_by(AuditLog.outcome)
        )
        events_by_outcome = {row.outcome.value: row.count for row in outcome_result}
        
        # Events by severity
        severity_result = await self.session.execute(
            select(
                AuditLog.severity,
                func.count(AuditLog.id).label('count')
            ).where(and_(*conditions)).group_by(AuditLog.severity)
        )
        events_by_severity = {row.severity.value: row.count for row in severity_result}
        
        # Top users
        user_result = await self.session.execute(
            select(
                AuditLog.username,
                func.count(AuditLog.id).label('count')
            ).where(
                and_(*conditions, AuditLog.username.isnot(None))
            ).group_by(AuditLog.username).order_by(desc('count')).limit(10)
        )
        top_users = [
            {'username': row.username, 'event_count': row.count}
            for row in user_result
        ]
        
        # Top resources
        resource_result = await self.session.execute(
            select(
                AuditLog.resource_type,
                AuditLog.resource_name,
                func.count(AuditLog.id).label('count')
            ).where(
                and_(*conditions, AuditLog.resource_type.isnot(None))
            ).group_by(AuditLog.resource_type, AuditLog.resource_name).order_by(desc('count')).limit(10)
        )
        top_resources = [
            {
                'resource_type': row.resource_type,
                'resource_name': row.resource_name,
                'access_count': row.count
            }
            for row in resource_result
        ]
        
        # Security events
        security_events_result = await self.session.execute(
            select(func.count(AuditLog.id)).where(
                and_(
                    *conditions,
                    AuditLog.event_type.in_([
                        AuditEventType.ACCESS_DENIED,
                        AuditEventType.SECURITY_VIOLATION,
                        AuditEventType.GUARDRAIL_TRIGGERED,
                        AuditEventType.SUSPICIOUS_ACTIVITY,
                        AuditEventType.USER_LOGIN_FAILED
                    ])
                )
            )
        )
        security_events = security_events_result.scalar()
        
        # Failed events
        failed_events_result = await self.session.execute(
            select(func.count(AuditLog.id)).where(
                and_(*conditions, AuditLog.outcome == AuditOutcome.FAILURE)
            )
        )
        failed_events = failed_events_result.scalar()
        
        return AuditStatistics(
            total_events=total_events,
            events_by_type=events_by_type,
            events_by_outcome=events_by_outcome,
            events_by_severity=events_by_severity,
            top_users=top_users,
            top_resources=top_resources,
            security_events=security_events,
            failed_events=failed_events
        )
    
    async def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        report_type: str = "general"
    ) -> ComplianceReport:
        """
        Generate a comprehensive compliance report.
        
        Args:
            start_date: Report period start
            end_date: Report period end
            report_type: Type of compliance report
            
        Returns:
            Compliance report
        """
        report_id = str(uuid.uuid4())
        
        # Base query conditions
        conditions = [
            AuditLog.tenant_id == self.tenant_id,
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date
        ]
        
        # Total events
        total_result = await self.session.execute(
            select(func.count(AuditLog.id)).where(and_(*conditions))
        )
        total_events = total_result.scalar()
        
        # User activities
        user_activities_result = await self.session.execute(
            select(
                AuditLog.username,
                func.count(AuditLog.id).label('count')
            ).where(
                and_(*conditions, AuditLog.username.isnot(None))
            ).group_by(AuditLog.username)
        )
        user_activities = {row.username: row.count for row in user_activities_result}
        
        # Resource access
        resource_access_result = await self.session.execute(
            select(
                AuditLog.resource_type,
                func.count(AuditLog.id).label('count')
            ).where(
                and_(*conditions, AuditLog.resource_type.isnot(None))
            ).group_by(AuditLog.resource_type)
        )
        resource_access = {row.resource_type: row.count for row in resource_access_result}
        
        # Security incidents
        security_incidents_result = await self.session.execute(
            select(AuditLog).where(
                and_(
                    *conditions,
                    AuditLog.event_type.in_([
                        AuditEventType.ACCESS_DENIED,
                        AuditEventType.SECURITY_VIOLATION,
                        AuditEventType.GUARDRAIL_TRIGGERED,
                        AuditEventType.SUSPICIOUS_ACTIVITY
                    ])
                )
            ).order_by(desc(AuditLog.timestamp))
        )
        security_incidents = [
            {
                'event_id': incident.event_id,
                'timestamp': incident.timestamp.isoformat(),
                'event_type': incident.event_type.value,
                'severity': incident.severity.value,
                'message': incident.message,
                'user': incident.username,
                'source_ip': str(incident.source_ip) if incident.source_ip else None
            }
            for incident in security_incidents_result.scalars().all()
        ]
        
        # Policy violations (guardrail triggers)
        policy_violations_result = await self.session.execute(
            select(AuditLog).where(
                and_(
                    *conditions,
                    AuditLog.event_type == AuditEventType.GUARDRAIL_TRIGGERED
                )
            ).order_by(desc(AuditLog.timestamp))
        )
        policy_violations = [
            {
                'event_id': violation.event_id,
                'timestamp': violation.timestamp.isoformat(),
                'message': violation.message,
                'user': violation.username,
                'details': violation.details
            }
            for violation in policy_violations_result.scalars().all()
        ]
        
        # Data access events
        data_access_result = await self.session.execute(
            select(func.count(AuditLog.id)).where(
                and_(
                    *conditions,
                    AuditLog.event_type == AuditEventType.DATA_ACCESSED
                )
            )
        )
        data_access_events = data_access_result.scalar()
        
        # Data export events
        data_export_result = await self.session.execute(
            select(func.count(AuditLog.id)).where(
                and_(
                    *conditions,
                    AuditLog.event_type == AuditEventType.DATA_EXPORTED
                )
            )
        )
        data_export_events = data_export_result.scalar()
        
        # Failed login attempts
        failed_login_result = await self.session.execute(
            select(func.count(AuditLog.id)).where(
                and_(
                    *conditions,
                    AuditLog.event_type == AuditEventType.USER_LOGIN_FAILED
                )
            )
        )
        failed_login_attempts = failed_login_result.scalar()
        
        # Privilege escalations (role assignments)
        privilege_escalation_result = await self.session.execute(
            select(func.count(AuditLog.id)).where(
                and_(
                    *conditions,
                    AuditLog.event_type.in_([
                        AuditEventType.ROLE_ASSIGNED,
                        AuditEventType.PERMISSION_GRANTED
                    ])
                )
            )
        )
        privilege_escalations = privilege_escalation_result.scalar()
        
        return ComplianceReport(
            report_id=report_id,
            generated_at=datetime.utcnow(),
            period_start=start_date,
            period_end=end_date,
            total_events=total_events,
            user_activities=user_activities,
            resource_access=resource_access,
            security_incidents=security_incidents,
            policy_violations=policy_violations,
            data_access_events=data_access_events,
            data_export_events=data_export_events,
            failed_login_attempts=failed_login_attempts,
            privilege_escalations=privilege_escalations
        )
    
    async def export_audit_logs(
        self,
        request: AuditLogRequest,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export audit logs in various formats for compliance.
        
        Args:
            request: Audit log query request
            format: Export format (json, csv, xml)
            
        Returns:
            Export data and metadata
        """
        # Get audit logs
        audit_logs, total_count = await self.get_audit_logs(request)
        
        export_data = {
            'export_id': str(uuid.uuid4()),
            'generated_at': datetime.utcnow().isoformat(),
            'tenant_id': self.tenant_id,
            'exported_by': self.user_id,
            'total_records': total_count,
            'format': format,
            'filters': request.dict(exclude_none=True),
            'data': [log.dict() for log in audit_logs]
        }
        
        # Log the export event
        await self.log_event(
            event_type=AuditEventType.DATA_EXPORTED,
            action="audit_logs_exported",
            message=f"Exported {len(audit_logs)} audit log records in {format} format",
            outcome=AuditOutcome.SUCCESS,
            severity=AuditSeverity.MEDIUM,
            resource_type="audit_logs",
            details={
                'export_id': export_data['export_id'],
                'record_count': len(audit_logs),
                'format': format,
                'filters_applied': request.dict(exclude_none=True)
            },
            compliance_tags=['data_export', 'audit_trail']
        )
        
        return export_data
    
    async def verify_audit_integrity(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Verify the integrity of audit logs using checksums.
        
        Args:
            start_date: Start date for verification
            end_date: End date for verification
            
        Returns:
            Integrity verification results
        """
        conditions = [AuditLog.tenant_id == self.tenant_id]
        
        if start_date:
            conditions.append(AuditLog.timestamp >= start_date)
        if end_date:
            conditions.append(AuditLog.timestamp <= end_date)
        
        # Get audit logs for verification
        result = await self.session.execute(
            select(AuditLog).where(and_(*conditions)).order_by(AuditLog.timestamp)
        )
        audit_logs = result.scalars().all()
        
        verification_results = {
            'verification_id': str(uuid.uuid4()),
            'verified_at': datetime.utcnow().isoformat(),
            'total_records': len(audit_logs),
            'verified_records': 0,
            'corrupted_records': 0,
            'missing_checksums': 0,
            'corrupted_entries': []
        }
        
        for log in audit_logs:
            if not log.checksum:
                verification_results['missing_checksums'] += 1
                continue
            
            if log.verify_integrity():
                verification_results['verified_records'] += 1
            else:
                verification_results['corrupted_records'] += 1
                verification_results['corrupted_entries'].append({
                    'event_id': log.event_id,
                    'timestamp': log.timestamp.isoformat(),
                    'event_type': log.event_type.value,
                    'expected_checksum': log.checksum,
                    'calculated_checksum': log.calculate_checksum()
                })
        
        # Log the integrity verification
        await self.log_event(
            event_type=AuditEventType.SYSTEM_STARTED,  # Using closest available event type
            action="audit_integrity_verification",
            message=f"Verified integrity of {len(audit_logs)} audit records",
            outcome=AuditOutcome.SUCCESS if verification_results['corrupted_records'] == 0 else AuditOutcome.PARTIAL,
            severity=AuditSeverity.HIGH if verification_results['corrupted_records'] > 0 else AuditSeverity.LOW,
            resource_type="audit_logs",
            details=verification_results,
            compliance_tags=['integrity_check', 'audit_verification']
        )
        
        return verification_results
    
    def _calculate_retention_date(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity
    ) -> Optional[datetime]:
        """
        Calculate retention date based on event type and severity.
        
        Args:
            event_type: Type of audit event
            severity: Event severity
            
        Returns:
            Retention date or None for permanent retention
        """
        # Default retention periods (in days)
        retention_periods = {
            AuditSeverity.CRITICAL: 2555,  # 7 years
            AuditSeverity.HIGH: 1825,      # 5 years
            AuditSeverity.MEDIUM: 1095,    # 3 years
            AuditSeverity.LOW: 365         # 1 year
        }
        
        # Security events get longer retention
        security_events = {
            AuditEventType.ACCESS_DENIED,
            AuditEventType.SECURITY_VIOLATION,
            AuditEventType.GUARDRAIL_TRIGGERED,
            AuditEventType.SUSPICIOUS_ACTIVITY,
            AuditEventType.USER_LOGIN_FAILED
        }
        
        if event_type in security_events:
            retention_days = max(retention_periods[severity], 1825)  # Minimum 5 years
        else:
            retention_days = retention_periods[severity]
        
        return datetime.utcnow() + timedelta(days=retention_days)
    
    async def _log_audit_event(
        self,
        session: AsyncSession,
        event_type: AuditEventType,
        action: str,
        message: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        severity: AuditSeverity = AuditSeverity.LOW,
        details: Optional[Dict[str, Any]] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None
    ):
        """Helper method for logging audit events from other services."""
        # Create temporary audit service for logging
        temp_service = AuditService(session, tenant_id or self.tenant_id, user_id or self.user_id)
        
        # Prepare details with old/new values if provided
        audit_details = details or {}
        if old_values:
            audit_details['old_values'] = old_values
        if new_values:
            audit_details['new_values'] = new_values
        
        await temp_service.log_event(
            event_type=event_type,
            action=action,
            message=message,
            outcome=outcome,
            severity=severity,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=audit_details
        )