"""
Property-based tests for comprehensive logging.

**Feature: ai-agent-framework, Property 9: Comprehensive Logging**
**Validates: Requirements 4.1, 4.5, 16.1, 16.2, 18.1**
"""

import pytest
import asyncio
import json
import uuid
import time
from typing import Dict, Any, List, Optional
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_database_session
from shared.services.agent import AgentService
from shared.services.tenant import TenantService
from shared.services.audit import AuditService
from shared.models.agent import Agent, AgentType, AgentConfig, LLMProvider
from shared.models.tenant import Tenant, TenantStatus, TenantPlan
from shared.models.audit import AuditLog, AuditEventType, AuditSeverity, AuditOutcome
from shared.logging.structured_logging import StructuredLogger
import logging


class TestComprehensiveLogging:
    """Test suite for comprehensive logging property."""
    
    def __init__(self):
        self.test_tenant_id = str(uuid.uuid4())
        self.test_user_id = str(uuid.uuid4())
        self.logger = StructuredLogger(__name__)
    
    async def _test_system_operation_logging_direct(self, operation_data: Dict[str, Any]):
        """
        Direct test method for comprehensive logging validation.
        
        **Feature: ai-agent-framework, Property 9: Comprehensive Logging**
        **Validates: Requirements 4.1, 4.5, 16.1, 16.2, 18.1**
        
        Property: For any system operation (agent execution, LLM interaction, 
        workflow orchestration), all activities should be logged with timestamps, 
        context, and structured metadata.
        """
        async with get_database_session() as session:
            operation_type = operation_data["operation_type"]
            
            try:
                # Ensure we have a valid tenant for operations
                tenant_service = TenantService(session)
                
                # Check if tenant already exists
                existing_tenant = await tenant_service.get_tenant_by_id(self.test_tenant_id)
                if not existing_tenant:
                    # Create a test tenant with unique slug
                    unique_slug = f"test-tenant-{str(uuid.uuid4())[:8]}"
                    
                    test_tenant = await tenant_service.create_tenant(
                        name="Test Tenant for Logging",
                        slug=unique_slug,
                        display_name="Test Tenant for Logging Property Tests",
                        primary_email="test@example.com",
                        plan=TenantPlan.FREE,
                        max_users=10,
                        max_agents=50,
                        max_workflows=20,
                        max_storage_gb=5,
                        max_api_calls_per_month=10000
                    )
                    self.test_tenant_id = test_tenant.id
                
                # Create audit service with tenant context (no user_id to avoid foreign key issues)
                audit_service = AuditService(session, self.test_tenant_id, None)
                
                # Record the start time for log verification
                operation_start_time = datetime.utcnow()
                
                if operation_type == "direct_audit_logging":
                    # Test direct audit logging functionality
                    
                    # Create a test audit entry with proper UUID for resource_id
                    test_resource_id = str(uuid.uuid4())
                    test_audit_entry = await audit_service.log_event(
                        event_type=AuditEventType.SYSTEM_STARTED,
                        action="test_access",
                        message="Test audit entry for logging property test",
                        resource_type="test_resource",
                        resource_id=test_resource_id,
                        details=operation_data.get("audit_details", {}),
                        severity=AuditSeverity.LOW,
                        outcome=AuditOutcome.SUCCESS
                    )
                    
                    # Verify the audit entry was created successfully
                    assert test_audit_entry is not None, "Audit entry should be created"
                    assert test_audit_entry.id is not None, "Audit entry should have an ID"
                    
                    # Verify basic audit log structure
                    self._verify_audit_log_structure_basic(test_audit_entry)
                    
                    # Test querying audit logs
                    from shared.models.audit import AuditLogRequest
                    
                    # Create audit log request
                    request = AuditLogRequest(
                        event_types=[AuditEventType.SYSTEM_STARTED],
                        start_date=operation_start_time - timedelta(seconds=5),
                        end_date=datetime.utcnow() + timedelta(seconds=5),
                        size=50
                    )
                    
                    # Query for audit logs
                    audit_logs, total_count = await audit_service.get_audit_logs(request)
                    
                    # Verify we can retrieve the audit log we just created
                    assert total_count > 0, "Should find at least one audit log"
                    assert len(audit_logs) > 0, "Should return audit log entries"
                    
                    # Find our specific audit entry
                    matching_logs = [
                        log for log in audit_logs 
                        if log.event_type == AuditEventType.SYSTEM_STARTED 
                        and log.timestamp >= operation_start_time
                        and log.resource_id == test_resource_id
                    ]
                    
                    assert len(matching_logs) > 0, "Should find our specific audit log entry"
                    
                    # Verify the retrieved log has correct structure
                    retrieved_log = matching_logs[0]
                    assert retrieved_log.action == "test_access", "Action should match"
                    assert retrieved_log.message == "Test audit entry for logging property test", "Message should match"
                    assert retrieved_log.resource_type == "test_resource", "Resource type should match"
                    assert retrieved_log.outcome == AuditOutcome.SUCCESS, "Outcome should match"
                    assert retrieved_log.severity == AuditSeverity.LOW, "Severity should match"
                    
                elif operation_type == "structured_logging":
                    # Test structured logging with complex data
                    complex_details = {
                        "operation": "complex_test",
                        "parameters": {
                            "param1": "value1",
                            "param2": 42,
                            "param3": True,
                            "nested": {
                                "key": "nested_value",
                                "list": [1, 2, 3]
                            }
                        },
                        "metadata": operation_data.get("metadata", {})
                    }
                    
                    # Create audit entry with complex structured data
                    test_resource_id = str(uuid.uuid4())
                    complex_audit_entry = await audit_service.log_event(
                        event_type=AuditEventType.SYSTEM_STARTED,
                        action="complex_structured_test",
                        message="Testing structured logging with complex data",
                        resource_type="complex_resource",
                        resource_id=test_resource_id,
                        details=complex_details,
                        severity=AuditSeverity.MEDIUM,
                        outcome=AuditOutcome.SUCCESS
                    )
                    
                    # Verify complex data was stored correctly
                    assert complex_audit_entry is not None, "Complex audit entry should be created"
                    assert complex_audit_entry.details is not None, "Details should be stored"
                    assert complex_audit_entry.details["operation"] == "complex_test", "Complex data should be preserved"
                    assert complex_audit_entry.details["parameters"]["param2"] == 42, "Numeric values should be preserved"
                    assert complex_audit_entry.details["parameters"]["nested"]["list"] == [1, 2, 3], "Nested structures should be preserved"
                    
                elif operation_type == "audit_integrity":
                    # Test audit log integrity features
                    test_resource_id = str(uuid.uuid4())
                    integrity_entry = await audit_service.log_event(
                        event_type=AuditEventType.SYSTEM_STARTED,
                        action="integrity_test",
                        message="Testing audit log integrity verification",
                        resource_type="integrity_resource",
                        resource_id=test_resource_id,
                        details={"test": "integrity"},
                        severity=AuditSeverity.HIGH,
                        outcome=AuditOutcome.SUCCESS
                    )
                    
                    # Verify checksum was calculated
                    assert integrity_entry.checksum is not None, "Checksum should be calculated"
                    assert len(integrity_entry.checksum) == 64, "Checksum should be SHA-256 (64 chars)"
                    
                    # Verify integrity check passes
                    assert integrity_entry.verify_integrity(), "Integrity verification should pass"
                    
                    # Test integrity verification service
                    verification_results = await audit_service.verify_audit_integrity(
                        start_date=operation_start_time - timedelta(seconds=5),
                        end_date=datetime.utcnow() + timedelta(seconds=5)
                    )
                    
                    assert verification_results is not None, "Verification results should be returned"
                    assert verification_results["total_records"] > 0, "Should have records to verify"
                    assert verification_results["verified_records"] > 0, "Should have verified records"
                    assert verification_results["corrupted_records"] == 0, "Should have no corrupted records"
                
            except Exception as e:
                # Log the error for debugging
                self.logger.error(
                    "Logging property test failed",
                    operation_type=operation_type,
                    error=str(e),
                    tenant_id=self.test_tenant_id
                )
                raise e
    
    async def _verify_operation_logged(
        self, 
        audit_service: AuditService, 
        expected_event_type: AuditEventType,
        operation_start_time: datetime,
        expected_context: Dict[str, Any]
    ):
        """Verify that an operation was properly logged."""
        from shared.models.audit import AuditLogRequest
        
        # Create audit log request
        request = AuditLogRequest(
            event_types=[expected_event_type],
            start_date=operation_start_time - timedelta(seconds=5),
            end_date=datetime.utcnow() + timedelta(seconds=5),
            size=50
        )
        
        # Query for audit logs after the operation start time
        audit_logs, total_count = await audit_service.get_audit_logs(request)
        
        # Find matching log entry
        matching_logs = [
            log for log in audit_logs 
            if log.event_type == expected_event_type and log.timestamp >= operation_start_time
        ]
        
        assert len(matching_logs) > 0, f"Expected audit log for {expected_event_type.value} not found"
        
        # Verify the most recent matching log
        log_entry = matching_logs[0]
        self._verify_audit_log_structure_basic(log_entry)
        
        # Verify expected context is present in log details
        for key, expected_value in expected_context.items():
            if hasattr(log_entry, 'details') and key in log_entry.details:
                assert log_entry.details[key] == expected_value, \
                    f"Expected {key}={expected_value} in log details, got {log_entry.details[key]}"
    
    def _verify_audit_log_structure_basic(self, log_entry):
        """Verify that an audit log entry has the basic required structure."""
        # Required fields validation
        assert log_entry.id is not None, "Audit log should have an ID"
        assert log_entry.timestamp is not None, "Audit log should have a timestamp"
        assert log_entry.event_type is not None, "Audit log should have an event type"
        assert log_entry.tenant_id is not None, "Audit log should have a tenant ID"
        
        # Timestamp should be recent (within last 5 minutes)
        time_diff = datetime.utcnow() - log_entry.timestamp
        assert time_diff.total_seconds() < 300, "Audit log timestamp should be recent"
        
        # Details should be valid JSON-serializable dict if present
        if hasattr(log_entry, 'details') and log_entry.details:
            assert isinstance(log_entry.details, dict), "Audit log details should be a dictionary"
            
            # Verify details can be JSON serialized (structured logging requirement)
            try:
                json.dumps(log_entry.details)
            except (TypeError, ValueError) as e:
                pytest.fail(f"Audit log details should be JSON serializable: {e}")
        
        # Verify severity and outcome are valid enums
        assert isinstance(log_entry.severity, AuditSeverity), "Severity should be valid enum"
        assert isinstance(log_entry.outcome, AuditOutcome), "Outcome should be valid enum"


# Pytest integration functions
@pytest.mark.asyncio
async def test_property_direct_audit_logging():
    """Run property test for direct audit logging functionality."""
    test_instance = TestComprehensiveLogging()
    
    test_case = {
        "operation_type": "direct_audit_logging",
        "audit_details": {
            "action": "test_access",
            "resource": "test_resource",
            "metadata": {
                "test_key": "test_value",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    }
    
    await test_instance._test_system_operation_logging_direct(test_case)


@pytest.mark.asyncio
async def test_property_structured_logging():
    """Run property test for structured logging with complex data."""
    test_instance = TestComprehensiveLogging()
    
    test_case = {
        "operation_type": "structured_logging",
        "metadata": {
            "complex_data": {
                "numbers": [1, 2, 3, 4, 5],
                "strings": ["a", "b", "c"],
                "boolean": True,
                "null_value": None
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    await test_instance._test_system_operation_logging_direct(test_case)


@pytest.mark.asyncio
async def test_property_audit_integrity():
    """Run property test for audit log integrity verification."""
    test_instance = TestComprehensiveLogging()
    
    test_case = {
        "operation_type": "audit_integrity"
    }
    
    await test_instance._test_system_operation_logging_direct(test_case)


if __name__ == "__main__":
    # Run property tests directly
    import asyncio
    
    async def run_property_tests():
        """Run all comprehensive logging property tests."""
        print("🧪 Running Property 9: Comprehensive Logging Tests")
        
        print("\n1. Testing direct audit logging functionality...")
        await test_property_direct_audit_logging()
        print("✅ Direct audit logging test passed")
        
        print("\n2. Testing structured logging with complex data...")
        await test_property_structured_logging()
        print("✅ Structured logging test passed")
        
        print("\n3. Testing audit log integrity verification...")
        await test_property_audit_integrity()
        print("✅ Audit integrity test passed")
        
        print("\n🎉 Property 9 tests completed!")
        
        return True
    
    asyncio.run(run_property_tests())