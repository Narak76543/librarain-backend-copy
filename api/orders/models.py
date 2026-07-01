import uuid
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from core.db import Base


class TBL_ORDER(Base):
    __tablename__ = "tbl_order"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("tbl_auth_user.id", ondelete="CASCADE"), nullable=False, index=True)
    total            = Column(Numeric(10, 2), nullable=False)
    status           = Column(String(20),     nullable=False, default="pending", index=True)
    delivery_way     = Column(String(50),     nullable=True,  default="Pick Up")
    delivery_partner = Column(String(50),     nullable=True)
    delivery_address = Column(String(255),    nullable=True)
    payment_method   = Column(String(50),     nullable=True,  default="COD")
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    user        = relationship("TBL_AUTH_USER")
    order_items = relationship("TBL_ORDER_ITEM", back_populates="order", cascade="all, delete-orphan")


class TBL_ORDER_ITEM(Base):
    __tablename__ = "tbl_order_item"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id           = Column(UUID(as_uuid=True), ForeignKey("tbl_order.id", ondelete="CASCADE"), nullable=False)
    book_id            = Column(UUID(as_uuid=True), ForeignKey("tbl_book.id",  ondelete="SET NULL"), nullable=True)
    quantity           = Column(Integer,        nullable=False)
    price_at_purchase  = Column(Numeric(10, 2), nullable=False)
    cost_price_at_purchase = Column(Numeric(10, 2), nullable=False, server_default="0.00")

    order = relationship("TBL_ORDER", back_populates="order_items")
    book  = relationship("TBL_BOOK")


class TBL_ORDER_ITEM_BATCH_ALLOCATION(Base):
    __tablename__ = "tbl_order_item_batch_allocation"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_item_id = Column(UUID(as_uuid=True), ForeignKey("tbl_order_item.id", ondelete="CASCADE"), nullable=False)
    stock_batch_id = Column(UUID(as_uuid=True), ForeignKey("tbl_stock_batch.id", ondelete="RESTRICT"), nullable=False)
    quantity_allocated = Column(Integer, nullable=False)
    unit_cost_price = Column(Numeric(10, 2), nullable=False)
    
    order_item = relationship("TBL_ORDER_ITEM")
    stock_batch = relationship("TBL_STOCK_BATCH")