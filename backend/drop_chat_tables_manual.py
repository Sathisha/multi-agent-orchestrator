from shared.database.connection import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def drop_tables():
    try:
        with engine.connect() as conn:
            logger.info("Dropping chat_messages table...")
            conn.execute(text('DROP TABLE IF EXISTS chat_messages CASCADE'))
            
            logger.info("Dropping chat_sessions table...")
            conn.execute(text('DROP TABLE IF EXISTS chat_sessions CASCADE'))
            
            conn.commit()
            logger.info("Tables dropped successfully.")
    except Exception as e:
        logger.error(f"Error dropping tables: {e}")

if __name__ == "__main__":
    drop_tables()
