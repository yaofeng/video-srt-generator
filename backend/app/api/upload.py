# backend/app/api/upload.py
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from .deps import get_db
from ..models.task import Task
from ..services.file_manager import save_upload_file

router = APIRouter()


def _serialize_datetime(dt: datetime) -> str:
    """序列化datetime对象，确保包含时区信息"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


@router.post("/tasks/upload")
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    上传视频文件并创建任务

    Args:
        file: 上传的视频文件
        db: 数据库会话

    Returns:
        包含任务ID和文件信息的响应
    """
    # 保存上传的文件
    task_id, file_path = await save_upload_file(file)

    # 创建任务记录
    task = Task(
        id=task_id,
        filename=file.filename,
        file_path=str(file_path),
        file_size=file_path.stat().st_size,
        status="pending"
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "task_id": task_id,
        "filename": file.filename,
        "file_size": task.file_size,
        "status": "pending",
        "created_at": _serialize_datetime(task.created_at) if task.created_at else None
    }
