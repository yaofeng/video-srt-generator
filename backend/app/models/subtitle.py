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
    translated_text_en = Column(Text, nullable=True)  # 英语
    translated_text_ja = Column(Text, nullable=True)  # 日语
    translated_text_ko = Column(Text, nullable=True)  # 韩语
    translated_text_fr = Column(Text, nullable=True)  # 法语
    translated_text_de = Column(Text, nullable=True)  # 德语
    translated_text_es = Column(Text, nullable=True)  # 西班牙语
    translated_text_zh_hant = Column(Text, nullable=True)  # 繁体中文
    translation_languages = Column(Text, nullable=True)  # JSON数组，存储已翻译的语言列表

    task = relationship("Task", back_populates="subtitles")

    __table_args__ = (
        Index('ix_subtitle_task_index', 'task_id', 'index'),
    )
