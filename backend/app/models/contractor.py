import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Contractor(Base):
    __tablename__ = "contractors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    edrpou = Column(String(20), unique=True, nullable=False)
    name = Column(String(500), nullable=False)
    name_normalized = Column(String(500))

    # Address
    address = Column(Text)
    region = Column(String(100))
    postal_code = Column(String(20))

    # Metadata
    is_active = Column(Boolean, default=True)
    first_seen_at = Column(DateTime(timezone=True))
    last_seen_at = Column(DateTime(timezone=True))

    # Aggregated stats
    total_tenders = Column(Integer, default=0)
    total_wins = Column(Integer, default=0)
    total_value_won = Column(Numeric(20, 2), default=Decimal("0"))
    win_rate = Column(Numeric(5, 4))

    # Risk scoring
    risk_score = Column(Numeric(5, 2))
    risk_category = Column(String(20))
    risk_updated_at = Column(DateTime(timezone=True))

    # Sanctions / PEP enrichment
    is_sanctioned = Column(Boolean, default=False)
    is_pep = Column(Boolean, default=False)
    sanctions_hits = Column(JSONB, default=list)
    enriched_at = Column(DateTime(timezone=True))

    # EDR (Ukrainian company registry)
    edr_status = Column(String(20), default="unknown")
    directors_fetched_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    directors = relationship("ContractorDirector", back_populates="contractor", cascade="all, delete-orphan")
    bids = relationship("Bid", back_populates="contractor")
    won_tenders = relationship("Tender", foreign_keys="Tender.winner_id", back_populates="winner")
    alerts = relationship("Alert", back_populates="contractor")
    co_bidding_as_a = relationship(
        "CoBidding", foreign_keys="CoBidding.contractor_a_id", back_populates="contractor_a"
    )
    co_bidding_as_b = relationship(
        "CoBidding", foreign_keys="CoBidding.contractor_b_id", back_populates="contractor_b"
    )
