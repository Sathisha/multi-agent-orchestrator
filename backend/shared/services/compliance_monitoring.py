"""Compliance monitoring service for continuous compliance assessment and alerting."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from enum import Enum
from dataclasses import dataclass

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit import AuditLog, AuditEventType, AuditSeverity, AuditOutcome
from ..models.user import User
from .base import BaseService
from .audit import AuditService


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""
    
    GDPR = "gdpr"
    SOC2 = "soc2"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    NIST = "nist"


class ViolationSeverity(str, Enum):
    """Compliance violation severity levels."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ComplianceViolation:
    """Represents a compliance violation."""
    
    violation_id: str
    framework: ComplianceFramework
    rule_id: str
    rule_name: str
    severity: ViolationSeverity
    description: str
    detected_at: datetime
    affected_events: List[str]
    affected_users: List[str]
    affected_resources: List[str]
    remediation_steps: List[str]
    auto_remediation_available: bool = False


@dataclass
class ComplianceRule:
    """Defines a compliance rule."""
    
    rule_id: str
    framework: ComplianceFramework
    name: str
    description: str
    severity: ViolationSeverity
    check_function: str
    parameters: Dict[str, Any]
    remediation_steps: List[str]
    auto_remediation: Optional[str] = None


class ComplianceMonitoringService(BaseService):
    """Service for continuous compliance monitoring and violation detection."""
    
    def __init__(self, session: AsyncSession, tenant_id: str, user_id: Optional[str] = None):
        super().__init__(session, tenant_id, user_id)
        self.audit_service = AuditService(session, tenant_id, user_id)
        self.compliance_rules = self._initialize_compliance_rules()
    
    def _initialize_compliance_rules(self) -> List[ComplianceRule]:
        """Initialize compliance rules for different frameworks."""
        
        rules = []
        
        # GDPR Rules
        rules.extend([
            ComplianceRule(
                rule_id="GDPR-001",
                framework=ComplianceFramework.GDPR,
                name="Data Access Logging",
                description="All personal data access must be logged",
                severity=ViolationSeverity.HIGH,
                check_function="check_data_access_logging",
                parameters={"required_event_types": ["DATA_ACCESSED", "DATA_EXPORTED"]},
                remediation_steps=[
                    "Ensure all data access operations are properly logged",
                    "Review data access patterns for compliance",
                    "Implement comprehensive audit logging"
                ]
            ),
            ComplianceRule(
                rule_id="GDPR-002",
                framework=ComplianceFramework.GDPR,
                name="Data Export Approval",
                description="Data exports must be approved and logged",
                severity=ViolationSeverity.CRITICAL,
                check_function="check_data_export_approval",
                parameters={"max_exports_per_hour": 5},
                remediation_steps=[
                    "Implement approval workflow for data exports",
                    "Review unauthorized data export attempts",
                    "Strengthen data loss prevention controls"
                ]
            ),
            ComplianceRule(
                rule_id="GDPR-003",
                framework=ComplianceFramework.GDPR,
                name="Data Retention Compliance",
                description="Data must be retained according to retention policies",
                severity=ViolationSeverity.MEDIUM,
                check_function="check_data_retention",
                parameters={"max_retention_days": 2555},  # 7 years
                remediation_steps=[
                    "Review data retention policies",
                    "Implement automated data purging",
                    "Document data retention decisions"
                ]
            )
        ])
        
        # SOC 2 Rules
        rules.extend([
            ComplianceRule(
                rule_id="SOC2-001",
                framework=ComplianceFramework.SOC2,
                name="Access Control Monitoring",
                description="All access control changes must be logged and approved",
                severity=ViolationSeverity.HIGH,
                check_function="check_access_control_changes",
                parameters={"monitor_events": ["ROLE_ASSIGNED", "PERMISSION_GRANTED", "ROLE_REVOKED"]},
                remediation_steps=[
                    "Review access control changes",
                    "Implement approval workflow for privilege changes",
                    "Monitor for unauthorized access escalation"
                ]
            ),
            ComplianceRule(
                rule_id="SOC2-002",
                framework=ComplianceFramework.SOC2,
                name="Security Incident Response",
                description="Security incidents must be detected and responded to promptly",
                severity=ViolationSeverity.CRITICAL,
                check_function="check_security_incident_response",
                parameters={"max_response_time_hours": 4},
                remediation_steps=[
                    "Implement automated security incident detection",
                    "Establish incident response procedures",
                    "Train staff on incident response protocols"
                ]
            ),
            ComplianceRule(
                rule_id="SOC2-003",
                framework=ComplianceFramework.SOC2,
                name="System Availability Monitoring",
                description="System availability must be monitored and maintained",
                severity=ViolationSeverity.MEDIUM,
                check_function="check_system_availability",
                parameters={"min_uptime_percentage": 99.5},
                remediation_steps=[
                    "Implement comprehensive system monitoring",
                    "Establish availability SLAs",
                    "Create redundancy and failover procedures"
                ]
            )
        ])
        
        # ISO 27001 Rules
        rules.extend([
            ComplianceRule(
                rule_id="ISO27001-001",
                framework=ComplianceFramework.ISO_27001,
                name="Information Security Event Logging",
                description="All information security events must be logged",
                severity=ViolationSeverity.HIGH,
                check_function="check_security_event_logging",
                parameters={"required_events": ["ACCESS_DENIED", "SECURITY_VIOLATION", "GUARDRAIL_TRIGGERED"]},
                remediation_steps=[
                    "Ensure comprehensive security event logging",
                    "Review security event detection capabilities",
                    "Implement security information and event management (SIEM)"
                ]
            ),
            ComplianceRule(
                rule_id="ISO27001-002",
                framework=ComplianceFramework.ISO_27001,
                name="Access Review Requirements",
                description="User access must be reviewed regularly",
                severity=ViolationSeverity.MEDIUM,
                check_function="check_access_review",
                parameters={"review_frequency_days": 90},
                remediation_steps=[
                    "Implement regular access reviews",
                    "Document access review procedures",
                    "Remove unnecessary access privileges"
                ]
            )
        ])
        
        return rules
    
    async def run_compliance_check(
        self,
        frameworks: Optional[List[ComplianceFramework]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ComplianceViolation]:
        """
        Run compliance checks for specified frameworks.
        
        Args:
            frameworks: List of compliance frameworks to check
            start_date: Start date for compliance check
            end_date: End date for compliance check
            
        Returns:
            List of detected compliance violations
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=1)
        if not end_date:
            end_date = datetime.utcnow()
        
        violations = []
        
        # Filter rules by frameworks
        rules_to_check = self.compliance_rules
        if frameworks:
            rules_to_check = [rule for rule in self.compliance_rules if rule.framework in frameworks]
        
        # Run each compliance rule check
        for rule in rules_to_check:
            try:
                rule_violations = await self._run_rule_check(rule, start_date, end_date)
                violations.extend(rule_violations)
            except Exception as e:
                print(f"Error checking compliance rule {rule.rule_id}: {e}")
        
        # Log compliance check execution
        await self.audit_service.log_event(
            event_type=AuditEventType.SYSTEM_STARTED,  # Using closest available event type
            action="compliance_check_executed",
            message=f"Compliance check completed: {len(violations)} violations found",
            outcome=AuditOutcome.SUCCESS,
            severity=AuditSeverity.MEDIUM,
            details={
                'frameworks_checked': [f.value for f in frameworks] if frameworks else 'all',
                'rules_checked': len(rules_to_check),
                'violations_found': len(violations),
                'period': f"{start_date.isoformat()} to {end_date.isoformat()}"
            },
            compliance_tags=['compliance_check', 'automated_monitoring']
        )
        
        return violations
    
    async def _run_rule_check(
        self,
        rule: ComplianceRule,
        start_date: datetime,
        end_date: datetime
    ) -> List[ComplianceViolation]:
        """Run a specific compliance rule check."""
        
        check_method = getattr(self, rule.check_function, None)
        if not check_method:
            print(f"Check method {rule.check_function} not found for rule {rule.rule_id}")
            return []
        
        return await check_method(rule, start_date, end_date)
    
    async def check_data_access_logging(
        self,
        rule: ComplianceRule,
        start_date: datetime,
        end_date: datetime
    ) -> List[ComplianceViolation]:
        """Check that all data access is properly logged."""
        
        violations = []
        required_events = rule.parameters.get('required_event_types', [])
        
        # Check for missing data access logs
        # This is a simplified check - in practice, you'd compare against expected access patterns
        data_access_count = await self.session.execute(
            select(func.count(AuditLog.id)).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.event_type.in_([AuditEventType(event) for event in required_events]),
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date
                )
            )
        )
        count = data_access_count.scalar()
        
        # If no data access events are logged, it might indicate missing logging
        if count == 0:
            violations.append(ComplianceViolation(
                violation_id=f"{rule.rule_id}_{int(start_date.timestamp())}",
                framework=rule.framework,
                rule_id=rule.rule_id,
                rule_name=rule.name,
                severity=rule.severity,
                description="No data access events logged during the monitoring period",
                detected_at=datetime.utcnow(),
                affected_events=[],
                affected_users=[],
                affected_resources=[],
                remediation_steps=rule.remediation_steps
            ))
        
        return violations
    
    async def check_data_export_approval(
        self,
        rule: ComplianceRule,
        start_date: datetime,
        end_date: datetime
    ) -> List[ComplianceViolation]:
        """Check for unauthorized data exports."""
        
        violations = []
        max_exports = rule.parameters.get('max_exports_per_hour', 5)
        
        # Check for excessive data exports
        export_events = await self.session.execute(
            select(
                AuditLog.user_id,
                AuditLog.username,
                func.count(AuditLog.id).label('export_count'),
                func.array_agg(AuditLog.event_id).label('event_ids')
            ).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.event_type == AuditEventType.DATA_EXPORTED,
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date
                )
            ).group_by(AuditLog.user_id, AuditLog.username)
            .having(func.count(AuditLog.id) > max_exports)
        )
        
        for row in export_events:
            violations.append(ComplianceViolation(
                violation_id=f"{rule.rule_id}_{row.user_id}_{int(start_date.timestamp())}",
                framework=rule.framework,
                rule_id=rule.rule_id,
                rule_name=rule.name,
                severity=rule.severity,
                description=f"User {row.username} performed {row.export_count} data exports (limit: {max_exports})",
                detected_at=datetime.utcnow(),
                affected_events=row.event_ids,
                affected_users=[row.username] if row.username else [],
                affected_resources=[],
                remediation_steps=rule.remediation_steps
            ))
        
        return violations
    
    async def check_data_retention(
        self,
        rule: ComplianceRule,
        start_date: datetime,
        end_date: datetime
    ) -> List[ComplianceViolation]:
        """Check data retention compliance."""
        
        violations = []
        max_retention_days = rule.parameters.get('max_retention_days', 2555)
        
        # Check for audit logs that should have been purged
        retention_cutoff = datetime.utcnow() - timedelta(days=max_retention_days)
        
        old_logs = await self.session.execute(
            select(func.count(AuditLog.id)).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.timestamp < retention_cutoff,
                    or_(
                        AuditLog.retention_date.is_(None),
                        AuditLog.retention_date < datetime.utcnow()
                    )
                )
            )
        )
        old_count = old_logs.scalar()
        
        if old_count > 0:
            violations.append(ComplianceViolation(
                violation_id=f"{rule.rule_id}_{int(start_date.timestamp())}",
                framework=rule.framework,
                rule_id=rule.rule_id,
                rule_name=rule.name,
                severity=rule.severity,
                description=f"{old_count} audit logs exceed retention period of {max_retention_days} days",
                detected_at=datetime.utcnow(),
                affected_events=[],
                affected_users=[],
                affected_resources=[],
                remediation_steps=rule.remediation_steps
            ))
        
        return violations
    
    async def check_access_control_changes(
        self,
        rule: ComplianceRule,
        start_date: datetime,
        end_date: datetime
    ) -> List[ComplianceViolation]:
        """Check access control changes for proper approval."""
        
        violations = []
        monitor_events = rule.parameters.get('monitor_events', [])
        
        # Check for access control changes without proper approval context
        access_changes = await self.session.execute(
            select(AuditLog).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.event_type.in_([AuditEventType(event) for event in monitor_events]),
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date
                )
            )
        )
        
        for log in access_changes.scalars():
            # Check if the change has approval information in details
            if not log.details or 'approved_by' not in log.details:
                violations.append(ComplianceViolation(
                    violation_id=f"{rule.rule_id}_{log.event_id}",
                    framework=rule.framework,
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    description=f"Access control change without approval: {log.message}",
                    detected_at=datetime.utcnow(),
                    affected_events=[log.event_id],
                    affected_users=[log.username] if log.username else [],
                    affected_resources=[log.resource_type] if log.resource_type else [],
                    remediation_steps=rule.remediation_steps
                ))
        
        return violations
    
    async def check_security_incident_response(
        self,
        rule: ComplianceRule,
        start_date: datetime,
        end_date: datetime
    ) -> List[ComplianceViolation]:
        """Check security incident response times."""
        
        violations = []
        max_response_hours = rule.parameters.get('max_response_time_hours', 4)
        
        # Find security incidents
        security_incidents = await self.session.execute(
            select(AuditLog).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.event_type.in_([
                        AuditEventType.SECURITY_VIOLATION,
                        AuditEventType.ACCESS_DENIED,
                        AuditEventType.GUARDRAIL_TRIGGERED
                    ]),
                    AuditLog.severity.in_([AuditSeverity.HIGH, AuditSeverity.CRITICAL]),
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date
                )
            ).order_by(AuditLog.timestamp)
        )
        
        for incident in security_incidents.scalars():
            # Check if there was a response within the required time
            response_cutoff = incident.timestamp + timedelta(hours=max_response_hours)
            
            # Look for response actions (this is simplified - in practice, you'd have specific response event types)
            response_check = await self.session.execute(
                select(func.count(AuditLog.id)).where(
                    and_(
                        AuditLog.tenant_id == self.tenant_id,
                        AuditLog.correlation_id == incident.correlation_id,
                        AuditLog.timestamp > incident.timestamp,
                        AuditLog.timestamp <= response_cutoff,
                        AuditLog.action.like('%response%')
                    )
                )
            )
            response_count = response_check.scalar()
            
            if response_count == 0:
                violations.append(ComplianceViolation(
                    violation_id=f"{rule.rule_id}_{incident.event_id}",
                    framework=rule.framework,
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    description=f"Security incident without timely response: {incident.message}",
                    detected_at=datetime.utcnow(),
                    affected_events=[incident.event_id],
                    affected_users=[incident.username] if incident.username else [],
                    affected_resources=[incident.resource_type] if incident.resource_type else [],
                    remediation_steps=rule.remediation_steps
                ))
        
        return violations
    
    async def check_system_availability(
        self,
        rule: ComplianceRule,
        start_date: datetime,
        end_date: datetime
    ) -> List[ComplianceViolation]:
        """Check system availability compliance."""
        
        violations = []
        min_uptime = rule.parameters.get('min_uptime_percentage', 99.5)
        
        # Calculate system downtime based on system events
        downtime_events = await self.session.execute(
            select(
                AuditLog.timestamp,
                AuditLog.event_type
            ).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.event_type.in_([
                        AuditEventType.SYSTEM_STOPPED,
                        AuditEventType.SYSTEM_STARTED
                    ]),
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date
                )
            ).order_by(AuditLog.timestamp)
        )
        
        events = downtime_events.all()
        total_downtime = timedelta()
        downtime_start = None
        
        for event in events:
            if event.event_type == AuditEventType.SYSTEM_STOPPED:
                downtime_start = event.timestamp
            elif event.event_type == AuditEventType.SYSTEM_STARTED and downtime_start:
                total_downtime += event.timestamp - downtime_start
                downtime_start = None
        
        # Calculate uptime percentage
        total_period = end_date - start_date
        uptime_percentage = ((total_period - total_downtime) / total_period) * 100
        
        if uptime_percentage < min_uptime:
            violations.append(ComplianceViolation(
                violation_id=f"{rule.rule_id}_{int(start_date.timestamp())}",
                framework=rule.framework,
                rule_id=rule.rule_id,
                rule_name=rule.name,
                severity=rule.severity,
                description=f"System availability {uptime_percentage:.2f}% below required {min_uptime}%",
                detected_at=datetime.utcnow(),
                affected_events=[],
                affected_users=[],
                affected_resources=['system'],
                remediation_steps=rule.remediation_steps
            ))
        
        return violations
    
    async def check_security_event_logging(
        self,
        rule: ComplianceRule,
        start_date: datetime,
        end_date: datetime
    ) -> List[ComplianceViolation]:
        """Check that security events are properly logged."""
        
        violations = []
        required_events = rule.parameters.get('required_events', [])
        
        # Check for presence of security event logging
        security_event_count = await self.session.execute(
            select(func.count(AuditLog.id)).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.event_type.in_([AuditEventType(event) for event in required_events]),
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date
                )
            )
        )
        count = security_event_count.scalar()
        
        # This is a simplified check - in practice, you'd have more sophisticated detection
        # For now, we'll just ensure that security event logging is active
        if count == 0:
            violations.append(ComplianceViolation(
                violation_id=f"{rule.rule_id}_{int(start_date.timestamp())}",
                framework=rule.framework,
                rule_id=rule.rule_id,
                rule_name=rule.name,
                severity=rule.severity,
                description="No security events logged during monitoring period",
                detected_at=datetime.utcnow(),
                affected_events=[],
                affected_users=[],
                affected_resources=[],
                remediation_steps=rule.remediation_steps
            ))
        
        return violations
    
    async def check_access_review(
        self,
        rule: ComplianceRule,
        start_date: datetime,
        end_date: datetime
    ) -> List[ComplianceViolation]:
        """Check access review compliance."""
        
        violations = []
        review_frequency_days = rule.parameters.get('review_frequency_days', 90)
        
        # Check for access review events
        review_cutoff = datetime.utcnow() - timedelta(days=review_frequency_days)
        
        recent_reviews = await self.session.execute(
            select(func.count(AuditLog.id)).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.action.like('%access_review%'),
                    AuditLog.timestamp >= review_cutoff
                )
            )
        )
        review_count = recent_reviews.scalar()
        
        if review_count == 0:
            violations.append(ComplianceViolation(
                violation_id=f"{rule.rule_id}_{int(start_date.timestamp())}",
                framework=rule.framework,
                rule_id=rule.rule_id,
                rule_name=rule.name,
                severity=rule.severity,
                description=f"No access reviews conducted in the last {review_frequency_days} days",
                detected_at=datetime.utcnow(),
                affected_events=[],
                affected_users=[],
                affected_resources=[],
                remediation_steps=rule.remediation_steps
            ))
        
        return violations
    
    async def generate_compliance_dashboard(
        self,
        frameworks: Optional[List[ComplianceFramework]] = None
    ) -> Dict[str, Any]:
        """Generate a compliance dashboard with current status."""
        
        # Run compliance checks for the last 24 hours
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        violations = await self.run_compliance_check(frameworks, start_date, end_date)
        
        # Organize violations by framework and severity
        framework_status = {}
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
        
        for violation in violations:
            framework = violation.framework.value
            if framework not in framework_status:
                framework_status[framework] = {
                    'total_violations': 0,
                    'critical': 0,
                    'high': 0,
                    'medium': 0,
                    'low': 0,
                    'info': 0
                }
            
            framework_status[framework]['total_violations'] += 1
            framework_status[framework][violation.severity.value] += 1
            severity_counts[violation.severity.value] += 1
        
        # Calculate compliance scores
        total_rules = len([rule for rule in self.compliance_rules if not frameworks or rule.framework in frameworks])
        total_violations = len(violations)
        compliance_score = max(0, (total_rules - total_violations) / total_rules * 100) if total_rules > 0 else 100
        
        return {
            'dashboard_generated_at': datetime.utcnow().isoformat(),
            'monitoring_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'overall_compliance_score': round(compliance_score, 2),
            'total_violations': total_violations,
            'severity_breakdown': severity_counts,
            'framework_status': framework_status,
            'recent_violations': [
                {
                    'violation_id': v.violation_id,
                    'framework': v.framework.value,
                    'rule_name': v.rule_name,
                    'severity': v.severity.value,
                    'description': v.description,
                    'detected_at': v.detected_at.isoformat()
                }
                for v in violations[-10:]  # Last 10 violations
            ],
            'recommendations': self._generate_compliance_recommendations(violations)
        }
    
    def _generate_compliance_recommendations(self, violations: List[ComplianceViolation]) -> List[str]:
        """Generate compliance recommendations based on violations."""
        
        recommendations = set()
        
        # Count violation types
        violation_types = {}
        for violation in violations:
            rule_id = violation.rule_id
            violation_types[rule_id] = violation_types.get(rule_id, 0) + 1
        
        # Generate recommendations based on most common violations
        for rule_id, count in sorted(violation_types.items(), key=lambda x: x[1], reverse=True)[:5]:
            # Find the rule to get its remediation steps
            rule = next((r for r in self.compliance_rules if r.rule_id == rule_id), None)
            if rule:
                recommendations.update(rule.remediation_steps)
        
        return list(recommendations)[:10]  # Top 10 recommendations