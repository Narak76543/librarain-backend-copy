from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime

# Request Schemas
class POItemCreate(BaseModel):
    book_id: UUID
    quantity: int = Field(gt=0)
    cost_price: float = Field(gt=0)

class PurchaseOrderCreate(BaseModel):
    supplier_id: UUID
    note: Optional[str] = None
    items: List[POItemCreate]

class PurchaseOrderStatusUpdate(BaseModel):
    status: str # 'received', 'cancelled'

# Response Schemas
class POItemResponse(BaseModel):
    id: UUID
    book_id: UUID
    quantity: int
    cost_price: float
    total_cost: float
    
    # Nested book info
    book_title: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class PurchaseOrderResponse(BaseModel):
    id: UUID
    po_number: str
    supplier_id: UUID
    total_cost: float
    status: str
    ordered_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    note: Optional[str] = None
    created_at: datetime
    
    # Nested supplier info
    supplier_name: Optional[str] = None
    items: List[POItemResponse] = []

    model_config = ConfigDict(from_attributes=True)
