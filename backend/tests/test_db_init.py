#!/usr/bin/env python3
"""
测试数据库初始化脚本

验证 SQLAlchemy 模型能正确创建数据库表
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import init_db, close_db, engine
from app.models import Task, Subtitle, Segment, Log
from sqlalchemy import text


def test_database_init():
    """测试数据库初始化"""
    print("=" * 60)
    print("开始测试数据库初始化...")
    print("=" * 60)

    try:
        # 初始化数据库
        print("\n1. 初始化数据库...")
        init_db()
        print("   ✓ 数据库初始化成功")

        # 验证表是否创建
        print("\n2. 验证数据库表...")
        with engine.begin() as conn:
            # 获取所有表名
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            )
            tables = [row[0] for row in result.fetchall()]

            expected_tables = ["tasks", "subtitles", "segments", "logs"]
            print(f"   创建的表: {', '.join(tables)}")

            for table in expected_tables:
                if table in tables:
                    print(f"   ✓ 表 '{table}' 已创建")
                else:
                    print(f"   ✗ 表 '{table}' 未找到")
                    return False

        # 验证模型导入
        print("\n3. 验证模型导入...")
        print(f"   ✓ Task 模型: {Task.__tablename__}")
        print(f"   ✓ Subtitle 模型: {Subtitle.__tablename__}")
        print(f"   ✓ Segment 模型: {Segment.__tablename__}")
        print(f"   ✓ Log 模型: {Log.__tablename__}")

        print("\n" + "=" * 60)
        print("所有测试通过！数据库模型配置正确。")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 关闭数据库连接
        print("\n4. 关闭数据库连接...")
        close_db()
        print("   ✓ 数据库连接已关闭")


def test_create_sample_data():
    """测试创建示例数据"""
    print("\n" + "=" * 60)
    print("测试创建示例数据...")
    print("=" * 60)

    try:
        from app.core.database import SessionLocal

        db = SessionLocal()

        # 创建任务
        print("\n1. 创建示例任务...")
        task = Task(
            filename="test_video.mp4",
            file_path="/uploads/test_video.mp4",
            file_size=1024000,
            status="pending",
            progress=0
        )
        db.add(task)
        db.flush()

        print(f"   ✓ 任务创建成功 (ID: {task.id})")

        # 创建字幕
        print("\n2. 创建示例字幕...")
        subtitle1 = Subtitle(
            task_id=task.id,
            index=1,
            start_time=0.0,
            end_time=2.5,
            text="这是第一句字幕"
        )
        subtitle2 = Subtitle(
            task_id=task.id,
            index=2,
            start_time=2.5,
            end_time=5.0,
            text="这是第二句字幕"
        )
        db.add_all([subtitle1, subtitle2])
        db.flush()

        print(f"   ✓ 字幕创建成功 (2条字幕)")

        # 创建片段
        print("\n3. 创建示例片段...")
        segment = Segment(
            task_id=task.id,
            index=1,
            start_time=0.0,
            end_time=30.0,
            audio_path="/uploads/segment_1.wav",
            status="pending"
        )
        db.add(segment)
        db.flush()

        print(f"   ✓ 片段创建成功")

        # 创建日志
        print("\n4. 创建示例日志...")
        log1 = Log(
            task_id=task.id,
            level="INFO",
            message="任务创建成功"
        )
        log2 = Log(
            task_id=task.id,
            level="INFO",
            message="开始处理视频"
        )
        db.add_all([log1, log2])

        # 提交所有更改
        db.commit()
        print(f"   ✓ 日志创建成功 (2条日志)")

        # 验证关系
        print("\n5. 验证关系...")
        print(f"   ✓ Task.subtitles: {len(task.subtitles)} 条字幕")
        print(f"   ✓ Task.segments: {len(task.segments)} 个片段")
        print(f"   ✓ Task.logs: {len(task.logs)} 条日志")

        db.close()

        print("\n" + "=" * 60)
        print("示例数据创建成功！")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    # 测试数据库初始化
    init_success = test_database_init()
    if not init_success:
        sys.exit(1)

    # 测试创建示例数据
    data_success = test_create_sample_data()
    if not data_success:
        sys.exit(1)

    print("\n所有测试完成！")


if __name__ == "__main__":
    main()
