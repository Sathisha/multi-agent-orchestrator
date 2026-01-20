import asyncio
import logging
import sys
import os

# Add /app to python path
sys.path.append("/app")

from shared.database.connection import engine, Base
from shared.models.chat import ChatSession, ChatMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_tables():
    logger.info("Starting manual table creation...")
    try:
        # Import all models to ensure they are registered with Base
        import shared.models
        
        # Create non-async engine for direct creation (since connection.py has both)
        # Actually connection.py uses async_engine for create_tables usually, but let's try strict approach
        
        logger.info(f"Models registered: {list(Base.metadata.tables.keys())}")
        
        if 'chat_sessions' in Base.metadata.tables:
            logger.info("chat_sessions table found in metadata")
        else:
            logger.error("chat_sessions table NOT found in metadata")

        # Create tables using the sync engine
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully!")
        
    except Exception as e:
        logger.error(f"Error creating tables: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(create_tables())
