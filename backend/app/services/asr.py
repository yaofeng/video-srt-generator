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
            results = model.transcribe(
                audio=str(audio_path),
                language=normalized_language,
                return_time_stamps=True,
            )

            if not results or len(results) == 0:
                return {
                    'text': '',
                    'segments': []
                }

            # 获取第一个结果
            result = results[0]

            # 提取文本和时间戳
            text = result.text

            # Qwen3-ForcedAligner 返回的时间戳是 token/字符级别的
            # 格式: ForcedAlignItem(text, start_time, end_time)
            # 需要按标点符号合并成句子级别
            segments = []
            if result.time_stamps is not None:
                # 先转换字符级别时间戳
                char_segments = []
                for item in result.time_stamps:
                    char_segments.append({
                        'start': float(item.start_time),
                        'end': float(item.end_time),
                        'text': str(item.text)
                    })

                # 按标点符号合并成句子
                segments = _merge_char_segments_to_sentences(char_segments)

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
    min_duration: float = 2.0,
    pause_threshold: float = 0.5
) -> List[Dict]:
    """
    将字符级别的时间戳合并成句子级别

    策略：
    1. 基于token之间的时间间隔判断句子边界（停顿>0.5秒认为是新句子）
    2. 结合时长控制（目标5秒，最大8秒，最小2秒）
    3. 超过最大时长强制切分

    Args:
        char_segments: 字符级别的时间戳列表
        target_duration: 目标字幕时长（秒）
        max_duration: 最大字幕时长（秒）
        min_duration: 最小字幕时长（秒）
        pause_threshold: 停顿阈值（秒），超过此值认为是句子边界

    Returns:
        List[Dict]: 句子级别的时间戳列表
    """
    if not char_segments:
        return []

    sentences = []
    current_chars = [char_segments[0]]  # 初始化，加入第一个字符

    for i in range(1, len(char_segments)):
        prev_seg = char_segments[i - 1]
        curr_seg = char_segments[i]

        # 计算相邻token之间的时间间隔
        gap = curr_seg['start'] - prev_seg['end']

        # 计算当前累积时长
        current_duration = current_chars[-1]['end'] - current_chars[0]['start']

        # 判断是否应该切分
        should_split = False

        # 1. 停顿切分：间隔超过阈值且时长足够
        if gap > pause_threshold and current_duration >= min_duration:
            should_split = True

        # 2. 超时切分：超过最大时长
        elif current_duration >= max_duration:
            should_split = True

        # 3. 目标时长+停顿：达到目标时长且有明显停顿
        elif current_duration >= target_duration and gap > pause_threshold * 0.5:
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
        else:
            # 继续累积
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
