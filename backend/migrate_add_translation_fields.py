#!/usr/bin/env python3
"""
数据库迁移脚本：为 subtitles 表添加多语言翻译字段

运行方式：
    cd backend
    python migrate_add_translation_fields.py
"""

import sqlite3
import sys
from pathlib import Path

# 数据库文件路径
DB_FILE = Path(__file__).parent / "srt_generator.db"


def migrate():
    """执行数据库迁移"""

    if not DB_FILE.exists():
        print(f"错误: 数据库文件不存在: {DB_FILE}")
        return False

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        # 检查是否已经存在 translated_text_en 列
        cursor.execute("PRAGMA table_info(subtitles)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'translated_text_en' in columns:
            print("翻译字段已存在，无需迁移")
            return True

        # 添加多语言翻译字段
        print("正在添加多语言翻译字段...")

        migrations = [
            "ALTER TABLE subtitles ADD COLUMN translated_text_en TEXT",
            "ALTER TABLE subtitles ADD COLUMN translated_text_ja TEXT",
            "ALTER TABLE subtitles ADD COLUMN translated_text_ko TEXT",
            "ALTER TABLE subtitles ADD COLUMN translated_text_fr TEXT",
            "ALTER TABLE subtitles ADD COLUMN translated_text_de TEXT",
            "ALTER TABLE subtitles ADD COLUMN translated_text_es TEXT",
            "ALTER TABLE subtitles ADD COLUMN translated_text_zh_hant TEXT",
            "ALTER TABLE subtitles ADD COLUMN translation_languages TEXT",
        ]

        for migration in migrations:
            print(f"  执行: {migration}")
            cursor.execute(migration)

        conn.commit()
        print("迁移完成!")

        return True

    except sqlite3.OperationalError as e:
        print(f"数据库错误: {e}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"未知错误: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
