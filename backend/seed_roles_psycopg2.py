import os
import uuid
import logging
import psycopg2
from psycopg2.extras import DictCursor

# Direct psycopg2 seeding
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://app:app@db:5432/app")

def seed():
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)
    log.info("Starting role seeding (psycopg2)...")
    
    default_roles = [
        {
            'name': 'view_user',
            'display_name': 'View User',
            'description': 'Can only view agents and workflows',
            'permission_level': 1,
            'is_system_role': True,
            'is_default': False
        },
        {
            'name': 'standard_user',
            'display_name': 'Standard User',
            'description': 'Can execute agents and workflows',
            'permission_level': 2,
            'is_system_role': True,
            'is_default': True
        },
        {
            'name': 'service_user',
            'display_name': 'Service User',
            'description': 'Can modify agents and workflows',
            'permission_level': 3,
            'is_system_role': True,
            'is_default': False
        },
        {
            'name': 'super_admin',
            'display_name': 'Super Administrator',
            'description': 'Full access',
            'permission_level': 4,
            'is_system_role': True,
            'is_default': False
        }
    ]

    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False # Explicit transaction
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        for role_data in default_roles:
            log.info(f"Processing {role_data['name']}")
            cursor.execute("SELECT id FROM roles WHERE name = %s", (role_data['name'],))
            existing = cursor.fetchone()
            
            if not existing:
                log.info(f"Inserting {role_data['name']}")
                role_id = str(uuid.uuid4())
                # Use literals to avoid binding issues
                sql = f"""
                    INSERT INTO roles (id, name, display_name, description, permission_level, is_system_role, is_default, created_at, updated_at, is_deleted)
                    VALUES ('{role_id}', '{role_data['name']}', '{role_data['display_name']}', '{role_data['description']}', {role_data['permission_level']}, {str(role_data['is_system_role']).lower()}, {str(role_data['is_default']).lower()}, NOW(), NOW(), false)
                """
                cursor.execute(sql)
            else:
                log.info(f"Role {role_data['name']} already exists")
        
        conn.commit()
        log.info("Seeding complete.")
        conn.close()

    except Exception as e:
        log.error(f"Seeding failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    seed()
