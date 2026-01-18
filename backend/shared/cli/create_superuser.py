"""
CLI tool to create a super admin user.

Usage:
    python -m shared.cli.create_superuser --email admin@example.com --password SecurePass123!
"""

import argparse
import asyncio
import sys
from uuid import uuid4

from shared.database.connection import get_async_db
from shared.services.auth import AuthService
from shared.services.rbac import RBACService
from shared.models.user import User


async def create_superuser(email: str, password: str, full_name: str = "Super Administrator"):
    """Create a super admin user."""
    
    async for db in get_async_db():
        try:
            auth_service = AuthService(db)
            rbac_service = RBACService(db)
            
            # Check if user already exists
            existing_user = await auth_service.get_user_by_email(email)
            if existing_user:
                print(f"[ERROR] User with email {email} already exists.")
                return False
            
            # Create the user
            user = await auth_service.register_user(
                email=email,
                password=password,
                full_name=full_name
            )
            
            # Set is_superuser flag
            user.is_superuser = True
            await db.commit()
            await db.refresh(user)
            
            # Assign super_admin role
            try:
                super_admin_role = await rbac_service.get_role_by_name("super_admin")
                if super_admin_role:
                    await rbac_service.assign_role_to_user(user.id, super_admin_role.id)
                    print(f"[SUCCESS] Created super admin user: {email}")
                    print(f"  User ID: {user.id}")
                    print(f"  Role: super_admin")
                    return True
                else:
                    print(f"[WARNING] User created but 'super_admin' role not found. User is marked as superuser.")
                    print(f"  Email: {email}")
                    print(f"  User ID: {user.id}")
                    return True
            except Exception as e:
                print(f"[WARNING] User created but role assignment failed: {e}")
                print(f"  Email: {email}")
                print(f"  User ID: {user.id}")
                return True
                
        except Exception as e:
            print(f"[ERROR] Failed to create super admin user: {e}")
            return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Create a super admin user")
    parser.add_argument("--email", required=True, help="Email address for the super admin")
    parser.add_argument("--password", required=True, help="Password for the super admin")
    parser.add_argument("--name", default="Super Administrator", help="Full name of the super admin")
    
    args = parser.parse_args()
    
    print("\n[INFO] Creating super admin user...")
    print(f"  Email: {args.email}")
    print(f"  Name: {args.name}\n")
    
    success = asyncio.run(create_superuser(args.email, args.password, args.name))
    
    if success:
        print("\n[SUCCESS] Super admin created successfully!")
        print("\n[IMPORTANT] Please change the password after first login.\n")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
