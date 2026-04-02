import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Numeric, String
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Bid(Base):
    __tablename__ = "bids"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    contractor_id = Column(UUID(as_uuid=True), ForeignKey("contractors.id"), nullable=False)

    # Bid details
    bid_value = Column(Numeric(20, 2))
    currency = Column(String(10), default="UAH")
    status = Column(String(50))

    # Result
    is_winner = Column(Boolean, default=False)

    # Dates
    bid_date = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    tender = relationship("Tender", back_populates="bids")
    contractor = relationship("Contractor", back_populates="bids")
