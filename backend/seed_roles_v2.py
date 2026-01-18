import uuid
import sys
import os
import logging
from sqlalchemy import create_engine, MetaData, Table, select, insert, update

# Robust seeding using Table Reflection
DATA_URL = os.getenv("DATABASE_URL", "postgresql://app:app@db:5432/app")
engine = create_engine(DATA_URL)

def seed():
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)
    log.info("Starting role seeding (v2 - reflection)...")
    
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    roles_table = metadata.tables['roles']
    permissions_table = metadata.tables['permissions']
    role_permissions_table = metadata.tables['role_permissions']
    
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
        with engine.begin() as conn:
            for role_data in default_roles:
                # Check
                stmt = select(roles_table.c.id).where(roles_table.c.name == role_data['name'])
                res = conn.execute(stmt)
                existing = res.fetchone()
                
                if not existing:
                    log.info(f"Inserting {role_data['name']}")
                    role_id = str(uuid.uuid4())
                    stmt = insert(roles_table).values(
                        id=role_id,
                        name=role_data['name'],
                        display_name=role_data['display_name'],
                        description=role_data['description'],
                        permission_level=role_data['permission_level'],
                        is_system_role=role_data['is_system_role'],
                        is_default=role_data['is_default']
                        # created_at defaults to server default if omitted? Yes usually.
                        # but if table requires check for NOT NULL usage.
                        # We hope models defined server_default.
                    )
                    conn.execute(stmt)
                else:
                    log.info(f"Role {role_data['name']} already exists")

            log.info("Seeding complete.")
            
    except Exception as e:
        log.error(f"Seeding failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    seed()
