import uuid
from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db import Base


class TBL_CATEGORY(Base):
    __tablename__ = "tbl_category"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name      = Column(String(100), nullable=False, unique=True)
    slug      = Column(String(100), nullable=False, unique=True)
    icon_url  = Column(String(255), nullable=True)
    is_active = Column(Boolean,     nullable=False, default=True)

    # books = relationship("TBL_BOOK", back_populates="category")