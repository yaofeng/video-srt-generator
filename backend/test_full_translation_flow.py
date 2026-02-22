#!/usr/bin/env python3
"""测试完整翻译流程"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, 'app')

from app.core.database import SessionLocal
from app.models.subtitle import Subtitle
from app.models.translation_task import TranslationTask
from app.services.translation import process_translation_task, group_subtitles_by_interval


async def test():
    """测试翻译流程"""
    task_id = 'cd0917d8-24a7-4c0f-ba7b-0dc9d9c6ec5f'
    target_language = 'zh'

    print(f'=== 测试完整翻译流程 ===')
    print(f'任务ID: {task_id}')
    print(f'目标语言: {target_language}')
    print()

    db = SessionLocal()

    try:
        # 1. 检查字幕
        subtitles = db.query(Subtitle).filter(
            Subtitle.task_id == task_id
        ).order_by(Subtitle.index).all()

        print(f'1. 字幕数量: {len(subtitles)}')

        # 2. 分组
        groups = await group_subtitles_by_interval(
            list(subtitles),
            interval_threshold=3.0,
            max_sentences=5
        )

        print(f'2. 分组数量: {len(groups)}')

        # 3. 创建翻译任务
        import uuid
        from datetime import datetime, timezone

        translation_task_id = str(uuid.uuid4())
        translation_task = TranslationTask(
            id=translation_task_id,
            parent_task_id=task_id,
            target_language=target_language,
            status='pending'
        )
        db.add(translation_task)
        db.commit()

        print(f'3. 创建翻译任务: {translation_task_id[:8]}...')

        # 4. 处理翻译任务
        print('4. 开始翻译...')

        class ProgressQueue:
            def __init__(self):
                self.events = []

            async def put(self, event):
                self.events.append(event)
                if event['type'] == 'progress':
                    print(f"   进度: {event['data']['progress']}% - {event['data']['step']}")
                elif event['type'] == 'log':
                    print(f"   日志: {event['data']['level']} - {event['data']['message']}")

        progress_queue = ProgressQueue()

        result = await process_translation_task(
            translation_task_id,
            task_id,
            target_language,
            db,
            progress_queue
        )

        print()
        print(f'5. 翻译结果: {result}')

        # 6. 检查翻译结果
        translated_count = db.query(Subtitle).filter(
            Subtitle.task_id == task_id,
            Subtitle.translated_text_zh.isnot(None)
        ).count()

        print(f'6. 已翻译字幕数量: {translated_count}')

        if translated_count > 0:
            print()
            print('=== 翻译示例（前3条）===')
            subs = db.query(Subtitle).filter(
                Subtitle.task_id == task_id,
                Subtitle.translated_text_zh.isnot(None)
            ).limit(3).all()
            for sub in subs:
                print(f'[{sub.index}] {sub.text[:40]}...')
                print(f'     -> {sub.translated_text_zh[:40]}...')
                print()

    except Exception as e:
        print(f'错误: {e}')
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == '__main__':
    asyncio.run(test())
