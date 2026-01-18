from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://app:app@db:5432/app")
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        print("Columns in roles table:")
        res = conn.execute(text("SELECT column_name, is_nullable, data_type FROM information_schema.columns WHERE table_name = 'roles'"))
        for row in res:
            print(row)
except Exception as e:
    print(f"Error: {e}")
