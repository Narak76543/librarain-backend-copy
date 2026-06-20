import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session
from core.db import get_db
from api.auth_user.models import TBL_AUTH_USER, TBL_AUTH_SESSION, TBL_AUTH_USER_ROLE, TBL_AUTH_ROLE
from config import configs

SECRET_KEY = configs.JWT_SECRET_KEY
ALGORITHM = configs.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = configs.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = configs.REFRESH_TOKEN_EXPIRE_DAYS

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/swagger-login"
)

def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = "Password must be 72 bytes or fewer",
        )

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, password_hash: str) -> bool:
    if len(plain_password.encode("utf-8")) > 72:
        return False

    return bcrypt.checkpw(plain_password.encode('utf-8'), password_hash.encode('utf-8'))

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def get_user_roles(db: Session, user_id) -> list[str]:
    roles = (
        db.query(TBL_AUTH_ROLE.role_code)
        .join(TBL_AUTH_USER_ROLE, TBL_AUTH_USER_ROLE.role_id == TBL_AUTH_ROLE.id)
        .filter(
            TBL_AUTH_USER_ROLE.user_id == user_id,
            TBL_AUTH_ROLE.is_active.is_(True),
        )
        .all()
    )

    return [role.role_code for role in roles]


def create_access_token(
    user : TBL_AUTH_USER,
    roles: list[str],
    session_id,
) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub"      : str(user.id),
        "email"    : user.email,
        "roles"    : roles,
        "sessionId": str(session_id),
        "type"     : "access",
        "iat"      : now,
        "exp"      : now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    user_id,
    session_id,
) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub"      : str(user_id),
        "sessionId": str(session_id),
        "type"     : "refresh",
        "iat"      : now,
        "exp"      : now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Invalid or expired token",
        )


def get_current_user(
    token: str     = Depends(oauth2_scheme),
    db   : Session = Depends(get_db),
) -> TBL_AUTH_USER:
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Invalid token type",
        )

    user_id    = payload.get("sub")
    session_id = payload.get("sessionId")

    if not user_id or not session_id:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Invalid token payload",
        )

    now = datetime.now(timezone.utc)

    session = (
        db.query(TBL_AUTH_SESSION)
        .filter(
            TBL_AUTH_SESSION.id == UUID(session_id),
            TBL_AUTH_SESSION.user_id == UUID(user_id),
            TBL_AUTH_SESSION.revoked_at.is_(None),
            TBL_AUTH_SESSION.expires_at > now,
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Session expired or revoked",
        )

    user = (
        db.query(TBL_AUTH_USER)
        .filter(
            TBL_AUTH_USER.id == UUID(user_id),
            TBL_AUTH_USER.deleted_at.is_(None),
            TBL_AUTH_USER.is_active.is_(True),
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "User not found or inactive",
        )

    return user

# ========= chekc if admin ? =========== 
def is_admin(db: Session, user_id) -> bool:
    result = (
        db.query(TBL_AUTH_ROLE)
        .join(TBL_AUTH_USER_ROLE, TBL_AUTH_USER_ROLE.role_id == TBL_AUTH_ROLE.id)
        .filter(
            TBL_AUTH_USER_ROLE.user_id == user_id,
            TBL_AUTH_ROLE.role_code    == "ADMIN",
            TBL_AUTH_ROLE.is_active.is_(True),
        )
        .first()
    )
    return result is not None


def require_admin(
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
) -> TBL_AUTH_USER:
    if not is_admin(db, current_user.id):
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Admin access required",
        )
    return current_user