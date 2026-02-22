# backend/app/models/task.py
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Text, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum

from app.core.database import Base


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"          # 等待处理
    DOWNLOADING = "downloading"  # 正在下载
    DOWNLOADED = "downloaded"    # 下载完成
    PROCESSING = "processing"    # 正在处理
    COMPLETED = "completed"      # 处理完成
    FAILED = "failed"            # 处理失败
    CANCELLED = "cancelled"      # 已取消


class Task(Base):
    """
    任务模型

    表示一个完整的视频字幕生成任务
    """
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    video_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 文件路径
    video_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    srt_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 视频信息
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 秒
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 字节

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 关系
    subtitles: Mapped[list["Subtitle"]] = relationship(
        "Subtitle",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    logs: Mapped[list["Log"]] = relationship(
        "Log",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, status={self.status}, video_url={self.video_url[:50]}...)>"
