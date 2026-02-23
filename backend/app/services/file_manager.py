# backend/app/services/file_manager.py
import os
from pathlib import Path
from fastapi import UploadFile, HTTPException
from ..core.config import settings
import uuid

# 基于文件扩展名的验证（更可靠）
ALLOWED_VIDEO_EXTENSIONS = [
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"
]

# 允许的 MIME 类型（作为辅助验证）
ALLOWED_VIDEO_TYPES = [
    "video/mp4", "video/avi", "video/x-msvideo", "video/mkv", "video/x-matroska",
    "video/quicktime", "video/x-ms-wmv", "video/webm", "video/x-flv",
    "application/octet-stream"  # 某些浏览器上传视频时使用此类型
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
    # 验证文件扩展名（主要验证方式）
    file_extension = Path(upload_file.filename).suffix.lower()
    if not file_extension:
        raise HTTPException(
            status_code=400,
            detail="文件缺少扩展名"
        )

    if file_extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的视频格式：{file_extension}。支持的格式：{', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        )

    # 生成任务 ID 和文件路径
    task_id = str(uuid.uuid4())
    file_path = settings.UPLOAD_DIR / f"{task_id}{file_extension}"

    # 保存文件 - 使用流式读写避免大文件内存问题
    try:
        # 确保上传目录存在
        settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # 流式写入：边读边写，避免大文件一次性加载到内存
        with open(file_path, 'wb') as f:
            # 每次读取 1MB 块
            chunk_size = 1024 * 1024  # 1MB
            total_bytes = 0
            while True:
                chunk = await upload_file.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                total_bytes += len(chunk)
                # 实时检查文件大小
                if total_bytes > MAX_FILE_SIZE:
                    os.remove(file_path)
                    raise HTTPException(
                        status_code=400,
                        detail=f"文件过大，最大支持 {MAX_FILE_SIZE // (1024**3)}GB"
                    )

    except HTTPException:
        raise
    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"文件保存失败：{str(e)}")

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
