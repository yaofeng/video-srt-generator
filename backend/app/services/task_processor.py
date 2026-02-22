# backend/app/services/task_processor.py
import asyncio
from pathlib import Path
from typing import AsyncIterator, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
import logging

from ..models.task import Task
from ..models.segment import Segment
from ..models.subtitle import Subtitle
from ..models.log import Log
from .audio import extract_audio, get_video_duration
from .vad import split_audio_by_vad
from .asr import transcribe_audio
from .srt import generate_srt
from ..core.config import settings

logger = logging.getLogger(__name__)


class ProgressEvent:
    """进度事件"""
    def __init__(self, event_type: str, data: dict):
        self.event_type = event_type
        self.data = data

    def to_sse(self) -> str:
        """转换为 SSE 格式"""
        import json
        return f"event: {self.event_type}\ndata: {json.dumps(self.data, ensure_ascii=False)}\n\n"


async def process_task(
    task_id: str,
    db: Session,
    progress_queue: asyncio.Queue
) -> dict:
    """
    处理字幕生成任务

    Args:
        task_id: 任务 ID
        db: 数据库会话（同步）
        progress_queue: 进度队列

    Returns:
        dict: 处理结果
    """
    task = None
    try:
        # 获取任务
        result = db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            await progress_queue.put(ProgressEvent('error', {'error': '任务不存在'}))
            return {'status': 'error', 'message': '任务不存在'}

        # 更新任务状态
        task.status = 'processing'
        task.started_at = datetime.now(timezone.utc)
        db.commit()

        await progress_queue.put(ProgressEvent('progress', {
            'progress': 0,
            'step': '开始处理...'
        }))

        # 1. 提取音频
        await _log(db, task_id, 'info', '开始提取音频...')
        audio_path = settings.OUTPUT_DIR / f"{task_id}_audio.wav"
        await extract_audio(Path(task.file_path), audio_path)
        await _log(db, task_id, 'info', '音频提取完成')

        # 2. 获取视频时长
        duration = await get_video_duration(Path(task.file_path))
        task.duration_seconds = int(duration)
        db.commit()

        # 3. VAD 切分
        await _log(db, task_id, 'info', '开始语音活动检测...')
        await progress_queue.put(ProgressEvent('progress', {
            'progress': 10,
            'step': '正在进行语音活动检测...'
        }))

        segments_dir = settings.OUTPUT_DIR / f"{task_id}_segments"
        segments = await split_audio_by_vad(
            audio_path,
            segments_dir,
            min_duration=settings.SEGMENT_MIN_DURATION,
            max_duration=settings.SEGMENT_MAX_DURATION
        )

        await _log(db, task_id, 'info', f'检测到 {len(segments)} 个音频片段')

        # 4. 保存片段信息到数据库
        for seg in segments:
            segment = Segment(
                task_id=task_id,
                index=seg['index'],
                start_time=seg['start_time'],
                end_time=seg['end_time'],
                audio_path=seg['audio_path']
            )
            db.add(segment)
        db.commit()

        # 5. ASR 识别
        await _log(db, task_id, 'info', '开始语音识别...')
        all_segments = []
        failed_segments = []

        for i, seg_info in enumerate(segments):
            await progress_queue.put(ProgressEvent('progress', {
                'progress': 20 + int(60 * i / len(segments)),
                'step': f'正在识别 ({i+1}/{len(segments)})...'
            }))

            # 更新片段状态
            result = db.execute(
                select(Segment).where(
                    Segment.task_id == task_id,
                    Segment.index == seg_info['index']
                )
            )
            segment = result.scalar_one_or_none()

            if segment:
                segment.status = 'processing'
                db.commit()

            # 重试逻辑
            for attempt in range(settings.MAX_RETRY_ATTEMPTS):
                try:
                    asr_result = await transcribe_audio(Path(seg_info['audio_path']))
                    all_segments.extend(asr_result.get('segments', []))

                    if segment:
                        segment.status = 'completed'
                        db.commit()

                    await _log(db, task_id, 'info', f'片段 {i+1} 识别完成')
                    break

                except Exception as e:
                    logger.error(f"片段 {i+1} 识别失败 (尝试 {attempt+1}/{settings.MAX_RETRY_ATTEMPTS}): {e}")

                    if attempt == settings.MAX_RETRY_ATTEMPTS - 1:
                        await _log(db, task_id, 'error', f'片段 {i+1} 识别失败: {str(e)}')
                        if segment:
                            segment.status = 'failed'
                            segment.retry_count = settings.MAX_RETRY_ATTEMPTS
                            segment.error_message = str(e)
                            db.commit()
                        failed_segments.append(i + 1)
                    else:
                        await _log(db, task_id, 'warning', f'片段 {i+1} 重试 ({attempt+1}/{settings.MAX_RETRY_ATTEMPTS})')
                        if segment:
                            segment.retry_count = attempt + 1
                            db.commit()
                        await asyncio.sleep(settings.RETRY_BASE_DELAY * (2 ** attempt))

        if failed_segments:
            await _log(db, task_id, 'warning', f'共有 {len(failed_segments)} 个片段识别失败: {failed_segments}')

        # 6. 生成 SRT
        await progress_queue.put(ProgressEvent('progress', {
            'progress': 85,
            'step': '正在生成字幕...'
        }))

        await _log(db, task_id, 'info', '开始生成 SRT 文件...')
        srt_filename = f"{Path(task.filename).stem}_字幕.srt"
        srt_path = settings.OUTPUT_DIR / srt_filename

        await generate_srt(
            all_segments,
            srt_path,
            min_duration=settings.SUBTITLE_MIN_DURATION,
            max_duration=settings.SUBTITLE_MAX_DURATION,
            merge_threshold=settings.SUBTITLE_MERGE_THRESHOLD
        )

        # 7. 保存字幕到数据库
        await _save_subtitles(db, task_id, all_segments)

        # 8. 更新任务状态
        task.status = 'completed'
        task.completed_at = datetime.now(timezone.utc)
        task.progress = 100
        task.current_step = '完成'
        db.commit()

        await progress_queue.put(ProgressEvent('complete', {
            'task_id': task_id,
            'srt_path': srt_filename,
            'subtitle_count': len(all_segments)
        }))

        await _log(db, task_id, 'info', '任务完成')

        return {
            'status': 'completed',
            'srt_path': str(srt_path),
            'subtitle_count': len(all_segments)
        }

    except Exception as e:
        logger.exception(f"任务处理失败: {task_id}")

        # 更新任务状态
        if task:
            task.status = 'failed'
            task.error_message = str(e)
            task.current_step = '处理失败'
            db.commit()

        await progress_queue.put(ProgressEvent('error', {
            'error': f'处理失败: {str(e)}'
        }))

        await _log(db, task_id, 'error', f'任务失败: {str(e)}')

        return {'status': 'error', 'message': str(e)}


def _log(db: Session, task_id: str, level: str, message: str):
    """记录日志（同步）"""
    try:
        log = Log(task_id=task_id, level=level, message=message)
        db.add(log)
        db.commit()
    except Exception as e:
        logger.error(f"日志记录失败: {e}")


async def _save_subtitles(db: Session, task_id: str, segments: list):
    """保存字幕到数据库"""
    try:
        for i, seg in enumerate(segments):
            subtitle = Subtitle(
                task_id=task_id,
                index=i + 1,
                start_time=seg.get('start', 0.0),
                end_time=seg.get('end', 0.0),
                text=seg.get('text', '')
            )
            db.add(subtitle)
        db.commit()
    except Exception as e:
        logger.error(f"保存字幕失败: {e}")
        raise


async def cleanup_task_files(task_id: str):
    """
    清理任务相关文件

    Args:
        task_id: 任务 ID
    """
    try:
        import os

        # 清理音频文件
        audio_path = settings.OUTPUT_DIR / f"{task_id}_audio.wav"
        if audio_path.exists():
            os.remove(audio_path)

        # 清理片段目录
        segments_dir = settings.OUTPUT_DIR / f"{task_id}_segments"
        if segments_dir.exists():
            import shutil
            shutil.rmtree(segments_dir)

        logger.info(f"任务文件清理完成: {task_id}")

    except Exception as e:
        logger.error(f"任务文件清理失败: {e}")


async def get_task_statistics(db: Session) -> dict:
    """
    获取任务统计信息

    Args:
        db: 数据库会话

    Returns:
        dict: 统计信息
    """
    try:
        # 总任务数
        total_result = db.execute(select(Task).count())
        total = total_result.scalar() or 0

        # 各状态任务数
        pending_result = db.execute(select(Task).where(Task.status == 'pending').count())
        pending = pending_result.scalar() or 0

        processing_result = db.execute(select(Task).where(Task.status == 'processing').count())
        processing = processing_result.scalar() or 0

        completed_result = db.execute(select(Task).where(Task.status == 'completed').count())
        completed = completed_result.scalar() or 0

        failed_result = db.execute(select(Task).where(Task.status == 'failed').count())
        failed = failed_result.scalar() or 0

        return {
            'total': total,
            'pending': pending,
            'processing': processing,
            'completed': completed,
            'failed': failed,
            'success_rate': round(completed / total * 100, 2) if total > 0 else 0
        }

    except Exception as e:
        logger.error(f"获取任务统计失败: {e}")
        return {
            'total': 0,
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0,
            'success_rate': 0
        }
