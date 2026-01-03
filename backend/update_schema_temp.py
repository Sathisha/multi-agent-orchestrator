import asyncio
import sys
from pathlib import Path
from sqlalchemy import text

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from shared.database.connection import async_engine

async def main():
    try:
        async with async_engine.begin() as conn:
            print("🔄 Applying schema updates...")
            
            # active_edges
            print("Adding active_edges column...")
            await conn.execute(text("ALTER TABLE chain_executions ADD COLUMN IF NOT EXISTS active_edges JSONB DEFAULT '[]'::jsonb;"))
            
            # edge_results
            print("Adding edge_results column...")
            await conn.execute(text("ALTER TABLE chain_executions ADD COLUMN IF NOT EXISTS edge_results JSONB DEFAULT '{}'::jsonb;"))
            
            print("✅ Schema updates applied successfully.")
    except Exception as e:
        print(f"❌ Error applying schema updates: {e}")

if __name__ == "__main__":
    asyncio.run(main())
