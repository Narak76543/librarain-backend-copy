from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime
from typing import Optional
from api.categories.schemas import CategoryResponse


class BookResponse(BaseModel):
    id:             UUID
    title:          str
    author:         str
    description:    Optional[str]     = None
    price:          Decimal
    cost_price:     Decimal
    cover_url:      Optional[str]     = None
    stock:          int
    min_profit_margin: Decimal = Decimal("20.00")
    isbn:           Optional[str]     = None
    language:       Optional[str]     = None
    pages:          Optional[int]     = None
    publisher:      Optional[str]     = None
    published_date: Optional[date]    = None
    featured:       bool              = False
    rating_average: Decimal
    rating_count:   int
    is_active:      bool              = True
    category:       Optional[CategoryResponse] = None
    created_at:     datetime

    class Config:
        from_attributes = True


class BookCreate(BaseModel):
    title:          str            = Field(min_length=1, max_length=255)
    author:         str            = Field(min_length=1, max_length=150)
    description:    Optional[str]  = None
    price:          Decimal        = Field(ge=0)
    cost_price:     Decimal        = Field(ge=0, default=0.00)
    stock:          int            = Field(ge=0, default=0)
    min_profit_margin: Decimal     = Field(ge=0, default=20.00)
    isbn:           Optional[str]  = None
    language:       Optional[str]  = "English"
    pages:          Optional[int]  = None
    publisher:      Optional[str]  = None
    published_date: Optional[date] = None
    category_id:    Optional[UUID] = None
    featured:       bool           = False
    is_active:      bool           = True


class BookUpdate(BaseModel):
    title:          Optional[str]     = None
    author:         Optional[str]     = None
    description:    Optional[str]     = None
    price:          Optional[Decimal] = None
    cost_price:     Optional[Decimal] = None
    stock:          Optional[int]     = None
    min_profit_margin: Optional[Decimal] = None
    isbn:           Optional[str]     = None
    language:       Optional[str]     = None
    pages:          Optional[int]     = None
    publisher:      Optional[str]     = None
    published_date: Optional[date]    = None
    category_id:    Optional[UUID]    = None
    is_active:      Optional[bool]    = None
    featured:       Optional[bool]    = None


class StockInCreate(BaseModel):
    quantity:   int     = Field(gt=0)
    cost_price: Decimal = Field(ge=0)
    sale_price: Decimal = Field(gt=0)
    notes:      Optional[str] = None