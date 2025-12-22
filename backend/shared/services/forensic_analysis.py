"""Forensic analysis service for advanced audit investigation and security incident response."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from collections import defaultdict, Counter

from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit import AuditLog, AuditEventType, AuditSeverity, AuditOutcome
from ..models.user import User
from .base import BaseService
from .audit import AuditService


class SecurityIncident:
    """Represents a detected security incident."""
    
    def __init__(
        self,
        incident_id: str,
        incident_type: str,
        severity: str,
        description: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        affected_users: List[str] = None,
        affected_resources: List[str] = None,
        indicators: List[Dict[str, Any]] = None,
        recommendations: List[str] = None
    ):
        self.incident_id = incident_id
        self.incident_type = incident_type
        self.severity = severity
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.affected_users = affected_users or []
        self.affected_resources = affected_resources or []
        self.indicators = indicators or []
        self.recommendations = recommendations or []


class ForensicAnalysisService(BaseService):
    """Advanced forensic analysis service for security incident investigation."""
    
    def __init__(self, session: AsyncSession, tenant_id: str, user_id: Optional[str] = None):
        super().__init__(session, tenant_id, user_id)
        self.audit_service = AuditService(session, tenant_id, user_id)
    
    async def detect_security_incidents(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        incident_types: Optional[List[str]] = None
    ) -> List[SecurityIncident]:
        """
        Detect potential security incidents using pattern analysis.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            incident_types: Specific incident types to detect
            
        Returns:
            List of detected security incidents
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        incidents = []
        
        # Define detection methods
        detection_methods = {
            'brute_force': self._detect_brute_force_attacks,
            'privilege_escalation': self._detect_privilege_escalation,
            'data_exfiltration': self._detect_data_exfiltration,
            'suspicious_access': self._detect_suspicious_access_patterns,
            'system_abuse': self._detect_system_abuse,
            'anomalous_behavior': self._detect_anomalous_behavior
        }
        
        # Run detection methods
        for incident_type, detection_method in detection_methods.items():
            if not incident_types or incident_type in incident_types:
                try:
                    detected_incidents = await detection_method(start_date, end_date)
                    incidents.extend(detected_incidents)
                except Exception as e:
                    print(f"Error in {incident_type} detection: {e}")
        
        # Sort incidents by severity and time
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        incidents.sort(key=lambda x: (severity_order.get(x.severity, 4), x.start_time), reverse=True)
        
        return incidents
    
    async def _detect_brute_force_attacks(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[SecurityIncident]:
        """Detect brute force authentication attacks."""
        
        incidents = []
        
        # Query for failed login attempts
        failed_logins = await self.session.execute(
            select(
                AuditLog.source_ip,
                AuditLog.username,
                func.count(AuditLog.id).label('attempt_count'),
                func.min(AuditLog.timestamp).label('first_attempt'),
                func.max(AuditLog.timestamp).label('last_attempt')
            ).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.event_type == AuditEventType.USER_LOGIN_FAILED,
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date
                )
            ).group_by(AuditLog.source_ip, AuditLog.username)
            .having(func.count(AuditLog.id) >= 5)  # 5+ failed attempts
            .order_by(desc('attempt_count'))
        )
        
        for row in failed_logins:
            # Check if attempts were within a short time window
            time_window = (row.last_attempt - row.first_attempt).total_seconds()
            if time_window <= 3600:  # Within 1 hour
                severity = 'critical' if row.attempt_count >= 20 else 'high' if row.attempt_count >= 10 else 'medium'
                
                incident = SecurityIncident(
                    incident_id=f"brute_force_{row.source_ip}_{row.username}_{int(row.first_attempt.timestamp())}",
                    incident_type='brute_force',
                    severity=severity,
                    description=f"Brute force attack detected: {row.attempt_count} failed login attempts for user '{row.username}' from IP {row.source_ip}",
                    start_time=row.first_attempt,
                    end_time=row.last_attempt,
                    affected_users=[row.username] if row.username else [],
                    indicators=[
                        {
                            'type': 'failed_login_attempts',
                            'count': row.attempt_count,
                            'source_ip': str(row.source_ip),
                            'time_window_seconds': time_window
                        }
                    ],
                    recommendations=[
                        f"Block IP address {row.source_ip}",
                        f"Force password reset for user {row.username}" if row.username else "Review authentication logs",
                        "Implement rate limiting for login attempts",
                        "Enable account lockout after failed attempts"
                    ]
                )
                incidents.append(incident)
        
        return incidents
    
    async def _detect_privilege_escalation(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[SecurityIncident]:
        """Detect privilege escalation attempts."""
        
        incidents = []
        
        # Query for role assignments and permission grants
        privilege_changes = await self.session.execute(
            select(
                AuditLog.user_id,
                AuditLog.username,
                AuditLog.event_type,
                AuditLog.timestamp,
                AuditLog.details,
                AuditLog.source_ip
            ).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.event_type.in_([
                        AuditEventType.ROLE_ASSIGNED,
                        AuditEventType.PERMISSION_GRANTED
                    ]),
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date
                )
            ).order_by(AuditLog.timestamp)
        )
        
        # Group by user and analyze patterns
        user_privilege_changes = defaultdict(list)
        for row in privilege_changes:
            user_privilege_changes[row.user_id].append(row)
        
        for user_id, changes in user_privilege_changes.items():
            if len(changes) >= 3:  # Multiple privilege changes
                # Check if changes happened quickly
                time_span = (changes[-1].timestamp - changes[0].timestamp).total_seconds()
                if time_span <= 1800:  # Within 30 minutes
                    
                    incident = SecurityIncident(
                        incident_id=f"privilege_escalation_{user_id}_{int(changes[0].timestamp.timestamp())}",
                        incident_type='privilege_escalation',
                        severity='high',
                        description=f"Rapid privilege escalation detected for user {changes[0].username}: {len(changes)} privilege changes in {time_span/60:.1f} minutes",
                        start_time=changes[0].timestamp,
                        end_time=changes[-1].timestamp,
                        affected_users=[changes[0].username] if changes[0].username else [],
                        indicators=[
                            {
                                'type': 'rapid_privilege_changes',
                                'count': len(changes),
                                'time_span_seconds': time_span,
                                'changes': [
                                    {
                                        'timestamp': change.timestamp.isoformat(),
                                        'event_type': change.event_type.value,
                                        'details': change.details
                                    }
                                    for change in changes
                                ]
                            }
                        ],
                        recommendations=[
                            f"Review privilege changes for user {changes[0].username}",
                            "Verify authorization for privilege escalations",
                            "Implement approval workflow for privilege changes",
                            "Monitor user activity for suspicious behavior"
                        ]
                    )
                    incidents.append(incident)
        
        return incidents
    
    async def _detect_data_exfiltration(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[SecurityIncident]:
        """Detect potential data exfiltration attempts."""
        
        incidents = []
        
        # Query for data export events
        data_exports = await self.session.execute(
            select(
                AuditLog.user_id,
                AuditLog.username,
                AuditLog.source_ip,
                func.count(AuditLog.id).label('export_count'),
                func.min(AuditLog.timestamp).label('first_export'),
                func.max(AuditLog.timestamp).label('last_export'),
                func.array_agg(AuditLog.resource_type).label('resource_types')
            ).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.event_type == AuditEventType.DATA_EXPORTED,
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date
                )
            ).group_by(AuditLog.user_id, AuditLog.username, AuditLog.source_ip)
            .having(func.count(AuditLog.id) >= 5)  # 5+ exports
            .order_by(desc('export_count'))
        )
        
        for row in data_exports:
            # Check if exports were within a short time window
            time_window = (row.last_export - row.first_export).total_seconds()
            if time_window <= 7200:  # Within 2 hours
                severity = 'critical' if row.export_count >= 20 else 'high' if row.export_count >= 10 else 'medium'
                
                incident = SecurityIncident(
                    incident_id=f"data_exfiltration_{row.user_id}_{int(row.first_export.timestamp())}",
                    incident_type='data_exfiltration',
                    severity=severity,
                    description=f"Potential data exfiltration: {row.export_count} data exports by user '{row.username}' from IP {row.source_ip}",
                    start_time=row.first_export,
                    end_time=row.last_export,
                    affected_users=[row.username] if row.username else [],
                    indicators=[
                        {
                            'type': 'bulk_data_export',
                            'count': row.export_count,
                            'source_ip': str(row.source_ip),
                            'time_window_seconds': time_window,
                            'resource_types': list(set(row.resource_types)) if row.resource_types else []
                        }
                    ],
                    recommendations=[
                        f"Investigate data exports by user {row.username}",
                        f"Review access from IP {row.source_ip}",
                        "Implement data loss prevention (DLP) controls",
                        "Require approval for bulk data exports",
                        "Monitor for unauthorized data access"
                    ]
                )
                incidents.append(incident)
        
        return incidents
    
    async def _detect_suspicious_access_patterns(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[SecurityIncident]:
        """Detect suspicious access patterns."""
        
        incidents = []
        
        # Detect access from unusual locations (multiple IPs for same user)
        user_ips = await self.session.execute(
            select(
                AuditLog.user_id,
                AuditLog.username,
                func.array_agg(func.distinct(AuditLog.source_ip)).label('source_ips'),
                func.count(func.distinct(AuditLog.source_ip)).label('ip_count')
            ).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date,
                    AuditLog.source_ip.isnot(None)
                )
            ).group_by(AuditLog.user_id, AuditLog.username)
            .having(func.count(func.distinct(AuditLog.source_ip)) >= 5)  # 5+ different IPs
        )
        
        for row in user_ips:
            incident = SecurityIncident(
                incident_id=f"suspicious_access_{row.user_id}_{int(start_date.timestamp())}",
                incident_type='suspicious_access',
                severity='medium',
                description=f"Suspicious access pattern: User '{row.username}' accessed from {row.ip_count} different IP addresses",
                start_time=start_date,
                end_time=end_date,
                affected_users=[row.username] if row.username else [],
                indicators=[
                    {
                        'type': 'multiple_source_ips',
                        'ip_count': row.ip_count,
                        'source_ips': [str(ip) for ip in row.source_ips if ip]
                    }
                ],
                recommendations=[
                    f"Verify legitimate access for user {row.username}",
                    "Implement geolocation-based access controls",
                    "Require additional authentication for new locations",
                    "Monitor for account compromise"
                ]
            )
            incidents.append(incident)
        
        return incidents
    
    async def _detect_system_abuse(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[SecurityIncident]:
        """Detect system abuse patterns."""
        
        incidents = []
        
        # Detect excessive API usage
        api_usage = await self.session.execute(
            select(
                AuditLog.user_id,
                AuditLog.username,
                AuditLog.source_ip,
                func.count(AuditLog.id).label('request_count'),
                func.min(AuditLog.timestamp).label('first_request'),
                func.max(AuditLog.timestamp).label('last_request')
            ).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date,
                    AuditLog.action.like('%api%')
                )
            ).group_by(AuditLog.user_id, AuditLog.username, AuditLog.source_ip)
            .having(func.count(AuditLog.id) >= 1000)  # 1000+ API requests
            .order_by(desc('request_count'))
        )
        
        for row in api_usage:
            time_window = (row.last_request - row.first_request).total_seconds()
            requests_per_minute = row.request_count / (time_window / 60) if time_window > 0 else row.request_count
            
            if requests_per_minute >= 10:  # 10+ requests per minute
                severity = 'high' if requests_per_minute >= 50 else 'medium'
                
                incident = SecurityIncident(
                    incident_id=f"system_abuse_{row.user_id}_{int(row.first_request.timestamp())}",
                    incident_type='system_abuse',
                    severity=severity,
                    description=f"Excessive API usage: {row.request_count} requests ({requests_per_minute:.1f}/min) by user '{row.username}' from IP {row.source_ip}",
                    start_time=row.first_request,
                    end_time=row.last_request,
                    affected_users=[row.username] if row.username else [],
                    indicators=[
                        {
                            'type': 'excessive_api_usage',
                            'request_count': row.request_count,
                            'requests_per_minute': round(requests_per_minute, 2),
                            'source_ip': str(row.source_ip),
                            'time_window_seconds': time_window
                        }
                    ],
                    recommendations=[
                        f"Investigate API usage by user {row.username}",
                        "Implement rate limiting for API endpoints",
                        "Monitor for automated/bot activity",
                        "Review API access patterns"
                    ]
                )
                incidents.append(incident)
        
        return incidents
    
    async def _detect_anomalous_behavior(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[SecurityIncident]:
        """Detect anomalous user behavior patterns."""
        
        incidents = []
        
        # Detect unusual activity times (outside normal business hours)
        unusual_times = await self.session.execute(
            select(
                AuditLog.user_id,
                AuditLog.username,
                func.count(AuditLog.id).label('activity_count'),
                func.min(AuditLog.timestamp).label('first_activity'),
                func.max(AuditLog.timestamp).label('last_activity')
            ).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date,
                    or_(
                        func.extract('hour', AuditLog.timestamp) < 6,  # Before 6 AM
                        func.extract('hour', AuditLog.timestamp) > 22,  # After 10 PM
                        func.extract('dow', AuditLog.timestamp).in_([0, 6])  # Weekends
                    )
                )
            ).group_by(AuditLog.user_id, AuditLog.username)
            .having(func.count(AuditLog.id) >= 20)  # 20+ activities outside hours
            .order_by(desc('activity_count'))
        )
        
        for row in unusual_times:
            incident = SecurityIncident(
                incident_id=f"anomalous_behavior_{row.user_id}_{int(row.first_activity.timestamp())}",
                incident_type='anomalous_behavior',
                severity='medium',
                description=f"Unusual activity timing: {row.activity_count} activities outside normal business hours by user '{row.username}'",
                start_time=row.first_activity,
                end_time=row.last_activity,
                affected_users=[row.username] if row.username else [],
                indicators=[
                    {
                        'type': 'unusual_activity_times',
                        'activity_count': row.activity_count,
                        'period': f"{row.first_activity.isoformat()} to {row.last_activity.isoformat()}"
                    }
                ],
                recommendations=[
                    f"Verify legitimate activity for user {row.username}",
                    "Review activity patterns for anomalies",
                    "Implement time-based access controls",
                    "Monitor for account compromise"
                ]
            )
            incidents.append(incident)
        
        return incidents
    
    async def investigate_user_activity(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Conduct detailed investigation of a specific user's activity.
        
        Args:
            user_id: User ID to investigate
            start_date: Start date for investigation
            end_date: End date for investigation
            
        Returns:
            Comprehensive user activity analysis
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Get user information
        user_result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError(f"User with ID {user_id} not found")
        
        # Get all audit logs for the user
        user_logs = await self.session.execute(
            select(AuditLog).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.user_id == user_id,
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date
                )
            ).order_by(AuditLog.timestamp)
        )
        logs = user_logs.scalars().all()
        
        # Analyze activity patterns
        analysis = {
            'user_info': {
                'user_id': str(user.id),
                'username': user.username,
                'email': user.email,
                'created_at': user.created_at.isoformat() if user.created_at else None
            },
            'investigation_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_events': len(logs)
            },
            'activity_summary': self._analyze_activity_summary(logs),
            'temporal_patterns': self._analyze_temporal_patterns(logs),
            'access_patterns': self._analyze_access_patterns(logs),
            'security_events': self._analyze_security_events(logs),
            'resource_access': self._analyze_resource_access(logs),
            'risk_indicators': self._identify_risk_indicators(logs),
            'timeline': self._create_activity_timeline(logs)
        }
        
        return analysis
    
    def _analyze_activity_summary(self, logs: List[AuditLog]) -> Dict[str, Any]:
        """Analyze overall activity summary."""
        
        event_types = Counter(log.event_type.value for log in logs)
        outcomes = Counter(log.outcome.value for log in logs)
        severities = Counter(log.severity.value for log in logs)
        
        return {
            'total_events': len(logs),
            'event_types': dict(event_types),
            'outcomes': dict(outcomes),
            'severities': dict(severities),
            'success_rate': outcomes.get('success', 0) / len(logs) if logs else 0,
            'first_activity': logs[0].timestamp.isoformat() if logs else None,
            'last_activity': logs[-1].timestamp.isoformat() if logs else None
        }
    
    def _analyze_temporal_patterns(self, logs: List[AuditLog]) -> Dict[str, Any]:
        """Analyze temporal activity patterns."""
        
        if not logs:
            return {}
        
        # Activity by hour of day
        hours = Counter(log.timestamp.hour for log in logs)
        
        # Activity by day of week
        days = Counter(log.timestamp.weekday() for log in logs)
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        days_named = {day_names[day]: count for day, count in days.items()}
        
        # Activity by date
        dates = Counter(log.timestamp.date() for log in logs)
        dates_str = {date.isoformat(): count for date, count in dates.items()}
        
        return {
            'activity_by_hour': dict(hours),
            'activity_by_day': days_named,
            'activity_by_date': dates_str,
            'peak_hour': max(hours, key=hours.get) if hours else None,
            'peak_day': day_names[max(days, key=days.get)] if days else None
        }
    
    def _analyze_access_patterns(self, logs: List[AuditLog]) -> Dict[str, Any]:
        """Analyze access patterns and locations."""
        
        source_ips = Counter(str(log.source_ip) for log in logs if log.source_ip)
        user_agents = Counter(log.user_agent for log in logs if log.user_agent)
        
        return {
            'unique_source_ips': len(source_ips),
            'source_ips': dict(source_ips.most_common(10)),
            'unique_user_agents': len(user_agents),
            'user_agents': dict(user_agents.most_common(5))
        }
    
    def _analyze_security_events(self, logs: List[AuditLog]) -> Dict[str, Any]:
        """Analyze security-related events."""
        
        security_event_types = {
            AuditEventType.USER_LOGIN_FAILED,
            AuditEventType.ACCESS_DENIED,
            AuditEventType.SECURITY_VIOLATION,
            AuditEventType.GUARDRAIL_TRIGGERED,
            AuditEventType.SUSPICIOUS_ACTIVITY
        }
        
        security_logs = [log for log in logs if log.event_type in security_event_types]
        failed_logs = [log for log in logs if log.outcome == AuditOutcome.FAILURE]
        
        return {
            'security_events_count': len(security_logs),
            'failed_events_count': len(failed_logs),
            'security_events': [
                {
                    'timestamp': log.timestamp.isoformat(),
                    'event_type': log.event_type.value,
                    'message': log.message,
                    'source_ip': str(log.source_ip) if log.source_ip else None
                }
                for log in security_logs[-10:]  # Last 10 security events
            ]
        }
    
    def _analyze_resource_access(self, logs: List[AuditLog]) -> Dict[str, Any]:
        """Analyze resource access patterns."""
        
        resource_types = Counter(log.resource_type for log in logs if log.resource_type)
        actions = Counter(log.action for log in logs)
        
        return {
            'resource_types_accessed': dict(resource_types),
            'actions_performed': dict(actions.most_common(10)),
            'unique_resources': len(set(log.resource_id for log in logs if log.resource_id))
        }
    
    def _identify_risk_indicators(self, logs: List[AuditLog]) -> List[Dict[str, Any]]:
        """Identify risk indicators in user activity."""
        
        indicators = []
        
        # High failure rate
        total_events = len(logs)
        failed_events = len([log for log in logs if log.outcome == AuditOutcome.FAILURE])
        if total_events > 0 and failed_events / total_events > 0.2:  # >20% failure rate
            indicators.append({
                'type': 'high_failure_rate',
                'severity': 'medium',
                'description': f'High failure rate: {failed_events}/{total_events} ({failed_events/total_events:.1%})',
                'recommendation': 'Investigate causes of frequent failures'
            })
        
        # Multiple IP addresses
        unique_ips = len(set(str(log.source_ip) for log in logs if log.source_ip))
        if unique_ips >= 5:
            indicators.append({
                'type': 'multiple_locations',
                'severity': 'medium',
                'description': f'Access from {unique_ips} different IP addresses',
                'recommendation': 'Verify legitimate access from multiple locations'
            })
        
        # Unusual activity times
        unusual_hours = len([log for log in logs if log.timestamp.hour < 6 or log.timestamp.hour > 22])
        if unusual_hours > 10:
            indicators.append({
                'type': 'unusual_hours',
                'severity': 'low',
                'description': f'{unusual_hours} activities outside normal business hours',
                'recommendation': 'Review activity during off-hours'
            })
        
        return indicators
    
    def _create_activity_timeline(self, logs: List[AuditLog]) -> List[Dict[str, Any]]:
        """Create a timeline of significant activities."""
        
        # Focus on significant events
        significant_event_types = {
            AuditEventType.USER_LOGIN,
            AuditEventType.USER_LOGIN_FAILED,
            AuditEventType.AGENT_CREATED,
            AuditEventType.AGENT_DELETED,
            AuditEventType.WORKFLOW_EXECUTED,
            AuditEventType.DATA_EXPORTED,
            AuditEventType.ROLE_ASSIGNED,
            AuditEventType.ACCESS_DENIED,
            AuditEventType.SECURITY_VIOLATION
        }
        
        significant_logs = [log for log in logs if log.event_type in significant_event_types]
        
        timeline = []
        for log in significant_logs[-50:]:  # Last 50 significant events
            timeline.append({
                'timestamp': log.timestamp.isoformat(),
                'event_type': log.event_type.value,
                'action': log.action,
                'message': log.message,
                'outcome': log.outcome.value,
                'severity': log.severity.value,
                'source_ip': str(log.source_ip) if log.source_ip else None,
                'resource_type': log.resource_type,
                'resource_id': str(log.resource_id) if log.resource_id else None
            })
        
        return timeline