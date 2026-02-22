from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, ForeignKey, Integer, DateTime, Index
from sqlalchemy.orm import relationship

from ..core.database import Base

class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    level = Column(String(20), nullable=False, index=True)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    task = relationship("Task", back_populates="logs")

    __table_args__ = (
        Index('ix_log_task_timestamp', 'task_id', 'timestamp'),
    )
