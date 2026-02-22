# backend/app/models/segment.py
from sqlalchemy import String, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Segment(Base):
    """
    字幕片段模型

    表示单个字幕片段，包含时间轴和文本内容
    """
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subtitle_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("subtitles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 片段序号

    # 时间轴（毫秒）
    start_time: Mapped[int] = mapped_column(Integer, nullable=False)  # 开始时间(ms)
    end_time: Mapped[int] = mapped_column(Integer, nullable=False)    # 结束时间(ms)
    duration: Mapped[float] = mapped_column(Float, nullable=False)    # 时长(秒)

    # 文本内容
    text: Mapped[str] = mapped_column(Text, nullable=False)           # 字幕文本
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # 置信度

    # 关系
    subtitle: Mapped["Subtitle"] = relationship(
        "Subtitle",
        back_populates="segments",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Segment(id={self.id}, index={self.segment_index}, text={self.text[:30]}...)>"

    @property
    def start_time_srt(self) -> str:
        """转换为 SRT 时间格式的开始时间"""
        return self._milliseconds_to_srt_time(self.start_time)

    @property
    def end_time_srt(self) -> str:
        """转换为 SRT 时间格式的结束时间"""
        return self._milliseconds_to_srt_time(self.end_time)

    @staticmethod
    def _milliseconds_to_srt_time(ms: int) -> str:
        """
        将毫秒转换为 SRT 时间格式

        Args:
            ms: 毫秒数

        Returns:
            SRT 时间格式字符串 (HH:MM:SS,mmm)
        """
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        milliseconds = ms % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
