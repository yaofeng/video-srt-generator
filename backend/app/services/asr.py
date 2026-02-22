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
                    dtype=torch.float16 if cls._is_cuda_available() else torch.float32,
                    device_map="cuda:0" if cls._is_cuda_available() else "cpu",
                    forced_aligner=forced_aligner_path,
                    forced_aligner_kwargs=dict(
                        dtype=torch.float16 if cls._is_cuda_available() else torch.float32,
                        device_map="cuda:0" if cls._is_cuda_available() else "cpu",
                    ),
                    max_inference_batch_size=32,
                    max_new_tokens=256,
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
    chunk_length_s: int = 30
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

    策略：
    1. 按full_text中的标点符号切分成句子
    2. 在char_segments中找到每个句子的开始和结束时间

    Args:
        char_segments: 字符级别的时间戳列表（来自time_stamps）
        full_text: 包含标点的完整文本（来自result.text）

    Returns:
        List[Dict]: 带标点和时间戳的句子列表
    """
    if not char_segments or not full_text:
        return []

    # 移除full_text中的空格
    clean_text = full_text.replace(' ', '').replace('\n', '').replace('\t', '')

    # 按标点符号切分clean_text
    sentence_end_punct = ['。', '！', '？', '.', '!', '?']

    # 切分成句子，记录每个句子在clean_text中的字符位置
    sentences_with_pos = []
    current = []
    start_pos = 0

    for i, char in enumerate(clean_text):
        current.append(char)
        if char in sentence_end_punct:
            sentence_text = ''.join(current)
            end_pos = i + 1
            sentences_with_pos.append({
                'text': sentence_text,
                'start_pos': start_pos,
                'end_pos': end_pos
            })
            current = []
            start_pos = i + 1

    # 处理剩余部分
    if current:
        sentence_text = ''.join(current)
        if sentences_with_pos and len(sentence_text) < 5:
            # 合并到上一句
            sentences_with_pos[-1]['text'] += sentence_text
            sentences_with_pos[-1]['end_pos'] = len(clean_text)
        else:
            sentences_with_pos.append({
                'text': sentence_text,
                'start_pos': start_pos,
                'end_pos': len(clean_text)
            })

    if not sentences_with_pos:
        # 没有标点，返回原始segments
        return char_segments

    # 为每个句子从char_segments中找到对应的时间戳
    # 策略：按字符比例匹配
    result = []

    for sent in sentences_with_pos:
        sent_text = sent['text'].replace(' ', '')
        start_pos = sent['start_pos']
        end_pos = sent['end_pos']

        # 计算这个句子对应char_segments的哪个范围
        total_chars = len(clean_text)
        start_ratio = start_pos / total_chars
        end_ratio = end_pos / total_chars

        # 在char_segments中找到对应的时间
        total_segments = len(char_segments)
        start_idx = int(start_ratio * total_segments)
        end_idx = int(end_ratio * total_segments)

        # 确保索引有效
        start_idx = max(0, min(start_idx, len(char_segments) - 1))
        end_idx = max(start_idx + 1, min(end_idx, len(char_segments)))

        start_time = char_segments[start_idx]['start']
        end_time = char_segments[end_idx - 1]['end']

        result.append({
            'start': start_time,
            'end': end_time,
            'text': sent_text
        })

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
