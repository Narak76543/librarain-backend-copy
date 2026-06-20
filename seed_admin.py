import sys
import os
from getpass import getpass

# Add current directory to path so it can find 'core' and 'api'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.db import Session
from api.auth_user.models import TBL_AUTH_USER, TBL_AUTH_ROLE, TBL_AUTH_USER_ROLE
from api.user_profile.models import TBL_USER_PROFILE  # imported to resolve mapper error
from api.auth_user.security import hash_password

def seed_admin():
    db = Session()
    try:
        print("=== Seed Admin User ===")
        full_name = input("Enter Admin Full Name [Admin]: ").strip() or "Admin"
        email = input("Enter Admin Email [admin@example.com]: ").strip() or "admin@example.com"
        
        # Check if user already exists
        existing_user = db.query(TBL_AUTH_USER).filter(TBL_AUTH_USER.email == email).first()
        if existing_user:
            print(f"Error: A user with the email '{email}' already exists.")
            return

        password = getpass("Enter Admin Password: ").strip()
        if not password:
            print("Error: Password cannot be empty.")
            return

        # 1. Create the user
        admin_user = TBL_AUTH_USER(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            is_active=True,
            is_verified=True,  # Admins should be verified by default
        )
        db.add(admin_user)
        db.flush()

        # 2. Get or create the ADMIN role
        admin_role = db.query(TBL_AUTH_ROLE).filter(TBL_AUTH_ROLE.role_code == "ADMIN").first()
        if not admin_role:
            admin_role = TBL_AUTH_ROLE(
                role_code="ADMIN",
                role_name="Administrator",
                description="System administrator role",
                is_active=True,
            )
            db.add(admin_role)
            db.flush()

        # 3. Link user and role
        user_role = TBL_AUTH_USER_ROLE(
            user_id=admin_user.id,
            role_id=admin_role.id,
        )
        db.add(user_role)

        db.commit()
        print(f"\nSuccess! Admin user '{email}' has been created successfully.")

    except Exception as e:
        db.rollback()
        print(f"\nFailed to create admin user. Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
