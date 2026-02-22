from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pathlib import Path
from typing import Generator

from app.core.config import settings

Base = declarative_base()

# 数据库文件路径
DB_FILE = settings.BASE_DIR / "srt_generator.db"
DATABASE_URL = f"sqlite:///{DB_FILE}"

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖注入函数

    Yields:
        Session: 数据库会话
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    初始化数据库，创建所有表

    在应用启动时调用此函数以确保所有表都已创建
    """
    Base.metadata.create_all(bind=engine)


def close_db() -> None:
    """
    关闭数据库连接

    在应用关闭时调用此函数以正确关闭数据库连接
    """
    engine.dispose()
