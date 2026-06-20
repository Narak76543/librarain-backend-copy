from pydantic import BaseModel , Field
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Optional

class OrderItemResponse(BaseModel):
    id:                UUID
    book_id:           Optional[UUID]    = None
    book_title:        Optional[str]     = None
    book_cover:        Optional[str]     = None
    quantity:          int
    price_at_purchase: Decimal
    subtotal:          Decimal

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id:          UUID
    total:       Decimal
    status:      str
    created_at:  datetime
    order_items: list[OrderItemResponse] = []

    class Config:
        from_attributes = True

class PlaceOrderRequest(BaseModel):
    delivery_way: Optional[str] = "Pick Up"
    delivery_partner: Optional[str] = None
    delivery_address: Optional[str] = None
    payment_method: Optional[str] = "COD"

class UpdateOrderStatusSchemas (BaseModel) :
    status : str=  Field(... , description="The new status of the order (e.g., 'pending', 'shipped', 'completed', 'cancelled')")