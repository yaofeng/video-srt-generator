#!/usr/bin/env python3
"""
测试翻译功能
对已生成的 SRT 字幕文件进行翻译验证
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, 'app')

from app.services.translation import translate_with_llm, get_language_name
from app.services.srt import parse_srt
from app.core.config import settings


async def test():
    """测试翻译功能"""
    # 使用最新生成的字幕文件
    srt_path = settings.OUTPUT_DIR / "催眠術体験！〖 いっしゅぷらざ 〗 - ISSUE (720p, h264)_字幕.srt"

    print(f"=== 翻译测试 ===")
    print(f"字幕文件: {srt_path}")
    print(f"文件存在: {srt_path.exists()}")

    if not srt_path.exists():
        print(f"\n错误: 字幕文件不存在")
        return

    # 解析字幕
    print(f"\n解析字幕文件...")
    try:
        subtitles = parse_srt(srt_path)  # 直接传递 Path 对象
        print(f"✓ 成功解析 {len(subtitles)} 条字幕")
    except Exception as e:
        print(f"✗ 解析失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 显示前 5 条原始字幕
    print(f"\n原始字幕（前 5 条）:")
    print("-" * 80)
    for i, sub in enumerate(subtitles[:5]):
        print(f"{i+1}. [{sub['start']} --> {sub['end']}]")
        print(f"   {sub['text']}")
        print()

    # 翻译配置
    target_language = "zh"
    print(f"开始翻译...")
    print(f"目标语言: {target_language} ({get_language_name(target_language)})")
    print(f"翻译模型: {settings.LLM_MODEL}")
    print(f"API 地址: {settings.LLM_API_BASE}")
    print()

    try:
        # 测试翻译前 10 条字幕
        test_count = 10
        test_subtitles = subtitles[:test_count]
        texts = [sub['text'] for sub in test_subtitles]

        print(f"测试翻译前 {test_count} 条字幕...")
        print(f"原文:")
        print("-" * 80)
        for i, text in enumerate(texts):
            print(f"{i+1}. {text}")

        print()
        print(f"调用 LLM 翻译...")

        # 调用翻译函数
        translations = await translate_with_llm(
            texts=texts,
            target_language=target_language
        )

        print(f"\n✓ 翻译完成！")

        # 显示翻译结果
        print(f"\n翻译结果:")
        print("-" * 80)
        for i, (orig, trans) in enumerate(zip(texts, translations)):
            print(f"{i+1}. 原文: {orig}")
            print(f"    译文: {trans}")
            print()

        # 检查翻译质量
        if len(translations) == len(texts):
            print(f"✓ 翻译数量匹配: {len(translations)}/{len(texts)}")
        else:
            print(f"⚠️  翻译数量不匹配: {len(translations)}/{len(texts)}")

        # 保存翻译结果
        output_srt_path = srt_path.parent / f"{srt_path.stem}_翻译测试.srt"
        print(f"\n保存翻译结果到: {output_srt_path}")

        # 生成 SRT 格式
        srt_content = ""
        for i, (orig_sub, trans_text) in enumerate(zip(test_subtitles, translations), 1):
            srt_content += f"{i}\n"
            srt_content += f"{orig_sub['start']} --> {orig_sub['end']}\n"
            srt_content += f"{trans_text}\n\n"

        with open(output_srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)

        print(f"✓ 翻译结果已保存")

        print(f"\n=== 翻译测试总结 ===")
        print(f"测试字幕数: {test_count}")
        print(f"目标语言: {get_language_name(target_language)}")
        print(f"翻译状态: 成功 ✓")
        print(f"输出文件: {output_srt_path}")

    except Exception as e:
        print(f"\n✗ 翻译失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test())
