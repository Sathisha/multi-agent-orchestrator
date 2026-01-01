"""Test script to verify agents API"""
import asyncio
import sys
sys.path.insert(0, '/app')

from shared.database.connection import AsyncSessionLocal
from shared.services.agent import AgentService

async def test_list_agents():
    async with AsyncSessionLocal() as session:
        service = AgentService(session)
        agents = await service.list_agents()
        print(f"✓ Found {len(agents)} agents")
        for agent in agents:
            print(f"  - {agent.name} ({agent.type})")

if __name__ == "__main__":
    asyncio.run(test_list_agents())
