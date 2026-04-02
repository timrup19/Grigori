import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey

from app.database import Base


class Tender(Base):
    __tablename__ = "tenders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prozorro_id = Column(String(100), unique=True, nullable=False)

    # Basic info
    title = Column(Text)
    description = Column(Text)
    status = Column(String(50))
    procurement_method = Column(String(50))
    procurement_method_type = Column(String(100))

    # Value
    expected_value = Column(Numeric(20, 2))
    currency = Column(String(10), default="UAH")

    # Classification
    cpv_code = Column(String(20))
    cpv_description = Column(String(500))

    # Relationships (FKs)
    buyer_id = Column(UUID(as_uuid=True), ForeignKey("buyers.id"))
    winner_id = Column(UUID(as_uuid=True), ForeignKey("contractors.id"))

    # Award info
    award_value = Column(Numeric(20, 2))
    award_date = Column(Date)

    # Competition
    num_bids = Column(Integer, default=0)
    num_qualified_bids = Column(Integer, default=0)

    # Dates
    tender_start_date = Column(DateTime(timezone=True))
    tender_end_date = Column(DateTime(timezone=True))
    date_modified = Column(DateTime(timezone=True))

    # Location
    region = Column(String(100))

    # Risk scoring
    risk_score = Column(Numeric(5, 2))
    risk_category = Column(String(20))
    risk_factors = Column(JSONB)
    risk_updated_at = Column(DateTime(timezone=True))

    # Flags
    is_single_bidder = Column(Boolean, default=False)
    is_price_anomaly = Column(Boolean, default=False)
    is_bid_pattern_anomaly = Column(Boolean, default=False)

    # Raw data
    raw_data = Column(JSONB)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    buyer = relationship("Buyer", back_populates="tenders")
    winner = relationship("Contractor", foreign_keys=[winner_id], back_populates="won_tenders")
    bids = relationship("Bid", back_populates="tender", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="tender")
