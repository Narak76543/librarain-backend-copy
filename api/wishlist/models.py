import uuid
from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from core.db import Base


class TBL_WISHLIST(Base):
    __tablename__ = "tbl_wishlist"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("tbl_auth_user.id", ondelete="CASCADE"), nullable=False, index=True)
    book_id    = Column(UUID(as_uuid=True), ForeignKey("tbl_book.id",      ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    book = relationship("TBL_BOOK")
    user = relationship("TBL_AUTH_USER")

    # One book per user only
    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_wishlist_user_book"),
    )