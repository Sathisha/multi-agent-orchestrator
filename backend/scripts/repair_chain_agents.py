import asyncio
import os
import sys
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database.connection import get_async_db_context
from shared.models.chain import ChainNode, ChainNodeType
from shared.models.agent import Agent

async def repair_agents():
    print("Repairing missing agent_ids in ChainNodes...")
    
    async with get_async_db_context() as session:
        # 1. Get a default agent (any active agent)
        result = await session.execute(select(Agent).limit(1))
        default_agent = result.scalar_one_or_none()
        
        if not default_agent:
            print("Error: No agents found in database. Cannot repair chains.")
            return

        print(f"Using default agent: {default_agent.name} ({default_agent.id})")

        # 2. Find nodes with type 'agent' but no agent_id
        stmt = select(ChainNode).where(
            ChainNode.node_type == ChainNodeType.AGENT,
            ChainNode.agent_id == None
        )
        result = await session.execute(stmt)
        broken_nodes = result.scalars().all()
        
        if not broken_nodes:
            print("No broken nodes found.")
            return

        print(f"Found {len(broken_nodes)} nodes missing agent_id.")

        # 3. Update them
        for node in broken_nodes:
            print(f" - Fixing node '{node.label}' ({node.node_id})")
            node.agent_id = default_agent.id
            session.add(node)
            
        await session.commit()
        print("Repair complete!")

if __name__ == "__main__":
    asyncio.run(repair_agents())
