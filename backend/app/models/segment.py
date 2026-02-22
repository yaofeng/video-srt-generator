from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from ..core.database import Base

class Segment(Base):
    __tablename__ = "segments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    audio_path = Column(String, nullable=False)
    status = Column(String, default="pending")
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    task = relationship("Task", back_populates="segments")
