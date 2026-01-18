from sqlalchemy import create_engine, text
import os
import uuid

# Create a local engine from scratch to test libraries
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://app:app@db:5432/app")
engine = create_engine(DATABASE_URL)

try:
    with engine.begin() as conn:
        print("Connection successful.")
        result = conn.execute(text("SELECT 1"))
        print(f"SELECT 1 result: {result.fetchone()}")
        
        # Test Boolean Binding
        try:
             print("Testing boolean binding...")
             conn.execute(text("CREATE TABLE IF NOT EXISTS test_bool (val BOOLEAN)"))
             # Using parameters=kwarg syntax just to be safe
             conn.execute(text("INSERT INTO test_bool (val) VALUES (:val)"), {"val": True})
             check = conn.execute(text("SELECT * FROM test_bool"))
             print(f"Bool check: {check.fetchone()}")
             conn.execute(text("DROP TABLE test_bool"))
             print("Boolean binding Success")
        except Exception as e:
             print(f"Boolean binding Failed: {e}")
             
        # Test REAL Role Insert using Literals for Booleans
        print("Testing Role Insert with Literals...")
        role_id = str(uuid.uuid4())
        # Note: We use {role_id} f-string but params for others if mixed? 
        # Let's try explicit SQL without params for booleans first.
        # :is_system_role -> true
        stmt = text("INSERT INTO roles (id, name, display_name, description, permission_level, is_system_role, is_default, created_at, updated_at) VALUES (:id, :name, :display_name, :description, :permission_level, true, false, NOW(), NOW())")
        
        # We leave out booleans from params since they are literals now
        params = {
                 'id': role_id,
                 'name': 'test_literal_bools',
                 'display_name': 'Test Lit Bools',
                 'description': 'Test',
                 'permission_level': 1
        }
        conn.execute(stmt, params)
        print("Role Insert with Boolean Literals Success")
        
        # Cleanup
        conn.execute(text("DELETE FROM roles WHERE id = :id"), {"id": role_id})

except Exception as e:
    print(f"Script failed: {e}")
    # raise
