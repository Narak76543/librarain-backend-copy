import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.db import Session
from api.auth_user.models import TBL_AUTH_USER, TBL_AUTH_ROLE, TBL_AUTH_USER_ROLE
from api.user_profile.models import TBL_USER_PROFILE
from api.auth_user.security import hash_password

def seed_admin_programmatic():
    db = Session()
    try:
        # Create Admin Role
        admin_role = db.query(TBL_AUTH_ROLE).filter(TBL_AUTH_ROLE.role_code == "ADMIN").first()
        if not admin_role:
            admin_role = TBL_AUTH_ROLE(
                role_code="ADMIN",
                role_name="Administrator",
                description="System administrator role",
                is_active=True,
            )
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)

        # Create Admin User
        admin_user = db.query(TBL_AUTH_USER).filter(TBL_AUTH_USER.email == "admin@example.com").first()
        if not admin_user:
            admin_user = TBL_AUTH_USER(
                full_name="Admin",
                email="admin@example.com",
                password_hash=hash_password("password123"),
                is_active=True,
                is_verified=True,
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

        # Link User and Role
        user_role = db.query(TBL_AUTH_USER_ROLE).filter(
            TBL_AUTH_USER_ROLE.user_id == admin_user.id,
            TBL_AUTH_USER_ROLE.role_id == admin_role.id
        ).first()
        
        if not user_role:
            user_role = TBL_AUTH_USER_ROLE(
                user_id=admin_user.id,
                role_id=admin_role.id,
            )
            db.add(user_role)
            db.commit()

        print("Admin user seeded successfully. email: admin@example.com, pass: password123")
    except Exception as e:
        db.rollback()
        print(f"Error seeding admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin_programmatic()
