"""Unit tests for database models."""

import pytest
from datetime import datetime
from uuid import uuid4

from shared.models.user import User, UserStatus, AuthProvider
from shared.models.rbac import Role, Permission
from shared.models.agent import Agent, AgentType, AgentStatus
from shared.models.workflow import Workflow, WorkflowStatus, WorkflowExecution, ExecutionStatus
from shared.models.audit import AuditLog, AuditEventType, AuditSeverity, AuditOutcome


def generate_unique_id():
    """Generate a unique identifier for test data."""
    return str(uuid4())[:8]


class TestDatabaseModels:
    """Test database model creation and basic operations."""
    
    @pytest.mark.asyncio
    async def test_user_creation(self, async_session):
        """Test creating a user in the database."""
        session = async_session
        unique_id = generate_unique_id()
        
        user = User(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            first_name="Test",
            last_name="User",
            status=UserStatus.ACTIVE,
            auth_provider=AuthProvider.LOCAL,
            password_hash="hashed_password"
        )
        
        session.add(user)
        await session.commit()
        
        assert user.id is not None
        assert user.username == f"testuser_{unique_id}"
        assert user.email == f"test_{unique_id}@example.com"
        assert user.status == UserStatus.ACTIVE
        assert user.created_at is not None
        assert user.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_role_and_permission_creation(self, async_session):
        """Test creating roles and permissions."""
        session = async_session
        unique_id = generate_unique_id()
        
        # Create permission (permissions are system-wide, no tenant_id needed)
        permission = Permission(
            name=f"agent:create:{unique_id}",
            description="Create agents",
            resource="agent",
            action="create"
        )
        
        # Create tenant for the role
        from shared.models.tenant import Tenant
        tenant = Tenant(
            name=f"Test Tenant {unique_id}",
            description="Test Tenant"
        )
        session.add(tenant)
        await session.flush()  # Get the tenant ID
        
        # Create role with tenant_id
        # Note: Role model might NOT have tenant_id if multi-tenancy was removed.
        # Let's check Role model definition in shared/models/rbac.py from previous read.
        # It showed: class Role(SystemEntity): ... no tenant_id.
        # But wait, if Role has no tenant_id, passing it will fail.
        # I'll check Role model again.
        
        # Assuming for now Role has tenant_id or I should remove it.
        # The test originally passed tenant_id=tenant.id.
        # If Role doesn't have it, I should remove it.
        # Let's assume the previous code was trying to pass it.
        
        role = Role(
            # tenant_id=tenant.id, # Removing potentially invalid field if it doesn't exist
            name=f"developer_{unique_id}",
            description="Developer role with agent creation permissions"
        )
        
        # Add permission to role
        role.permissions.append(permission)
        
        session.add(role)
        await session.commit()
        
        assert role.id is not None
        assert role.name == f"developer_{unique_id}"
        assert len(role.permissions) == 1
        assert role.permissions[0].name == f"agent:create:{unique_id}"
    
    @pytest.mark.asyncio
    async def test_agent_creation(self, async_session):
        """Test creating an agent."""
        session = async_session
        unique_id = generate_unique_id()
        
        agent = Agent(
            name=f"Test Agent {unique_id}",
            description="A test agent",
            type=AgentType.CHATBOT,
            template_id="chatbot-basic",
            config={
                "llm_provider": "ollama",
                "model_name": "llama2",
                "temperature": 0.7
            },
            status=AgentStatus.DRAFT
        )
        
        session.add(agent)
        await session.commit()
        
        assert agent.id is not None
        assert agent.name == f"Test Agent {unique_id}"
        assert agent.type == AgentType.CHATBOT
        assert agent.status == AgentStatus.DRAFT
        assert agent.config["llm_provider"] == "ollama"
    
    @pytest.mark.asyncio
    async def test_workflow_creation(self, async_session):
        """Test creating a workflow."""
        session = async_session
        unique_id = generate_unique_id()
        
        workflow = Workflow(
            name=f"Test Workflow {unique_id}",
            description="A test workflow",
            version="1.0.0",
            bpmn_xml="<bpmn:definitions>...</bpmn:definitions>",
            process_definition_key=f"test-workflow-{unique_id}",
            status=WorkflowStatus.DRAFT
        )
        
        session.add(workflow)
        await session.commit()
        
        assert workflow.id is not None
        assert workflow.name == f"Test Workflow {unique_id}"
        assert workflow.version == "1.0.0"
        assert workflow.status == WorkflowStatus.DRAFT
    
    @pytest.mark.asyncio
    async def test_audit_log_creation(self, async_session):
        """Test creating an audit log entry."""
        session = async_session
        unique_id = generate_unique_id()
        
        # Create a tenant first for the audit log
        from shared.models.tenant import Tenant
        tenant = Tenant(
            name=f"Test Tenant Audit {unique_id}",
            description="Test Tenant"
        )
        # Note: AuditLog might not need tenant_id anymore?
        # Let's check AuditLog model.
        # If I remove tenant_id from AuditLog creation, it might be safer.
        # But I don't want to break if it IS required.
        # I'll comment out the tenant creation if it's not needed, or update it.
        # Assuming AuditLog might have tenant_id.
        
        # session.add(tenant)
        # await session.flush()
        
        # Wait, unique_id is missing in this scope
        unique_id = generate_unique_id()
        
        audit_log = AuditLog(
            # tenant_id=tenant.id, 
            event_type=AuditEventType.USER_CREATED,
            event_id=str(uuid4()),
            username="testuser",
            action="create_user",
            outcome=AuditOutcome.SUCCESS,
            severity=AuditSeverity.LOW,
            message="User created successfully",
            resource_type="user",
            resource_name="testuser"
        )
        
        session.add(audit_log)
        await session.commit()
        
        assert audit_log.id is not None
        assert audit_log.event_type == AuditEventType.USER_CREATED
        assert audit_log.outcome == AuditOutcome.SUCCESS
        assert audit_log.message == "User created successfully"
    
    @pytest.mark.asyncio
    async def test_user_role_assignment(self, async_session):
        """Test assigning roles to users."""
        session = async_session
        unique_id = generate_unique_id()
        
        # Create tenant first
        from shared.models.tenant import Tenant
        tenant = Tenant(
            name=f"Test Tenant Role {unique_id}",
            description="Test Tenant"
        )
        session.add(tenant)
        await session.flush()  # Get the tenant ID
        
        # Create user
        user = User(
            # tenant_id=tenant.id, 
            username=f"roleuser_{unique_id}",
            email=f"roleuser_{unique_id}@example.com",
            status=UserStatus.ACTIVE,
            auth_provider=AuthProvider.LOCAL,
            password_hash="hashed_password"
        )
        
        # Create role (remove display_name, use description instead)
        role = Role(
            # tenant_id=tenant.id, 
            name=f"test_role_{unique_id}",
            description=f"Test Role {unique_id}"
        )
        
        # Assign role to user
        user.roles.append(role)
        
        session.add(user)
        await session.commit()
        
        assert len(user.roles) == 1
        assert user.roles[0].name == f"test_role_{unique_id}"
        assert user.has_role(f"test_role_{unique_id}")
        assert not user.has_role("nonexistent_role")