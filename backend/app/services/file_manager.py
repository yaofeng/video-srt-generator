# backend/app/services/file_manager.py
import os
from pathlib import Path
from fastapi import UploadFile, HTTPException
from ..core.config import settings
import uuid

ALLOWED_VIDEO_TYPES = [
    "video/mp4",
    "video/avi",
    "video/x-msvideo",
    "video/mkv",
    "video/x-matroska",
    "video/quicktime",
    "video/x-ms-wmv",
    "video/webm"
]

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB


async def save_upload_file(upload_file: UploadFile) -> tuple[str, Path]:
    """
    保存上传的文件

    Args:
        upload_file: 上传的文件对象

    Returns:
        tuple: (task_id, file_path)
    """
    # 验证文件类型
    if upload_file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {upload_file.content_type}"
        )

    # 生成任务 ID 和文件路径
    task_id = str(uuid.uuid4())
    file_extension = Path(upload_file.filename).suffix
    file_path = settings.UPLOAD_DIR / f"{task_id}{file_extension}"

    # 保存文件
    try:
        content = await upload_file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件过大，最大支持 {MAX_FILE_SIZE // (1024**3)}GB"
            )

        # 确保上传目录存在
        settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # 写入文件
        with open(file_path, 'wb') as f:
            f.write(content)

    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    return task_id, file_path


async def delete_file(file_path: Path) -> bool:
    """
    删除文件

    Args:
        file_path: 文件路径

    Returns:
        bool: 是否删除成功
    """
    try:
        if file_path.exists():
            os.remove(file_path)
        return True
    except Exception:
        return False
