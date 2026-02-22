from sqlalchemy import Column, String, Integer, Float, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from ..core.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pending")
    progress = Column(Integer, default=0)
    current_step = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    subtitles = relationship("Subtitle", back_populates="task", cascade="all, delete-orphan")
    segments = relationship("Segment", back_populates="task", cascade="all, delete-orphan")
    logs = relationship("Log", back_populates="task", cascade="all, delete-orphan")
