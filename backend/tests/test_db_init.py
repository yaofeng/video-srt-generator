#!/usr/bin/env python3
"""
测试数据库初始化脚本

验证 SQLAlchemy 模型能正确创建数据库表
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import init_db, close_db, engine
from app.models import Task, Subtitle, Segment, Log, TaskStatus, LogLevel
from sqlalchemy import text


async def test_database_init():
    """测试数据库初始化"""
    print("=" * 60)
    print("开始测试数据库初始化...")
    print("=" * 60)

    try:
        # 初始化数据库
        print("\n1. 初始化数据库...")
        await init_db()
        print("   ✓ 数据库初始化成功")

        # 验证表是否创建
        print("\n2. 验证数据库表...")
        async with engine.begin() as conn:
            # 获取所有表名
            result = await conn.execute(
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

        # 验证枚举
        print("\n4. 验证枚举类型...")
        print(f"   ✓ TaskStatus: {', '.join([s.value for s in TaskStatus])}")
        print(f"   ✓ LogLevel: {', '.join([l.value for l in LogLevel])}")

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
        print("\n5. 关闭数据库连接...")
        await close_db()
        print("   ✓ 数据库连接已关闭")


async def test_create_sample_data():
    """测试创建示例数据"""
    print("\n" + "=" * 60)
    print("测试创建示例数据...")
    print("=" * 60)

    try:
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            # 创建任务
            print("\n1. 创建示例任务...")
            task = Task(
                video_url="https://example.com/video.mp4",
                video_title="测试视频",
                status=TaskStatus.PENDING,
                progress=0
            )
            session.add(task)
            await session.flush()  # 获取 task.id

            print(f"   ✓ 任务创建成功 (ID: {task.id})")

            # 创建字幕
            print("\n2. 创建示例字幕...")
            subtitle = Subtitle(
                task_id=task.id,
                language="zh",
                total_segments=2,
                total_duration=5.0
            )
            session.add(subtitle)
            await session.flush()

            print(f"   ✓ 字幕创建成功 (ID: {subtitle.id})")

            # 创建字幕片段
            print("\n3. 创建示例字幕片段...")
            segment1 = Segment(
                subtitle_id=subtitle.id,
                segment_index=1,
                start_time=0,
                end_time=2500,
                duration=2.5,
                text="这是第一句字幕",
                confidence=0.95
            )
            segment2 = Segment(
                subtitle_id=subtitle.id,
                segment_index=2,
                start_time=2500,
                end_time=5000,
                duration=2.5,
                text="这是第二句字幕",
                confidence=0.92
            )
            session.add_all([segment1, segment2])
            await session.flush()

            print(f"   ✓ 字幕片段创建成功 (2个片段)")

            # 创建日志
            print("\n4. 创建示例日志...")
            log1 = Log(
                task_id=task.id,
                level=LogLevel.INFO,
                message="任务创建成功",
                step="init"
            )
            log2 = Log(
                task_id=task.id,
                level=LogLevel.INFO,
                message="字幕生成成功",
                step="subtitle"
            )
            session.add_all([log1, log2])

            # 提交所有更改
            await session.commit()
            print(f"   ✓ 日志创建成功 (2条日志)")

            print("\n" + "=" * 60)
            print("示例数据创建成功！")
            print("=" * 60)
            return True

    except Exception as e:
        print(f"\n✗ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    # 测试数据库初始化
    init_success = await test_database_init()
    if not init_success:
        sys.exit(1)

    # 测试创建示例数据
    data_success = await test_create_sample_data()
    if not data_success:
        sys.exit(1)

    print("\n所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
