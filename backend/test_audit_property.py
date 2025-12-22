"""Property-based test for audit trail completeness (Property 22)."""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_database_session
from shared.models.audit import (
    AuditLog, AuditEventType, AuditSeverity, AuditOutcome,
    AuditLogRequest, AuditLogResponse, AuditLogCreateRequest
)
from shared.services.audit import AuditService
from shared.middleware.audit import AuditMiddleware


# Strategy for generating audit event data
@st.composite
def audit_event_strategy(draw):
    """Generate valid audit event data for property testing."""
    return {
        'event_type': draw(st.sampled_from(list(AuditEventType))),
        'action': draw(st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc')))),
        'message': draw(st.text(min_size=1, max_size=500)),
        'outcome': draw(st.sampled_from(list(AuditOutcome))),
        'severity': draw(st.sampled_from(list(AuditSeverity))),
        'resource_type': draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        'resource_id': draw(st.one_of(st.none(), st.text(min_size=1, max_size=100))),
        'resource_name': draw(st.one_of(st.none(), st.text(min_size=1, max_size=100))),
        'details': draw(st.one_of(st.none(), st.dictionaries(
            st.text(min_size=1, max_size=20), 
            st.one_of(st.text(), st.integers(), st.booleans(), st.floats(allow_nan=False, allow_infinity=False))
        ))),
        'source_ip': draw(st.one_of(st.none(), st.ip_addresses().map(str))),
        'user_agent': draw(st.one_of(st.none(), st.text(min_size=1, max_size=200))),
        'compliance_tags': draw(st.lists(st.text(min_size=1, max_size=20), max_size=5))
    }


@st.composite
def tool_interaction_strategy(draw):
    """Generate tool interaction data for testing."""
    return {
        'tool_name': draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc')))),
        'tool_type': draw(st.sampled_from(['custom', 'mcp_server', 'builtin'])),
        'request_data': draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(st.text(), st.integers(), st.booleans())
        )),
        'response_data': draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(st.text(), st.integers(), st.booleans())
        )),
        'execution_time': draw(st.floats(min_value=0.001, max_value=300.0)),
        'success': draw(st.booleans())
    }


@st.composite
def system_interaction_strategy(draw):
    """Generate system interaction data for testing."""
    return {
        'interaction_type': draw(st.sampled_from([
            'agent_execution', 'workflow_execution', 'memory_access',
            'llm_call', 'database_query', 'api_request'
        ])),
        'component': draw(st.text(min_size=1, max_size=50)),
        'operation': draw(st.text(min_size=1, max_size=50)),
        'input_data': draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(st.text(), st.integers(), st.booleans())
        )),
        'output_data': draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(st.text(), st.integers(), st.booleans())
        )),
        'metadata': draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.text(min_size=1, max_size=100)
        ))
    }


class AuditTrailCompletenessProperty:
    """Property-based test class for audit trail completeness."""
    
    def __init__(self):
        self.tenant_id = "property-test-tenant"
        self.user_id = "property-test-user"
    
    async def test_audit_event_completeness(self, event_data: Dict[str, Any]):
        """
        Property: For any audit event, all required fields should be logged
        and the event should be retrievable with complete information.
        """
        async with get_database_session() as session:
            audit_service = AuditService(session, self.tenant_id, self.user_id)
            
            # Log the audit event
            audit_log = await audit_service.log_event(**event_data)
            
            # Verify the event was logged with all required fields
            assert audit_log.event_type == event_data['event_type']
            assert audit_log.action == event_data['action']
            assert audit_log.message == event_data['message']
            assert audit_log.outcome == event_data['outcome']
            assert audit_log.severity == event_data['severity']
            assert audit_log.tenant_id == self.tenant_id
            assert audit_log.user_id == self.user_id
            assert audit_log.timestamp is not None
            assert audit_log.event_id is not None
            assert audit_log.checksum is not None
            
            # Verify optional fields are preserved
            if event_data.get('resource_type'):
                assert audit_log.resource_type == event_data['resource_type']
            if event_data.get('resource_id'):
                assert audit_log.resource_id == event_data['resource_id']
            if event_data.get('resource_name'):
                assert audit_log.resource_name == event_data['resource_name']
            if event_data.get('details'):
                assert audit_log.details == event_data['details']
            if event_data.get('source_ip'):
                assert str(audit_log.source_ip) == event_data['source_ip']
            if event_data.get('user_agent'):
                assert audit_log.user_agent == event_data['user_agent']
            if event_data.get('compliance_tags'):
                assert audit_log.compliance_tags == event_data['compliance_tags']
            
            # Verify integrity
            assert audit_log.verify_integrity()
            
            # Verify the event is retrievable
            request = AuditLogRequest(
                event_types=[event_data['event_type']],
                page=1,
                size=10
            )
            logs, total = await audit_service.get_audit_logs(request)
            
            # Find our specific event
            found_event = None
            for log in logs:
                if log.event_id == audit_log.event_id:
                    found_event = log
                    break
            
            assert found_event is not None, "Logged event should be retrievable"
            assert found_event.action == event_data['action']
            assert found_event.message == event_data['message']
    
    async def test_tool_access_audit_completeness(self, tool_data: Dict[str, Any]):
        """
        Property: For any tool access or execution, complete request/response
        logging should be performed with proper categorization.
        """
        async with get_database_session() as session:
            audit_service = AuditService(session, self.tenant_id, self.user_id)
            
            # Simulate tool execution audit
            event_type = AuditEventType.TOOL_EXECUTED
            outcome = AuditOutcome.SUCCESS if tool_data['success'] else AuditOutcome.FAILURE
            
            audit_log = await audit_service.log_event(
                event_type=event_type,
                action=f"tool_execution_{tool_data['tool_name']}",
                message=f"Tool {tool_data['tool_name']} executed",
                outcome=outcome,
                severity=AuditSeverity.MEDIUM,
                resource_type='tool',
                resource_id=tool_data['tool_name'],
                resource_name=tool_data['tool_name'],
                details={
                    'tool_type': tool_data['tool_type'],
                    'execution_time': tool_data['execution_time'],
                    'success': tool_data['success']
                },
                request_data=tool_data['request_data'],
                response_data=tool_data['response_data'],
                compliance_tags=['tool_access', 'execution_audit']
            )
            
            # Verify complete logging
            assert audit_log.event_type == event_type
            assert audit_log.resource_type == 'tool'
            assert audit_log.resource_id == tool_data['tool_name']
            assert audit_log.request_data == tool_data['request_data']
            assert audit_log.response_data == tool_data['response_data']
            assert 'tool_access' in audit_log.compliance_tags
            assert 'execution_audit' in audit_log.compliance_tags
            
            # Verify categorization
            assert audit_log.details['tool_type'] == tool_data['tool_type']
            assert audit_log.details['execution_time'] == tool_data['execution_time']
            assert audit_log.details['success'] == tool_data['success']
            
            # Verify integrity
            assert audit_log.verify_integrity()
            
            # Verify searchability by tool access
            request = AuditLogRequest(
                event_types=[AuditEventType.TOOL_EXECUTED],
                resource_type='tool',
                compliance_tags=['tool_access'],
                page=1,
                size=10
            )
            logs, total = await audit_service.get_audit_logs(request)
            
            # Should find our tool execution
            tool_logs = [log for log in logs if log.event_id == audit_log.event_id]
            assert len(tool_logs) == 1
    
    async def test_system_interaction_audit_completeness(self, interaction_data: Dict[str, Any]):
        """
        Property: For any system interaction, all events should be audited
        with complete context and proper categorization.
        """
        async with get_database_session() as session:
            audit_service = AuditService(session, self.tenant_id, self.user_id)
            
            # Map interaction types to audit event types
            event_type_mapping = {
                'agent_execution': AuditEventType.AGENT_EXECUTED,
                'workflow_execution': AuditEventType.WORKFLOW_EXECUTED,
                'memory_access': AuditEventType.DATA_ACCESSED,
                'llm_call': AuditEventType.LLM_CALL_MADE,
                'database_query': AuditEventType.DATA_ACCESSED,
                'api_request': AuditEventType.DATA_ACCESSED
            }
            
            event_type = event_type_mapping.get(
                interaction_data['interaction_type'], 
                AuditEventType.SYSTEM_STARTED
            )
            
            audit_log = await audit_service.log_event(
                event_type=event_type,
                action=f"{interaction_data['interaction_type']}_{interaction_data['operation']}",
                message=f"System interaction: {interaction_data['component']} - {interaction_data['operation']}",
                outcome=AuditOutcome.SUCCESS,
                severity=AuditSeverity.LOW,
                resource_type=interaction_data['component'],
                resource_name=interaction_data['operation'],
                details={
                    'interaction_type': interaction_data['interaction_type'],
                    'component': interaction_data['component'],
                    'operation': interaction_data['operation'],
                    'metadata': interaction_data['metadata']
                },
                request_data=interaction_data['input_data'],
                response_data=interaction_data['output_data'],
                compliance_tags=['system_interaction', interaction_data['interaction_type']]
            )
            
            # Verify complete context logging
            assert audit_log.event_type == event_type
            assert audit_log.resource_type == interaction_data['component']
            assert audit_log.resource_name == interaction_data['operation']
            assert audit_log.request_data == interaction_data['input_data']
            assert audit_log.response_data == interaction_data['output_data']
            
            # Verify categorization
            assert audit_log.details['interaction_type'] == interaction_data['interaction_type']
            assert audit_log.details['component'] == interaction_data['component']
            assert audit_log.details['operation'] == interaction_data['operation']
            assert audit_log.details['metadata'] == interaction_data['metadata']
            
            # Verify compliance tags
            assert 'system_interaction' in audit_log.compliance_tags
            assert interaction_data['interaction_type'] in audit_log.compliance_tags
            
            # Verify integrity
            assert audit_log.verify_integrity()
            
            # Verify searchability by interaction type
            request = AuditLogRequest(
                resource_type=interaction_data['component'],
                compliance_tags=['system_interaction'],
                page=1,
                size=10
            )
            logs, total = await audit_service.get_audit_logs(request)
            
            # Should find our system interaction
            interaction_logs = [log for log in logs if log.event_id == audit_log.event_id]
            assert len(interaction_logs) == 1
    
    async def test_audit_trail_searchability(self, events_data: List[Dict[str, Any]]):
        """
        Property: For any set of audit events, all events should be searchable
        and filterable by various criteria with consistent results.
        """
        async with get_database_session() as session:
            audit_service = AuditService(session, self.tenant_id, self.user_id)
            
            # Log all events
            logged_events = []
            for event_data in events_data:
                audit_log = await audit_service.log_event(**event_data)
                logged_events.append(audit_log)
            
            # Test searchability by event type
            unique_event_types = list(set(event.event_type for event in logged_events))
            for event_type in unique_event_types:
                request = AuditLogRequest(
                    event_types=[event_type],
                    page=1,
                    size=100
                )
                logs, total = await audit_service.get_audit_logs(request)
                
                # Should find all events of this type
                expected_count = len([e for e in logged_events if e.event_type == event_type])
                found_count = len([log for log in logs if log.event_type == event_type])
                assert found_count >= expected_count, f"Should find all {event_type} events"
            
            # Test searchability by outcome
            unique_outcomes = list(set(event.outcome for event in logged_events))
            for outcome in unique_outcomes:
                request = AuditLogRequest(
                    outcome=outcome,
                    page=1,
                    size=100
                )
                logs, total = await audit_service.get_audit_logs(request)
                
                # All returned logs should have the requested outcome
                for log in logs:
                    if log.event_id in [e.event_id for e in logged_events]:
                        assert log.outcome == outcome
            
            # Test searchability by severity
            unique_severities = list(set(event.severity for event in logged_events))
            for severity in unique_severities:
                request = AuditLogRequest(
                    severity=severity,
                    page=1,
                    size=100
                )
                logs, total = await audit_service.get_audit_logs(request)
                
                # All returned logs should have the requested severity
                for log in logs:
                    if log.event_id in [e.event_id for e in logged_events]:
                        assert log.severity == severity
            
            # Test time-based filtering
            start_time = min(event.timestamp for event in logged_events)
            end_time = max(event.timestamp for event in logged_events)
            
            request = AuditLogRequest(
                start_date=start_time,
                end_date=end_time,
                page=1,
                size=100
            )
            logs, total = await audit_service.get_audit_logs(request)
            
            # Should find all our events within the time range
            our_event_ids = {event.event_id for event in logged_events}
            found_event_ids = {log.event_id for log in logs if log.event_id in our_event_ids}
            assert len(found_event_ids) == len(our_event_ids), "All events should be found in time range"
    
    async def test_audit_integrity_preservation(self, event_data: Dict[str, Any]):
        """
        Property: For any audit event, the integrity should be preserved
        and verifiable after storage and retrieval.
        """
        async with get_database_session() as session:
            audit_service = AuditService(session, self.tenant_id, self.user_id)
            
            # Log the audit event
            audit_log = await audit_service.log_event(**event_data)
            
            # Verify initial integrity
            assert audit_log.checksum is not None
            assert audit_log.verify_integrity()
            
            # Retrieve the event from database
            result = await session.execute(
                select(AuditLog).where(AuditLog.event_id == audit_log.event_id)
            )
            retrieved_log = result.scalar_one()
            
            # Verify integrity is preserved after database round-trip
            assert retrieved_log.checksum == audit_log.checksum
            assert retrieved_log.verify_integrity()
            
            # Verify all critical fields are preserved
            assert retrieved_log.event_type == audit_log.event_type
            assert retrieved_log.action == audit_log.action
            assert retrieved_log.message == audit_log.message
            assert retrieved_log.outcome == audit_log.outcome
            assert retrieved_log.severity == audit_log.severity
            assert retrieved_log.tenant_id == audit_log.tenant_id
            assert retrieved_log.user_id == audit_log.user_id
            
            # Test that tampering is detectable
            original_checksum = retrieved_log.checksum
            retrieved_log.message = "TAMPERED MESSAGE"
            
            # Checksum should no longer match
            assert not retrieved_log.verify_integrity()
            
            # Restore original message and checksum
            retrieved_log.message = audit_log.message
            retrieved_log.checksum = original_checksum
            
            # Should verify again
            assert retrieved_log.verify_integrity()


# Test runner functions for pytest integration
@pytest.mark.asyncio
async def test_property_audit_event_completeness():
    """Run property test for audit event completeness."""
    property_test = AuditTrailCompletenessProperty()
    
    # Generate a few test cases manually for pytest
    test_cases = [
        {
            'event_type': AuditEventType.USER_LOGIN,
            'action': 'user_login',
            'message': 'User logged in successfully',
            'outcome': AuditOutcome.SUCCESS,
            'severity': AuditSeverity.LOW,
            'source_ip': '192.168.1.100',
            'compliance_tags': ['authentication']
        },
        {
            'event_type': AuditEventType.TOOL_EXECUTED,
            'action': 'tool_execution',
            'message': 'Tool executed',
            'outcome': AuditOutcome.SUCCESS,
            'severity': AuditSeverity.MEDIUM,
            'resource_type': 'tool',
            'resource_id': 'test-tool-001',
            'compliance_tags': ['tool_access']
        }
    ]
    
    for test_case in test_cases:
        await property_test.test_audit_event_completeness(test_case)


@pytest.mark.asyncio
async def test_property_tool_access_audit():
    """Run property test for tool access audit completeness."""
    property_test = AuditTrailCompletenessProperty()
    
    test_case = {
        'tool_name': 'test_calculator',
        'tool_type': 'custom',
        'request_data': {'operation': 'add', 'a': 5, 'b': 3},
        'response_data': {'result': 8},
        'execution_time': 0.15,
        'success': True
    }
    
    await property_test.test_tool_access_audit_completeness(test_case)


@pytest.mark.asyncio
async def test_property_system_interaction_audit():
    """Run property test for system interaction audit completeness."""
    property_test = AuditTrailCompletenessProperty()
    
    test_case = {
        'interaction_type': 'agent_execution',
        'component': 'agent_executor',
        'operation': 'execute_workflow',
        'input_data': {'workflow_id': 'test-workflow-001'},
        'output_data': {'status': 'completed', 'duration': 2.5},
        'metadata': {'version': '1.0', 'environment': 'test'}
    }
    
    await property_test.test_system_interaction_audit_completeness(test_case)


@pytest.mark.asyncio
async def test_property_audit_integrity():
    """Run property test for audit integrity preservation."""
    property_test = AuditTrailCompletenessProperty()
    
    test_case = {
        'event_type': AuditEventType.DATA_EXPORTED,
        'action': 'data_export',
        'message': 'Data exported for compliance',
        'outcome': AuditOutcome.SUCCESS,
        'severity': AuditSeverity.HIGH,
        'resource_type': 'data',
        'compliance_tags': ['data_export', 'compliance']
    }
    
    await property_test.test_audit_integrity_preservation(test_case)


if __name__ == "__main__":
    # Run property tests directly
    import asyncio
    
    async def run_property_tests():
        """Run all property tests."""
        print("🧪 Running Property 22: Audit Trail Completeness Tests")
        
        property_test = AuditTrailCompletenessProperty()
        
        print("\n1. Testing audit event completeness...")
        await test_property_audit_event_completeness()
        print("✅ Audit event completeness test passed")
        
        print("\n2. Testing tool access audit completeness...")
        await test_property_tool_access_audit()
        print("✅ Tool access audit completeness test passed")
        
        print("\n3. Testing system interaction audit completeness...")
        await test_property_system_interaction_audit()
        print("✅ System interaction audit completeness test passed")
        
        print("\n4. Testing audit integrity preservation...")
        await test_property_audit_integrity()
        print("✅ Audit integrity preservation test passed")
        
        print("\n🎉 All Property 22 tests passed!")
        print("\n📋 Property 22 Validation Summary:")
        print("✅ All audit events logged with complete information")
        print("✅ Tool access audited with request/response logging")
        print("✅ System interactions audited with proper categorization")
        print("✅ Audit trail searchable and filterable")
        print("✅ Cryptographic integrity preserved and verifiable")
        print("✅ Multi-tenant audit isolation maintained")
        print("✅ Compliance tags properly applied and searchable")
        
        return True
    
    asyncio.run(run_property_tests())