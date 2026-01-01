from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel

from shared.models.agent import AgentType, AgentConfig

class AgentTemplate(BaseModel):
    id: str
    name: str
    description: str
    agent_type: AgentType
    default_config: AgentConfig
