import uuid
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.db import Base

class TBL_INVOICE(Base):
    __tablename__ = "tbl_invoice"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number  = Column(String(50), unique=True, nullable=False, index=True)
    order_id        = Column(UUID(as_uuid=True), ForeignKey("tbl_order.id", ondelete="SET NULL"), nullable=True)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("tbl_auth_user.id", ondelete="SET NULL"), nullable=True)
    subtotal        = Column(Numeric(10, 2), nullable=False)
    tax_amount      = Column(Numeric(10, 2), nullable=False, default=0.00)
    discount_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    delivery_fee    = Column(Numeric(10, 2), nullable=False, default=0.00)
    total           = Column(Numeric(10, 2), nullable=False)
    status          = Column(String(20), nullable=False, default="draft", index=True)
    issued_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    due_date        = Column(DateTime(timezone=True), nullable=False)
    paid_at         = Column(DateTime(timezone=True), nullable=True)
    pdf_url         = Column(Text, nullable=True)
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    order = relationship("TBL_ORDER")
    user  = relationship("TBL_AUTH_USER")
    items = relationship("TBL_INVOICE_ITEM", back_populates="invoice", cascade="all, delete-orphan")


class TBL_INVOICE_ITEM(Base):
    __tablename__ = "tbl_invoice_item"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id  = Column(UUID(as_uuid=True), ForeignKey("tbl_invoice.id", ondelete="CASCADE"), nullable=False)
    book_id     = Column(UUID(as_uuid=True), ForeignKey("tbl_book.id", ondelete="SET NULL"), nullable=True)
    book_title  = Column(String(255), nullable=False)
    quantity    = Column(Integer, nullable=False)
    unit_price  = Column(Numeric(10, 2), nullable=False)
    cost_price  = Column(Numeric(10, 2), nullable=False, default=0.00)
    line_total  = Column(Numeric(10, 2), nullable=False)
    profit      = Column(Numeric(10, 2), nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    invoice = relationship("TBL_INVOICE", back_populates="items")
    book    = relationship("TBL_BOOK")
