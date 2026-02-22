#!/usr/bin/env python3
"""
简单的翻译测试并更新数据库
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, 'app')

from app.services.translation import translate_with_llm
from app.services.srt import parse_srt
from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select


async def test():
    """测试翻译并更新数据库"""
    # 使用最新任务 ID
    parent_task_id = "ca22a7c9-f9ac-4d3b-bd4a-4f1534cb9af9"
    target_language = "zh"

    print(f"=== 翻译并更新数据库测试 ===")
    print(f"父任务 ID: {parent_task_id}")
    print(f"目标语言: {target_language}")
    print()

    # 创建数据库连接
    db_path = Path("srt_generator.db")  # 直接使用当前目录的数据库
    engine = create_engine(f"sqlite:///{db_path}")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 导入模型
        from app.models.subtitle import Subtitle

        # 查询所有字幕
        stmt = select(Subtitle).where(
            Subtitle.task_id == parent_task_id
        ).order_by(Subtitle.index)
        subtitles = list(db.execute(stmt).scalars().all())

        print(f"查询到 {len(subtitles)} 条字幕")

        # 获取原始文本
        texts = [sub.text for sub in subtitles]
        print(f"准备翻译 {len(texts)} 条字幕...")
        print(f"调用 LLM API: {settings.LLM_MODEL}")
        print()

        # 调用翻译
        print("开始翻译（这可能需要几分钟）...")
        translations = await translate_with_llm(texts, target_language)

        print(f"✓ 翻译完成！获得 {len(translations)} 条翻译结果")
        print()

        # 更新数据库
        print("保存翻译结果到数据库...")
        for sub, translation in zip(subtitles, translations):
            setattr(sub, 'translated_text_zh', translation)

            # 更新 translation_languages 字段
            import json
            if not sub.translation_languages:
                sub.translation_languages = json.dumps([])
            languages = json.loads(sub.translation_languages)
            if target_language not in languages:
                languages.append(target_language)
                sub.translation_languages = json.dumps(languages)

        db.commit()
        print(f"✓ 已保存 {len(subtitles)} 条翻译到数据库")
        print()

        # 验证
        print("=== 验证翻译结果（前 10 条）===")
        print("-" * 80)
        for sub in subtitles[:10]:
            zh_text = getattr(sub, 'translated_text_zh', None)
            print(f"{sub.index}. 原文: {sub.text[:50]}...")
            print(f"   译文: {zh_text[:50] if zh_text else 'N/A'}...")
            print()

        print("✓ 翻译测试完成！")

    except Exception as e:
        print(f"\n✗ 翻译失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test())
