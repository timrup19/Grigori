import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class CpvBenchmark(Base):
    __tablename__ = "cpv_benchmarks"

    __table_args__ = (
        UniqueConstraint("cpv_code", name="cpv_benchmarks_unique"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cpv_code = Column(String(20), nullable=False)
    cpv_description = Column(String(500))

    # Statistics
    sample_count = Column(Integer)
    mean_value = Column(Numeric(20, 2))
    median_value = Column(Numeric(20, 2))
    std_value = Column(Numeric(20, 2))
    p25_value = Column(Numeric(20, 2))
    p75_value = Column(Numeric(20, 2))

    # Computed thresholds
    anomaly_threshold_high = Column(Numeric(20, 2))
    anomaly_threshold_low = Column(Numeric(20, 2))

    calculated_at = Column(DateTime(timezone=True), default=datetime.utcnow)
