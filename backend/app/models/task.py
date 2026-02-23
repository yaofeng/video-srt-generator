from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Index
from sqlalchemy.orm import relationship

from ..core.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="pending", index=True)
    progress = Column(Integer, default=0)
    current_step = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    keywords = Column(Text, nullable=True)  # 用于 ASR 识别的关键字/上下文

    subtitles = relationship("Subtitle", back_populates="task", cascade="all, delete-orphan")
    segments = relationship("Segment", back_populates="task", cascade="all, delete-orphan")
    logs = relationship("Log", back_populates="task", cascade="all, delete-orphan")
    translation_tasks = relationship("TranslationTask", back_populates="parent_task", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_task_status_created', 'status', 'created_at'),
    )
