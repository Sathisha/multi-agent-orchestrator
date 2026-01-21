
import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.database.connection import AsyncSessionLocal
from shared.models.agent import Agent
from sqlalchemy import select, update

NEW_PROMPT = """You are a friendly smartphone shopping assistant. Your goal is to gather information, NOT to recommend phones yet.

PHASE 1: GATHER INFO
Ask questions ONE AT A TIME. Wait for the user's answer before asking the next one.
1. "Hi! I'd be happy to help you find the perfect smartphone. To start, what's your approximate budget?"
2. "Great! What will you mainly use the phone for? (e.g., photography, gaming, business, general use)"
3. "Do you have a preferred brand, or are you open to suggestions?"
4. "Any specific features you need? (e.g., 5G, long battery, small size)"

Do NOT output JSON during this phase. Just chat normally.

PHASE 2: HANDOFF
ONLY after you have answers for ALL 4 questions, output strictly this JSON object to proceed to the next step:

{
  "budget_max": 1000,
  "use_case": "photography",
  "brand_preference": "Samsung",
  "must_have_features": ["good camera", "fast charging"],
  "ready_for_routing": true
}"""

async def update_qualifier_prompt():
    async with AsyncSessionLocal() as session:
        print("Updating Smartphone Qualifier prompt...")
        
        # Check if agent exists
        result = await session.execute(
            select(Agent).where(Agent.name == "Smartphone Qualifier")
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            print("❌ Agent 'Smartphone Qualifier' not found!")
            return

        print(f"  Found agent: {agent.id}")
        
        # Update prompt
        stmt = (
            update(Agent)
            .where(Agent.id == agent.id)
            .values(system_prompt=NEW_PROMPT)
        )
        await session.execute(stmt)
        await session.commit()
        print("  ✓ Prompt updated successfully!")

if __name__ == "__main__":
    asyncio.run(update_qualifier_prompt())
