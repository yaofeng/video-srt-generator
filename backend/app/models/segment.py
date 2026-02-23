import uuid

from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from ..core.database import Base

class Segment(Base):
    __tablename__ = "segments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    audio_path = Column(String(500), nullable=False)
    status = Column(String(50), default="pending", index=True)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    task = relationship("Task", back_populates="segments")

    __table_args__ = (
        Index('ix_segment_task_status', 'task_id', 'status'),
        Index('ix_segment_task_index', 'task_id', 'index', unique=True),
    )
