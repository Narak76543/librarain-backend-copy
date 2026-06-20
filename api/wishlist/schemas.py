from pydantic import BaseModel
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Optional


class WishlistItemResponse(BaseModel):
    id:           UUID
    book_id:      UUID
    book_title:   Optional[str]     = None
    book_author:  Optional[str]     = None
    book_cover:   Optional[str]     = None
    book_price:   Optional[Decimal] = None
    book_rating:  Optional[Decimal] = None
    category_name:Optional[str]     = None
    created_at:   datetime

    class Config:
        from_attributes = True


class WishlistAddRequest(BaseModel):
    book_id: UUID