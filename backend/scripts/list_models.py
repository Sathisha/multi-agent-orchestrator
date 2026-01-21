import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.database.connection import get_database_session
from shared.models.llm_model import LLMModel
from sqlalchemy import select

async def main():
    async with get_database_session() as session:
        result = await session.execute(select(LLMModel))
        models = result.scalars().all()
        print('Available models:')
        for m in models:
            print(f'  - {m.name} ({m.provider})')

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
