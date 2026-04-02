import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Buyer(Base):
    __tablename__ = "buyers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prozorro_id = Column(String(100), unique=True)
    edrpou = Column(String(20))
    name = Column(String(500), nullable=False)
    name_normalized = Column(String(500))

    # Location
    region = Column(String(100))
    address = Column(Text)

    # Classification
    buyer_type = Column(String(50))

    # Stats
    total_tenders = Column(Integer, default=0)
    total_value = Column(Numeric(20, 2), default=Decimal("0"))
    avg_competition = Column(Numeric(5, 2))

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    tenders = relationship("Tender", back_populates="buyer")
