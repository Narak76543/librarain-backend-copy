import uuid 
from datetime import datetime
from sqlalchemy import (
    Column , 
    String , 
    Boolean, 
    DateTime, 
    Text, 
    ForeignKey, 
    UniqueConstraint, 
    Integer, 
    text
)
from sqlalchemy.dialects.postgresql import UUID , INET
from sqlalchemy.orm import relationship 
from sqlalchemy.sql import func 
from sqlalchemy import text
from core.db import Base

class TBL_USER_PROFILE(Base):
    __tablename__ = "tbl_user_profile"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("tbl_auth_user.id", ondelete="CASCADE"), nullable=False, unique=True)

    first_name       = Column(String(100), nullable=True)
    last_name        = Column(String(100), nullable=True)
    first_name_local = Column(String(100), nullable=True)  # Khmer first name
    last_name_local  = Column(String(100), nullable=True)  # Khmer last name
    phone            = Column(String(30),  nullable=True)
    telegram         = Column(String(100), nullable=True)  # @username
    address          = Column(Text,        nullable=True)
    avatar_url       = Column(Text,        nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    fcm_token = Column(Text, nullable=True)

    # Relationship back to auth user
    user = relationship("TBL_AUTH_USER", back_populates="profile")