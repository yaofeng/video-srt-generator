#!/usr/bin/env python3
"""
使用直接 SQL 更新翻译结果
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, 'app')

from app.services.translation import translate_with_llm
from app.core.config import settings


async def test():
    """使用直接 SQL 更新翻译"""
    parent_task_id = "ca22a7c9-f9ac-4d3b-bd4a-4f1534cb9af9"
    target_language = "zh"

    print(f"=== 使用直接 SQL 更新翻译 ===")
    print(f"父任务 ID: {parent_task_id}")
    print(f"目标语言: {target_language}")
    print()

    # 使用 sqlite3 直接操作
    import sqlite3
    conn = sqlite3.connect('srt_generator.db')
    cursor = conn.cursor()

    try:
        # 查询所有字幕
        cursor.execute("""
            SELECT id, "index", text
            FROM subtitles
            WHERE task_id = ?
            ORDER BY "index"
        """, (parent_task_id,))

        subtitles = cursor.fetchall()
        print(f"查询到 {len(subtitles)} 条字幕")

        # 获取原始文本
        texts = [sub[2] for sub in subtitles]
        print(f"准备翻译 {len(texts)} 条字幕...")
        print()

        # 调用翻译
        print("开始翻译...")
        translations = await translate_with_llm(texts, target_language)
        print(f"✓ 翻译完成！")

        # 使用 SQL 更新
        print("保存到数据库...")
        for sub_id, translation in zip([sub[0] for sub in subtitles], translations):
            cursor.execute("""
                UPDATE subtitles
                SET translated_text_zh = ?
                WHERE id = ?
            """, (translation, sub_id))

        # 更新 translation_languages
        import json
        for sub_id in [sub[0] for sub in subtitles]:
            cursor.execute("""
                SELECT translation_languages FROM subtitles WHERE id = ?
            """, (sub_id,))
            row = cursor.fetchone()
            if row and row[0]:
                try:
                    languages = json.loads(row[0])
                except:
                    languages = []
            else:
                languages = []

            if target_language not in languages:
                languages.append(target_language)
                cursor.execute("""
                    UPDATE subtitles
                    SET translation_languages = ?
                    WHERE id = ?
                """, (json.dumps(languages), sub_id))

        conn.commit()
        print(f"✓ 已保存 {len(subtitles)} 条翻译")

        # 验证
        print()
        print("=== 验证翻译结果（前 10 条）===")
        cursor.execute("""
            SELECT "index", text, translated_text_zh
            FROM subtitles
            WHERE task_id = ?
            ORDER BY "index"
            LIMIT 10
        """, (parent_task_id,))

        for row in cursor.fetchall():
            idx, text, zh_text = row
            print(f"{idx}. 原文: {text[:40]}...")
            if zh_text:
                print(f"   译文: {zh_text[:40]}...")
            print()

        print("✓ 翻译测试完成！")

    except Exception as e:
        print(f"\n✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(test())
