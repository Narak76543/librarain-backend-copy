import uuid
from sqlalchemy import (
    Column, String, Boolean, Text,
    Integer, Numeric, Date, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from core.db import Base


class TBL_BOOK(Base):
    __tablename__ = "tbl_book"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title          = Column(String(255),    nullable=False, index=True)
    author         = Column(String(150),    nullable=False, index=True)
    description    = Column(Text,           nullable=True)
    price          = Column(Numeric(10, 2), nullable=False)
    cost_price     = Column(Numeric(10, 2), nullable=False, default=0)
    cover_url      = Column(Text,           nullable=True)
    stock          = Column(Integer,        nullable=False, default=0)
    min_stock_level = Column(Integer,       nullable=False, default=5)
    min_profit_margin = Column(Numeric(5, 2), nullable=False, default=20.00)
    isbn           = Column(String(20),     nullable=True,  unique=True)
    language       = Column(String(50),     nullable=True,  default="English")
    pages          = Column(Integer,        nullable=True)
    publisher      = Column(String(150),    nullable=True)
    published_date = Column(Date,           nullable=True)
    featured       = Column(Boolean,        nullable=False, default=False)
    rating_average = Column(Numeric(3, 2),  nullable=False, default=0.0)
    rating_count   = Column(Integer,        nullable=False, default=0)
    is_active      = Column(Boolean,        nullable=False, default=True, index=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tbl_category.id", ondelete="SET NULL"),
        nullable=True,
    )

    category = relationship("TBL_CATEGORY")


class TBL_STOCK_HISTORY(Base):
    __tablename__ = "tbl_stock_history"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id     = Column(UUID(as_uuid=True), ForeignKey("tbl_book.id", ondelete="CASCADE"), nullable=False)
    quantity    = Column(Integer, nullable=False)
    cost_price  = Column(Numeric(10, 2), nullable=False)
    sale_price  = Column(Numeric(10, 2), nullable=False)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("tbl_auth_user.id", ondelete="SET NULL"), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    book = relationship("TBL_BOOK")
    user = relationship("TBL_AUTH_USER")


class TBL_STOCK_IN(Base):
    __tablename__ = "tbl_stock_in"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id     = Column(UUID(as_uuid=True), ForeignKey("tbl_book.id", ondelete="CASCADE"), nullable=False)
    quantity    = Column(Integer, nullable=False)
    cost_price  = Column(Numeric(10, 2), nullable=False)
    total_cost  = Column(Numeric(10, 2), nullable=False)
    note        = Column(String(255), nullable=True)
    created_by  = Column(UUID(as_uuid=True), ForeignKey("tbl_auth_user.id", ondelete="SET NULL"), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    book = relationship("TBL_BOOK")
    user = relationship("TBL_AUTH_USER")