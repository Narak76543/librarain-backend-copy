import uuid
from sqlalchemy import (
    Column, String, Boolean, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from core.db import Base


class TBL_SUPPLIER(Base):
    __tablename__ = "tbl_supplier"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name           = Column(String(255), nullable=False, index=True)
    contact_person = Column(String(255), nullable=True)
    phone          = Column(String(50), nullable=True)
    email          = Column(String(255), nullable=True)
    address        = Column(Text, nullable=True)
    is_active      = Column(Boolean, nullable=False, default=True, index=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
