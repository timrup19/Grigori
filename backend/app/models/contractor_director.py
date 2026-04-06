import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ContractorDirector(Base):
    __tablename__ = "contractor_directors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contractor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contractors.id", ondelete="CASCADE"),
        nullable=False,
    )
    full_name = Column(Text, nullable=False)
    role = Column(Text)
    edrpou_person = Column(Text)
    source = Column(Text, default="edr")
    fetched_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    contractor = relationship("Contractor", back_populates="directors")
