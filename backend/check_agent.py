import asyncio
from shared.database.connection import AsyncSessionLocal
from shared.models.agent import Agent
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Agent).limit(1))
        agent = result.scalar_one_or_none()
        if agent:
            print(f"Agent: {agent.name}")
            print(f"Config: {agent.config}")
        else:
            print("No agents found")

asyncio.run(check())
