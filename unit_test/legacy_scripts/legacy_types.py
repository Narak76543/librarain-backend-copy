import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.db import SessionLocal
from api.auth_user.models import TBL_AUTH_USER

def main():
    db = SessionLocal()
    users = db.query(TBL_AUTH_USER).all()
    for user in users:
        print(f"User: {user.email}, locked_reason type: {type(user.locked_reason)}, locked_reason: {repr(user.locked_reason)}")
        
if __name__ == "__main__":
    main()
