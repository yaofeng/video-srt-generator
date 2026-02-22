# backend/app/services/translation.py
"""字幕翻译服务"""

import asyncio
import json
import logging
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

import openai

from ..models.subtitle import Subtitle
from ..models.translation_task import TranslationTask
from ..models.task import Task
from ..core.config import settings

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """翻译错误"""
    pass


def get_language_name(code: str) -> str:
    """获取语言名称"""
    lang_map = {
        'en': '英语',
        'ja': '日语',
        'ko': '韩语',
        'fr': '法语',
        'de': '德语',
        'es': '西班牙语',
        'zh_hant': '繁体中文',
    }
    return lang_map.get(code, code)


async def group_subtitles_by_interval(
    subtitles: List[Subtitle],
    interval_threshold: float = 3.0,
    max_sentences: int = 5
) -> List[List[Subtitle]]:
    """
    按时间间隔分组字幕

    Args:
        subtitles: 字幕列表
        interval_threshold: 时间间隔阈值（秒）
        max_sentences: 每组最大句数

    Returns:
        分组后的字幕列表
    """
    if not subtitles:
        return []

    groups = []
    current_group = [subtitles[0]]

    for i in range(1, len(subtitles)):
        interval = subtitles[i].start_time - subtitles[i-1].end_time

        # 时间间隔超过阈值或已达到最大句数，结束当前组
        if interval >= interval_threshold or len(current_group) >= max_sentences:
            groups.append(current_group)
            current_group = [subtitles[i]]
        else:
            # 继续累积到当前组
            current_group.append(subtitles[i])

    if current_group:
        groups.append(current_group)

    return groups


async def translate_with_llm(
    texts: List[str],
    target_language: str
) -> List[str]:
    """
    使用 LLM 翻译文本

    Args:
        texts: 待翻译文本列表
        target_language: 目标语言

    Returns:
        翻译结果列表

    Raises:
        TranslationError: 翻译失败时抛出
    """
    if not settings.LLM_API_BASE or not settings.LLM_API_KEY or not settings.LLM_MODEL:
        raise TranslationError("LLM 配置不完整，请检查配置")

    client = openai.AsyncOpenAI(
        base_url=settings.LLM_API_BASE,
        api_key=settings.LLM_API_KEY
    )

    # 构建提示词
    language_name = get_language_name(target_language)

    prompt = f"""请将以下字幕翻译成{language_name}，要求：
1. 保持原文的语气和风格
2. 准确传达原意，不要意译
3. 只返回翻译结果，每行对应一句原文

原文：
{chr(10).join(texts)}

翻译："""

    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个专业的字幕翻译助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            ),
            timeout=settings.TRANSLATION_TIMEOUT
        )

        result = response.choices[0].message.content.strip()
        translations = result.split('\n')

        # 确保翻译结果数量与原文一致
        if len(translations) != len(texts):
            logger.warning(f"翻译结果数量不匹配: 期望 {len(texts)}，实际 {len(translations)}")
            # 如果不匹配，尝试补齐或截断
            if len(translations) < len(texts):
                translations.extend([''] * (len(texts) - len(translations)))
            else:
                translations = translations[:len(texts)]

        return translations

    except asyncio.TimeoutError:
        raise TranslationError("翻译请求超时")
    except openai.APIError as e:
        raise TranslationError(f"LLM API 错误: {str(e)}")
    except Exception as e:
        raise TranslationError(f"翻译失败: {str(e)}")


async def process_translation_task(
    translation_task_id: str,
    parent_task_id: str,
    target_language: str,
    db: Session,
    progress_queue: Optional[asyncio.Queue] = None
) -> dict:
    """
    处理翻译任务

    Args:
        translation_task_id: 翻译任务 ID
        parent_task_id: 父任务 ID
        target_language: 目标语言
        db: 数据库会话
        progress_queue: 进度队列

    Returns:
        处理结果
    """
    translation_task = None
    try:
        # 获取翻译任务
        result = db.execute(
            select(TranslationTask).where(TranslationTask.id == translation_task_id)
        )
        translation_task = result.scalar_one_or_none()

        if not translation_task:
            if progress_queue:
                await progress_queue.put({'type': 'error', 'data': {'error': '翻译任务不存在'}})
            return {'status': 'error', 'message': '翻译任务不存在'}

        # 更新任务状态
        translation_task.status = 'processing'
        translation_task.started_at = datetime.now(timezone.utc)
        db.commit()

        await _log(db, translation_task_id, 'info', f'开始翻译任务，目标语言: {get_language_name(target_language)}', progress_queue)

        # 1. 获取原始字幕
        result = db.execute(
            select(Subtitle)
            .where(Subtitle.task_id == parent_task_id)
            .order_by(Subtitle.index)
        )
        subtitles = result.scalars().all()

        if not subtitles:
            raise TranslationError("没有找到可翻译的字幕")

        await _log(db, translation_task_id, 'info', f'获取到 {len(subtitles)} 条字幕', progress_queue)

        # 2. 分组
        groups = await group_subtitles_by_interval(
            list(subtitles),
            settings.TRANSLATION_GROUP_INTERVAL,
            settings.TRANSLATION_MAX_SENTENCES_PER_GROUP
        )

        await _log(db, translation_task_id, 'info',
                   f'字幕已分为 {len(groups)} 组 (间隔阈值: {settings.TRANSLATION_GROUP_INTERVAL}s, 最大句数: {settings.TRANSLATION_MAX_SENTENCES_PER_GROUP})',
                   progress_queue)

        # 3. 逐组翻译
        translated_count = 0
        failed_groups = []

        for i, group in enumerate(groups):
            await progress_queue.put({
                'type': 'progress',
                'data': {
                    'progress': int(100 * i / len(groups)),
                    'step': f'正在翻译第 {i+1}/{len(groups)} 组...'
                }
            })

            texts = [s.text for s in group]

            # 重试逻辑
            for attempt in range(settings.TRANSLATION_RETRY_ATTEMPTS):
                try:
                    await _log(db, translation_task_id, 'info',
                              f'  第 {i+1} 组: 进行第 {attempt+1} 次翻译尝试 ({len(texts)} 句)',
                              progress_queue)

                    translations = await translate_with_llm(texts, target_language)

                    # 保存翻译结果
                    field_name = f'translated_text_{target_language}'
                    for subtitle, translation in zip(group, translations):
                        setattr(subtitle, field_name, translation)

                        # 更新 translation_languages 字段
                        if not subtitle.translation_languages:
                            subtitle.translation_languages = json.dumps([])
                        languages = json.loads(subtitle.translation_languages)
                        if target_language not in languages:
                            languages.append(target_language)
                            subtitle.translation_languages = json.dumps(languages)

                    translated_count += len(group)
                    db.commit()

                    await _log(db, translation_task_id, 'info', f'  第 {i+1} 组翻译成功', progress_queue)
                    break

                except TranslationError as e:
                    if attempt == settings.TRANSLATION_RETRY_ATTEMPTS - 1:
                        failed_groups.append(i)
                        await _log(db, translation_task_id, 'error',
                                  f'  第 {i+1} 组翻译失败: {str(e)}', progress_queue)
                    else:
                        wait_time = 2 ** attempt
                        await _log(db, translation_task_id, 'warning',
                                  f'  第 {i+1} 组翻译失败，{wait_time}秒后重试',
                                  progress_queue)
                        await asyncio.sleep(wait_time)

        # 4. 检查失败率
        failure_rate = len(failed_groups) / len(groups) if groups else 0
        if failure_rate > 0.3:
            raise TranslationError(f"失败率过高 ({failure_rate*100:.1f}%)，翻译终止")

        # 5. 更新任务状态
        translation_task.status = 'completed'
        translation_task.completed_at = datetime.now(timezone.utc)
        translation_task.progress = 100
        translation_task.current_step = '完成'
        db.commit()

        await _log(db, translation_task_id, 'info',
                   f'翻译完成！成功翻译 {translated_count} 条字幕，失败 {len(failed_groups)} 组',
                   progress_queue)

        await progress_queue.put({
            'type': 'complete',
            'data': {
                'translation_task_id': translation_task_id,
                'translated_count': translated_count,
                'failed_groups': failed_groups
            }
        })

        return {
            'status': 'completed',
            'translated_count': translated_count,
            'failed_groups': failed_groups
        }

    except TranslationError as e:
        logger.error(f"翻译任务失败: {translation_task_id}, 错误: {e}")

        if translation_task:
            translation_task.status = 'failed'
            translation_task.error_message = str(e)
            translation_task.current_step = '翻译失败'
            db.commit()

        if progress_queue:
            await progress_queue.put({
                'type': 'error',
                'data': {'error': str(e)}
            })

        return {'status': 'error', 'message': str(e)}

    except Exception as e:
        logger.exception(f"翻译任务异常: {translation_task_id}")

        if translation_task:
            translation_task.status = 'failed'
            translation_task.error_message = str(e)
            translation_task.current_step = '翻译失败'
            db.commit()

        if progress_queue:
            await progress_queue.put({
                'type': 'error',
                'data': {'error': f'翻译异常: {str(e)}'}
            })

        return {'status': 'error', 'message': str(e)}


async def _log(db: Session, task_id: str, level: str, message: str, progress_queue: Optional[asyncio.Queue] = None):
    """记录日志"""
    try:
        # 发送到进度队列
        if progress_queue:
            await progress_queue.put({
                'type': 'log',
                'data': {'level': level, 'message': message}
            })

        logger.info(f"[{task_id}] [{level.upper()}] {message}")
    except Exception as e:
        logger.error(f"日志记录失败: {e}")


def get_translation_task(db: Session, parent_task_id: str, target_language: str) -> Optional[TranslationTask]:
    """获取翻译任务"""
    result = db.execute(
        select(TranslationTask).where(
            TranslationTask.parent_task_id == parent_task_id,
            TranslationTask.target_language == target_language
        ).order_by(TranslationTask.created_at.desc())
    )
    return result.scalar_one_or_none()


def get_subtitles_by_task(db: Session, task_id: str, lang: Optional[str] = None) -> List[dict]:
    """
    获取任务的字幕

    Args:
        db: 数据库会话
        task_id: 任务 ID
        lang: 语言代码（如 'en'），如果指定则返回翻译后的字幕

    Returns:
        字幕列表
    """
    result = db.execute(
        select(Subtitle)
        .where(Subtitle.task_id == task_id)
        .order_by(Subtitle.index)
    )
    subtitles = result.scalars().all()

    subtitles_data = []
    for sub in subtitles:
        text = sub.text
        if lang and lang != 'original':
            field_name = f'translated_text_{lang}'
            text = getattr(sub, field_name, None) or sub.text

        subtitles_data.append({
            'id': sub.id,
            'index': sub.index,
            'start_time': sub.start_time,
            'end_time': sub.end_time,
            'text': text,
            'translation_languages': json.loads(sub.translation_languages) if sub.translation_languages else []
        })

    return subtitles_data
