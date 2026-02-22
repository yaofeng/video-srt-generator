# backend/app/services/srt.py
from pathlib import Path
from typing import List, Dict
import re
import logging

logger = logging.getLogger(__name__)


async def generate_srt(
    segments: List[Dict],
    output_path: Path,
    min_duration: float = 2.0,
    max_duration: float = 8.0,
    merge_threshold: float = 1.5
):
    """
    生成 SRT 字幕文件

    Args:
        segments: ASR 结果片段列表，每个元素包含 start, end, text
        output_path: 输出文件路径
        min_duration: 最短字幕时长（秒）
        max_duration: 最长字幕时长（秒）
        merge_threshold: 短字幕合并阈值（秒）
    """
    try:
        # segments 已经是句子级别的字幕（来自 asr.py 的 merge_char_segments_to_sentences_with_text）
        # 只合并短字幕，不进行任何切分（保持句子完整性）
        subtitles = merge_short_subtitles(segments, merge_threshold)

        # 生成 SRT 内容
        srt_content = _format_srt(subtitles)

        # 写入文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(srt_content, encoding='utf-8')

        logger.info(f"SRT 字幕文件已生成: {output_path}, 共 {len(subtitles)} 条字幕")

    except Exception as e:
        logger.error(f"SRT 生成失败: {e}")
        raise


def _convert_to_sentence_level(
    segments: List[Dict],
    min_duration: float,
    max_duration: float
) -> List[Dict]:
    """
    将 token 级别时间戳转换为句子级别

    策略：按标点符号切分，确保时长在合理范围内
    """
    subtitles = []

    for seg in segments:
        text = seg.get('text', '').strip()
        start = seg.get('start', 0.0)
        end = seg.get('end', start + 1.0)

        if not text:
            continue

        duration = end - start

        # 如果时长适中，直接使用
        if min_duration <= duration <= max_duration:
            subtitles.append({
                'start': start,
                'end': end,
                'text': text
            })
            continue

        # 处理长片段 - 按标点切分
        if duration > max_duration:
            sub_sentences = _split_text_by_punctuation(text)
            if len(sub_sentences) > 1:
                # 为每个子句子分配时间
                total_chars = sum(len(s) for s in sub_sentences)
                current_start = start

                for sub_text in sub_sentences:
                    if not sub_text.strip():
                        continue
                    sub_duration = (len(sub_text) / total_chars) * duration
                    subtitles.append({
                        'start': current_start,
                        'end': current_start + sub_duration,
                        'text': sub_text.strip()
                    })
                    current_start += sub_duration
            else:
                # 无法切分，保留原样
                subtitles.append({
                    'start': start,
                    'end': end,
                    'text': text
                })
        else:
            # 短片段也保留
            subtitles.append({
                'start': start,
                'end': end,
                'text': text
            })

    return subtitles


def _split_text_by_punctuation(text: str) -> List[str]:
    """
    按标点符号分割文本

    Args:
        text: 输入文本

    Returns:
        List[str]: 分割后的文本列表
    """
    # 匹配中文和英文标点
    pattern = r'([。！？.!?；;、,，])'
    parts = re.split(pattern, text)

    # 重组，保留标点
    result = []
    current = ""

    for i, part in enumerate(parts):
        if re.match(pattern, part):
            # 是标点，加到当前文本
            current += part
            # 标点出现时，结束当前句子
            if current:
                result.append(current)
                current = ""
        else:
            current += part

    # 处理剩余部分
    if current:
        result.append(current)

    return [r for r in result if r.strip()]


def _split_long_subtitles_by_punctuation(
    subtitles: List[Dict],
    max_duration: float
) -> List[Dict]:
    """
    智能分割过长的字幕，按标点符号分割而不是破坏句子完整性

    对于超过 max_duration 的字幕，按逗号、分号等停顿标点分割

    Args:
        subtitles: 字幕列表
        max_duration: 最大时长（秒）

    Returns:
        List[Dict]: 分割后的字幕列表
    """
    result = []

    for sub in subtitles:
        duration = sub['end'] - sub['start']

        if duration <= max_duration:
            result.append(sub)
            continue

        # 需要分割的长字幕
        text = sub['text']

        # 按停顿标点（逗号、分号等）分割，不包括句末标点（因为输入已经是按句末标点分割的）
        pause_punct_pattern = r'([,，;；、])'
        parts = re.split(pause_punct_pattern, text)

        # 重组，保留标点
        text_parts = []
        current = ""
        for part in parts:
            if re.match(pause_punct_pattern, part):
                current += part
                if current:
                    text_parts.append(current)
                    current = ""
            else:
                current += part

        if current:
            text_parts.append(current)

        # 如果无法分割，保留原样
        if len(text_parts) <= 1:
            result.append(sub)
            continue

        # 按字符数比例分配时间
        total_chars = sum(len(part) for part in text_parts)
        current_start = sub['start']

        for part in text_parts:
            if not part.strip():
                continue
            part_duration = (len(part) / total_chars) * duration
            result.append({
                'start': current_start,
                'end': current_start + part_duration,
                'text': part.strip()
            })
            current_start += part_duration

    return result


def merge_short_subtitles(
    subtitles: List[Dict],
    threshold: float
) -> List[Dict]:
    """
    合并短字幕

    策略：
    - 只合并真正的"碎片"字幕（非常短的字幕，如 < 1 秒）
    - 不合并已包含完整句子的字幕（以句末标点结尾）
    - 尊重原始的句子切分

    Args:
        subtitles: 字幕列表
        threshold: 合并阈值（秒），相邻短字幕间隔小于此值时合并

    Returns:
        List[Dict]: 合并后的字幕列表
    """
    if not subtitles:
        return []

    if len(subtitles) == 1:
        return subtitles

    # 句末标点
    sentence_end_punct = {'。', '！', '？', '.', '!', '?'}

    merged = []
    current = subtitles[0].copy()
    current_text = current['text'].strip()
    current_ends_with_punct = current_text and current_text[-1] in sentence_end_punct if current_text else False

    for next_sub in subtitles[1:]:
        gap = next_sub['start'] - current['end']
        current_duration = current['end'] - current['start']
        next_duration = next_sub['end'] - next_sub['start']
        next_text = next_sub['text'].strip()
        next_ends_with_punct = next_text and next_text[-1] in sentence_end_punct if next_text else False

        # 合并条件（必须同时满足）：
        # 1. 当前字幕非常短（< 1秒）或下个字幕非常短（< 1秒）
        # 2. 间隔很小（< threshold）
        # 3. 当前字幕不以句末标点结尾（不是完整句子）
        is_very_short = current_duration < 1.0 or next_duration < 1.0
        small_gap = gap < threshold
        not_complete_sentence = not current_ends_with_punct

        if is_very_short and small_gap and not_complete_sentence:
            # 合并
            current['end'] = next_sub['end']
            current['text'] = current['text'] + ' ' + next_sub['text']
            current_text = current['text'].strip()
            current_ends_with_punct = current_text and current_text[-1] in sentence_end_punct if current_text else False
        else:
            merged.append(current)
            current = next_sub.copy()
            current_text = current['text'].strip()
            current_ends_with_punct = current_text and current_text[-1] in sentence_end_punct if current_text else False

    # 添加最后一个
    merged.append(current)

    return merged


def _split_long_subtitles(
    subtitles: List[Dict],
    max_duration: float
) -> List[Dict]:
    """
    分割过长的字幕

    Args:
        subtitles: 字幕列表
        max_duration: 最大时长（秒）

    Returns:
        List[Dict]: 分割后的字幕列表
    """
    result = []

    for sub in subtitles:
        duration = sub['end'] - sub['start']

        if duration <= max_duration:
            result.append(sub)
            continue

        # 按字符数均分
        text = sub['text']
        chars = len(text)

        if chars == 0:
            result.append(sub)
            continue

        # 计算分割数量
        split_count = int(duration / max_duration) + 1
        chars_per_split = max(1, chars // split_count)

        start_time = sub['start']
        time_per_split = duration / split_count

        for i in range(split_count):
            start_idx = i * chars_per_split
            end_idx = min(start_idx + chars_per_split, chars)

            split_text = text[start_idx:end_idx].strip()

            if split_text:
                result.append({
                    'start': start_time + i * time_per_split,
                    'end': min(start_time + (i + 1) * time_per_split, sub['end']),
                    'text': split_text
                })

    return result


def _format_srt(subtitles: List[Dict]) -> str:
    """
    格式化为 SRT 文件内容

    Args:
        subtitles: 字幕列表

    Returns:
        str: SRT 格式的文本
    """
    lines = []

    for i, sub in enumerate(subtitles, 1):
        start_time = _format_timestamp(sub['start'])
        end_time = _format_timestamp(sub['end'])

        lines.append(str(i))
        lines.append(f"{start_time} --> {end_time}")
        lines.append(sub['text'])
        lines.append("")  # 空行分隔

    return '\n'.join(lines)


def _format_timestamp(seconds: float) -> str:
    """
    格式化时间戳为 SRT 格式: HH:MM:SS,mmm

    Args:
        seconds: 时间（秒）

    Returns:
        str: 格式化后的时间戳
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def parse_srt(srt_path: Path) -> List[Dict]:
    """
    解析 SRT 字幕文件

    Args:
        srt_path: SRT 文件路径

    Returns:
        List[Dict]: 字幕列表
    """
    content = srt_path.read_text(encoding='utf-8')
    subtitles = []

    # 分割字幕块
    blocks = re.split(r'\n\s*\n', content.strip())

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        try:
            # 解析序号
            index = int(lines[0].strip())

            # 解析时间戳
            time_match = re.match(
                r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})',
                lines[1]
            )
            if not time_match:
                continue

            start_time = _parse_timestamp(time_match.group(1))
            end_time = _parse_timestamp(time_match.group(2))

            # 解析文本
            text = '\n'.join(lines[2:]).strip()

            subtitles.append({
                'index': index,
                'start': start_time,
                'end': end_time,
                'text': text
            })
        except (ValueError, IndexError) as e:
            logger.warning(f"解析字幕块失败: {block}, 错误: {e}")
            continue

    return subtitles


def _parse_timestamp(timestamp: str) -> float:
    """
    解析 SRT 时间戳为秒数

    Args:
        timestamp: SRT 格式的时间戳 (HH:MM:SS,mmm)

    Returns:
        float: 时间（秒）
    """
    match = re.match(r'(\d+):(\d+):(\d+),(\d+)', timestamp)
    if not match:
        return 0.0

    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    millis = int(match.group(4))

    return hours * 3600 + minutes * 60 + seconds + millis / 1000


async def merge_srt_files(srt_paths: List[Path], output_path: Path, time_offset: float = 0.0):
    """
    合并多个 SRT 文件

    Args:
        srt_paths: SRT 文件路径列表
        output_path: 输出文件路径
        time_offset: 时间偏移（秒）
    """
    all_subtitles = []
    current_offset = time_offset

    for srt_path in srt_paths:
        subtitles = parse_srt(srt_path)

        # 调整时间偏移
        for sub in subtitles:
            sub['start'] += current_offset
            sub['end'] += current_offset
            all_subtitles.append(sub)

        # 更新下一个文件的偏移量
        if subtitles:
            last_end = max(s['end'] for s in subtitles)
            current_offset = last_end + 0.5  # 0.5秒间隔

    # 重新编号
    for i, sub in enumerate(all_subtitles, 1):
        sub['index'] = i

    # 生成 SRT
    srt_content = _format_srt(all_subtitles)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(srt_content, encoding='utf-8')

    logger.info(f"合并 SRT 文件完成: {output_path}, 共 {len(all_subtitles)} 条字幕")


def validate_srt(srt_path: Path) -> tuple[bool, List[str]]:
    """
    验证 SRT 文件

    Args:
        srt_path: SRT 文件路径

    Returns:
        tuple: (是否有效, 错误列表)
    """
    errors = []

    if not srt_path.exists():
        errors.append(f"文件不存在: {srt_path}")
        return False, errors

    try:
        subtitles = parse_srt(srt_path)

        if not subtitles:
            errors.append("没有找到有效的字幕")
            return False, errors

        # 检查时间戳
        for i, sub in enumerate(subtitles):
            if sub['start'] >= sub['end']:
                errors.append(f"字幕 {i+1} 的开始时间大于或等于结束时间")
            if sub['start'] < 0:
                errors.append(f"字幕 {i+1} 的开始时间为负数")

        # 检查序号连续性
        for i in range(len(subtitles) - 1):
            if subtitles[i+1]['index'] - subtitles[i]['index'] != 1:
                errors.append(f"字幕序号不连续: {subtitles[i]['index']} -> {subtitles[i+1]['index']}")

        return len(errors) == 0, errors

    except Exception as e:
        errors.append(f"解析失败: {str(e)}")
        return False, errors
