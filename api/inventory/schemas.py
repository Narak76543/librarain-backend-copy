from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime

class StockAdjustmentCreate(BaseModel):
    book_id: UUID
    quantity_adjusted: int
    reason: str
    notes: Optional[str] = None

class StockAdjustmentResponse(BaseModel):
    id: UUID
    book_id: UUID
    quantity_adjusted: int
    reason: str
    notes: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
