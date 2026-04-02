import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class RegionStats(Base):
    __tablename__ = "region_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region = Column(String(100), nullable=False, unique=True)

    # Coordinates for map (center point)
    latitude = Column(Numeric(10, 6))
    longitude = Column(Numeric(10, 6))

    # Statistics
    total_tenders = Column(Integer, default=0)
    total_value = Column(Numeric(20, 2), default=0)
    high_risk_tenders = Column(Integer, default=0)
    avg_risk_score = Column(Numeric(5, 2))
    single_bidder_rate = Column(Numeric(5, 4))

    # Top issues
    top_risk_factors = Column(JSONB)

    calculated_at = Column(DateTime(timezone=True), default=datetime.utcnow)
