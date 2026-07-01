import uuid
from sqlalchemy import (
    Column, String, Text, Integer, Numeric, DateTime, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.db import Base


class TBL_PURCHASE_ORDER(Base):
    __tablename__ = "tbl_purchase_order"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    po_number   = Column(String(50), nullable=False, unique=True, index=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("tbl_supplier.id", ondelete="RESTRICT"), nullable=False)
    total_cost  = Column(Numeric(10, 2), nullable=False, default=0)
    status      = Column(String(50), nullable=False, default="pending") # pending, received, cancelled
    ordered_at  = Column(DateTime(timezone=True), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)
    note        = Column(Text, nullable=True)
    created_by  = Column(UUID(as_uuid=True), ForeignKey("tbl_auth_user.id", ondelete="SET NULL"), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    supplier = relationship("TBL_SUPPLIER")
    user     = relationship("TBL_AUTH_USER")
    items    = relationship("TBL_PURCHASE_ORDER_ITEM", back_populates="purchase_order", cascade="all, delete-orphan")


class TBL_PURCHASE_ORDER_ITEM(Base):
    __tablename__ = "tbl_purchase_order_item"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    po_id      = Column(UUID(as_uuid=True), ForeignKey("tbl_purchase_order.id", ondelete="CASCADE"), nullable=False)
    book_id    = Column(UUID(as_uuid=True), ForeignKey("tbl_book.id", ondelete="RESTRICT"), nullable=False)
    quantity   = Column(Integer, nullable=False)
    cost_price = Column(Numeric(10, 2), nullable=False)
    total_cost = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    purchase_order = relationship("TBL_PURCHASE_ORDER", back_populates="items")
    book           = relationship("TBL_BOOK")
