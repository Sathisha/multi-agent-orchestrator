import asyncio
import os
import sys
from sqlalchemy import select, update

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database.connection import get_async_db_context
from shared.models.agent import Agent

async def update_agents():
    print("Updating all agents to use Ollama with tinyllama...")
    
    async with get_async_db_context() as session:
        # Update all agents using an UPDATE statement
        stmt = update(Agent).values(
            config={
                "provider": "ollama",
                "model": "tinyllama",
                "temperature": 0.7,
                "max_tokens": 2000,
                "base_url": "http://ollama:11434"
            }
        )
        
        result = await session.execute(stmt)
        await session.commit()
        
        print(f"Updated {result.rowcount} agents successfully!")
        
        # Verify
        verify = await session.execute(select(Agent).limit(1))
        agent = verify.scalar_one_or_none()
        if agent:
            print(f"Verification - Agent '{agent.name}' config: {agent.config}")

if __name__ == "__main__":
    asyncio.run(update_agents())
