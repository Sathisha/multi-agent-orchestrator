"""Data validation services using Pydantic models."""

from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.base import BaseEntity
from shared.models.user import User
from shared.models.rbac import Role, Permission
from shared.models.agent import Agent, AgentConfig
from shared.models.workflow import Workflow, WorkflowExecution
from shared.models.audit import AuditLog

T = TypeVar('T', bound=BaseModel)


class ValidationService:
    """Service for validating data using Pydantic models."""
    
    @staticmethod
    def validate_model(model_class: Type[T], data: Dict[str, Any]) -> T:
        """Validate data against a Pydantic model."""
        try:
            return model_class(**data)
        except ValidationError as e:
            raise ValueError(f"Validation failed: {e}")
    
    @staticmethod
    def validate_agent_config(config_data: Dict[str, Any]) -> AgentConfig:
        """Validate agent configuration data."""
        return ValidationService.validate_model(AgentConfig, config_data)
    
    @staticmethod
    async def validate_user_permissions(
        session: AsyncSession,
        user_id: UUID,
        resource_type: str,
        action: str,
        resource_id: Optional[UUID] = None
    ) -> bool:
        """Validate if a user has permission to perform an action on a resource."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        # Get user with roles and permissions
        stmt = select(User).options(
            selectinload(User.roles).selectinload(Role.permissions)
        ).where(User.id == user_id)
        
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        # Check if user has the required permission
        return user.has_permission(resource_type, action)
    
    @staticmethod
    def validate_bpmn_xml(bpmn_xml: str) -> bool:
        """Validate BPMN XML structure (basic validation)."""
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(bpmn_xml)
            
            # Check for required BPMN elements
            bpmn_namespace = "http://www.omg.org/spec/BPMN/20100524/MODEL"
            
            # Look for process definition
            processes = root.findall(f".//{{{bpmn_namespace}}}process")
            if not processes:
                return False
            
            # Basic structure validation passed
            return True
            
        except ET.ParseError:
            return False
    
    @staticmethod
    def validate_json_schema(data: Any, schema: Dict[str, Any]) -> bool:
        """Validate data against a JSON schema."""
        try:
            import jsonschema
            try:
                jsonschema.validate(data, schema)
                return True
            except (jsonschema.ValidationError, jsonschema.SchemaError):
                return False
        except ImportError:
            # If jsonschema is not installed, log warning and return True (allow)
            # or return False (strict). For now, strict but safe.
            return False
    
    @staticmethod
    def sanitize_input(data: Any) -> Any:
        """Sanitize input data to prevent injection attacks."""
        if isinstance(data, str):
            # Basic HTML/script tag removal
            import re
            data = re.sub(r'<script[^>]*>.*?</script>', '', data, flags=re.IGNORECASE | re.DOTALL)
            data = re.sub(r'<[^>]+>', '', data)  # Remove HTML tags
            data = data.strip()
        elif isinstance(data, dict):
            return {key: ValidationService.sanitize_input(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [ValidationService.sanitize_input(item) for item in data]
        
        return data
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """Validate password strength and return detailed feedback."""
        import re
        
        result = {
            "is_valid": True,
            "score": 0,
            "feedback": []
        }
        
        # Length check
        if len(password) < 8:
            result["is_valid"] = False
            result["feedback"].append("Password must be at least 8 characters long")
        else:
            result["score"] += 1
        
        # Uppercase check
        if not re.search(r'[A-Z]', password):
            result["is_valid"] = False
            result["feedback"].append("Password must contain at least one uppercase letter")
        else:
            result["score"] += 1
        
        # Lowercase check
        if not re.search(r'[a-z]', password):
            result["is_valid"] = False
            result["feedback"].append("Password must contain at least one lowercase letter")
        else:
            result["score"] += 1
        
        # Digit check
        if not re.search(r'\d', password):
            result["is_valid"] = False
            result["feedback"].append("Password must contain at least one digit")
        else:
            result["score"] += 1
        
        # Special character check
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            result["is_valid"] = False
            result["feedback"].append("Password must contain at least one special character")
        else:
            result["score"] += 1
        
        # Common password check
        common_passwords = [
            "password", "123456", "password123", "admin", "qwerty",
            "letmein", "welcome", "monkey", "dragon", "master"
        ]
        if password.lower() in common_passwords:
            result["is_valid"] = False
            result["feedback"].append("Password is too common")
        
        # Calculate strength score (0-5)
        if result["is_valid"]:
            if len(password) >= 12:
                result["score"] += 1
            if re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]{2,}', password):
                result["score"] += 1
        
        return result
    
    @staticmethod
    def validate_email_format(email: str) -> bool:
        """Validate email format."""
        import re
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_uuid_format(uuid_string: str) -> bool:
        """Validate UUID format."""
        try:
            UUID(uuid_string)
            return True
        except ValueError:
            return False


class DataIntegrityService:
    """Service for ensuring data integrity and consistency."""
    
    @staticmethod
    async def check_referential_integrity(
        session: AsyncSession,
        entity: BaseEntity
    ) -> List[str]:
        """Check referential integrity for an entity."""
        errors = []
        
        # This would be expanded based on specific business rules
        # For now, basic checks
        
        if hasattr(entity, 'created_by') and entity.created_by:
            # Check if creator exists
            from sqlalchemy import select
            stmt = select(User).where(User.id == entity.created_by)
            result = await session.execute(stmt)
            if not result.scalar_one_or_none():
                errors.append(f"Creator with ID {entity.created_by} does not exist")
        
        return errors
    
    @staticmethod
    async def validate_business_rules(
        session: AsyncSession,
        entity: BaseEntity,
        operation: str = "create"
    ) -> List[str]:
        """Validate business rules for an entity."""
        errors = []
        
        # Agent-specific business rules
        if isinstance(entity, Agent):
            errors.extend(await DataIntegrityService._validate_agent_rules(session, entity, operation))
        
        # Workflow-specific business rules
        elif isinstance(entity, Workflow):
            errors.extend(await DataIntegrityService._validate_workflow_rules(session, entity, operation))
        
        # User-specific business rules
        elif isinstance(entity, User):
            errors.extend(await DataIntegrityService._validate_user_rules(session, entity, operation))
        
        return errors
    
    @staticmethod
    async def _validate_agent_rules(
        session: AsyncSession,
        agent: Agent,
        operation: str
    ) -> List[str]:
        """Validate agent-specific business rules."""
        errors = []
        
        # Check for duplicate agent names for the same creator
        if operation in ["create", "update"]:
            from sqlalchemy import select, and_
            
            stmt = select(Agent).where(
                and_(
                    Agent.name == agent.name,
                    Agent.created_by == agent.created_by,
                    Agent.id != agent.id if operation == "update" else True,
                    Agent.is_deleted == False
                )
            )
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                errors.append(f"Agent with name '{agent.name}' already exists for this user")
        
        return errors
    
    @staticmethod
    async def _validate_workflow_rules(
        session: AsyncSession,
        workflow: Workflow,
        operation: str
    ) -> List[str]:
        """Validate workflow-specific business rules."""
        errors = []
        
        # Validate BPMN XML
        if workflow.bpmn_xml and not ValidationService.validate_bpmn_xml(workflow.bpmn_xml):
            errors.append("Invalid BPMN XML format")
        
        # Check for duplicate process definition keys
        if operation in ["create", "update"]:
            from sqlalchemy import select, and_
            
            stmt = select(Workflow).where(
                and_(
                    Workflow.process_definition_key == workflow.process_definition_key,
                    Workflow.version == workflow.version,
                    Workflow.id != workflow.id if operation == "update" else True,
                    Workflow.is_deleted == False
                )
            )
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                errors.append(f"Workflow with process key '{workflow.process_definition_key}' and version '{workflow.version}' already exists")
        
        return errors
    
    @staticmethod
    async def _validate_user_rules(
        session: AsyncSession,
        user: User,
        operation: str
    ) -> List[str]:
        """Validate user-specific business rules."""
        errors = []
        
        # Check for duplicate usernames and emails
        if operation in ["create", "update"]:
            from sqlalchemy import select, and_, or_
            
            stmt = select(User).where(
                and_(
                    or_(
                        User.username == user.username,
                        User.email == user.email
                    ),
                    User.id != user.id if operation == "update" else True,
                    User.is_deleted == False
                )
            )
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()
            if existing_user:
                if existing_user.username == user.username:
                    errors.append(f"Username '{user.username}' is already taken")
                if existing_user.email == user.email:
                    errors.append(f"Email '{user.email}' is already registered")
        
        return errors