# backend/app/api/translation.py
"""翻译相关 API"""

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select
from pathlib import Path

from ..core.database import get_db
from ..core.config import settings
from ..models.task import Task
from ..models.translation_task import TranslationTask
from ..models.subtitle import Subtitle
from .tasks import ProgressEvent

logger = logging.getLogger(__name__)
from .tasks import ProgressEvent
from ..services.translation import (
    process_translation_task,
    get_translation_task,
    get_subtitles_by_task,
    get_language_name
)

router = APIRouter()


class CreateTranslationRequest(BaseModel):
    """创建翻译任务请求"""
    target_language: str = Field(..., description="目标语言代码（en, ja, ko 等）")
    force: bool = Field(False, description="是否强制重新翻译（覆盖现有翻译）")


class TranslationResponse(BaseModel):
    """翻译响应"""
    translation_task_id: str
    status: str
    message: str


@router.post("/tasks/{task_id}/translate", response_model=TranslationResponse)
async def create_translation_task(
    task_id: str,
    request: CreateTranslationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    创建翻译任务

    Args:
        task_id: 原始任务 ID
        request: 翻译请求
        background_tasks: 后台任务
        db: 数据库会话

    Returns:
        翻译任务信息
    """
    # 1. 验证原始任务存在且已完成
    result = db.execute(select(Task).where(Task.id == task_id))
    parent_task = result.scalar_one_or_none()

    if not parent_task:
        raise HTTPException(404, "任务不存在")

    if parent_task.status != 'completed':
        raise HTTPException(400, "任务未完成，无法翻译")

    # 2. 验证目标语言
    supported_codes = [lang['code'] for lang in settings.SUPPORTED_LANGUAGES]
    if request.target_language not in supported_codes:
        raise HTTPException(
            400,
            f"不支持的目标语言: {request.target_language}，支持的语言: {', '.join(supported_codes)}"
        )

    # 3. 检查是否已存在相同语言的翻译任务
    existing = get_translation_task(db, task_id, request.target_language)
    if existing and existing.status != 'failed':
        if not request.force:
            raise HTTPException(
                409,
                f"已存在 {get_language_name(request.target_language)} 语言的翻译任务（状态: {existing.status}）。如需重新翻译，请设置 force=true"
            )
        # 如果强制重新翻译，删除旧的翻译任务
        else:
            # 清除数据库中已翻译的内容
            field_name = f'translated_text_{request.target_language}'
            db.execute(
                select(Subtitle).where(Subtitle.task_id == task_id)
            )
            subtitles = db.execute(
                select(Subtitle).where(Subtitle.task_id == task_id)
            ).scalars().all()
            for sub in subtitles:
                setattr(sub, field_name, None)
                # 更新 translation_languages
                if sub.translation_languages:
                    try:
                        languages = json.loads(sub.translation_languages)
                        if request.target_language in languages:
                            languages.remove(request.target_language)
                            sub.translation_languages = json.dumps(languages)
                    except:
                        pass
            db.commit()
            # 删除旧的翻译任务
            db.delete(existing)
            db.commit()

    # 4. 创建翻译任务
    translation_task_id = str(uuid.uuid4())
    translation_task = TranslationTask(
        id=translation_task_id,
        parent_task_id=task_id,
        target_language=request.target_language,
        status='pending'
    )
    db.add(translation_task)
    db.commit()

    # 5. 启动后台翻译任务（使用独立会话）
    def run_translation_task():
        """在后台线程中运行翻译任务"""
        # 为后台任务创建独立的数据库会话
        from ..core.database import SessionLocal
        independent_db = SessionLocal()
        progress_queue = asyncio.Queue()

        async def run_async():
            try:
                # 启动翻译任务和进度处理器
                translation_task_handler = asyncio.create_task(
                    process_translation_task(
                        translation_task_id,
                        task_id,
                        request.target_language,
                        independent_db,
                        progress_queue
                    )
                )

                # 处理进度更新
                while True:
                    try:
                        # 设置超时以避免永久阻塞
                        event = await asyncio.wait_for(progress_queue.get(), timeout=2.0)

                        # 更新数据库中的进度
                        if event['type'] == 'progress':
                            trans_task = independent_db.execute(
                                select(TranslationTask).where(TranslationTask.id == translation_task_id)
                            ).scalar_one_or_none()

                            if trans_task:
                                trans_task.progress = event['data']['progress']
                                trans_task.current_step = event['data']['step']
                                independent_db.commit()

                        elif event['type'] == 'complete':
                            # 任务完成，退出循环
                            break

                        elif event['type'] == 'error':
                            # 任务出错，退出循环
                            break

                    except asyncio.TimeoutError:
                        # 检查翻译任务是否还在运行
                        if translation_task_handler.done():
                            break
                        continue
                    except Exception as e:
                        logger.error(f"处理进度更新失败: {e}")
                        continue

                # 等待翻译任务完成
                await translation_task_handler

            finally:
                independent_db.close()

        # 在新的事件循环中运行异步任务
        asyncio.run(run_async())

    background_tasks.add_task(run_translation_task)

    return TranslationResponse(
        translation_task_id=translation_task_id,
        status='pending',
        message=f"翻译任务已创建，目标语言: {get_language_name(request.target_language)}"
    )


@router.get("/tasks/{task_id}/translations")
async def get_translations(task_id: str, db: Session = Depends(get_db)):
    """
    获取任务的所有翻译

    Args:
        task_id: 原始任务 ID
        db: 数据库会话

    Returns:
        翻译列表
    """
    # 验证任务存在
    result = db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(404, "任务不存在")

    # 获取所有翻译任务
    result = db.execute(
        select(TranslationTask)
        .where(TranslationTask.parent_task_id == task_id)
        .order_by(TranslationTask.created_at)
    )
    translations = result.scalars().all()

    return {
        "task_id": task_id,
        "translations": [
            {
                "id": t.id,
                "language": t.target_language,
                "language_name": get_language_name(t.target_language),
                "status": t.status,
                "progress": t.progress,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "error_message": t.error_message
            }
            for t in translations
        ]
    }


@router.get("/tasks/{task_id}/subtitles")
async def get_task_subtitles(
    task_id: str,
    lang: Optional[str] = Query(None, description="语言代码（如 en、ja），不指定则返回原文"),
    db: Session = Depends(get_db)
):
    """
    获取任务的字幕

    Args:
        task_id: 任务 ID
        lang: 语言代码
        db: 数据库会话

    Returns:
        字幕列表
    """
    # 验证任务存在
    result = db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(404, "任务不存在")

    subtitles = get_subtitles_by_task(db, task_id, lang)

    return {
        "task_id": task_id,
        "language": lang or 'original',
        "subtitles": subtitles
    }


@router.get("/tasks/{task_id}/download-srt")
async def download_srt(
    task_id: str,
    lang: Optional[str] = Query(None, description="语言代码（如 en、ja），不指定则下载原文"),
    db: Session = Depends(get_db)
):
    """
    下载指定语言的 SRT 文件

    Args:
        task_id: 任务 ID
        lang: 语言代码
        db: 数据库会话

    Returns:
        SRT 文件
    """
    # 验证任务存在
    result = db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(404, "任务不存在")

    # 获取字幕
    subtitles = get_subtitles_by_task(db, task_id, lang)

    if not subtitles:
        raise HTTPException(404, "没有找到字幕")

    # 生成 SRT 内容
    srt_content = generate_srt_content(subtitles)

    # 确定文件名
    base_name = Path(task.filename).stem
    if lang:
        lang_name = get_language_name(lang)
        filename = f"{base_name}_字幕_{lang_name}.srt"
    else:
        filename = f"{base_name}_字幕.srt"

    # 保存到临时文件
    temp_file = settings.OUTPUT_DIR / f"{task_id}_{lang or 'original'}_temp.srt"
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(srt_content)

    return FileResponse(
        path=temp_file,
        filename=filename,
        media_type='text/plain'
    )


def generate_srt_content(subtitles: list) -> str:
    """生成 SRT 文件内容"""
    lines = []

    for i, sub in enumerate(subtitles, 1):
        start_time = format_srt_time(sub['start_time'])
        end_time = format_srt_time(sub['end_time'])

        lines.append(str(i))
        lines.append(f"{start_time} --> {end_time}")
        lines.append(sub['text'])
        lines.append("")  # 空行

    return '\n'.join(lines)


def format_srt_time(seconds: float) -> str:
    """格式化 SRT 时间戳"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"
