import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.db import Base

class TBL_STOCK_ADJUSTMENT(Base):
    __tablename__ = "tbl_stock_adjustment"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id           = Column(UUID(as_uuid=True), ForeignKey("tbl_book.id", ondelete="CASCADE"), nullable=False)
    quantity_adjusted = Column(Integer, nullable=False) # e.g., -2 or +5
    reason            = Column(String(100), nullable=False) # e.g., Damaged, Lost, Found, Audit
    notes             = Column(String(255), nullable=True)
    created_by        = Column(UUID(as_uuid=True), ForeignKey("tbl_auth_user.id", ondelete="SET NULL"), nullable=True)
    created_at        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    book = relationship("TBL_BOOK")
    user = relationship("TBL_AUTH_USER")


class TBL_INVENTORY_TRANSACTION(Base):
    __tablename__ = "tbl_inventory_transaction"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id          = Column(UUID(as_uuid=True), ForeignKey("tbl_book.id", ondelete="CASCADE"), nullable=False)
    transaction_type = Column(String(50), nullable=False) # e.g., 'sale', 'purchase', 'adjustment', 'return'
    quantity         = Column(Integer, nullable=False) # positive or negative
    current_stock    = Column(Integer, nullable=False) # snapshot of stock after this transaction
    reference_id     = Column(String(100), nullable=True) # order_id, po_id, or adjustment_id
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    book = relationship("TBL_BOOK")


class TBL_STOCK_BATCH(Base):
    __tablename__ = "tbl_stock_batch"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("tbl_book.id", ondelete="CASCADE"), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("tbl_supplier.id", ondelete="RESTRICT"), nullable=True) # Nullable for legacy data
    po_item_id = Column(UUID(as_uuid=True), ForeignKey("tbl_purchase_order_item.id", ondelete="SET NULL"), nullable=True)
    
    initial_quantity = Column(Integer, nullable=False)
    remaining_quantity = Column(Integer, nullable=False)
    unit_cost_price = Column(Numeric(10, 2), nullable=False)
    
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(20), default="active") # active, depleted

    book = relationship("TBL_BOOK")
    supplier = relationship("TBL_SUPPLIER")
