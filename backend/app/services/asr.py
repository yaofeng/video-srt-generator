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
            segments = []
            if result.time_stamps is not None:
                for item in result.time_stamps:
                    segments.append({
                        'start': float(item.start_time),
                        'end': float(item.end_time),
                        'text': str(item.text)
                    })

            return {
                'text': text,
                'segments': segments
            }

        except Exception as e:
            logger.exception(f"ASR 识别失败: {audio_path}")
            raise RuntimeError(f"ASR 识别失败: {str(e)}")

    return await asyncio.get_event_loop().run_in_executor(None, _transcribe)


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
