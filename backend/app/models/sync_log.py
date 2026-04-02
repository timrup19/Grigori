import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class SyncLog(Base):
    __tablename__ = "sync_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_type = Column(String(50), nullable=False)

    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True))

    records_fetched = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    errors = Column(Integer, default=0)

    status = Column(String(20), default="running")
    error_message = Column(Text)

    metadata_ = Column("metadata", JSONB)
