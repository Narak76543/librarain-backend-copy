import uuid
from sqlalchemy import Column, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime, ForeignKey
from core.db import Base


class TBL_SYSTEM_LOG(Base):
    __tablename__ = "tbl_system_log"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Who did it
    user_id     = Column(UUID(as_uuid=True), ForeignKey("tbl_auth_user.id",
                  ondelete="SET NULL"), nullable=True, index=True)
    user_email  = Column(String(255), nullable=True)  # keep even if user deleted
    user_role   = Column(String(50),  nullable=True)  # ADMIN / USER

    # What happened
    action      = Column(String(100), nullable=False, index=True)
    # e.g. ORDER_PLACED / USER_LOGIN / BOOK_CREATED

    module      = Column(String(50),  nullable=False, index=True)
    # e.g. AUTH / ORDER / BOOK / CATEGORY / STOCK / CART / WISHLIST

    level       = Column(String(20),  nullable=False, default="INFO", index=True)
    # INFO / WARNING / ERROR / CRITICAL

    status      = Column(String(20),  nullable=False, default="SUCCESS")
    # SUCCESS / FAILED / WARNING

    # Details
    description = Column(Text,        nullable=True)
    # Human readable: "User sarat@gmail.com placed order #A1B2C3"

    entity_type = Column(String(50),  nullable=True)
    # e.g. "order" / "book" / "user"

    entity_id   = Column(String(255), nullable=True)
    # The UUID of the affected record

    old_value   = Column(JSON,        nullable=True)
    # Previous state before change

    new_value   = Column(JSON,        nullable=True)
    # New state after change

    # Request info
    ip_address  = Column(INET,        nullable=True)
    user_agent  = Column(Text,        nullable=True)
    endpoint    = Column(String(255), nullable=True)
    method      = Column(String(10),  nullable=True)

    created_at  = Column(DateTime(timezone=True),
                  server_default=func.now(), nullable=False, index=True)

    user = relationship("TBL_AUTH_USER", foreign_keys=[user_id])
