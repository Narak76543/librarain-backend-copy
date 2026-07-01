from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class InvoiceItemResponse(BaseModel):
    id: UUID
    book_id: Optional[UUID]
    book_title: str
    quantity: int
    unit_price: str
    line_total: str
    profit: str

    class Config:
        from_attributes = True

class InvoiceResponse(BaseModel):
    id: UUID
    invoice_number: str
    order_id: Optional[UUID]
    user_id: Optional[UUID]
    customer_name: str
    subtotal: str
    tax_amount: str
    discount_amount: str
    delivery_fee: str
    total: str
    status: str
    issued_at: datetime
    due_date: datetime
    paid_at: Optional[datetime]
    pdf_url: Optional[str]
    notes: Optional[str]
    items: List[InvoiceItemResponse]

    class Config:
        from_attributes = True

class InvoiceListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    invoices: List[InvoiceResponse]
