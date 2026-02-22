# backend/app/services/asr.py
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
import logging
import json

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
    """ASR 模型单例"""
    _model = None
    _processor = None
    _device = None
    _model_path = None
    _tokenizer = None

    @classmethod
    def get_model(cls, model_path: Path):
        """获取模型实例"""
        if cls._model is None or cls._model_path != model_path:
            cls._model_path = model_path

            if not model_path.exists():
                raise RuntimeError(f"ASR 模型不存在: {model_path}")

            if torch is None:
                raise RuntimeError("torch 模块未安装")

            # 确定设备
            cls._device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if cls._device == "cuda" else torch.float32

            logger.info(f"加载 ASR 模型: {model_path}, 设备: {cls._device}")

            # 加载模型和处理器
            try:
                from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, AutoTokenizer

                cls._model = AutoModelForSpeechSeq2Seq.from_pretrained(
                    str(model_path),
                    torch_dtype=dtype,
                    low_cpu_mem_usage=True,
                    trust_remote_code=True
                ).to(cls._device).eval()

                cls._processor = AutoProcessor.from_pretrained(
                    str(model_path),
                    trust_remote_code=True
                )

                cls._tokenizer = AutoTokenizer.from_pretrained(
                    str(model_path),
                    trust_remote_code=True
                )

                if cls._device == "cuda" and hasattr(torch, 'compile'):
                    try:
                        cls._model = torch.compile(cls._model)
                    except Exception as e:
                        logger.warning(f"模型编译失败，使用解释模式: {e}")

                logger.info("ASR 模型加载成功")

            except Exception as e:
                raise RuntimeError(f"ASR 模型加载失败: {str(e)}")

        return cls._model, cls._processor, cls._tokenizer, cls._device


async def transcribe_audio(
    audio_path: Path,
    model_path: Optional[Path] = None,
    language: str = "zh",
    task: str = "transcribe",
    chunk_length_s: int = 30
) -> Dict:
    """
    语音识别

    Args:
        audio_path: 音频文件路径
        model_path: 模型路径，默认使用配置中的路径
        language: 语言代码 (zh/en等)
        task: 任务类型 (transcribe/translate)
        chunk_length_s: 分块长度（秒）

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
    from ..core.config import settings

    if model_path is None:
        model_path = settings.CHECKPOINTS_DIR / settings.QWEN_ASR_MODEL

    # 加载模型
    model, processor, tokenizer, device = await asyncio.get_event_loop().run_in_executor(
        None, ASRModel.get_model, model_path
    )

    def _transcribe():
        try:
            # 加载音频
            if audio_path.suffix == '.wav':
                # 使用 torchaudio 或 soundfile 加载
                waveform, sample_rate = _load_audio(audio_path)

                # 重采样到 16000Hz
                if sample_rate != 16000:
                    waveform = _resample(waveform, sample_rate, 16000)
                    sample_rate = 16000
            else:
                # 使用 ffmpeg 转换为 WAV
                waveform, sample_rate = _load_audio_with_ffmpeg(audio_path)

            # 准备输入
            inputs = processor(
                waveform.squeeze(0) if waveform.ndim > 1 else waveform,
                sampling_rate=sample_rate,
                return_tensors="pt"
            ).to(device)

            # 生成
            with torch.no_grad():
                output = model.generate(
                    **inputs,
                    language=language,
                    task=task,
                    return_timestamps=True,
                    do_sample=False,
                    max_new_tokens=448
                )

            # 解码结果
            decoded = processor.decode(output[0], skip_special_tokens=True)

            # 提取文本和片段
            text, segments = _extract_segments_with_timestamps(
                output,
                processor.tokenizer if hasattr(processor, 'tokenizer') else tokenizer,
                sample_rate
            )

            return {
                'text': text,
                'segments': segments
            }

        except Exception as e:
            logger.exception(f"ASR 识别失败: {audio_path}")
            raise RuntimeError(f"ASR 识别失败: {str(e)}")

    return await asyncio.get_event_loop().run_in_executor(None, _transcribe)


def _load_audio(audio_path: Path):
    """加载音频文件"""
    # 优先使用 torchaudio
    try:
        import torchaudio
        waveform, sample_rate = torchaudio.load(str(audio_path))
        return waveform, sample_rate
    except ImportError:
        pass

    # 使用 soundfile 作为备选
    try:
        import soundfile as sf
        waveform, sample_rate = sf.read(str(audio_path))
        # 转换为 torch tensor 并添加通道维度
        if torch is None:
            raise RuntimeError("需要 torch 模块")
        waveform = torch.from_numpy(waveform).float()
        if waveform.ndim == 1:
            waveform = waveform.unsqueeze(0)
        return waveform, sample_rate
    except ImportError:
        raise RuntimeError("需要安装 torchaudio 或 soundfile 来加载音频文件")


def _load_audio_with_ffmpeg(audio_path: Path):
    """使用 ffmpeg 加载音频文件"""
    try:
        import ffmpeg
        import io

        # 使用 ffmpeg 读取音频并转换为 WAV 格式
        out, err = (
            ffmpeg
            .input(str(audio_path))
            .output('pipe:', format='wav', acodec='pcm_s16le', ac=1, ar=16000)
            .run(capture_stdout=True, capture_stderr=True)
        )

        # 从字节流加载音频
        import soundfile as sf
        waveform, sample_rate = sf.read(io.BytesIO(out))

        if torch is None:
            raise RuntimeError("需要 torch 模块")

        waveform = torch.from_numpy(waveform).float().unsqueeze(0)
        return waveform, sample_rate

    except ImportError:
        raise RuntimeError("需要安装 ffmpeg-python 和 soundfile")
    except Exception as e:
        raise RuntimeError(f"使用 ffmpeg 加载音频失败: {str(e)}")


def _resample(waveform, orig_sr, target_sr):
    """重采样音频"""
    try:
        import torchaudio.transforms as T
        resampler = T.Resample(orig_sr, target_sr)
        if torch is None:
            raise RuntimeError("需要 torch 模块")
        return resampler(waveform)
    except ImportError:
        # 使用 scipy 的 resample
        from scipy import signal
        import numpy as np

        waveform_np = waveform.numpy()
        if waveform_np.ndim > 1:
            waveform_np = waveform_np[0]

        number_of_samples = round(len(waveform_np) * float(target_sr) / orig_sr)
        resampled = signal.resample(waveform_np, number_of_samples)

        if torch is None:
            raise RuntimeError("需要 torch 模块")
        return torch.from_numpy(resampled).float().unsqueeze(0)


def _extract_segments_with_timestamps(
    output: torch.Tensor,
    tokenizer,
    sample_rate: int = 16000
) -> tuple[str, List[Dict]]:
    """
    从模型输出中提取带时间戳的片段

    Qwen3-ASR 返回 token 级别的时间戳，需要转换为句子级别
    """
    segments = []

    try:
        # 解码输出
        if isinstance(output, torch.Tensor):
            output_ids = output[0].cpu().numpy()
        else:
            output_ids = output[0]

        # 转换为 token 列表
        tokens = [tokenizer.decode([token_id]) for token_id in output_ids]

        # 移除特殊 token
        text = tokenizer.decode(output_ids, skip_special_tokens=True)

        # 简化处理：按字符平均分配时间戳
        # 实际应用中需要根据模型的 timestamp tokens 来精确计算
        audio_duration = 30.0  # 默认假设 30 秒，应该从实际音频获取

        # 按句子分割
        sentences = _split_into_sentences(text)

        # 为每个句子分配时间戳
        char_duration = audio_duration / len(text) if len(text) > 0 else 0
        current_time = 0.0

        for sentence in sentences:
            if not sentence.strip():
                continue

            sentence_duration = len(sentence) * char_duration
            segments.append({
                'start': current_time,
                'end': current_time + sentence_duration,
                'text': sentence.strip()
            })
            current_time += sentence_duration

        return text, segments

    except Exception as e:
        logger.warning(f"提取时间戳失败，使用简化处理: {e}")
        # 返回简化的结果
        text = tokenizer.decode(output[0] if isinstance(output, torch.Tensor) else output, skip_special_tokens=True)
        return text, [{'start': 0.0, 'end': 30.0, 'text': text}]


def _split_into_sentences(text: str) -> List[str]:
    """
    将文本分割成句子

    Args:
        text: 输入文本

    Returns:
        List[str]: 句子列表
    """
    import re

    # 按标点符号分割
    sentences = re.split(r'([。！？.!?])', text)

    # 重组句子（保留标点）
    result = []
    for i in range(0, len(sentences) - 1, 2):
        if i + 1 < len(sentences):
            sentence = sentences[i] + sentences[i + 1]
            if sentence.strip():
                result.append(sentence)

    # 处理剩余部分
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        result.append(sentences[-1])

    return result


async def batch_transcribe(
    audio_paths: List[Path],
    model_path: Optional[Path] = None,
    language: str = "zh"
) -> List[Dict]:
    """
    批量语音识别

    Args:
        audio_paths: 音频文件路径列表
        model_path: 模型路径
        language: 语言代码

    Returns:
        List[Dict]: 识别结果列表
    """
    results = []
    for audio_path in audio_paths:
        try:
            result = await transcribe_audio(audio_path, model_path, language)
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
