#!/usr/bin/env python3
"""
数据库迁移脚本：创建 translation_tasks 表

运行方式：
    cd backend
    python migrate_create_translation_tasks.py
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
        # 检查表是否已存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='translation_tasks'")
        if cursor.fetchone():
            print("translation_tasks 表已存在，无需迁移")
            return True

        # 创建 translation_tasks 表
        print("正在创建 translation_tasks 表...")

        cursor.execute("""
            CREATE TABLE translation_tasks (
                id VARCHAR(36) PRIMARY KEY,
                parent_task_id VARCHAR(36) NOT NULL,
                target_language VARCHAR(10) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                current_step VARCHAR(100),
                started_at TIMESTAMP WITH TIME ZONE,
                completed_at TIMESTAMP WITH TIME ZONE,
                error_message TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX ix_translation_tasks_parent ON translation_tasks(parent_task_id)")
        cursor.execute("CREATE INDEX ix_translation_tasks_status ON translation_tasks(status)")

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
