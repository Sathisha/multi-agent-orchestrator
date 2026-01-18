"""
Script to register all built-in tools in the database.
Run this once after deployment to make tools available to agents.
"""

import asyncio
import logging
import os
import sys

# Add parent directory to path so we can import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.services.builtin_tools import BUILTIN_TOOLS
from shared.services.tool_registry import ToolRegistryService
from shared.database.connection import AsyncSessionLocal
from shared.models.tool import ToolRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def register_builtin_tools():
    """Register all built-in tools in the database."""
    logger.info("Starting built-in tools registration...")
    
    async with AsyncSessionLocal() as session:
        tool_service = ToolRegistryService(session)
        
        registered_count = 0
        failed_count = 0
        
        # Use a hardcoded UUID for the system user to satisfy validation
        SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"
        
        for tool_data in BUILTIN_TOOLS:
            try:
                # Check if tool already exists
                existing_tools = await tool_service.list_tools(limit=1000)
                existing_tool = next((t for t in existing_tools if t.name == tool_data["name"]), None)
                
                if existing_tool:
                    logger.info(f"🔄 Updating '{tool_data['name']}'...")
                    tool_request = ToolRequest(**tool_data)
                    await tool_service.update_tool(
                        user_id=SYSTEM_USER_ID,
                        tool_id=existing_tool.id,
                        tool_request=tool_request
                    )
                    logger.info(f" Updated: {tool_data['name']}")
                else:
                    tool_request = ToolRequest(**tool_data)
                    tool = await tool_service.create_tool(
                        user_id=SYSTEM_USER_ID,
                        tool_request=tool_request
                    )
                    logger.info(f" Registered: {tool.name} (ID: {tool.id})")
                    registered_count += 1
                
            except Exception as e:
                logger.error(f" Failed to process '{tool_data['name']}': {e}")
                failed_count += 1
        
        logger.info("\n" + "="*50)
        logger.info(f"Registration/Update complete!")
        logger.info(f"   Processed: {registered_count}")
        logger.info(f"   Failed: {failed_count}")
        logger.info("="*50)


if __name__ == "__main__":
    asyncio.run(register_builtin_tools())
