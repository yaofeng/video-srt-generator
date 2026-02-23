# backend/app/api/tasks.py
import asyncio
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from pathlib import Path
import os

from .deps import get_db
from ..models.task import Task
from ..models.subtitle import Subtitle
from ..models.segment import Segment
from ..models.log import Log
from ..services.task_processor import process_task, ProgressEvent, cleanup_task_files
from ..core.config import settings
from ..services.video import generate_thumbnail, get_video_info

router = APIRouter()

# 存储任务进度队列
_task_queues: dict[str, asyncio.Queue] = {}


def _serialize_datetime(dt: Optional[datetime]) -> Optional[str]:
    """序列化datetime对象，确保包含时区信息"""
    if dt is None:
        return None
    # 如果没有时区信息，假设是UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


# ==================== 视频库相关 API ====================


@router.get("/library")
async def get_video_library(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    获取视频库列表（所有视频，无论是否处理）
    """
    query = select(Task).order_by(Task.created_at.desc())

    # 计算总数
    count_result = db.execute(select(Task))
    total = len(count_result.scalars().all())

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = db.execute(query)
    tasks = result.scalars().all()

    videos = []
    for task in tasks:
        video_info = {
            "id": task.id,
            "filename": task.filename,
            "status": task.status,
            "progress": task.progress,
            "current_step": task.current_step,
            "created_at": _serialize_datetime(task.created_at),
            "file_size": task.file_size,
            "duration_seconds": task.duration_seconds,
            "thumbnail_url": f"/api/tasks/{task.id}/thumbnail",
            "video_url": f"/api/tasks/{task.id}/video",
        }

        # 尝试获取视频元信息
        if task.file_path and Path(task.file_path).exists():
            video_meta = get_video_info(Path(task.file_path))
            if video_meta:
                video_info["video_info"] = video_meta

        videos.append(video_info)

    return {
        "videos": videos,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size
        }
    }


@router.get("/")
async def list_tasks(
    status: Optional[str] = Query(None, description="按状态过滤任务"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    获取任务列表

    支持按状态过滤和分页查询
    """
    query = select(Task)

    if status:
        query = query.where(Task.status == status)

    query = query.order_by(Task.created_at.desc())

    # 计算总数
    count_result = db.execute(select(Task).where(Task.status == status) if status else select(Task))
    total = len(count_result.scalars().all()) if count_result else 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = db.execute(query)
    tasks = result.scalars().all()

    return {
        "tasks": [
            {
                "id": t.id,
                "filename": t.filename,
                "status": t.status,
                "progress": t.progress,
                "current_step": t.current_step,
                "error_message": t.error_message,
                "created_at": _serialize_datetime(t.created_at),
                "started_at": _serialize_datetime(t.started_at),
                "completed_at": _serialize_datetime(t.completed_at),
                "duration_seconds": t.duration_seconds
            }
            for t in tasks
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size
        }
    }


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """获取任务详情"""
    result = db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "id": task.id,
        "filename": task.filename,
        "file_path": task.file_path,
        "file_size": task.file_size,
        "status": task.status,
        "progress": task.progress,
        "current_step": task.current_step,
        "error_message": task.error_message,
        "created_at": _serialize_datetime(task.created_at),
        "started_at": _serialize_datetime(task.started_at),
        "completed_at": _serialize_datetime(task.completed_at),
        "duration_seconds": task.duration_seconds
    }


@router.post("/{task_id}/start")
async def start_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """开始处理任务"""
    result = db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "pending":
        raise HTTPException(status_code=400, detail=f"任务已开始或已完成（当前状态: {task.status}）")

    # 创建进度队列
    _task_queues[task_id] = asyncio.Queue()

    # 启动后台任务，创建独立的数据库会话
    async def run_task_with_db():
        from ..core.database import SessionLocal
        task_db = SessionLocal()
        try:
            await process_task(task_id, task_db, _task_queues[task_id])
        finally:
            task_db.close()

    asyncio.create_task(run_task_with_db())

    return {"message": "任务已开始", "task_id": task_id}


@router.get("/{task_id}/events")
async def task_events(task_id: str):
    """
    SSE 实时进度推送

    返回 Server-Sent Events 格式的实时进度更新
    """
    async def event_stream():
        # 获取或创建队列
        queue = _task_queues.get(task_id)
        if not queue:
            queue = asyncio.Queue()
            _task_queues[task_id] = queue

        try:
            while True:
                try:
                    # 等待事件，30秒超时发送心跳
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event.to_sse()

                    if event.event_type in ['complete', 'error']:
                        break
                except asyncio.TimeoutError:
                    # 发送心跳
                    yield "event: heartbeat\ndata: {}\n\n"

        finally:
            # 清理队列
            if task_id in _task_queues:
                del _task_queues[task_id]

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# /subtitles 路由已移至 translation.py，支持语言切换参数
# 保留此注释说明迁移历史


@router.get("/{task_id}/subtitles/download")
async def download_subtitles(
    task_id: str,
    db: Session = Depends(get_db)
):
    """下载 SRT 字幕文件"""
    result = db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "completed":
        raise HTTPException(status_code=400, detail="任务未完成")

    # 查找字幕文件
    srt_filename = f"{Path(task.filename).stem}_字幕.srt"
    srt_path = settings.OUTPUT_DIR / srt_filename

    if not srt_path.exists():
        raise HTTPException(status_code=404, detail="字幕文件不存在")

    return FileResponse(
        path=str(srt_path),
        filename=srt_filename,
        media_type='text/srt'
    )


@router.get("/{task_id}/video")
async def get_video(
    task_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """获取视频文件用于预览，支持范围请求"""
    result = db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    video_path = Path(task.file_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="视频文件不存在")

    # 获取文件扩展名对应的 MIME 类型
    import mimetypes
    media_type = mimetypes.guess_type(str(video_path))[0] or 'video/mp4'
    file_size = video_path.stat().st_size

    # 处理范围请求
    range_header = request.headers.get("range")

    if range_header:
        # 解析 Range 头
        try:
            start, end = range_header.replace("bytes=", "").split("-")
            start = int(start)
            end = int(end) if end else file_size - 1
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的 Range 头")

        # 验证范围
        if start >= file_size or end >= file_size or start > end:
            raise HTTPException(
                status_code=416,
                detail=f"请求范围无效 (文件大小: {file_size} 字节)",
                headers={"Content-Range": f"bytes */{file_size}"}
            )

        # 读取指定范围的数据
        chunk_size = end - start + 1
        with open(video_path, "rb") as f:
            f.seek(start)
            content = f.read(chunk_size)

        return Response(
            content=content,
            status_code=206,  # Partial Content
            media_type=media_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_size),
                "Cache-Control": "public, max-age=3600",
            }
        )

    # 返回完整文件
    return FileResponse(
        path=str(video_path),
        media_type=media_type,
        headers={
            'Accept-Ranges': 'bytes',
            'Cache-Control': 'public, max-age=3600',
        }
    )


@router.get("/{task_id}/segments")
async def get_segments(
    task_id: str,
    db: Session = Depends(get_db)
):
    """获取音频片段信息"""
    # 先检查任务是否存在
    task_result = db.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 查询片段
    result = db.execute(
        select(Segment)
        .where(Segment.task_id == task_id)
        .order_by(Segment.index)
    )
    segments = result.scalars().all()

    return {
        "segments": [
            {
                "index": s.index,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "status": s.status,
                "retry_count": s.retry_count,
                "error_message": s.error_message
            }
            for s in segments
        ],
        "total": len(segments)
    }


@router.get("/{task_id}/logs")
async def get_logs(
    task_id: str,
    level: Optional[str] = Query(None, description="日志级别过滤"),
    db: Session = Depends(get_db)
):
    """获取任务日志"""
    # 先检查任务是否存在
    task_result = db.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 查询日志
    query = select(Log).where(Log.task_id == task_id)
    if level:
        query = query.where(Log.level == level)

    query = query.order_by(Log.timestamp.desc())
    result = db.execute(query)
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "level": log.level,
                "message": log.message,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None
            }
            for log in logs
        ],
        "total": len(logs)
    }


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """删除任务"""
    result = db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 删除数据库记录（级联删除相关记录）
    db.execute(delete(Task).where(Task.id == task_id))
    db.commit()

    # 清理文件
    await cleanup_task_files(task_id)

    return {"message": "任务已删除", "task_id": task_id}


@router.get("/stats/overview")
async def get_statistics(db: Session = Depends(get_db)):
    """获取任务统计概览"""
    from ..services.task_processor import get_task_statistics

    stats = await get_task_statistics(db)
    return stats


@router.post("/{task_id}/retry")
async def retry_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """重试失败的任务"""
    result = db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "failed":
        raise HTTPException(status_code=400, detail=f"只能重试失败的任务（当前状态: {task.status}）")

    # 重置任务状态
    task.status = "pending"
    task.error_message = None
    task.progress = 0
    task.current_step = None
    task.started_at = None
    task.completed_at = None
    db.commit()

    # 创建进度队列
    _task_queues[task_id] = asyncio.Queue()

    # 启动后台任务，创建独立的数据库会话
    async def run_task_with_db():
        from ..core.database import SessionLocal
        task_db = SessionLocal()
        try:
            await process_task(task_id, task_db, _task_queues[task_id])
        finally:
            task_db.close()

    asyncio.create_task(run_task_with_db())

    return {"message": "任务已重新开始", "task_id": task_id}


@router.post("/{task_id}/reprocess")
async def reprocess_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """重新识别已完成或失败的任务（重新生成字幕）"""
    result = db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status == "processing" or task.status == "pending":
        raise HTTPException(status_code=400, detail=f"任务正在处理中，无法重新识别（当前状态: {task.status}）")

    # 保存原始文件名和路径
    original_filename = task.filename
    original_file_path = task.file_path
    original_file_size = task.file_size

    # 删除旧的字幕记录
    db.execute(delete(Subtitle).where(Subtitle.task_id == task_id))

    # 重置任务状态
    task.status = "pending"
    task.error_message = None
    task.progress = 0
    task.current_step = None
    task.started_at = None
    task.completed_at = None
    task.duration_seconds = None
    db.commit()

    # 删除旧的 SRT 文件
    if original_filename:
        srt_filename = f"{Path(original_filename).stem}_字幕.srt"
        srt_path = settings.OUTPUT_DIR / srt_filename
        if srt_path.exists():
            srt_path.unlink()

    # 创建进度队列
    _task_queues[task_id] = asyncio.Queue()

    # 启动后台任务，创建独立的数据库会话
    async def run_task_with_db():
        from ..core.database import SessionLocal
        task_db = SessionLocal()
        try:
            await process_task(task_id, task_db, _task_queues[task_id])
        finally:
            task_db.close()

    asyncio.create_task(run_task_with_db())

    return {"message": "开始重新识别", "task_id": task_id}


@router.get("/{task_id}/thumbnail")
async def get_video_thumbnail_api(
    task_id: str,
    db: Session = Depends(get_db)
):
    """获取视频缩略图（从视频帧或 cover 生成）"""
    result = db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    video_path = Path(task.file_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="视频文件不存在")

    # 生成缩略图路径
    thumbnail_dir = settings.OUTPUT_DIR / "thumbnails"
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    thumbnail_path = thumbnail_dir / f"{task_id}.jpg"

    # 如果缩略图不存在，生成它
    if not thumbnail_path.exists():
        generate_thumbnail(video_path, thumbnail_path)

    # 返回缩略图
    if thumbnail_path.exists():
        return FileResponse(
            path=str(thumbnail_path),
            media_type='image/jpeg',
            headers={
                'Cache-Control': 'public, max-age=86400',  # 缓存 1 天
            }
        )
    else:
        raise HTTPException(status_code=404, detail="缩略图生成失败")


@router.post("/{task_id}/generate-subtitles")
async def generate_subtitles(
    task_id: str,
    db: Session = Depends(get_db)
):
    """为已上传的视频生成字幕"""
    result = db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 检查视频文件是否存在
    video_path = Path(task.file_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="视频文件不存在")

    # 如果任务已完成，先删除旧的字幕
    if task.status == "completed":
        # 删除旧字幕记录
        db.execute(delete(Subtitle).where(Subtitle.task_id == task_id))
        db.commit()

        # 删除旧 SRT 文件
        srt_filename = f"{Path(task.filename).stem}_字幕.srt"
        srt_path = settings.OUTPUT_DIR / srt_filename
        if srt_path.exists():
            srt_path.unlink()

    # 重置任务状态为 pending
    task.status = "pending"
    task.error_message = None
    task.progress = 0
    task.current_step = None
    task.started_at = None
    task.completed_at = None
    task.duration_seconds = None
    db.commit()

    # 创建进度队列
    _task_queues[task_id] = asyncio.Queue()

    # 启动后台任务
    async def run_task_with_db():
        from ..core.database import SessionLocal
        task_db = SessionLocal()
        try:
            await process_task(task_id, task_db, _task_queues[task_id])
        finally:
            task_db.close()

    asyncio.create_task(run_task_with_db())

    return {"message": "开始生成字幕", "task_id": task_id}


@router.get("/{task_id}/keywords")
async def get_keywords(
    task_id: str,
    db: Session = Depends(get_db)
):
    """获取任务的关键字设置"""
    result = db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "keywords": task.keywords or ""
    }


@router.post("/{task_id}/keywords")
async def set_keywords(
    task_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """设置任务的关键字，用于 ASR 识别时的上下文"""
    result = db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 从 JSON body 中读取 keywords
    try:
        body = await request.json()
        keywords = body.get('keywords', '') if body else ''
    except Exception:
        # 兼容纯文本格式
        body = await request.body()
        keywords = body.decode('utf-8') if body else ''

    task.keywords = keywords
    db.commit()

    return {"message": "关键字已保存", "keywords": keywords}


@router.delete("/{task_id}/keywords")
async def delete_keywords(
    task_id: str,
    db: Session = Depends(get_db)
):
    """删除任务的关键字设置"""
    result = db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    task.keywords = None
    db.commit()

    return {"message": "关键字已删除"}
