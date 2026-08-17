# from datetime import datetime, timedelta, timezone
# from json import JSONDecodeError
# import json as json_lib
# import logging
# import os
# import random
# import subprocess
# from typing import Any
# from urllib.parse import parse_qs
# from uuid import uuid4
# from fastapi import Depends, HTTPException, Query, Request, status , Body
# from fastapi.encoders import jsonable_encoder
# from fastapi.responses import FileResponse, JSONResponse
# from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
# from sqlalchemy import or_
# from sqlalchemy.orm import Session
# from core.fcm import notify_password_reset
# from main import app
# from config import configs
# from core.db import get_db
# from api.auth_user import schemas
# from api.auth_user.models import (
#     TBL_AUTH_USER,
#     TBL_AUTH_ROLE,
#     TBL_AUTH_USER_ROLE,
#     TBL_AUTH_SESSION,
#     TBL_AUTH_LOGIN_LOG,
#     OtpCode,
# )
# from sqlalchemy import nulls_last
# from api.auth_user.security import (
#     ACCESS_TOKEN_EXPIRE_MINUTES,
#     REFRESH_TOKEN_EXPIRE_DAYS,
#     hash_password,
#     require_admin,
#     verify_password,
#     hash_token,
#     create_access_token,
#     create_refresh_token,
#     decode_token,
#     get_user_roles,
#     get_current_user,
# )

# logger = logging.getLogger(__name__)

# def response(ok: bool, status_code: int, message: str, data=None):
#     return JSONResponse(
#         status_code=status_code,
#         content={
#             "ok"     : ok,
#             "status" : status_code,
#             "message": message,
#             "data"   : data,
#         },
#     )

# def get_mail_config() -> ConnectionConfig:
#     if (
#         not configs.MAIL_USERNAME
#         or not configs.MAIL_PASSWORD
#         or not configs.MAIL_FROM
#         or configs.MAIL_USERNAME == "yourgmail@gmail.com"
#         or configs.MAIL_FROM == "yourgmail@gmail.com"
#         or configs.MAIL_PASSWORD == "xxxxxxxxxxxxxxxx"
#     ):
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Email service is not configured",
#         )

#     return ConnectionConfig(
#         MAIL_USERNAME   = configs.MAIL_USERNAME,
#         MAIL_PASSWORD   = configs.MAIL_PASSWORD,
#         MAIL_FROM       = configs.MAIL_FROM,
#         MAIL_PORT       = configs.MAIL_PORT,
#         MAIL_SERVER     = configs.MAIL_SERVER,
#         MAIL_STARTTLS   = True,
#         MAIL_SSL_TLS    = False,
#         USE_CREDENTIALS = True,
#         VALIDATE_CERTS  = True,
#     )

# async def send_otp_email(email: str, otp_code: str):
#     message = MessageSchema(
#         subject    = "Your password reset OTP",
#         recipients = [email],
#         body       = f"Your password reset OTP is {otp_code}. It expires in 10 minutes.",
#         subtype    = "plain",
#     )

#     await FastMail(get_mail_config()).send_message(message)

# def get_client_ip(request: Request):
#     forwarded_for = request.headers.get("x-forwarded-for")

#     if forwarded_for:
#         return forwarded_for.split(",")[0].strip()

# from fastapi import APIRouter, Depends, Query, Request
# from fastapi import status
# from sqlalchemy.orm import Session
# from sqlalchemy import or_
# from typing import List
# from datetime import datetime, timezone, timedelta
# import uuid
# import secrets
# import string

# from main import app
# from core.db import get_db
# from api.auth_user.security import hash_password, verify_password, create_access_token

# from core.logger import write_log, LogAction, LogModule
# from api.auth_user import schemas
# from api.auth_user.models import (
#     TBL_AUTH_USER,
#     TBL_AUTH_ROLE,
#     TBL_AUTH_USER_ROLE,
#     TBL_AUTH_SESSION,
#     TBL_AUTH_LOGIN_LOG,
# )



# def get_client_ip(request: Request):
#     if not request:
#         return None

#     # standard forward
#     forwarded = request.headers.get("x-forwarded-for")
#     if forwarded:
#         return forwarded.split(",")[0].strip()

#     # direct client
#     if request.client:
#         return request.client.host

#     return None

# def write_login_log(
#     db          : Session,
#     request     : Request,
#     email       : str,
#     login_status: str,
#     user_id=None,
#     failure_reason: str | None = None,
# ):
#     log = TBL_AUTH_LOGIN_LOG(
#         user_id        = user_id,
#         email          = email,
#         login_status   = login_status,
#         ip_address     = get_client_ip(request),
#         user_agent     = request.headers.get("user-agent"),
#         failure_reason = failure_reason,
#     )
#     db.add(log)

#     # Write to System Log
#     if login_status == "SUCCESS":
#         write_log(
#             db          = db,
#             action      = LogAction.USER_LOGIN_SUCCESS,
#             module      = LogModule.AUTH,
#             description = f"User logged in: {email}",
#             user_id     = user_id,
#             user_email  = email,
#             entity_type = "user",
#             entity_id   = str(user_id) if user_id else None,
#             request     = request,
#             commit      = False,
#         )
#     else:
#         write_log(
#             db          = db,
#             action      = LogAction.USER_LOGIN_FAILED,
#             module      = LogModule.AUTH,
#             level       = "WARNING",
#             status      = "FAILED",
#             description = f"Login failed for: {email} — reason: {failure_reason}",
#             user_email  = email,
#             new_value   = {"reason": failure_reason},
#             request     = request,
#             commit      = False,
#         )

# def serialize_user(user: TBL_AUTH_USER):
#     return {
#         "id":          str(user.id),
#         "full_name":   user.full_name,
#         "email":       user.email,
#         "phone":       user.phone,
#         "is_active":   user.is_active,
#         "is_verified": user.is_verified,
#         "failed_login_attempts": user.failed_login_attempts or 0,
#         "locked_until": user.locked_until.isoformat() if user.locked_until else None,
#         "locked_at": user.locked_at.isoformat() if user.locked_at else None,
#         "locked_reason": user.locked_reason,
#         "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
#         "created_at": user.created_at.isoformat() if user.created_at else None,
#     }

# @app.post("/api/v1/auth/register", tags=["Auth"])
# def register_user(
#     request: Request,
#     payload: schemas.RegisterRequest,
#     db     : Session = Depends(get_db),
# ):
#     existing_user = (
#         db.query(TBL_AUTH_USER)
#         .filter(TBL_AUTH_USER.email == payload.email)
#         .first()
#     )

#     if existing_user:
#         return response(
#             ok          = False,
#             status_code = status.HTTP_400_BAD_REQUEST,
#             message     = "Email already exists",
#         )

#     new_user = TBL_AUTH_USER(
#         full_name     = payload.full_name,
#         email         = payload.email,
#         phone         = payload.phone,
#         password_hash = hash_password(payload.password),
#         is_active     = True,
#         is_verified   = False,
#     )

#     db.add(new_user)
#     db.flush()

#     # Get or create default USER role
#     default_role = (
#         db.query(TBL_AUTH_ROLE)
#         .filter(TBL_AUTH_ROLE.role_code == "USER")
#         .first()
#     )

#     if not default_role:
#         default_role = TBL_AUTH_ROLE(
#             role_code   = "USER",
#             role_name   = "User",
#             description = "Default application user role",
#             is_active   = True,
#         )
#         db.add(default_role)
#         db.flush()

#     user_role = TBL_AUTH_USER_ROLE(
#         user_id = new_user.id,
#         role_id = default_role.id,
#     )

#     db.add(user_role)
#     db.commit()
#     db.refresh(new_user)

#     write_log(
#         db          = db,
#         action      = LogAction.USER_REGISTERED,
#         module      = LogModule.AUTH,
#         description = f"New user registered: {payload.email}",
#         user_id     = new_user.id,
#         user_email  = new_user.email,
#         user_role   = "USER",
#         entity_type = "user",
#         entity_id   = str(new_user.id),
#         new_value   = {"email": new_user.email, "full_name": new_user.full_name},
#         request     = request,
#         commit      = True,
#     )

#     user_data = serialize_user(new_user)

#     return response(
#         ok          = True,
#         status_code = status.HTTP_201_CREATED,
#         message     = "User registered successfully",
#         data        = user_data,
#     )
# def is_account_locked(user: TBL_AUTH_USER, now: datetime) -> bool:
#     return user.locked_until is not None and user.locked_until > now


# def reset_user_attempt(user: TBL_AUTH_USER):
#     user.failed_login_attempts = 0
#     user.locked_until          = None
#     user.locked_at             = None
#     user.locked_reason         = None


# def increase_failed_attempt(user: TBL_AUTH_USER, now: datetime):
#     user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

#     if user.failed_login_attempts >= configs.MAX_FAILED_LOGIN_ATTEMPTS:
#         user.locked_at = now
#         user.locked_until = now + timedelta(
#             minutes=configs.ACCOUNT_LOCK_MINUTES
#         )
#         user.locked_reason = "TOO_MANY_FAILED_ATTEMPTS"

# @app.post(
#     "/api/v1/auth/login",
#     tags           = ["Auth"],
#     response_model = schemas.ApiResponse,
#     summary        = "Login User",
# )
# async def login_user(
#     request: Request,
#     payload: schemas.LoginRequest,
#     db     : Session = Depends(get_db),
# ):
#     user = (
#         db.query(TBL_AUTH_USER)
#         .filter(
#             TBL_AUTH_USER.email == payload.email,
#             TBL_AUTH_USER.deleted_at.is_(None),
#         )
#         .first()
#     )

#     if not user:
#         write_login_log(
#             db             = db,
#             request        = request,
#             email          = payload.email,
#             login_status   = "FAILED",
#             failure_reason = "USER_NOT_FOUND",
#         )
#         db.commit()

#         return response(
#             ok          = False,
#             status_code = status.HTTP_401_UNAUTHORIZED,
#             message     = "Invalid email or password",
#         )

#     if not user.is_active:
        
#         write_login_log(
#             db             = db,
#             request        = request,
#             email          = payload.email,
#             login_status   = "FAILED",
#             user_id        = user.id,
#             failure_reason = "USER_INACTIVE",
#         )
#         db.commit()

#         return response(
#             ok          = False,
#             status_code = status.HTTP_403_FORBIDDEN,
#             message     = "User account is inactive",
#         )
#     now = datetime.now(timezone.utc)

#     if is_account_locked(user, now):
#         write_login_log(
#             db             = db,
#             request        = request,
#             email          = payload.email,
#             login_status   = "FAILED",
#             user_id        = user.id,
#             failure_reason = "ACCOUNT_LOCKED",
#         )
#         db.commit()

#         return response(
#             ok          = False,
#             status_code = status.HTTP_423_LOCKED,
#             message     = "Account is locked due to too many failed login attempts.",
#             data={
#                 "lockedUntil": user.locked_until.isoformat(),
#             },
#         )

#     if not verify_password(payload.password, user.password_hash):
#         increase_failed_attempt(user, now)

#         write_login_log(
#             db             = db,
#             request        = request,
#             email          = payload.email,
#             login_status   = "FAILED",
#             user_id        = user.id,
#             failure_reason = "INVALID_PASSWORD",
#         )

#         db.commit()

#         remaining_attempts = (
#             configs.MAX_FAILED_LOGIN_ATTEMPTS - user.failed_login_attempts
#         )

#         if user.locked_until:
#             return response(
#                 ok          = False,
#                 status_code = status.HTTP_423_LOCKED,
#                 message     = "Account locked due to too many failed login attempts.",
#                 data={
#                     "lockedUntil": user.locked_until.isoformat(),
#                 },
#             )

#         return response(
#             ok          = False,
#             status_code = status.HTTP_401_UNAUTHORIZED,
#             message     = "Invalid email or password",
#             data={
#                 "remainingAttempts": max(remaining_attempts, 0),
#             },
#         )

#     session_id         = uuid4()
#     reset_user_attempt(user)

#     refresh_expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
#     roles = get_user_roles(db, user.id)

#     access_token = create_access_token(
#         user       = user,
#         roles      = roles,
#         session_id = session_id,
#     )

#     refresh_token = create_refresh_token(
#         user_id    = user.id,
#         session_id = session_id,
#     )

#     if configs.SINGLE_SESSION_LOGIN:
#         db.query(TBL_AUTH_SESSION).filter(
#             TBL_AUTH_SESSION.user_id == user.id,
#             TBL_AUTH_SESSION.revoked_at.is_(None),
#         ).update(
#             {
#                 "revoked_at"    : now,
#                 "revoked_reason": "NEW_LOGIN",
#             },
#             synchronize_session = False,
#         )

#     new_session = TBL_AUTH_SESSION(
#         id                 = session_id,
#         user_id            = user.id,
#         refresh_token_hash = hash_token(refresh_token),
#         device_id          = request.headers.get("x-device-id"),
#         device_name        = request.headers.get("x-device-name"),
#         user_agent         = request.headers.get("user-agent"),
#         ip_address         = get_client_ip(request),
#         issued_at          = now,
#         expires_at         = refresh_expires_at,
#     )

#     user.last_login_at = now
#     db.add(new_session)

#     write_login_log(
#         db           = db,
#         request      = request,
#         email        = payload.email,
#         login_status = "SUCCESS",
#         user_id      = user.id,
#     )

#     db.commit()

#     user_data = serialize_user(user)

#     return response(
#         ok          = True,
#         status_code = status.HTTP_200_OK,
#         message     = "Login successfully",
#         data={
#             "accessToken" : access_token,
#             "refreshToken": refresh_token,
#             "tokenType"   : "bearer",
#             "expiresIn"   : ACCESS_TOKEN_EXPIRE_MINUTES * 60,
#             "roles"       : roles,
#             "user"        : user_data,
#         },
#     )


# @app.post("/api/v1/auth/refresh-token", tags=["Auth"])
# def refresh_token(
#     payload: schemas.RefreshTokenRequest,
#     db: Session = Depends(get_db),
# ):
#     token_data = decode_token(payload.refresh_token)

#     if token_data.get("type") != "refresh":
#         return response(
#             ok          = False,
#             status_code = status.HTTP_401_UNAUTHORIZED,
#             message     = "Invalid token type",
#         )

#     user_id = token_data.get("sub")
#     session_id = token_data.get("sessionId")

#     if not user_id or not session_id:
#         return response(
#             ok          = False,
#             status_code = status.HTTP_401_UNAUTHORIZED,
#             message     = "Invalid token payload",
#         )

#     now = datetime.now(timezone.utc)

#     session = (
#         db.query(TBL_AUTH_SESSION)
#         .filter(
#             TBL_AUTH_SESSION.id == session_id,
#             TBL_AUTH_SESSION.user_id == user_id,
#             TBL_AUTH_SESSION.refresh_token_hash == hash_token(payload.refresh_token),
#             TBL_AUTH_SESSION.revoked_at.is_(None),
#             TBL_AUTH_SESSION.expires_at > now,
#         )
#         .first()
#     )

#     if not session:
#         return response(
#             ok          = False,
#             status_code = status.HTTP_401_UNAUTHORIZED,
#             message     = "Refresh token expired or revoked",
#         )

#     user = (
#         db.query(TBL_AUTH_USER)
#         .filter(
#             TBL_AUTH_USER.id == user_id,
#             TBL_AUTH_USER.deleted_at.is_(None),
#             TBL_AUTH_USER.is_active.is_(True),
#         )
#         .first()
#     )

#     if not user:
#         return response(
#             ok          = False,
#             status_code = status.HTTP_401_UNAUTHORIZED,
#             message     = "User not found or inactive",
#         )

#     roles = get_user_roles(db, user.id)

#     new_access_token = create_access_token(
#         user       = user,
#         roles      = roles,
#         session_id = session.id,
#     )

#     new_refresh_token = create_refresh_token(
#         user_id    = user.id,
#         session_id = session.id,
#     )

#     session.refresh_token_hash = hash_token(new_refresh_token)
#     session.expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

#     db.commit()

#     return response(
#         ok          = True,
#         status_code = status.HTTP_200_OK,
#         message     = "Token refreshed successfully",
#         data={
#             "accessToken" : new_access_token,
#             "refreshToken": new_refresh_token,
#             "tokenType"   : "bearer",
#             "expiresIn"   : ACCESS_TOKEN_EXPIRE_MINUTES * 60,
#         },
#     )


# @app.post("/api/v1/auth/logout", tags=["Auth"])
# def logout_user(
#     payload: schemas.LogoutRequest,
#     db     : Session = Depends(get_db),
# ):
#     token_data = decode_token(payload.refresh_token)

#     if token_data.get("type") != "refresh":
#         return response(
#             ok          = False,
#             status_code = status.HTTP_401_UNAUTHORIZED,
#             message     = "Invalid token type",
#         )

#     session_id = token_data.get("sessionId")
#     user_id    = token_data.get("sub")

#     session = (
#         db.query(TBL_AUTH_SESSION)
#         .filter(
#             TBL_AUTH_SESSION.id == session_id,
#             TBL_AUTH_SESSION.user_id == user_id,
#             TBL_AUTH_SESSION.refresh_token_hash == hash_token(payload.refresh_token),
#             TBL_AUTH_SESSION.revoked_at.is_(None),
#         )
#         .first()
#     )

#     if session:
#         session.revoked_at = datetime.now(timezone.utc)
#         session.revoked_reason = "USER_LOGOUT"
#         db.commit()

#     return response(
#         ok          = True,
#         status_code = status.HTTP_200_OK,
#         message     = "Logout successfully",
#     )


# from google.oauth2 import id_token
# from google.auth.transport import requests

# @app.post(
#     "/api/v1/auth/google-login",
#     tags           = ["Auth"],
#     response_model = schemas.ApiResponse,
#     summary        = "Login with Google",
# )
# async def google_login(
#     request: Request,
#     payload: schemas.GoogleLoginRequest,
#     db     : Session = Depends(get_db),
# ):
#     try:
#         # If GOOGLE_CLIENT_ID is set in env, we pass it. If not, we still verify but bypass strict audience check
#         client_id = os.environ.get("GOOGLE_CLIENT_ID")
#         try:
#             idinfo = id_token.verify_oauth2_token(
#                 payload.id_token, requests.Request(), client_id
#             )
#         except ValueError as e:
#             logger.exception("Failed to verify Google Token strict")
#             # Fallback if client ID doesn't match perfectly or is absent, but token is valid
#             idinfo = id_token.verify_oauth2_token(
#                 payload.id_token, requests.Request()
#             )

#         if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
#             raise ValueError("Wrong issuer.")

#         email = idinfo["email"]
#         full_name = idinfo.get("name", "Google User")

#     except Exception as e:
#         logger.exception("Google token verification failed")
#         return response(
#             ok          = False,
#             status_code = status.HTTP_401_UNAUTHORIZED,
#             message     = "Invalid Google Token",
#         )

#     user = (
#         db.query(TBL_AUTH_USER)
#         .filter(
#             TBL_AUTH_USER.email == email,
#             TBL_AUTH_USER.deleted_at.is_(None),
#         )
#         .first()
#     )

#     now = datetime.now(timezone.utc)

#     if not user:
#         import secrets
#         from api.auth_user.security import hash_password
        
#         # Create new user
#         user = TBL_AUTH_USER(
#             full_name     = full_name,
#             email         = email,
#             phone         = None,
#             password_hash = hash_password(secrets.token_urlsafe(32)),
#             is_active     = True,
#             is_verified   = True, # Google emails are already verified
#         )

#         db.add(user)
#         db.flush()

#         # Get or create default USER role
#         default_role = (
#             db.query(TBL_AUTH_ROLE)
#             .filter(TBL_AUTH_ROLE.role_code == "USER")
#             .first()
#         )

#         if not default_role:
#             default_role = TBL_AUTH_ROLE(
#                 role_code   = "USER",
#                 role_name   = "User",
#                 description = "Default application user role",
#                 is_active   = True,
#             )
#             db.add(default_role)
#             db.flush()

#         user_role = TBL_AUTH_USER_ROLE(
#             user_id = user.id,
#             role_id = default_role.id,
#         )

#         db.add(user_role)
#         db.commit()
#         db.refresh(user)
#     else:
#         if not user.is_active:
#             return response(
#                 ok          = False,
#                 status_code = status.HTTP_403_FORBIDDEN,
#                 message     = "User account is inactive",
#             )
#         if is_account_locked(user, now):
#             return response(
#                 ok          = False,
#                 status_code = status.HTTP_423_LOCKED,
#                 message     = "Account is locked due to too many failed login attempts.",
#             )

#     session_id         = uuid4()
#     reset_user_attempt(user)

#     refresh_expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
#     roles = get_user_roles(db, user.id)

#     access_token = create_access_token(
#         user       = user,
#         roles      = roles,
#         session_id = session_id,
#     )

#     refresh_token = create_refresh_token(
#         user_id    = user.id,
#         session_id = session_id,
#     )

#     if configs.SINGLE_SESSION_LOGIN:
#         db.query(TBL_AUTH_SESSION).filter(
#             TBL_AUTH_SESSION.user_id == user.id,
#             TBL_AUTH_SESSION.revoked_at.is_(None),
#         ).update(
#             {
#                 "revoked_at"    : now,
#                 "revoked_reason": "NEW_LOGIN",
#             },
#             synchronize_session = False,
#         )

#     new_session = TBL_AUTH_SESSION(
#         id                 = session_id,
#         user_id            = user.id,
#         refresh_token_hash = hash_token(refresh_token),
#         device_id          = payload.device_id or request.headers.get("x-device-id"),
#         device_name        = payload.device_name or request.headers.get("x-device-name"),
#         user_agent         = request.headers.get("user-agent"),
#         ip_address         = get_client_ip(request),
#         issued_at          = now,
#         expires_at         = refresh_expires_at,
#     )

#     user.last_login_at = now
#     db.add(new_session)

#     write_login_log(
#         db           = db,
#         request      = request,
#         email        = email,
#         login_status = "SUCCESS",
#         user_id      = user.id,
#     )

#     db.commit()

#     user_data = serialize_user(user)

#     return response(
#         ok          = True,
#         status_code = status.HTTP_200_OK,
#         message     = "Login successfully",
#         data={
#             "accessToken" : access_token,
#             "refreshToken": refresh_token,
#             "tokenType"   : "bearer",
#             "expiresIn"   : ACCESS_TOKEN_EXPIRE_MINUTES * 60,
#             "roles"       : roles,
#             "user"        : user_data,
#         },
#     )


# @app.get("/api/v1/auth/me", tags=["Auth"])
# def get_me(
#     current_user: TBL_AUTH_USER = Depends(get_current_user),
#     db          : Session       = Depends(get_db),
# ):
#     roles     = get_user_roles(db, current_user.id)
#     user_data = serialize_user(current_user)

#     return response(
#         ok          = True,
#         status_code = status.HTTP_200_OK,
#         message     = "Current user retrieved successfully",
#         data={
#             "user" : user_data,
#             "roles": roles,
#         },
#     )
# # ================ reset attempt api ==================================
# @app.post("/api/v1/auth/reset-attempt", tags=["Auth"])
# def reset_login_attempt(
#     payload: schemas.ResetAttemptRequest,
#     db     : Session = Depends(get_db),
# ):
#     user = (
#         db.query(TBL_AUTH_USER)
#         .filter(
#             TBL_AUTH_USER.email == payload.email,
#             TBL_AUTH_USER.deleted_at.is_(None),
#         )
#         .first()
#     )

#     if not user:
#         return response(
#             ok          = False,
#             status_code = status.HTTP_404_NOT_FOUND,
#             message     = "User not found",
#         )

#     reset_user_attempt(user)
#     db.commit()

#     return response(
#         ok          = True,
#         status_code = status.HTTP_200_OK,
#         message     = "Login attempt reset successfully",
#         data={
#             "email"              : user.email,
#             "failedLoginAttempts": user.failed_login_attempts,
#             "lockedUntil"        : None,
#         },
#     )

# # ================= forgot password api ===========================
# @app.post("/api/v1/auth/forgot-password", tags=["Auth"])
# async def forgot_password(
#     payload: schemas.ForgotPasswordRequest,
#     db     : Session = Depends(get_db),
# ):
#     user = (
#         db.query(TBL_AUTH_USER)
#         .filter(
#             TBL_AUTH_USER.email == payload.email,
#             TBL_AUTH_USER.deleted_at.is_(None),
#         )
#         .first()
#     )

#     if not user:
#         return response(
#             ok          = False,
#             status_code = status.HTTP_404_NOT_FOUND,
#             message     = "User not found",
#         )

#     channel = payload.channel or "email"

#     if channel == "telegram":
#         if not user.telegram_chat_id:
#             return response(
#                 ok          = False,
#                 status_code = status.HTTP_400_BAD_REQUEST,
#                 message     = "Telegram account is not linked. Please select Email instead.",
#             )

#     otp_code = f"{random.SystemRandom().randint(0, 999999):06d}"
#     now = datetime.utcnow()

#     db.query(OtpCode).filter(
#         OtpCode.email == payload.email,
#         OtpCode.used.is_(False),
#     ).update(
#         {"used": True},
#         synchronize_session=False,
#     )

#     db.add(
#         OtpCode(
#             email      = payload.email,
#             code       = otp_code,
#             expires_at = now + timedelta(minutes=10),
#             used       = False,
#         )
#     )
#     db.commit()

#     if channel == "telegram":
#         try:
#             from api.telegram_bots.bot_polling import send_telegram_message
#             await send_telegram_message(
#                 user.telegram_chat_id,
#                 f"🔐 *Librarain Password Reset OTP*\n\nYour OTP code is: `{otp_code}`\n\nIt expires in 10 minutes."
#             )
#         except Exception as e:
#             logger.exception("Failed to send telegram OTP message")
#             db.query(OtpCode).filter(
#                 OtpCode.email == payload.email,
#                 OtpCode.code == otp_code,
#                 OtpCode.used.is_(False),
#             ).delete(synchronize_session=False)
#             db.commit()
#             return response(
#                 ok          = False,
#                 status_code = status.HTTP_502_BAD_GATEWAY,
#                 message     = f"Failed to send Telegram message: {str(e)}",
#             )
#     else:
#         # Email channel
#         try:
#             await send_otp_email(payload.email, otp_code)
#         except HTTPException:
#             db.query(OtpCode).filter(
#                 OtpCode.email == payload.email,
#                 OtpCode.code == otp_code,
#                 OtpCode.used.is_(False),
#             ).delete(synchronize_session=False)
#             db.commit()
#             raise
#         except Exception:
#             db.query(OtpCode).filter(
#                 OtpCode.email == payload.email,
#                 OtpCode.code == otp_code,
#                 OtpCode.used.is_(False),
#             ).delete(synchronize_session=False)
#             db.commit()
#             logger.exception("Failed to send password reset OTP email")

#             return response(
#                 ok          = False,
#                 status_code = status.HTTP_502_BAD_GATEWAY,
#                 message     = "Failed to send OTP email. Check Gmail app password settings.",
#             )

#     return {"message": "OTP sent"}


# @app.post("/api/v1/auth/verify-otp", tags=["Auth"])
# def verify_otp(
#     payload: schemas.VerifyOtpRequest,
#     db     : Session = Depends(get_db),
# ):
#     otp = (
#         db.query(OtpCode)
#         .filter(
#             OtpCode.email == payload.email,
#             OtpCode.used.is_(False),
#         )
#         .order_by(OtpCode.created_at.desc())
#         .first()
#     )

#     if not otp:
#         return response(
#             ok          = False,
#             status_code = status.HTTP_400_BAD_REQUEST,
#             message     = "Invalid or expired OTP",
#         )

#     now = datetime.utcnow()

#     if otp.expires_at < now:
#         otp.used = True
#         db.commit()

#         return response(
#             ok          = False,
#             status_code = status.HTTP_400_BAD_REQUEST,
#             message     = "OTP expired",
#         )

#     if otp.code != payload.otp_code:
#         return response(
#             ok          = False,
#             status_code = status.HTTP_400_BAD_REQUEST,
#             message     = "Invalid OTP",
#         )

#     otp.used = True
#     db.commit()

#     return {"message": "OTP verified"}


# # ================= reset password api ===========================
# @app.post("/api/v1/auth/reset-password", tags=["Auth"])
# def reset_password(
#     request: Request,
#     payload: schemas.ResetPasswordRequest,
#     db     : Session = Depends(get_db),
# ):
#     user = (
#         db.query(TBL_AUTH_USER)
#         .filter(
#             TBL_AUTH_USER.email == payload.email,
#             TBL_AUTH_USER.deleted_at.is_(None),
#         )
#         .first()
#     )

#     if not user:
#         return response(
#             ok          = False,
#             status_code = status.HTTP_404_NOT_FOUND,
#             message     = "User not found",
#         )

#     now_utc = datetime.utcnow()
#     verified_otp = (
#         db.query(OtpCode)
#         .filter(
#             OtpCode.email == payload.email,
#             OtpCode.used.is_(True),
#             OtpCode.expires_at >= now_utc,
#         )
#         .order_by(OtpCode.created_at.desc())
#         .first()
#     )

#     if not verified_otp:
#         return response(
#             ok          = False,
#             status_code = status.HTTP_400_BAD_REQUEST,
#             message     = "OTP verification required",
#         )

#     now = datetime.now(timezone.utc)
#     user.password_hash       = hash_password(payload.new_password)
#     user.password_changed_at = now
#     reset_user_attempt(user)

#     db.query(TBL_AUTH_SESSION).filter(
#         TBL_AUTH_SESSION.user_id == user.id,
#         TBL_AUTH_SESSION.revoked_at.is_(None),
#     ).update(
#         {
#             "revoked_at"    : now,
#             "revoked_reason": "PASSWORD_RESET",
#         },
#         synchronize_session=False,
#     )

#     db.query(OtpCode).filter(
#         OtpCode.email == payload.email,
#     ).delete(synchronize_session=False)

#     db.commit()
#     notify_password_reset(db=db, user_id=user.id)

#     write_log(
#         db          = db,
#         action      = LogAction.PASSWORD_RESET_SUCCESS,
#         module      = LogModule.AUTH,
#         description = f"Password reset successful for: {user.email}",
#         user_id     = user.id,
#         user_email  = user.email,
#         entity_type = "user",
#         entity_id   = str(user.id),
#         request     = request,
#         commit      = True,
#     )

#     return {"message": "Password reset successful"}


# @app.post("/api/v1/auth/change-password", tags=["Auth"])
# def change_password(
#     payload: schemas.ChangePasswordRequest,
#     current_user: TBL_AUTH_USER = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     if not verify_password(payload.current_password, current_user.password_hash):
#         return response(
#             ok          = False,
#             status_code = status.HTTP_400_BAD_REQUEST,
#             message     = "Incorrect current password",
#         )

#     now = datetime.now(timezone.utc)
#     current_user.password_hash       = hash_password(payload.new_password)
#     current_user.password_changed_at = now

#     db.query(TBL_AUTH_SESSION).filter(
#         TBL_AUTH_SESSION.user_id == current_user.id,
#         TBL_AUTH_SESSION.revoked_at.is_(None),
#     ).update(
#         {
#             "revoked_at"    : now,
#             "revoked_reason": "PASSWORD_CHANGED",
#         },
#         synchronize_session=False,
#     )

#     db.commit()
#     return response(
#         ok          = True,
#         status_code = status.HTTP_200_OK,
#         message     = "Password changed successfully",
#     )


# from fastapi.security import OAuth2PasswordRequestForm
# import json

# @app.post("/api/v1/auth/swagger-login", include_in_schema=False)
# async def swagger_login(
#     request: Request,
#     form_data: OAuth2PasswordRequestForm = Depends(),
#     db: Session = Depends(get_db),
# ):
#     payload = schemas.LoginRequest(email=form_data.username, password=form_data.password)
#     response_obj = await login_user(request=request, payload=payload, db=db)
    
#     body_data = response_obj.body.decode("utf-8")
#     body = json.loads(body_data)
    
#     if body.get("ok"):
#         return {
#             "access_token": body["data"]["accessToken"],
#             "token_type": "bearer"
#         }
#     else:
#         raise HTTPException(status_code=response_obj.status_code, detail=body.get("message"))

# @app.get("/api/v1/admin/users", tags=["Admin"])
# def admin_get_all_users(
#     current_user: TBL_AUTH_USER = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
    
#     roles = get_user_roles(db, current_user.id)
    
#     if "ADMIN" not in roles:
#         return response(
#             ok=False,
#             status_code=status.HTTP_403_FORBIDDEN,
#             message="Access denied. Admin privileges required.",
#         )
        
#     users = (
#         db.query(TBL_AUTH_USER)
#         .filter(TBL_AUTH_USER.deleted_at.is_(None))
#         .all()
#     )
    
#     serialized_users = [serialize_user(u) for u in users]
    
#     return response(

#         ok          = True,
#         status_code = status.HTTP_200_OK,
#         message     = "Users list retrieved successfully",
#         data        = serialized_users,
#     )

# @app.put("/api/v1/admin/users/{user_id}/reset-attempts", tags=["Admin"])
# def admin_reset_user_attempts(
#     user_id: str,
#     current_user: TBL_AUTH_USER = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     roles = get_user_roles(db, current_user.id)
#     if "ADMIN" not in roles:
#         return response(
#             ok=False,
#             status_code=status.HTTP_403_FORBIDDEN,
#             message="Access denied. Admin privileges required.",
#         )
        
#     user = db.query(TBL_AUTH_USER).filter(TBL_AUTH_USER.id == user_id, TBL_AUTH_USER.deleted_at.is_(None)).first()
#     if not user:
#         return response(
#             ok=False,
#             status_code=status.HTTP_404_NOT_FOUND,
#             message="User not found",
#         )
        
#     reset_user_attempt(user)
#     db.commit()
    
#     return response(
#         ok=True,
#         status_code=status.HTTP_200_OK,
#         message="User login attempts reset successfully",
#         data=serialize_user(user),
#     )
# # ========== Admin back up Database ======================
# @app.get("/api/v1/admin/backup", tags=["Admin"])
# def backup_database(
#     current_user: TBL_AUTH_USER = Depends(require_admin),
#     db          : Session       = Depends(get_db),
# ):
#     try:
#         # Create backups folder if not exists
#         backup_dir = "backups"
#         os.makedirs(backup_dir, exist_ok=True)

#         # Filename with timestamp
#         timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
#         filename    = f"librarain_backup_{timestamp}.sql"
#         filepath    = os.path.join(backup_dir, filename)

#         # Run pg_dump
#         result = subprocess.run(
#             [
#                 "pg_dump",
#                 "--host",     configs.POSTGRES_SERVER,
#                 "--port",     configs.POSTGRES_PORT,
#                 "--username", configs.POSTGRES_USER,
#                 "--dbname",   configs.POSTGRES_DB,
#                 "--no-password",
#                 "--file",     filepath,
#                 "--format",   "plain",
#                 "--encoding", "UTF8",
#             ],
#             env={
#                 **os.environ,
#                 "PGPASSWORD": configs.POSTGRES_PASSWORD,
#             },
#             capture_output = True,
#             text           = True,
#         )

#         if result.returncode != 0:
#             logger.error(f"pg_dump failed: {result.stderr}")
#             return response(
#                 ok          = False,
#                 status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 message     = f"Backup failed: {result.stderr}",
#             )

#         # Return the SQL file as download
#         return FileResponse(
#             path             = filepath,
#             media_type       = "application/octet-stream",
#             filename         = filename,
#         )

#     except FileNotFoundError:
#         return response(
#             ok          = False,
#             status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
#             message     = "pg_dump not found. Make sure PostgreSQL client tools are installed.",
#         )
#     except Exception as e:
#         logger.exception("Database backup failed")
#         return response(
#             ok          = False,
#             status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
#             message     = f"Backup failed: {str(e)}",
#         )

# @app.get("/api/v1/auth/telegram-login-status", tags=["Auth"])
# async def telegram_login_status(
#     token: str,
#     request: Request,
#     db: Session = Depends(get_db),
# ):
#     from api.auth_user.models import TBL_TELEGRAM_LOGIN_TOKEN, TBL_AUTH_SESSION
#     from api.auth_user.security import create_access_token, create_refresh_token, get_user_roles, hash_token

#     login_token = db.query(TBL_TELEGRAM_LOGIN_TOKEN).filter(
#         TBL_TELEGRAM_LOGIN_TOKEN.token == token,
#         TBL_TELEGRAM_LOGIN_TOKEN.is_authenticated == True
#     ).first()

#     if not login_token:
#         return response(
#             ok=False,
#             status_code=status.HTTP_400_BAD_REQUEST,
#             message="Token not found or not authenticated yet",
#             data={"status": "pending"}
#         )

#     user = login_token.user
#     if not user or not user.is_active:
#         return response(
#             ok=False,
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             message="User is inactive or deleted"
#         )

#     roles = get_user_roles(db, user.id)

#     session_id = uuid4()

#     # Create tokens
#     access_token  = create_access_token(user, roles, session_id)
#     refresh_token = create_refresh_token(user.id, session_id)

#     # Create session
#     new_session = TBL_AUTH_SESSION(
#         id                 = session_id,
#         user_id            = user.id,
#         refresh_token_hash = hash_token(refresh_token),
#         ip_address         = request.client.host if request.client else None,
#         user_agent         = request.headers.get("user-agent"),
#         expires_at         = datetime.now(timezone.utc) + timedelta(days=configs.REFRESH_TOKEN_EXPIRE_DAYS),
#     )
#     db.add(new_session)
#     db.commit()

#     return response(
#         ok=True,
#         status_code=status.HTTP_200_OK,
#         message="Telegram Login successful",
#         data={
#             "user": {
#                 "id": str(user.id),
#                 "full_name": user.full_name,
#                 "email": user.email,
#                 "roles": roles,
#             },
#             "accessToken": access_token,
#             "refreshToken": refresh_token,
#             "tokenType": "bearer",
#         }
#     )

# from fastapi.responses import HTMLResponse

# @app.get("/api/v1/auth/return-to-app", tags=["Auth"])
# async def return_to_app():
#     html_content = """
#     <html>
#         <head>
#             <meta name="viewport" content="width=device-width, initial-scale=1">
#             <style>
#                 body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f0f2f5; margin: 0; }
#                 .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; }
#                 h2 { color: #333; }
#                 a { display: inline-block; margin-top: 15px; padding: 12px 24px; background: #559B9B; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; }
#             </style>
#         </head>
#         <body>
#             <div class="card">
#                 <h2>Login Successful!</h2>
#                 <p>You can now return to the Librarain app.</p>
#                 <a href="naraklibrarain://login">Open App</a>
#             </div>
#             <script>
#                 setTimeout(function() {
#                     window.location.href = "naraklibrarain://login";
#                 }, 500);
#             </script>
#         </body>
#     </html>
#     """
#     return HTMLResponse(content=html_content)

import hashlib
import logging
import os
import random
import secrets
import subprocess
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from jose import JWTError, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.fcm import notify_password_reset
from main import app
from config import configs
from core.db import get_db
from api.auth_user import schemas
from api.auth_user.models import (
    TBL_AUTH_USER,
    TBL_AUTH_ROLE,
    TBL_AUTH_USER_ROLE,
    TBL_AUTH_SESSION,
    TBL_AUTH_LOGIN_LOG,
    TBL_EMAIL_VERIFICATION_TOKEN,
    TBL_PHONE_OTP,
    OtpCode,
)
from api.auth_user.rate_limiter import (
    enforce_registration_limits,
    enforce_rate_limit,
    get_client_ip,
)
from core.logger import write_log, LogAction, LogModule
from api.auth_user.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
    ALGORITHM,
    hash_password,
    require_admin,
    verify_password,
    hash_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_user_roles,
    get_current_user,
)

logger = logging.getLogger(__name__)


def response(ok: bool, status_code: int, message: str, data=None):
    return JSONResponse(
        status_code=status_code,
        content={
            "ok"     : ok,
            "status" : status_code,
            "message": message,
            "data"   : data,
        },
    )


def get_mail_config() -> ConnectionConfig:
    if (
        not configs.MAIL_USERNAME
        or not configs.MAIL_PASSWORD
        or not configs.MAIL_FROM
        or configs.MAIL_USERNAME == "yourgmail@gmail.com"
        or configs.MAIL_FROM == "yourgmail@gmail.com"
        or configs.MAIL_PASSWORD == "xxxxxxxxxxxxxxxx"
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email service is not configured",
        )

    return ConnectionConfig(
        MAIL_USERNAME   = configs.MAIL_USERNAME,
        MAIL_PASSWORD   = configs.MAIL_PASSWORD,
        MAIL_FROM       = configs.MAIL_FROM,
        MAIL_PORT       = configs.MAIL_PORT,
        MAIL_SERVER     = configs.MAIL_SERVER,
        MAIL_STARTTLS   = True,
        MAIL_SSL_TLS    = False,
        USE_CREDENTIALS = True,
        VALIDATE_CERTS  = True,
    )


async def send_otp_email(email: str, otp_code: str):
    message = MessageSchema(
        subject    = "Your password reset OTP",
        recipients = [email],
        body       = f"Your password reset OTP is {otp_code}. It expires in 10 minutes.",
        subtype    = "plain",
    )

    await FastMail(get_mail_config()).send_message(message)


async def send_verification_email(email: str, verify_link: str):
    message = MessageSchema(
        subject    = "Verify your email to finish registering",
        recipients = [email],
        body       = f"Click this link to verify your email and continue registering: {verify_link}\nThis link expires in 30 minutes.",
        subtype    = "plain",
    )

    await FastMail(get_mail_config()).send_message(message)


def write_login_log(
    db          : Session,
    request     : Request,
    email       : str,
    login_status: str,
    user_id=None,
    failure_reason: str | None = None,
):
    log = TBL_AUTH_LOGIN_LOG(
        user_id        = user_id,
        email          = email,
        login_status   = login_status,
        ip_address     = get_client_ip(request),
        user_agent     = request.headers.get("user-agent"),
        failure_reason = failure_reason,
    )
    db.add(log)

    if login_status == "SUCCESS":
        write_log(
            db          = db,
            action      = LogAction.USER_LOGIN_SUCCESS,
            module      = LogModule.AUTH,
            description = f"User logged in: {email}",
            user_id     = user_id,
            user_email  = email,
            entity_type = "user",
            entity_id   = str(user_id) if user_id else None,
            request     = request,
            commit      = False,
        )
    else:
        write_log(
            db          = db,
            action      = LogAction.USER_LOGIN_FAILED,
            module      = LogModule.AUTH,
            level       = "WARNING",
            status      = "FAILED",
            description = f"Login failed for: {email} — reason: {failure_reason}",
            user_email  = email,
            new_value   = {"reason": failure_reason},
            request     = request,
            commit      = False,
        )


def serialize_user(user: TBL_AUTH_USER):
    return {
        "id":          str(user.id),
        "full_name":   user.full_name,
        "email":       user.email,
        "phone":       user.phone,
        "is_active":   user.is_active,
        "is_verified": user.is_verified,
        "failed_login_attempts": user.failed_login_attempts or 0,
        "locked_until": user.locked_until.isoformat() if user.locked_until else None,
        "locked_at": user.locked_at.isoformat() if user.locked_at else None,
        "locked_reason": user.locked_reason,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _issue_reference(kind: str, subject: str, minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "type": kind,     # "registration_ref" | "phone_ref"
        "sub": subject,   # email or phone this reference is valid for
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_reference(token: str, expected_type: str, expected_subject: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reference")

    if payload.get("type") != expected_type:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid reference type")

    if payload.get("sub") != expected_subject:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Reference does not match this email/phone")

    return payload


REGISTRATION_TOKEN_TTL_MINUTES = 30
REGISTRATION_REFERENCE_TTL_MINUTES = 15
PHONE_OTP_TTL_MINUTES = 10
PHONE_OTP_REFERENCE_TTL_MINUTES = 15


# =============================================================================
# Step 1: request the verification email (replaces the old open POST /register)
# =============================================================================
@app.post("/api/v1/auth/request-registration", tags=["Auth"])
async def request_registration(
    payload: schemas.RequestRegistrationEmail,
    request: Request,
    db: Session = Depends(get_db),
):
    email = payload.email.lower()

    # Rate limit first — this is the endpoint bots and scrapers hit.
    enforce_registration_limits(db, request, email)

    existing_user = (
        db.query(TBL_AUTH_USER)
        .filter(TBL_AUTH_USER.email == email, TBL_AUTH_USER.deleted_at.is_(None))
        .first()
    )

    # Same response whether or not the account already exists, so this
    # endpoint can't be used to enumerate registered emails.
    if not existing_user:
        raw_token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)

        db.query(TBL_EMAIL_VERIFICATION_TOKEN).filter(
            TBL_EMAIL_VERIFICATION_TOKEN.email == email,
            TBL_EMAIL_VERIFICATION_TOKEN.used.is_(False),
        ).update({"used": True, "used_at": now}, synchronize_session=False)

        db.add(
            TBL_EMAIL_VERIFICATION_TOKEN(
                email=email,
                token_hash=_hash_value(raw_token),
                purpose="REGISTER",
                ip_address=get_client_ip(request),
                expires_at=now + timedelta(minutes=REGISTRATION_TOKEN_TTL_MINUTES),
            )
        )
        db.commit()

        verify_link = f"{configs.APP_BASE_URL}/api/v1/auth/verify-registration?token={raw_token}"
        try:
            await send_verification_email(email, verify_link)
        except Exception:
            # Don't leak delivery failures — response stays identical either way.
            logger.exception("Failed to send registration verification email")

    return response(
        ok=True,
        status_code=status.HTTP_200_OK,
        message="If that email can receive mail, a verification link has been sent.",
    )


# =============================================================================
# Step 2: consume the link, get a short-lived registration reference
# =============================================================================
@app.get("/api/v1/auth/verify-registration", tags=["Auth"])
def verify_registration(
    token: str,
    db: Session = Depends(get_db),
):
    token_row = (
        db.query(TBL_EMAIL_VERIFICATION_TOKEN)
        .filter(
            TBL_EMAIL_VERIFICATION_TOKEN.token_hash == _hash_value(token),
            TBL_EMAIL_VERIFICATION_TOKEN.used.is_(False),
        )
        .with_for_update()
        .first()
    )

    if not token_row or token_row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired verification link")

    token_row.used = True
    token_row.used_at = datetime.now(timezone.utc)
    db.commit()

    reference = _issue_reference(
        "registration_ref", token_row.email, REGISTRATION_REFERENCE_TTL_MINUTES
    )

    return response(
        ok=True,
        status_code=status.HTTP_200_OK,
        message="Email verified. Use this reference to finish registering.",
        data={
            "email": token_row.email,
            "registrationReference": reference,
            "expiresInMinutes": REGISTRATION_REFERENCE_TTL_MINUTES,
        },
    )


# =============================================================================
# Phone OTP: request + verify (second channel, required if phone is supplied)
# =============================================================================
@app.post("/api/v1/auth/request-phone-otp", tags=["Auth"])
def request_phone_otp(
    payload: schemas.RequestPhoneOtp,
    request: Request,
    db: Session = Depends(get_db),
):
    phone = payload.phone.strip()
    enforce_rate_limit(db, "PHONE", phone, max_hits=1, window_seconds=60)
    enforce_rate_limit(db, "PHONE", phone, max_hits=5, window_seconds=600)

    otp_code = f"{secrets.randbelow(1_000_000):06d}"
    now = datetime.now(timezone.utc)

    db.query(TBL_PHONE_OTP).filter(
        TBL_PHONE_OTP.phone == phone, TBL_PHONE_OTP.used.is_(False)
    ).update({"used": True, "used_at": now}, synchronize_session=False)

    db.add(
        TBL_PHONE_OTP(
            phone=phone,
            code_hash=_hash_value(otp_code),
            purpose="REGISTER",
            ip_address=get_client_ip(request),
            expires_at=now + timedelta(minutes=PHONE_OTP_TTL_MINUTES),
        )
    )
    db.commit()

    # TODO: plug in your SMS provider (Twilio, Vonage, etc.) here instead:
    # send_sms(phone, f"Your verification code is {otp_code}")

    return response(ok=True, status_code=status.HTTP_200_OK, message="OTP sent")


@app.post("/api/v1/auth/verify-phone-otp", tags=["Auth"])
def verify_phone_otp(
    payload: schemas.VerifyPhoneOtp,
    db: Session = Depends(get_db),
):
    otp_row = (
        db.query(TBL_PHONE_OTP)
        .filter(TBL_PHONE_OTP.phone == payload.phone, TBL_PHONE_OTP.used.is_(False))
        .order_by(TBL_PHONE_OTP.created_at.desc())
        .with_for_update()
        .first()
    )

    if not otp_row or otp_row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired OTP")

    if otp_row.attempts >= 5:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, request a new code")

    if otp_row.code_hash != _hash_value(payload.otp_code):
        otp_row.attempts += 1
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect code")

    otp_row.used = True
    otp_row.used_at = datetime.now(timezone.utc)
    db.commit()

    reference = _issue_reference("phone_ref", payload.phone, PHONE_OTP_REFERENCE_TTL_MINUTES)

    return response(
        ok=True,
        status_code=status.HTTP_200_OK,
        message="Phone verified.",
        data={"phoneReference": reference, "expiresInMinutes": PHONE_OTP_REFERENCE_TTL_MINUTES},
    )


# =============================================================================
# Step 3: actually create the account — requires a valid registration
# reference (and phone_reference, if a phone was supplied)
# =============================================================================
@app.post("/api/v1/auth/register", tags=["Auth"])
def register_user(
    request: Request,
    payload: schemas.RegisterRequest,
    db     : Session = Depends(get_db),
):
    email = payload.email.lower()

    # Proves this request comes from the same person who clicked the email link.
    _decode_reference(payload.registration_reference, "registration_ref", email)

    # If a phone was supplied, it must be independently verified too.
    if payload.phone:
        if not payload.phone_reference:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Phone verification is required")
        _decode_reference(payload.phone_reference, "phone_ref", payload.phone)

    new_user = TBL_AUTH_USER(
        full_name     = payload.full_name,
        email         = email,
        phone         = payload.phone,
        password_hash = hash_password(payload.password),
        is_active     = True,
        is_verified   = True,  # they proved control of the email (and phone, if given)
    )
    db.add(new_user)

    try:
        db.flush()
    except IntegrityError:
        # The email UNIQUE constraint is the real source of truth for
        # "does this account already exist" — it closes the race window
        # that a SELECT-then-INSERT check alone can't close.
        db.rollback()
        return response(
            ok          = False,
            status_code = status.HTTP_400_BAD_REQUEST,
            message     = "Email already exists",
        )

    # Get or create default USER role
    default_role = (
        db.query(TBL_AUTH_ROLE)
        .filter(TBL_AUTH_ROLE.role_code == "USER")
        .first()
    )

    if not default_role:
        default_role = TBL_AUTH_ROLE(
            role_code   = "USER",
            role_name   = "User",
            description = "Default application user role",
            is_active   = True,
        )
        db.add(default_role)
        db.flush()

    user_role = TBL_AUTH_USER_ROLE(
        user_id = new_user.id,
        role_id = default_role.id,
    )

    db.add(user_role)
    db.commit()
    db.refresh(new_user)

    write_log(
        db          = db,
        action      = LogAction.USER_REGISTERED,
        module      = LogModule.AUTH,
        description = f"New user registered: {email}",
        user_id     = new_user.id,
        user_email  = new_user.email,
        user_role   = "USER",
        entity_type = "user",
        entity_id   = str(new_user.id),
        new_value   = {"email": new_user.email, "full_name": new_user.full_name},
        request     = request,
        commit      = True,
    )

    user_data = serialize_user(new_user)

    return response(
        ok          = True,
        status_code = status.HTTP_201_CREATED,
        message     = "User registered successfully",
        data        = user_data,
    )


def is_account_locked(user: TBL_AUTH_USER, now: datetime) -> bool:
    return user.locked_until is not None and user.locked_until > now


def reset_user_attempt(user: TBL_AUTH_USER):
    user.failed_login_attempts = 0
    user.locked_until          = None
    user.locked_at             = None
    user.locked_reason         = None


def increase_failed_attempt(user: TBL_AUTH_USER, now: datetime):
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

    if user.failed_login_attempts >= configs.MAX_FAILED_LOGIN_ATTEMPTS:
        user.locked_at = now
        user.locked_until = now + timedelta(
            minutes=configs.ACCOUNT_LOCK_MINUTES
        )
        user.locked_reason = "TOO_MANY_FAILED_ATTEMPTS"


@app.post(
    "/api/v1/auth/login",
    tags           = ["Auth"],
    response_model = schemas.ApiResponse,
    summary        = "Login User",
)
async def login_user(
    request: Request,
    payload: schemas.LoginRequest,
    db     : Session = Depends(get_db),
):
    user = (
        db.query(TBL_AUTH_USER)
        .filter(
            TBL_AUTH_USER.email == payload.email,
            TBL_AUTH_USER.deleted_at.is_(None),
        )
        .first()
    )

    if not user:
        write_login_log(
            db             = db,
            request        = request,
            email          = payload.email,
            login_status   = "FAILED",
            failure_reason = "USER_NOT_FOUND",
        )
        db.commit()

        return response(
            ok          = False,
            status_code = status.HTTP_401_UNAUTHORIZED,
            message     = "Invalid email or password",
        )

    if not user.is_active:
        write_login_log(
            db             = db,
            request        = request,
            email          = payload.email,
            login_status   = "FAILED",
            user_id        = user.id,
            failure_reason = "USER_INACTIVE",
        )
        db.commit()

        return response(
            ok          = False,
            status_code = status.HTTP_403_FORBIDDEN,
            message     = "User account is inactive",
        )
    now = datetime.now(timezone.utc)

    if is_account_locked(user, now):
        write_login_log(
            db             = db,
            request        = request,
            email          = payload.email,
            login_status   = "FAILED",
            user_id        = user.id,
            failure_reason = "ACCOUNT_LOCKED",
        )
        db.commit()

        return response(
            ok          = False,
            status_code = status.HTTP_423_LOCKED,
            message     = "Account is locked due to too many failed login attempts.",
            data={
                "lockedUntil": user.locked_until.isoformat(),
            },
        )

    if not verify_password(payload.password, user.password_hash):
        increase_failed_attempt(user, now)

        write_login_log(
            db             = db,
            request        = request,
            email          = payload.email,
            login_status   = "FAILED",
            user_id        = user.id,
            failure_reason = "INVALID_PASSWORD",
        )

        db.commit()

        remaining_attempts = (
            configs.MAX_FAILED_LOGIN_ATTEMPTS - user.failed_login_attempts
        )

        if user.locked_until:
            return response(
                ok          = False,
                status_code = status.HTTP_423_LOCKED,
                message     = "Account locked due to too many failed login attempts.",
                data={
                    "lockedUntil": user.locked_until.isoformat(),
                },
            )

        return response(
            ok          = False,
            status_code = status.HTTP_401_UNAUTHORIZED,
            message     = "Invalid email or password",
            data={
                "remainingAttempts": max(remaining_attempts, 0),
            },
        )

    session_id         = uuid4()
    reset_user_attempt(user)

    refresh_expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    roles = get_user_roles(db, user.id)

    access_token = create_access_token(
        user       = user,
        roles      = roles,
        session_id = session_id,
    )

    refresh_token = create_refresh_token(
        user_id    = user.id,
        session_id = session_id,
    )

    if configs.SINGLE_SESSION_LOGIN:
        db.query(TBL_AUTH_SESSION).filter(
            TBL_AUTH_SESSION.user_id == user.id,
            TBL_AUTH_SESSION.revoked_at.is_(None),
        ).update(
            {
                "revoked_at"    : now,
                "revoked_reason": "NEW_LOGIN",
            },
            synchronize_session = False,
        )

    new_session = TBL_AUTH_SESSION(
        id                 = session_id,
        user_id            = user.id,
        refresh_token_hash = hash_token(refresh_token),
        device_id          = request.headers.get("x-device-id"),
        device_name        = request.headers.get("x-device-name"),
        user_agent         = request.headers.get("user-agent"),
        ip_address         = get_client_ip(request),
        issued_at          = now,
        expires_at         = refresh_expires_at,
    )

    user.last_login_at = now
    db.add(new_session)

    write_login_log(
        db           = db,
        request      = request,
        email        = payload.email,
        login_status = "SUCCESS",
        user_id      = user.id,
    )

    db.commit()

    user_data = serialize_user(user)

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Login successfully",
        data={
            "accessToken" : access_token,
            "refreshToken": refresh_token,
            "tokenType"   : "bearer",
            "expiresIn"   : ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "roles"       : roles,
            "user"        : user_data,
        },
    )


@app.post("/api/v1/auth/refresh-token", tags=["Auth"])
def refresh_token(
    payload: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    token_data = decode_token(payload.refresh_token)

    if token_data.get("type") != "refresh":
        return response(
            ok          = False,
            status_code = status.HTTP_401_UNAUTHORIZED,
            message     = "Invalid token type",
        )

    user_id = token_data.get("sub")
    session_id = token_data.get("sessionId")

    if not user_id or not session_id:
        return response(
            ok          = False,
            status_code = status.HTTP_401_UNAUTHORIZED,
            message     = "Invalid token payload",
        )

    now = datetime.now(timezone.utc)

    session = (
        db.query(TBL_AUTH_SESSION)
        .filter(
            TBL_AUTH_SESSION.id == session_id,
            TBL_AUTH_SESSION.user_id == user_id,
            TBL_AUTH_SESSION.refresh_token_hash == hash_token(payload.refresh_token),
            TBL_AUTH_SESSION.revoked_at.is_(None),
            TBL_AUTH_SESSION.expires_at > now,
        )
        .first()
    )

    if not session:
        return response(
            ok          = False,
            status_code = status.HTTP_401_UNAUTHORIZED,
            message     = "Refresh token expired or revoked",
        )

    user = (
        db.query(TBL_AUTH_USER)
        .filter(
            TBL_AUTH_USER.id == user_id,
            TBL_AUTH_USER.deleted_at.is_(None),
            TBL_AUTH_USER.is_active.is_(True),
        )
        .first()
    )

    if not user:
        return response(
            ok          = False,
            status_code = status.HTTP_401_UNAUTHORIZED,
            message     = "User not found or inactive",
        )

    roles = get_user_roles(db, user.id)

    new_access_token = create_access_token(
        user       = user,
        roles      = roles,
        session_id = session.id,
    )

    new_refresh_token = create_refresh_token(
        user_id    = user.id,
        session_id = session.id,
    )

    session.refresh_token_hash = hash_token(new_refresh_token)
    session.expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    db.commit()

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Token refreshed successfully",
        data={
            "accessToken" : new_access_token,
            "refreshToken": new_refresh_token,
            "tokenType"   : "bearer",
            "expiresIn"   : ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        },
    )


@app.post("/api/v1/auth/logout", tags=["Auth"])
def logout_user(
    payload: schemas.LogoutRequest,
    db     : Session = Depends(get_db),
):
    token_data = decode_token(payload.refresh_token)

    if token_data.get("type") != "refresh":
        return response(
            ok          = False,
            status_code = status.HTTP_401_UNAUTHORIZED,
            message     = "Invalid token type",
        )

    session_id = token_data.get("sessionId")
    user_id    = token_data.get("sub")

    session = (
        db.query(TBL_AUTH_SESSION)
        .filter(
            TBL_AUTH_SESSION.id == session_id,
            TBL_AUTH_SESSION.user_id == user_id,
            TBL_AUTH_SESSION.refresh_token_hash == hash_token(payload.refresh_token),
            TBL_AUTH_SESSION.revoked_at.is_(None),
        )
        .first()
    )

    if session:
        session.revoked_at = datetime.now(timezone.utc)
        session.revoked_reason = "USER_LOGOUT"
        db.commit()

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Logout successfully",
    )


from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


@app.post(
    "/api/v1/auth/google-login",
    tags           = ["Auth"],
    response_model = schemas.ApiResponse,
    summary        = "Login with Google",
)
async def google_login(
    request: Request,
    payload: schemas.GoogleLoginRequest,
    db     : Session = Depends(get_db),
):
    try:
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        try:
            idinfo = id_token.verify_oauth2_token(
                payload.id_token, google_requests.Request(), client_id
            )
        except ValueError:
            logger.exception("Failed to verify Google Token strict")
            idinfo = id_token.verify_oauth2_token(
                payload.id_token, google_requests.Request()
            )

        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Wrong issuer.")

        email = idinfo["email"]
        full_name = idinfo.get("name", "Google User")

    except Exception:
        logger.exception("Google token verification failed")
        return response(
            ok          = False,
            status_code = status.HTTP_401_UNAUTHORIZED,
            message     = "Invalid Google Token",
        )

    user = (
        db.query(TBL_AUTH_USER)
        .filter(
            TBL_AUTH_USER.email == email,
            TBL_AUTH_USER.deleted_at.is_(None),
        )
        .first()
    )

    now = datetime.now(timezone.utc)

    if not user:
        # Google has already verified this identity, so it's the one path
        # that's allowed to create an account without the email-link /
        # phone-OTP reference flow above.
        user = TBL_AUTH_USER(
            full_name     = full_name,
            email         = email,
            phone         = None,
            password_hash = hash_password(secrets.token_urlsafe(32)),
            is_active     = True,
            is_verified   = True,
        )

        db.add(user)

        try:
            db.flush()
        except IntegrityError:
            # Someone else's request created this same email a moment ago —
            # re-fetch instead of erroring.
            db.rollback()
            user = (
                db.query(TBL_AUTH_USER)
                .filter(
                    TBL_AUTH_USER.email == email,
                    TBL_AUTH_USER.deleted_at.is_(None),
                )
                .first()
            )
            if not user:
                return response(
                    ok          = False,
                    status_code = status.HTTP_409_CONFLICT,
                    message     = "Could not complete Google login, please retry",
                )
        else:
            default_role = (
                db.query(TBL_AUTH_ROLE)
                .filter(TBL_AUTH_ROLE.role_code == "USER")
                .first()
            )

            if not default_role:
                default_role = TBL_AUTH_ROLE(
                    role_code   = "USER",
                    role_name   = "User",
                    description = "Default application user role",
                    is_active   = True,
                )
                db.add(default_role)
                db.flush()

            user_role = TBL_AUTH_USER_ROLE(
                user_id = user.id,
                role_id = default_role.id,
            )

            db.add(user_role)
            db.commit()
            db.refresh(user)
    else:
        if not user.is_active:
            return response(
                ok          = False,
                status_code = status.HTTP_403_FORBIDDEN,
                message     = "User account is inactive",
            )
        if is_account_locked(user, now):
            return response(
                ok          = False,
                status_code = status.HTTP_423_LOCKED,
                message     = "Account is locked due to too many failed login attempts.",
            )

    session_id         = uuid4()
    reset_user_attempt(user)

    refresh_expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    roles = get_user_roles(db, user.id)

    access_token = create_access_token(
        user       = user,
        roles      = roles,
        session_id = session_id,
    )

    refresh_token = create_refresh_token(
        user_id    = user.id,
        session_id = session_id,
    )

    if configs.SINGLE_SESSION_LOGIN:
        db.query(TBL_AUTH_SESSION).filter(
            TBL_AUTH_SESSION.user_id == user.id,
            TBL_AUTH_SESSION.revoked_at.is_(None),
        ).update(
            {
                "revoked_at"    : now,
                "revoked_reason": "NEW_LOGIN",
            },
            synchronize_session = False,
        )

    new_session = TBL_AUTH_SESSION(
        id                 = session_id,
        user_id            = user.id,
        refresh_token_hash = hash_token(refresh_token),
        device_id          = payload.device_id or request.headers.get("x-device-id"),
        device_name        = payload.device_name or request.headers.get("x-device-name"),
        user_agent         = request.headers.get("user-agent"),
        ip_address         = get_client_ip(request),
        issued_at          = now,
        expires_at         = refresh_expires_at,
    )

    user.last_login_at = now
    db.add(new_session)

    write_login_log(
        db           = db,
        request      = request,
        email        = email,
        login_status = "SUCCESS",
        user_id      = user.id,
    )

    db.commit()

    user_data = serialize_user(user)

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Login successfully",
        data={
            "accessToken" : access_token,
            "refreshToken": refresh_token,
            "tokenType"   : "bearer",
            "expiresIn"   : ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "roles"       : roles,
            "user"        : user_data,
        },
    )


@app.get("/api/v1/auth/me", tags=["Auth"])
def get_me(
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    roles     = get_user_roles(db, current_user.id)
    user_data = serialize_user(current_user)

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Current user retrieved successfully",
        data={
            "user" : user_data,
            "roles": roles,
        },
    )


@app.post("/api/v1/auth/reset-attempt", tags=["Auth"])
def reset_login_attempt(
    payload: schemas.ResetAttemptRequest,
    db     : Session = Depends(get_db),
):
    user = (
        db.query(TBL_AUTH_USER)
        .filter(
            TBL_AUTH_USER.email == payload.email,
            TBL_AUTH_USER.deleted_at.is_(None),
        )
        .first()
    )

    if not user:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "User not found",
        )

    reset_user_attempt(user)
    db.commit()

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Login attempt reset successfully",
        data={
            "email"              : user.email,
            "failedLoginAttempts": user.failed_login_attempts,
            "lockedUntil"        : None,
        },
    )


@app.post("/api/v1/auth/forgot-password", tags=["Auth"])
async def forgot_password(
    payload: schemas.ForgotPasswordRequest,
    db     : Session = Depends(get_db),
):
    user = (
        db.query(TBL_AUTH_USER)
        .filter(
            TBL_AUTH_USER.email == payload.email,
            TBL_AUTH_USER.deleted_at.is_(None),
        )
        .first()
    )

    if not user:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "User not found",
        )

    channel = payload.channel or "email"

    if channel == "telegram":
        if not user.telegram_chat_id:
            return response(
                ok          = False,
                status_code = status.HTTP_400_BAD_REQUEST,
                message     = "Telegram account is not linked. Please select Email instead.",
            )

    otp_code = f"{random.SystemRandom().randint(0, 999999):06d}"
    now = datetime.utcnow()

    db.query(OtpCode).filter(
        OtpCode.email == payload.email,
        OtpCode.used.is_(False),
    ).update(
        {"used": True},
        synchronize_session=False,
    )

    db.add(
        OtpCode(
            email      = payload.email,
            code       = otp_code,
            expires_at = now + timedelta(minutes=10),
            used       = False,
        )
    )
    db.commit()

    if channel == "telegram":
        try:
            from api.telegram_bots.bot_polling import send_telegram_message
            await send_telegram_message(
                user.telegram_chat_id,
                f"🔐 *Librarain Password Reset OTP*\n\nYour OTP code is: `{otp_code}`\n\nIt expires in 10 minutes."
            )
        except Exception as e:
            logger.exception("Failed to send telegram OTP message")
            db.query(OtpCode).filter(
                OtpCode.email == payload.email,
                OtpCode.code == otp_code,
                OtpCode.used.is_(False),
            ).delete(synchronize_session=False)
            db.commit()
            return response(
                ok          = False,
                status_code = status.HTTP_502_BAD_GATEWAY,
                message     = f"Failed to send Telegram message: {str(e)}",
            )
    else:
        try:
            await send_otp_email(payload.email, otp_code)
        except HTTPException:
            db.query(OtpCode).filter(
                OtpCode.email == payload.email,
                OtpCode.code == otp_code,
                OtpCode.used.is_(False),
            ).delete(synchronize_session=False)
            db.commit()
            raise
        except Exception:
            db.query(OtpCode).filter(
                OtpCode.email == payload.email,
                OtpCode.code == otp_code,
                OtpCode.used.is_(False),
            ).delete(synchronize_session=False)
            db.commit()
            logger.exception("Failed to send password reset OTP email")

            return response(
                ok          = False,
                status_code = status.HTTP_502_BAD_GATEWAY,
                message     = "Failed to send OTP email. Check Gmail app password settings.",
            )

    return {"message": "OTP sent"}


@app.post("/api/v1/auth/verify-otp", tags=["Auth"])
def verify_otp(
    payload: schemas.VerifyOtpRequest,
    db     : Session = Depends(get_db),
):
    otp = (
        db.query(OtpCode)
        .filter(
            OtpCode.email == payload.email,
            OtpCode.used.is_(False),
        )
        .order_by(OtpCode.created_at.desc())
        .first()
    )

    if not otp:
        return response(
            ok          = False,
            status_code = status.HTTP_400_BAD_REQUEST,
            message     = "Invalid or expired OTP",
        )

    now = datetime.utcnow()

    if otp.expires_at < now:
        otp.used = True
        db.commit()

        return response(
            ok          = False,
            status_code = status.HTTP_400_BAD_REQUEST,
            message     = "OTP expired",
        )

    if otp.code != payload.otp_code:
        return response(
            ok          = False,
            status_code = status.HTTP_400_BAD_REQUEST,
            message     = "Invalid OTP",
        )

    otp.used = True
    db.commit()

    return {"message": "OTP verified"}


@app.post("/api/v1/auth/reset-password", tags=["Auth"])
def reset_password(
    request: Request,
    payload: schemas.ResetPasswordRequest,
    db     : Session = Depends(get_db),
):
    user = (
        db.query(TBL_AUTH_USER)
        .filter(
            TBL_AUTH_USER.email == payload.email,
            TBL_AUTH_USER.deleted_at.is_(None),
        )
        .first()
    )

    if not user:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "User not found",
        )

    now_utc = datetime.utcnow()
    verified_otp = (
        db.query(OtpCode)
        .filter(
            OtpCode.email == payload.email,
            OtpCode.used.is_(True),
            OtpCode.expires_at >= now_utc,
        )
        .order_by(OtpCode.created_at.desc())
        .first()
    )

    if not verified_otp:
        return response(
            ok          = False,
            status_code = status.HTTP_400_BAD_REQUEST,
            message     = "OTP verification required",
        )

    now = datetime.now(timezone.utc)
    user.password_hash       = hash_password(payload.new_password)
    user.password_changed_at = now
    reset_user_attempt(user)

    db.query(TBL_AUTH_SESSION).filter(
        TBL_AUTH_SESSION.user_id == user.id,
        TBL_AUTH_SESSION.revoked_at.is_(None),
    ).update(
        {
            "revoked_at"    : now,
            "revoked_reason": "PASSWORD_RESET",
        },
        synchronize_session=False,
    )

    db.query(OtpCode).filter(
        OtpCode.email == payload.email,
    ).delete(synchronize_session=False)

    db.commit()
    notify_password_reset(db=db, user_id=user.id)

    write_log(
        db          = db,
        action      = LogAction.PASSWORD_RESET_SUCCESS,
        module      = LogModule.AUTH,
        description = f"Password reset successful for: {user.email}",
        user_id     = user.id,
        user_email  = user.email,
        entity_type = "user",
        entity_id   = str(user.id),
        request     = request,
        commit      = True,
    )

    return {"message": "Password reset successful"}


@app.post("/api/v1/auth/change-password", tags=["Auth"])
def change_password(
    payload: schemas.ChangePasswordRequest,
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        return response(
            ok          = False,
            status_code = status.HTTP_400_BAD_REQUEST,
            message     = "Incorrect current password",
        )

    now = datetime.now(timezone.utc)
    current_user.password_hash       = hash_password(payload.new_password)
    current_user.password_changed_at = now

    db.query(TBL_AUTH_SESSION).filter(
        TBL_AUTH_SESSION.user_id == current_user.id,
        TBL_AUTH_SESSION.revoked_at.is_(None),
    ).update(
        {
            "revoked_at"    : now,
            "revoked_reason": "PASSWORD_CHANGED",
        },
        synchronize_session=False,
    )

    db.commit()
    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Password changed successfully",
    )


from fastapi.security import OAuth2PasswordRequestForm
import json


@app.post("/api/v1/auth/swagger-login", include_in_schema=False)
async def swagger_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    payload = schemas.LoginRequest(email=form_data.username, password=form_data.password)
    response_obj = await login_user(request=request, payload=payload, db=db)

    body_data = response_obj.body.decode("utf-8")
    body = json.loads(body_data)

    if body.get("ok"):
        return {
            "access_token": body["data"]["accessToken"],
            "token_type": "bearer"
        }
    else:
        raise HTTPException(status_code=response_obj.status_code, detail=body.get("message"))


@app.get("/api/v1/admin/users", tags=["Admin"])
def admin_get_all_users(
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(db, current_user.id)

    if "ADMIN" not in roles:
        return response(
            ok=False,
            status_code=status.HTTP_403_FORBIDDEN,
            message="Access denied. Admin privileges required.",
        )

    users = (
        db.query(TBL_AUTH_USER)
        .filter(TBL_AUTH_USER.deleted_at.is_(None))
        .all()
    )

    serialized_users = [serialize_user(u) for u in users]

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Users list retrieved successfully",
        data        = serialized_users,
    )


@app.put("/api/v1/admin/users/{user_id}/reset-attempts", tags=["Admin"])
def admin_reset_user_attempts(
    user_id: str,
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(db, current_user.id)
    if "ADMIN" not in roles:
        return response(
            ok=False,
            status_code=status.HTTP_403_FORBIDDEN,
            message="Access denied. Admin privileges required.",
        )

    user = db.query(TBL_AUTH_USER).filter(TBL_AUTH_USER.id == user_id, TBL_AUTH_USER.deleted_at.is_(None)).first()
    if not user:
        return response(
            ok=False,
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found",
        )

    reset_user_attempt(user)
    db.commit()

    return response(
        ok=True,
        status_code=status.HTTP_200_OK,
        message="User login attempts reset successfully",
        data=serialize_user(user),
    )


@app.get("/api/v1/admin/backup", tags=["Admin"])
def backup_database(
    current_user: TBL_AUTH_USER = Depends(require_admin),
    db          : Session       = Depends(get_db),
):
    try:
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)

        timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename    = f"librarain_backup_{timestamp}.sql"
        filepath    = os.path.join(backup_dir, filename)

        result = subprocess.run(
            [
                "pg_dump",
                "--host",     configs.POSTGRES_SERVER,
                "--port",     configs.POSTGRES_PORT,
                "--username", configs.POSTGRES_USER,
                "--dbname",   configs.POSTGRES_DB,
                "--no-password",
                "--file",     filepath,
                "--format",   "plain",
                "--encoding", "UTF8",
            ],
            env={
                **os.environ,
                "PGPASSWORD": configs.POSTGRES_PASSWORD,
            },
            capture_output = True,
            text           = True,
        )

        if result.returncode != 0:
            logger.error(f"pg_dump failed: {result.stderr}")
            return response(
                ok          = False,
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                message     = f"Backup failed: {result.stderr}",
            )

        return FileResponse(
            path             = filepath,
            media_type       = "application/octet-stream",
            filename         = filename,
        )

    except FileNotFoundError:
        return response(
            ok          = False,
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            message     = "pg_dump not found. Make sure PostgreSQL client tools are installed.",
        )
    except Exception as e:
        logger.exception("Database backup failed")
        return response(
            ok          = False,
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            message     = f"Backup failed: {str(e)}",
        )


@app.get("/api/v1/auth/telegram-login-status", tags=["Auth"])
async def telegram_login_status(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    from api.auth_user.models import TBL_TELEGRAM_LOGIN_TOKEN

    login_token = db.query(TBL_TELEGRAM_LOGIN_TOKEN).filter(
        TBL_TELEGRAM_LOGIN_TOKEN.token == token,
        TBL_TELEGRAM_LOGIN_TOKEN.is_authenticated == True
    ).first()

    if not login_token:
        return response(
            ok=False,
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Token not found or not authenticated yet",
            data={"status": "pending"}
        )

    user = login_token.user
    if not user or not user.is_active:
        return response(
            ok=False,
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="User is inactive or deleted"
        )

    roles = get_user_roles(db, user.id)

    session_id = uuid4()

    access_token  = create_access_token(user, roles, session_id)
    refresh_token = create_refresh_token(user.id, session_id)

    new_session = TBL_AUTH_SESSION(
        id                 = session_id,
        user_id            = user.id,
        refresh_token_hash = hash_token(refresh_token),
        ip_address         = request.client.host if request.client else None,
        user_agent         = request.headers.get("user-agent"),
        expires_at         = datetime.now(timezone.utc) + timedelta(days=configs.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_session)
    db.commit()

    return response(
        ok=True,
        status_code=status.HTTP_200_OK,
        message="Telegram Login successful",
        data={
            "user": {
                "id": str(user.id),
                "full_name": user.full_name,
                "email": user.email,
                "roles": roles,
            },
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "tokenType": "bearer",
        }
    )


from fastapi.responses import HTMLResponse


@app.get("/api/v1/auth/return-to-app", tags=["Auth"])
async def return_to_app():
    html_content = """
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f0f2f5; margin: 0; }
                .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; }
                h2 { color: #333; }
                a { display: inline-block; margin-top: 15px; padding: 12px 24px; background: #559B9B; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="card">
                <h2>Login Successful!</h2>
                <p>You can now return to the Librarain app.</p>
                <a href="naraklibrarain://login">Open App</a>
            </div>
            <script>
                setTimeout(function() {
                    window.location.href = "naraklibrarain://login";
                }, 500);
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)