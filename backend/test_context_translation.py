#!/usr/bin/env python3
"""
测试带上下文的翻译功能
对比有无上下文的翻译效果
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, 'app')

from app.services.translation import translate_with_llm, get_language_name


async def test():
    """测试带上下文的翻译"""
    # 模拟字幕组
    groups = [
        ["大家好，欢迎来到我的频道。", "今天我们要讨论的话题非常重要。"],
        ["这个问题困扰了很多人。", "让我们一步步来分析。"],
        ["首先，我们需要了解背景。", "这涉及到历史因素。"],
        ["其次，我们要考虑现状。", "现在的环境已经不同了。"],
    ]

    target_language = "en"
    print(f"=== 翻译对比测试 ===")
    print(f"目标语言: {get_language_name(target_language)}")
    print()

    # 测试第 2 组（有前后上下文）
    test_group_idx = 2
    current_group = groups[test_group_idx]

    print(f"当前翻译组 ({test_group_idx + 1}):")
    for i, text in enumerate(current_group):
        print(f"  {i+1}. {text}")
    print()

    # 获取上下文
    context_before = []
    context_after = []

    if test_group_idx > 0:
        context_before.extend(groups[test_group_idx - 1])
    if test_group_idx > 1:
        context_before.extend(groups[test_group_idx - 2])

    if test_group_idx < len(groups) - 1:
        context_after.extend(groups[test_group_idx + 1])

    print("上下文信息:")
    if context_before:
        print(f"  前面的内容: {len(context_before)} 句")
        for i, text in enumerate(context_before):
            print(f"    {i+1}. {text}")
    if context_after:
        print(f"  后面的内容: {len(context_after)} 句")
        for i, text in enumerate(context_after):
            print(f"    {i+1}. {text}")
    print()

    # 1. 无上下文翻译
    print("【方式 1: 无上下文翻译】")
    print("-" * 80)
    try:
        translations_no_context = await translate_with_llm(
            current_group,
            target_language,
            context_before=None,
            context_after=None
        )
        for orig, trans in zip(current_group, translations_no_context):
            print(f"原文: {orig}")
            print(f"译文: {trans}")
            print()
    except Exception as e:
        print(f"失败: {e}")
        return

    # 2. 有上下文翻译
    print()
    print("【方式 2: 带上下文翻译】")
    print("-" * 80)
    try:
        translations_with_context = await translate_with_llm(
            current_group,
            target_language,
            context_before=context_before,
            context_after=context_after
        )
        for orig, trans in zip(current_group, translations_with_context):
            print(f"原文: {orig}")
            print(f"译文: {trans}")
            print()
    except Exception as e:
        print(f"失败: {e}")
        return

    # 对比结果
    print()
    print("=== 对比结果 ===")
    print("-" * 80)
    for i, (orig, trans1, trans2) in enumerate(zip(
        current_group,
        translations_no_context,
        translations_with_context
    )):
        print(f"{i+1}. 原文: {orig}")
        print(f"   无上下文: {trans1}")
        print(f"   有上下文: {trans2}")
        if trans1 != trans2:
            print(f"   ✓ 翻译有改进")
        else:
            print(f"   = 翻译相同")
        print()


if __name__ == "__main__":
    asyncio.run(test())
