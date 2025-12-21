"""ID generation service for creating unique identifiers."""

import uuid
import secrets
import string
from typing import Optional
from datetime import datetime


class IDGeneratorService:
    """Service for generating unique identifiers for various entities."""
    
    @staticmethod
    def generate_uuid() -> str:
        """Generate a UUID4 string."""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_short_id(length: int = 8) -> str:
        """
        Generate a short alphanumeric ID.
        
        Args:
            length: Length of the ID (default: 8)
            
        Returns:
            Short alphanumeric ID
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def generate_agent_id(prefix: Optional[str] = None) -> str:
        """
        Generate a unique agent ID.
        
        Args:
            prefix: Optional prefix for the ID
            
        Returns:
            Unique agent ID
        """
        short_id = IDGeneratorService.generate_short_id(12)
        if prefix:
            return f"{prefix}-{short_id}"
        return f"agent-{short_id}"
    
    @staticmethod
    def generate_execution_id() -> str:
        """Generate a unique execution ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        short_id = IDGeneratorService.generate_short_id(8)
        return f"exec-{timestamp}-{short_id}"
    
    @staticmethod
    def generate_deployment_id() -> str:
        """Generate a unique deployment ID."""
        short_id = IDGeneratorService.generate_short_id(10)
        return f"deploy-{short_id}"
    
    @staticmethod
    def generate_session_id() -> str:
        """Generate a unique session ID."""
        return IDGeneratorService.generate_short_id(16)
    
    @staticmethod
    def generate_memory_id() -> str:
        """Generate a unique memory ID."""
        short_id = IDGeneratorService.generate_short_id(12)
        return f"mem-{short_id}"
    
    @staticmethod
    def is_valid_uuid(id_string: str) -> bool:
        """
        Check if a string is a valid UUID.
        
        Args:
            id_string: String to validate
            
        Returns:
            True if valid UUID, False otherwise
        """
        try:
            uuid.UUID(id_string)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def generate_api_key(length: int = 32) -> str:
        """
        Generate a secure API key.
        
        Args:
            length: Length of the API key
            
        Returns:
            Secure API key
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_workflow_id() -> str:
        """Generate a unique workflow ID."""
        short_id = IDGeneratorService.generate_short_id(10)
        return f"wf-{short_id}"
    
    @staticmethod
    def generate_tool_id() -> str:
        """Generate a unique tool ID."""
        short_id = IDGeneratorService.generate_short_id(8)
        return f"tool-{short_id}"