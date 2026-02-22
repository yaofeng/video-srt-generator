# backend/app/api/deps.py
from sqlalchemy.orm import Session
from ..core.database import SessionLocal

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
