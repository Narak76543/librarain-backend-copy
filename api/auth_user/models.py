import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
    Integer, 
    text,
    Index
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.db import Base
from sqlalchemy import text


class TBL_AUTH_USER(Base):
    __tablename__ = "tbl_auth_user"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name             = Column(String(150), nullable=False)
    email                 = Column(String(150), nullable=False, unique=True, index=True)
    phone                 = Column(String(30), nullable=True)
    password_hash         = Column(Text, nullable=False)
    is_active             = Column(Boolean, nullable=False, default=True)
    is_verified           = Column(Boolean, nullable=False, default=False)
    telegram_chat_id      = Column(String(50), nullable=True)
    last_login_at         = Column(DateTime(timezone=True), nullable=True)
    created_at            = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at            = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    deleted_at            = Column(DateTime(timezone=True), nullable=True)

    # failed_login_attempts = Column(Integer, nullable=False, default=0)
    failed_login_attempts = Column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    locked_until          = Column(DateTime(timezone=True), nullable=True)
    locked_at             = Column(DateTime(timezone=True), nullable=True)
    locked_reason         = Column(String(255), nullable=True)
    password_changed_at   = Column(DateTime(timezone=True), nullable=True)

    user_roles = relationship(
        "TBL_AUTH_USER_ROLE",
        back_populates = "user",
        cascade        = "all, delete-orphan",
    )

    sessions = relationship(
        "TBL_AUTH_SESSION",
        back_populates = "user",
        cascade        = "all, delete-orphan",
    )

    login_logs = relationship(
        "TBL_AUTH_LOGIN_LOG",
        back_populates="user",
    )
    
    profile = relationship(
    "TBL_USER_PROFILE",
    back_populates = "user",
    uselist        = False,
    cascade        = "all, delete-orphan",
)

class TBL_AUTH_ROLE(Base):
    __tablename__ = "tbl_auth_role"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_code   = Column(String(50), nullable=False, unique=True, index=True)
    role_name   = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    user_roles = relationship(
        "TBL_AUTH_USER_ROLE",
        back_populates = "role",
        cascade        = "all, delete-orphan",
    )

class TBL_AUTH_USER_ROLE(Base):
    __tablename__ = "tbl_auth_user_role"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tbl_auth_user.id", ondelete="CASCADE"),
        nullable = False,
        index    = True,
    )

    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tbl_auth_role.id", ondelete="CASCADE"),
        nullable = False,
        index    = True,
    )

    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "role_id",
            name="uq_tbl_auth_user_role_user_id_role_id",
        ),
    )

    user = relationship(
        "TBL_AUTH_USER",
        back_populates="user_roles",
    )

    role = relationship(
        "TBL_AUTH_ROLE",
        back_populates="user_roles",
    )


class TBL_AUTH_SESSION(Base):
    __tablename__ = "tbl_auth_session"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tbl_auth_user.id", ondelete="CASCADE"),
        nullable = False,
        index    = True,
    )

    refresh_token_hash = Column(Text, nullable=False, unique=True)
    device_id          = Column(String(150), nullable=True)
    device_name        = Column(String(200), nullable=True)
    user_agent         = Column(Text, nullable=True)
    ip_address         = Column(INET, nullable=True)
    issued_at          = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at         = Column(DateTime(timezone=True), nullable=False)
    revoked_at         = Column(DateTime(timezone=True), nullable=True)
    revoked_reason     = Column(String(255), nullable=True)
    created_at         = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship(
        "TBL_AUTH_USER",
        back_populates="sessions",
    )


class TBL_AUTH_LOGIN_LOG(Base):
    __tablename__ = "tbl_auth_login_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tbl_auth_user.id", ondelete="SET NULL"),
        nullable = True,
        index    = True,
    )

    email = Column(String(150), nullable=True)
      # SUCCESS / FAILED
    login_status   = Column(String(30), nullable=False)
    ip_address     = Column(INET, nullable=True)
    user_agent     = Column(Text, nullable=True)
    failure_reason = Column(String(255), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship(
        "TBL_AUTH_USER",
        back_populates="login_logs",
    )

class OtpCode(Base):
    __tablename__ = "otp_codes"

    id         = Column(Integer, primary_key=True)
    email      = Column(String, nullable=False)
    code       = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used       = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class TBL_TELEGRAM_LOGIN_TOKEN(Base):
    __tablename__ = "tbl_telegram_login_token"

    token            = Column(String(100), primary_key=True)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("tbl_auth_user.id", ondelete="CASCADE"), nullable=True)
    is_authenticated = Column(Boolean, nullable=False, default=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship(
        "TBL_AUTH_USER",
    )

# registration security  [ email verification, phone OTP , and rate Limite]

class TBL_EMAIL_VERIFICATION_TOKEN(Base):

    __tablename__ = "tbl_email_verification_token"

    id            = Column(UUID(as_uuid=True) , primary_key=True , default=uuid.uuid4)
    email         = Column(String(150) , nullable=False , index= True)
    token_hash    = Column(String(64) , nullable=False , unique= True , index= True)
    purpose       = Column(String(30) , nullable=False , server_default=text("'REGISTER'"))
    ip_address    = Column(INET , nullable=True)
    used          = Column(Boolean , nullable=False , server_default=text("false"))
    used_at       = Column(DateTime(timezone=True) , nullable= True)
    expire_date   = Column(DateTime(timezone=True) , nullable=False)
    created_at    = Column(DateTime(timezone=True) , server_default=func.now() , nullable=False)

    __table_args__ = (
        Index("ix_email_verif_email_used_created", "email", "used", "created_at"),
    )


class TBL_PHONE_OTP(Base):
    __tablename__ = "tbl_phone_otp"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(20), nullable=False, index=True)
    code_hash = Column(String(128), nullable=False)
    purpose = Column(String(30), nullable=False, server_default=text("'REGISTER'"))
    ip_address = Column(INET, nullable=True)
    used = Column(Boolean, nullable=False, server_default=text("false"))
    used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, nullable=False, server_default=text("0"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_phone_otp_phone_used_created", "phone", "used", "created_at"),
    )


class TBL_REGISTRATION_RATE_LIMIT(Base) :

    __tablename__ = "tbl_registration_rate_limit"

    id             = Column(UUID(as_uuid=True) , primary_key=True , default=uuid.uuid4)
    scope_type     = Column(String(20) , nullable=False)
    scope_value    = Column(String(100) , nullable=False)
    window_start   = Column(DateTime(timezone=True) , nullable= False)
    hit_count      = Column(Integer , nullable= False , server_default=text("1"))
    __table_args__ = (
                UniqueConstraint(
            "scope_type", "scope_value", "window_start",
            name="uq_reg_rate_limit_scope_window",
        ),
        Index("ix_reg_rate_limit_scope", "scope_type", "scope_value"),

    )