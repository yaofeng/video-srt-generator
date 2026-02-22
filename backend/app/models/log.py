# backend/app/models/log.py
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum

from app.core.database import Base


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Log(Base):
    """
    日志模型

    记录任务处理过程中的日志信息
    """
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 日志内容
    level: Mapped[LogLevel] = mapped_column(
        SQLEnum(LogLevel),
        default=LogLevel.INFO,
        nullable=False,
        index=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    step: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 处理步骤

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # 关系
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="logs",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Log(id={self.id}, task_id={self.task_id}, level={self.level}, message={self.message[:50]}...)>"
