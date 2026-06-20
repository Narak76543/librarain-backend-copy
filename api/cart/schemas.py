from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Optional


class CartItemCreate(BaseModel):
    book_id:  UUID
    quantity: int = Field(default=1, ge=1)

class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1)

class CartItemResponse(BaseModel):
    id:         UUID
    book_id:    UUID
    quantity:   int
    book_title: Optional[str]    = None
    book_cover: Optional[str]    = None
    book_price: Optional[Decimal]= None
    subtotal:   Optional[Decimal]= None
    created_at: datetime

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    items:      list[CartItemResponse]
    total:      Decimal
    item_count: int