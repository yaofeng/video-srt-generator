import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Text, ForeignKey, Index, DateTime
from sqlalchemy.orm import relationship

from ..core.database import Base


class TranslationTask(Base):
    """翻译任务模型"""

    __tablename__ = "translation_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    target_language = Column(String(10), nullable=False)  # en, ja, ko 等
    status = Column(String(20), nullable=False, default="pending")  # pending/processing/completed/failed
    progress = Column(Integer, nullable=False, default=0)  # 0-100
    current_step = Column(String(100), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # 关系
    parent_task = relationship("Task", back_populates="translation_tasks")

    __table_args__ = (
        Index('ix_translation_tasks_parent', 'parent_task_id'),
        Index('ix_translation_tasks_status', 'status'),
    )

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "parent_task_id": self.parent_task_id,
            "target_language": self.target_language,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
