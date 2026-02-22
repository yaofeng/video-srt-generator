# backend/app/models/subtitle.py
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Float, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Subtitle(Base):
    """
    字幕模型

    表示生成的字幕文件，包含元数据
    """
    __tablename__ = "subtitles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 字幕信息
    language: Mapped[str] = mapped_column(String(10), default="zh", nullable=False)  # 语言代码
    total_segments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 总片段数
    total_duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 总时长(秒)

    # 文件路径
    srt_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    json_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # 关系
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="subtitles",
        lazy="selectin"
    )
    segments: Mapped[list["Segment"]] = relationship(
        "Segment",
        back_populates="subtitle",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Segment.start_time"
    )

    def __repr__(self) -> str:
        return f"<Subtitle(id={self.id}, task_id={self.task_id}, segments={self.total_segments})>"
