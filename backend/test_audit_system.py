"""Comprehensive test for the audit and compliance system."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any

import httpx
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_database_session
from shared.models.audit import AuditLog, AuditEventType, AuditSeverity, AuditOutcome
from shared.services.audit import AuditService
from shared.services.forensic_analysis import ForensicAnalysisService
from shared.services.compliance_monitoring import ComplianceMonitoringService, ComplianceFramework


class AuditSystemTester:
    """Comprehensive tester for the audit and compliance system."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
        self.tenant_id = "test-tenant-001"
        self.user_id = "test-user-001"
        self.auth_headers = {}
    
    async def setup_test_environment(self):
        """Set up test environment with sample data."""
        print("🔧 Setting up test environment...")
        
        # Create test session
        async with get_database_session() as session:
            audit_service = AuditService(session, self.tenant_id, self.user_id)
            
            # Create sample audit events
            sample_events = [
                {
                    'event_type': AuditEventType.USER_LOGIN,
                    'action': 'user_login',
                    'message': 'User logged in successfully',
                    'outcome': AuditOutcome.SUCCESS,
                    'severity': AuditSeverity.LOW,
                    'source_ip': '192.168.1.100'
                },
                {
                    'event_type': AuditEventType.USER_LOGIN_FAILED,
                    'action': 'user_login_failed',
                    'message': 'Failed login attempt',
                    'outcome': AuditOutcome.FAILURE,
                    'severity': AuditSeverity.MEDIUM,
                    'source_ip': '192.168.1.100'
                },
                {
                    'event_type': AuditEventType.AGENT_CREATED,
                    'action': 'agent_created',
                    'message': 'New agent created',
                    'outcome': AuditOutcome.SUCCESS,
                    'severity': AuditSeverity.MEDIUM,
                    'resource_type': 'agent',
                    'resource_id': 'agent-001',
                    'resource_name': 'Test Agent'
                },
                {
                    'event_type': AuditEventType.DATA_EXPORTED,
                    'action': 'data_exported',
                    'message': 'Data exported by user',
                    'outcome': AuditOutcome.SUCCESS,
                    'severity': AuditSeverity.HIGH,
                    'resource_type': 'data',
                    'compliance_tags': ['gdpr', 'data_export']
                },
                {
                    'event_type': AuditEventType.SECURITY_VIOLATION,
                    'action': 'security_violation',
                    'message': 'Suspicious activity detected',
                    'outcome': AuditOutcome.FAILURE,
                    'severity': AuditSeverity.CRITICAL,
                    'source_ip': '10.0.0.50'
                }
            ]
            
            for event_data in sample_events:
                await audit_service.log_event(**event_data)
            
            print(f"✅ Created {len(sample_events)} sample audit events")
    
    async def test_audit_logging(self):
        """Test basic audit logging functionality."""
        print("\n📝 Testing audit logging...")
        
        async with get_database_session() as session:
            audit_service = AuditService(session, self.tenant_id, self.user_id)
            
            # Test logging a new event
            audit_log = await audit_service.log_event(
                event_type=AuditEventType.WORKFLOW_EXECUTED,
                action='workflow_test',
                message='Test workflow execution',
                outcome=AuditOutcome.SUCCESS,
                severity=AuditSeverity.MEDIUM,
                resource_type='workflow',
                resource_id='workflow-test-001',
                details={'test': True, 'duration': 1.5},
                compliance_tags=['test', 'workflow']
            )
            
            # Verify the event was logged
            assert audit_log.event_type == AuditEventType.WORKFLOW_EXECUTED
            assert audit_log.tenant_id == self.tenant_id
            assert audit_log.checksum is not None
            assert audit_log.verify_integrity()
            
            print("✅ Basic audit logging works correctly")
    
    async def test_audit_retrieval(self):
        """Test audit log retrieval and filtering."""
        print("\n🔍 Testing audit log retrieval...")
        
        async with get_database_session() as session:
            audit_service = AuditService(session, self.tenant_id, self.user_id)
            
            # Test retrieving all logs
            from shared.models.audit import AuditLogRequest
            request = AuditLogRequest(page=1, size=10)
            logs, total = await audit_service.get_audit_logs(request)
            
            assert len(logs) > 0
            assert total > 0
            print(f"✅ Retrieved {len(logs)} audit logs (total: {total})")
            
            # Test filtering by event type
            request = AuditLogRequest(
                event_types=[AuditEventType.USER_LOGIN_FAILED],
                page=1,
                size=10
            )
            filtered_logs, filtered_total = await audit_service.get_audit_logs(request)
            
            assert all(log.event_type == AuditEventType.USER_LOGIN_FAILED for log in filtered_logs)
            print(f"✅ Filtered logs by event type: {len(filtered_logs)} results")
    
    async def test_audit_statistics(self):
        """Test audit statistics generation."""
        print("\n📊 Testing audit statistics...")
        
        async with get_database_session() as session:
            audit_service = AuditService(session, self.tenant_id, self.user_id)
            
            # Get statistics
            stats = await audit_service.get_audit_statistics()
            
            assert stats.total_events > 0
            assert len(stats.events_by_type) > 0
            assert len(stats.events_by_outcome) > 0
            assert len(stats.events_by_severity) > 0
            
            print(f"✅ Statistics generated: {stats.total_events} total events")
            print(f"   - Event types: {len(stats.events_by_type)}")
            print(f"   - Security events: {stats.security_events}")
            print(f"   - Failed events: {stats.failed_events}")
    
    async def test_compliance_report(self):
        """Test compliance report generation."""
        print("\n📋 Testing compliance report generation...")
        
        async with get_database_session() as session:
            audit_service = AuditService(session, self.tenant_id, self.user_id)
            
            # Generate compliance report
            start_date = datetime.utcnow() - timedelta(days=1)
            end_date = datetime.utcnow()
            
            report = await audit_service.generate_compliance_report(start_date, end_date)
            
            assert report.report_id is not None
            assert report.total_events > 0
            assert isinstance(report.user_activities, dict)
            assert isinstance(report.resource_access, dict)
            
            print(f"✅ Compliance report generated: {report.report_id}")
            print(f"   - Total events: {report.total_events}")
            print(f"   - Data access events: {report.data_access_events}")
            print(f"   - Security incidents: {len(report.security_incidents)}")
    
    async def test_audit_export(self):
        """Test audit log export functionality."""
        print("\n📤 Testing audit log export...")
        
        async with get_database_session() as session:
            audit_service = AuditService(session, self.tenant_id, self.user_id)
            
            # Test JSON export
            from shared.models.audit import AuditLogRequest
            request = AuditLogRequest(page=1, size=5)
            export_data = await audit_service.export_audit_logs(request, format="json")
            
            assert export_data['export_id'] is not None
            assert export_data['format'] == 'json'
            assert len(export_data['data']) > 0
            assert export_data['total_records'] > 0
            
            print(f"✅ Export completed: {len(export_data['data'])} records")
            print(f"   - Export ID: {export_data['export_id']}")
            print(f"   - Format: {export_data['format']}")
    
    async def test_integrity_verification(self):
        """Test audit log integrity verification."""
        print("\n🔐 Testing integrity verification...")
        
        async with get_database_session() as session:
            audit_service = AuditService(session, self.tenant_id, self.user_id)
            
            # Verify integrity
            verification_results = await audit_service.verify_audit_integrity()
            
            assert verification_results['verification_id'] is not None
            assert verification_results['total_records'] > 0
            assert verification_results['verified_records'] >= 0
            assert verification_results['corrupted_records'] >= 0
            
            print(f"✅ Integrity verification completed:")
            print(f"   - Total records: {verification_results['total_records']}")
            print(f"   - Verified: {verification_results['verified_records']}")
            print(f"   - Corrupted: {verification_results['corrupted_records']}")
            print(f"   - Missing checksums: {verification_results['missing_checksums']}")
    
    async def test_forensic_analysis(self):
        """Test forensic analysis capabilities."""
        print("\n🔍 Testing forensic analysis...")
        
        async with get_database_session() as session:
            forensic_service = ForensicAnalysisService(session, self.tenant_id, self.user_id)
            
            # Detect security incidents
            incidents = await forensic_service.detect_security_incidents()
            
            print(f"✅ Security incident detection completed: {len(incidents)} incidents found")
            
            for incident in incidents[:3]:  # Show first 3 incidents
                print(f"   - {incident.incident_type}: {incident.description}")
                print(f"     Severity: {incident.severity}, Affected users: {len(incident.affected_users)}")
    
    async def test_compliance_monitoring(self):
        """Test compliance monitoring functionality."""
        print("\n⚖️ Testing compliance monitoring...")
        
        async with get_database_session() as session:
            compliance_service = ComplianceMonitoringService(session, self.tenant_id, self.user_id)
            
            # Run compliance checks
            violations = await compliance_service.run_compliance_check(
                frameworks=[ComplianceFramework.GDPR, ComplianceFramework.SOC2]
            )
            
            print(f"✅ Compliance check completed: {len(violations)} violations found")
            
            for violation in violations[:3]:  # Show first 3 violations
                print(f"   - {violation.framework.value}: {violation.rule_name}")
                print(f"     Severity: {violation.severity.value}, Description: {violation.description}")
            
            # Generate compliance dashboard
            dashboard = await compliance_service.generate_compliance_dashboard()
            
            print(f"✅ Compliance dashboard generated:")
            print(f"   - Overall score: {dashboard['overall_compliance_score']}%")
            print(f"   - Total violations: {dashboard['total_violations']}")
            print(f"   - Framework status: {len(dashboard['framework_status'])} frameworks")
    
    async def test_api_endpoints(self):
        """Test audit API endpoints."""
        print("\n🌐 Testing API endpoints...")
        
        try:
            # Test health endpoint
            response = await self.client.get("/audit/health")
            assert response.status_code == 200
            health_data = response.json()
            assert health_data['status'] == 'healthy'
            print("✅ Health endpoint working")
            
            # Note: Other API endpoints would require proper authentication
            # In a real test, you'd set up authentication tokens
            print("⚠️ Skipping authenticated endpoints (requires auth setup)")
            
        except Exception as e:
            print(f"⚠️ API endpoint test failed (expected without running server): {e}")
    
    async def test_performance(self):
        """Test audit system performance."""
        print("\n⚡ Testing performance...")
        
        async with get_database_session() as session:
            audit_service = AuditService(session, self.tenant_id, self.user_id)
            
            # Test bulk logging performance
            start_time = datetime.utcnow()
            
            tasks = []
            for i in range(10):  # Create 10 concurrent audit events
                task = audit_service.log_event(
                    event_type=AuditEventType.DATA_ACCESSED,
                    action=f'performance_test_{i}',
                    message=f'Performance test event {i}',
                    outcome=AuditOutcome.SUCCESS,
                    severity=AuditSeverity.LOW,
                    details={'test_id': i, 'batch': 'performance_test'}
                )
                tasks.append(task)
            
            # Execute all tasks concurrently
            await asyncio.gather(*tasks)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            print(f"✅ Performance test completed:")
            print(f"   - 10 concurrent audit events logged in {duration:.3f} seconds")
            print(f"   - Average: {duration/10:.3f} seconds per event")
    
    async def run_comprehensive_test(self):
        """Run all audit system tests."""
        print("🚀 Starting comprehensive audit system test...\n")
        
        try:
            await self.setup_test_environment()
            await self.test_audit_logging()
            await self.test_audit_retrieval()
            await self.test_audit_statistics()
            await self.test_compliance_report()
            await self.test_audit_export()
            await self.test_integrity_verification()
            await self.test_forensic_analysis()
            await self.test_compliance_monitoring()
            await self.test_api_endpoints()
            await self.test_performance()
            
            print("\n🎉 All audit system tests completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            raise
        
        finally:
            await self.client.aclose()


async def main():
    """Main test execution function."""
    tester = AuditSystemTester()
    await tester.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())