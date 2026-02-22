#!/usr/bin/env python3
"""
完整的翻译测试
对已生成的任务进行重新翻译并保存到数据库
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, 'app')

from app.services.translation import process_translation_task
from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


async def test():
    """测试完整翻译流程"""
    # 使用最新任务 ID
    parent_task_id = "ca22a7c9-f9ac-4d3b-bd4a-4f1534cb9af9"
    target_language = "zh"

    print(f"=== 完整翻译测试 ===")
    print(f"父任务 ID: {parent_task_id}")
    print(f"目标语言: {target_language}")
    print()

    # 创建数据库连接
    engine = create_engine(f"sqlite:///{settings.BASE_DIR / 'backend' / 'srt_generator.db'}")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 创建一个新的翻译任务 ID
        import uuid
        translation_task_id = str(uuid.uuid4())

        print(f"创建翻译任务 ID: {translation_task_id}")
        print(f"开始翻译处理...")

        # 调用翻译任务处理
        result = await process_translation_task(
            translation_task_id=translation_task_id,
            parent_task_id=parent_task_id,
            target_language=target_language,
            db=db
        )

        print()
        print(f"=== 翻译完成 ===")
        print(f"状态: {result.get('status')}")
        print(f"总字幕数: {result.get('total_subtitles')}")
        print(f"成功翻译: {result.get('translated_count')}")
        print(f"失败数量: {result.get('failed_count')}")

        # 验证翻译结果是否保存到数据库
        print()
        print(f"=== 验证数据库保存 ===")
        from sqlalchemy import select
        from ..models.subtitle import Subtitle

        stmt = select(Subtitle).where(
            Subtitle.task_id == parent_task_id
        ).order_by(Subtitle.index)
        subtitles = db.execute(stmt).scalars().all()

        has_translation = 0
        print(f"前 10 条字幕的翻译结果:")
        print("-" * 80)
        for sub in subtitles[:10]:
            zh_text = getattr(sub, 'translated_text_zh', None)
            if zh_text:
                has_translation += 1
                print(f"{sub.index}. 原文: {sub.text[:40]}...")
                print(f"   译文: {zh_text[:40]}...")
                print()

        print()
        if has_translation > 0:
            print(f"✓ 翻译已保存到数据库 ({has_translation}/{len(subtitles)})")
        else:
            print(f"✗ 翻译未保存到数据库")

    except Exception as e:
        print(f"\n✗ 翻译失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test())
