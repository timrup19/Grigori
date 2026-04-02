import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, Numeric
from sqlalchemy import ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class CoBidding(Base):
    __tablename__ = "co_bidding"

    __table_args__ = (
        CheckConstraint("contractor_a_id < contractor_b_id", name="co_bidding_order"),
        UniqueConstraint("contractor_a_id", "contractor_b_id", name="co_bidding_unique"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contractor_a_id = Column(UUID(as_uuid=True), ForeignKey("contractors.id"), nullable=False)
    contractor_b_id = Column(UUID(as_uuid=True), ForeignKey("contractors.id"), nullable=False)

    # Stats
    co_bid_count = Column(Integer, default=1)
    first_co_bid_date = Column(Date)
    last_co_bid_date = Column(Date)

    # Analysis
    suspicion_score = Column(Numeric(5, 2))

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    contractor_a = relationship(
        "Contractor", foreign_keys=[contractor_a_id], back_populates="co_bidding_as_a"
    )
    contractor_b = relationship(
        "Contractor", foreign_keys=[contractor_b_id], back_populates="co_bidding_as_b"
    )
