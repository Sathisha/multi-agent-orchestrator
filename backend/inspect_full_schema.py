from sqlalchemy import create_engine, MetaData
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://app:app@db:5432/app")
engine = create_engine(DATABASE_URL)
metadata = MetaData()
metadata.reflect(bind=engine)

if 'roles' in metadata.tables:
    t = metadata.tables['roles']
    print(f"Table: {t.name}")
    for c in t.columns:
        print(f" - {c.name}: {c.type} (nullable={c.nullable})")
else:
    print("roles table not found!")
