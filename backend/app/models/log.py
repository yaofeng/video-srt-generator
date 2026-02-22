from sqlalchemy import Column, String, Text, ForeignKey, Integer, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base

class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    level = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="logs")
