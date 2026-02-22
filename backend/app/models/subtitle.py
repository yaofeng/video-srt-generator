import uuid

from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from ..core.database import Base

class Subtitle(Base):
    __tablename__ = "subtitles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)

    # 多语言翻译字段
    translated_text_zh = Column(Text, nullable=True)  # 简体中文
    translated_text_en = Column(Text, nullable=True)  # 英语
    translation_languages = Column(Text, nullable=True)  # JSON数组，存储已翻译的语言列表

    task = relationship("Task", back_populates="subtitles")

    __table_args__ = (
        Index('ix_subtitle_task_index', 'task_id', 'index'),
    )
