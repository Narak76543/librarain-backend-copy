from pydantic import BaseModel
from uuid import UUID
from typing import Optional


class CategoryResponse(BaseModel):
    id:        UUID
    name:      str
    slug:      str
    icon_url:  Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    name:     str
    slug:     str
    icon_url: Optional[str] = None


class CategoryUpdate(BaseModel):
    name:      Optional[str]  = None
    slug:      Optional[str]  = None
    icon_url:  Optional[str]  = None
    is_active: Optional[bool] = None