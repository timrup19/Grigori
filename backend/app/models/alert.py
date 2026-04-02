import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Numeric, String
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # What's flagged
    alert_type = Column(String(50), nullable=False)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"))
    contractor_id = Column(UUID(as_uuid=True), ForeignKey("contractors.id"))

    # Alert details
    risk_score = Column(Numeric(5, 2), nullable=False)
    risk_category = Column(String(20), nullable=False)
    reasons = Column(JSONB, nullable=False)

    # Values at stake
    value_at_risk = Column(Numeric(20, 2))

    # Status
    is_active = Column(Boolean, default=True)
    reviewed_at = Column(DateTime(timezone=True))

    # Timing
    detected_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    tender = relationship("Tender", back_populates="alerts")
    contractor = relationship("Contractor", back_populates="alerts")
