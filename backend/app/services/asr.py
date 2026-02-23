# backend/app/services/asr.py
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

try:
    import torch
except ImportError:
    logger.error("torch 未安装")
    torch = None

try:
    import numpy as np
except ImportError:
    logger.error("numpy 未安装")
    np = None


class ASRModel:
    """ASR 模型单例（Qwen3-ASR + ForcedAligner）"""
    _model = None
    _model_path = None

    @classmethod
    def get_model(cls, model_path: Optional[Path] = None, aligner_path: Optional[Path] = None):
        """获取 Qwen3-ASR 模型实例"""
        if cls._model is None:
            from qwen_asr import Qwen3ASRModel

            # 使用配置的路径或默认路径
            asr_model_path = str(model_path) if model_path else "Qwen/Qwen3-ASR-1.7B"
            forced_aligner_path = str(aligner_path) if aligner_path else "Qwen/Qwen3-ForcedAligner-0.6B"

            # 检查是否使用本地路径
            from ..core.config import settings
            local_asr_path = settings.CHECKPOINTS_DIR / "Qwen" / "Qwen3-ASR-1.7B"
            local_aligner_path = settings.CHECKPOINTS_DIR / "Qwen" / "Qwen3-ForcedAligner-0.6B"

            if local_asr_path.exists():
                asr_model_path = str(local_asr_path)
                logger.info(f"使用本地 ASR 模型: {asr_model_path}")

            if local_aligner_path.exists():
                forced_aligner_path = str(local_aligner_path)
                logger.info(f"使用本地 ForcedAligner 模型: {forced_aligner_path}")

            logger.info(f"加载 Qwen3-ASR 模型: {asr_model_path}")
            logger.info(f"加载 Qwen3-ForcedAligner 模型: {forced_aligner_path}")

            try:
                cls._model = Qwen3ASRModel.from_pretrained(
                    asr_model_path,
                    dtype=torch.bfloat16 if cls._is_cuda_available() else torch.float32,
                    device_map="cuda:0" if cls._is_cuda_available() else "cpu",
                    forced_aligner=forced_aligner_path,
                    forced_aligner_kwargs=dict(
                        dtype=torch.bfloat16 if cls._is_cuda_available() else torch.float32,
                        device_map="cuda:0" if cls._is_cuda_available() else "cpu",
                    ),
                    max_inference_batch_size=32,
                    max_new_tokens=1024,
                )
                logger.info("Qwen3-ASR 模型加载成功")
            except Exception as e:
                logger.error(f"Qwen3-ASR 模型加载失败: {str(e)}")
                raise RuntimeError(f"Qwen3-ASR 模型加载失败: {str(e)}")

        return cls._model

    @classmethod
    def _is_cuda_available(cls) -> bool:
        """检查 CUDA 是否可用"""
        try:
            if torch is None:
                return False
            return torch.cuda.is_available()
        except ImportError:
            return False


async def transcribe_audio(
    audio_path: Path,
    model_path: Optional[Path] = None,
    aligner_path: Optional[Path] = None,
    language: str = "zh",
    task: str = "transcribe",
    chunk_length_s: int = 30,
    save_raw_result: bool = False,
    context: Optional[str] = None
) -> Dict:
    """
    使用 Qwen3-ASR 进行语音识别

    Args:
        audio_path: 音频文件路径
        model_path: ASR 模型路径，默认使用配置中的路径
        aligner_path: ForcedAligner 模型路径
        language: 语言代码 (zh/en等)
        task: 任务类型 (transcribe/translate) - 保留兼容性
        chunk_length_s: 分块长度（秒）- 保留兼容性
        save_raw_result: 是否保存原始 ASR 结果为 JSON 文件
        context: 上下文提示字符串，用于提供 ASR 识别时的背景信息（如专有名词、术语等）

    Returns:
        Dict: {
            'text': str,  # 完整文本
            'segments': [  # 带时间戳的片段
                {'start': float, 'end': float, 'text': str},
                ...
            ]
        }

    Raises:
        RuntimeError: 识别失败
    """
    # 加载模型
    model = await asyncio.get_event_loop().run_in_executor(
        None, ASRModel.get_model, model_path, aligner_path
    )

    def _transcribe():
        try:
            # 标准化语言名称
            language_map = {
                "zh": "Chinese",
                "zh-CN": "Chinese",
                "zh-TW": "Chinese",
                "en": "English",
                "yue": "Cantonese",
                "ja": "Japanese",
                "ko": "Korean",
            }
            normalized_language = language_map.get(language, language)

            # 使用 Qwen3-ASR 进行识别，带时间戳
            logger.info(f"开始 ASR 识别: {audio_path}")
            results = model.transcribe(
                audio=str(audio_path),
                language=normalized_language,
                return_time_stamps=True,
                context=context if context else "",
            )

            if not results or len(results) == 0:
                logger.warning(f"ASR 识别未返回结果: {audio_path}")
                return {
                    'text': '',
                    'segments': []
                }

            # 获取第一个结果
            result = results[0]

            # 提取文本和时间戳
            text = result.text
            logger.info(f"ASR 识别完成，文本长度: {len(text)} 字符")

            # 保存原始 ASR 结果为 JSON 文件（如果需要）
            if save_raw_result and result.time_stamps is not None:
                import json
                raw_result = {
                    'text': text,
                    'time_stamps': []
                }
                for item in result.time_stamps:
                    raw_result['time_stamps'].append({
                        'start_time': float(item.start_time),
                        'end_time': float(item.end_time),
                        'text': str(item.text)
                    })

                # 生成 JSON 文件路径（与音频文件同名）
                json_path = audio_path.with_suffix('.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(raw_result, f, ensure_ascii=False, indent=4)
                logger.info(f"原始 ASR 结果已保存到: {json_path}")

            # Qwen3-ForcedAligner 返回的时间戳是 token/字符级别的
            # 注意：time_stamps 不包含标点符号，但 result.text 包含
            # 策略：基于 result.text 按标点切分成句子，然后从 time_stamps 中找到对应的时间戳
            segments = []
            if result.time_stamps is not None:
                char_count = len(result.time_stamps)
                logger.info(f"字符级别时间戳数量: {char_count}")

                # 先转换字符级别时间戳
                char_segments = []
                for item in result.time_stamps:
                    char_segments.append({
                        'start': float(item.start_time),
                        'end': float(item.end_time),
                        'text': str(item.text)
                    })

                # 基于result.text按标点切分句子，并从time_stamps中找到对应的时间戳
                logger.info("开始按标点切分成句子级别字幕...")
                segments = _merge_char_segments_to_sentences_with_text(char_segments, text)
                logger.info(f"切分完成，生成 {len(segments)} 条句子级别字幕")

            return {
                'text': text,
                'segments': segments
            }

        except Exception as e:
            logger.exception(f"ASR 识别失败: {audio_path}")
            raise RuntimeError(f"ASR 识别失败: {str(e)}")

    return await asyncio.get_event_loop().run_in_executor(None, _transcribe)


def _merge_char_segments_to_sentences(
    char_segments: List[Dict],
    target_duration: float = 5.0,
    max_duration: float = 8.0,
    min_duration: float = 2.0
) -> List[Dict]:
    """
    将字符级别的时间戳合并成句子级别

    策略：
    1. Qwen3-ASR返回的text包含标点符号，但time_stamps是字符级
    2. 按标点符号优先切分（。，！？；；）
    3. 结合时间间隔判断（停顿>0.5秒加强切分）
    4. 结合时长控制（目标5秒，最大8秒，最小2秒）

    Args:
        char_segments: 字符级别的时间戳列表
        target_duration: 目标字幕时长（秒）
        max_duration: 最大字幕时长（秒）
        min_duration: 最小字幕时长（秒）

    Returns:
        List[Dict]: 句子级别的时间戳列表
    """
    if not char_segments:
        return []

    # 标点符号集合 - 这些是模型实际生成的标点
    sentence_end_punct = {'。', '！', '？', '.', '!', '?'}  # 句末标点
    pause_punct = {'，', ',', ';', '；', '、'}  # 停顿标点

    sentences = []
    current_chars = [char_segments[0]]
    last_pause_idx = -1  # 上一个停顿标点位置

    for i in range(1, len(char_segments)):
        curr_seg = char_segments[i]
        prev_seg = char_segments[i - 1]

        # 如果current_chars为空（刚处理完句末标点），直接添加当前字符
        if not current_chars:
            current_chars.append(curr_seg)
            continue

        # 计算相邻token之间的时间间隔
        gap = curr_seg['start'] - prev_seg['end']

        # 计算当前累积时长
        current_duration = current_chars[-1]['end'] - current_chars[0]['start']

        # 判断是否应该切分
        should_split = False

        # 1. 句末标点切分（最高优先级）
        if curr_seg['text'] in sentence_end_punct:
            # 标点作为当前句子的结尾
            current_chars.append(curr_seg)
            sentence_text = ''.join([c['text'] for c in current_chars])
            sentence_start = current_chars[0]['start']
            sentence_end = current_chars[-1]['end']

            sentences.append({
                'start': sentence_start,
                'end': sentence_end,
                'text': sentence_text
            })

            current_chars = []
            last_pause_idx = -1
            continue

        # 2. 停顿标点
        if curr_seg['text'] in pause_punct:
            current_chars.append(curr_seg)
            last_pause_idx = len(current_chars)

            # 如果达到目标时长，且有停顿标点，考虑切分
            if current_duration >= target_duration:
                should_split = True
            else:
                continue  # 停顿标点已添加，不需要后面的处理

        # 3. 时间停顿切分（语音停顿）
        elif gap > 0.5 and current_duration >= min_duration:
            should_split = True

        # 4. 超时切分：超过最大时长
        elif current_duration >= max_duration:
            should_split = True

        if should_split:
            # 保存当前句子
            sentence_text = ''.join([c['text'] for c in current_chars])
            sentence_start = current_chars[0]['start']
            sentence_end = current_chars[-1]['end']

            sentences.append({
                'start': sentence_start,
                'end': sentence_end,
                'text': sentence_text
            })

            # 开始新句子
            current_chars = [curr_seg]
            last_pause_idx = -1
        else:
            # 继续累积（非停顿标点的情况）
            current_chars.append(curr_seg)

    # 处理剩余字符
    if current_chars:
        sentence_text = ''.join([c['text'] for c in current_chars])
        sentence_start = current_chars[0]['start']
        sentence_end = current_chars[-1]['end']

        # 如果剩余内容太短，合并到上一条
        if sentences and (sentence_end - sentence_start) < min_duration:
            last_sentence = sentences[-1]
            last_sentence['text'] += sentence_text
            last_sentence['end'] = sentence_end
        else:
            sentences.append({
                'start': sentence_start,
                'end': sentence_end,
                'text': sentence_text
            })

    return sentences


def _merge_char_segments_to_sentences_with_text(
    char_segments: List[Dict],
    full_text: str
) -> List[Dict]:
    """
    基于full_text按标点切分句子，并从time_stamps中找到对应的时间戳

    Qwen3-ASR 的 time_stamps 特点：
    1. 每个 item 包含多个字符（不是单字符级别）
    2. time_stamps 不包含标点符号
    3. 需要通过字符位置映射来找到对应关系

    策略：
    1. 按full_text中的标点符号切分成句子，记录每个句子的位置
    2. 构建字符位置到time_stamps索引的映射
    3. 通过位置映射获取每个句子对应的时间戳

    Args:
        char_segments: 时间戳列表（来自time_stamps，每个item含多个字符）
        full_text: 包含标点的完整文本（来自result.text）

    Returns:
        List[Dict]: 带标点和时间戳的句子列表
    """
    import re

    if not char_segments or not full_text:
        return []

    logger.info(f"_merge_char_segments_to_sentences_with_text: full_text长度={len(full_text)}, char_segments数量={len(char_segments)}")

    # 1. 构建字符位置到 time_stamps 索引的映射
    position_map = []
    for idx, seg in enumerate(char_segments):
        text_length = len(seg['text'])
        for _ in range(text_length):
            position_map.append(idx)

    # 2. 按标点分割句子，同时记录位置
    pattern = r'[^。！？\.\!\?]+[。！？\.\!\?]'
    sentences_with_pos = []
    for match in re.finditer(pattern, full_text):
        sentences_with_pos.append((match.group(), match.start(), match.end()))

    # 处理可能剩下的文本
    if sentences_with_pos:
        last_end = sentences_with_pos[-1][2]
        if last_end < len(full_text):
            remaining = full_text[last_end:].strip()
            if remaining:
                sentences_with_pos.append((remaining, last_end, len(full_text)))
    else:
        # 没有标点，返回原始segments
        return char_segments

    logger.info(f"按标点切分后句子数量: {len(sentences_with_pos)}")

    # 辅助函数: 将包含标点的位置转换为去除标点后的位置
    def get_clean_position(text: str, pos: int) -> int:
        """将包含标点的文本位置转换为去除标点后的位置"""
        punct_before = len(re.findall(r'[\s，,、;：:。！？\.\!\?]', text[:pos]))
        return pos - punct_before

    # 辅助函数: 根据字符位置获取时间戳
    def get_time_at_position(char_pos: int) -> tuple:
        """根据字符位置获取 (start_time, end_time)"""
        if char_pos < 0:
            char_pos = 0
        if char_pos >= len(position_map):
            char_pos = len(position_map) - 1

        idx = position_map[char_pos]
        return char_segments[idx]['start'], char_segments[idx]['end']

    # 3. 为每个句子分配时间戳
    result = []
    for i, (sentence, start_pos, end_pos) in enumerate(sentences_with_pos):
        # 计算去除标点后的字符位置
        clean_start = get_clean_position(full_text, start_pos)
        clean_end = get_clean_position(full_text, end_pos)

        # 边界检查
        clean_start = max(0, min(clean_start, len(position_map) - 1))
        clean_end = max(0, min(clean_end - 1, len(position_map) - 1))

        # 获取时间戳
        start_time, _ = get_time_at_position(clean_start)
        _, end_time = get_time_at_position(clean_end)

        result.append({
            'start': start_time,
            'end': end_time,
            'text': sentence.strip()
        })

    logger.info(f"最终生成 {len(result)} 条字幕")
    return result


async def batch_transcribe(
    audio_paths: List[Path],
    model_path: Optional[Path] = None,
    aligner_path: Optional[Path] = None,
    language: str = "zh"
) -> List[Dict]:
    """
    批量语音识别

    Args:
        audio_paths: 音频文件路径列表
        model_path: 模型路径
        aligner_path: ForcedAligner 模型路径
        language: 语言代码

    Returns:
        List[Dict]: 识别结果列表
    """
    results = []
    for audio_path in audio_paths:
        try:
            result = await transcribe_audio(audio_path, model_path, aligner_path, language)
            results.append({
                'audio_path': str(audio_path),
                'success': True,
                'result': result
            })
        except Exception as e:
            logger.error(f"识别失败: {audio_path}, 错误: {e}")
            results.append({
                'audio_path': str(audio_path),
                'success': False,
                'error': str(e)
            })

    return results
