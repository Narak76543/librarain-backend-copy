import uuid
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from core.db import Base


class TBL_CART_ITEM(Base):
    __tablename__ = "tbl_cart_item"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("tbl_auth_user.id", ondelete="CASCADE"), nullable=False, index=True)
    book_id    = Column(UUID(as_uuid=True), ForeignKey("tbl_book.id",      ondelete="CASCADE"), nullable=False, index=True)
    quantity   = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    book = relationship("TBL_BOOK")
    user = relationship("TBL_AUTH_USER")