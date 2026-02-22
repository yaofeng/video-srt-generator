# backend/app/services/vad.py
import asyncio
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

try:
    import numpy as np
except ImportError:
    logger.error("numpy 未安装")
    np = None

try:
    import ffmpeg
except ImportError:
    logger.error("ffmpeg-python 未安装")
    ffmpeg = None


class VADModel:
    """fsmn-vad 模型单例"""
    _model = None
    _model_path = None

    @classmethod
    def get_model(cls, model_path: Optional[Path] = None):
        """获取 fsmn-vad 模型实例"""
        if cls._model is None:
            from funasr import AutoModel

            # 如果未指定路径，使用默认模型名称
            if model_path is None:
                model_name = "fsmn-vad"
            else:
                model_name = str(model_path)

            logger.info(f"加载 fsmn-vad 模型: {model_name}")

            try:
                cls._model = AutoModel(
                    model=model_name,
                    model_revision="v2.0.4",
                    device="cuda" if cls._is_cuda_available() else "cpu"
                )
                logger.info("fsmn-vad 模型加载成功")
            except Exception as e:
                logger.error(f"fsmn-vad 模型加载失败: {str(e)}")
                raise RuntimeError(f"fsmn-vad 模型加载失败: {str(e)}")

        return cls._model

    @classmethod
    def _is_cuda_available(cls) -> bool:
        """检查 CUDA 是否可用"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False


async def detect_speech_activity(
    audio_path: Path,
    threshold: float = 0.5
) -> List[Tuple[float, float]]:
    """
    使用 fsmn-vad 检测语音活动

    Args:
        audio_path: 音频文件路径
        threshold: 语音概率阈值 (fsmn-vad 内部使用)

    Returns:
        List[Tuple[float, float]]: [(start_time, end_time), ...] 语音片段列表
    """
    if np is None:
        raise RuntimeError("numpy 模块未安装")

    def _detect():
        try:
            # 加载模型
            model = VADModel.get_model()

            # 加载音频
            import soundfile as sf
            waveform, sample_rate = sf.read(str(audio_path))

            # 确保单声道
            if len(waveform.shape) > 1:
                waveform = waveform[:, 0]

            # 重采样到 16kHz（fsmn-vad 要求）
            if sample_rate != 16000:
                from scipy import signal
                number_of_samples = round(len(waveform) * float(16000) / sample_rate)
                waveform = signal.resample(waveform, number_of_samples)
                sample_rate = 16000

            # 使用 fsmn-vad 进行语音活动检测
            # fsmn-vad 期望输入格式: [numpy.ndarray, sample_rate]
            vad_result = model.generate(
                input=[waveform],
                batch_size_s=300  # 5 分钟批量处理
            )

            logger.info(f"fsmn-vad 原始结果类型: {type(vad_result)}, 数量: {len(vad_result) if vad_result else 0}")

            # 解析结果
            segments = []
            if vad_result and len(vad_result) > 0:
                # fsmn-vad 返回格式可能是字典或列表
                result = vad_result[0]
                logger.info(f"fsmn-vad 第一个结果类型: {type(result)}, 内容: {str(result)[:500]}")

                # 尝试不同的解析方式
                # 方式1: result 是字典，包含 'sentence_info' 键
                if isinstance(result, dict) and 'sentence_info' in result:
                    sentence_info = result['sentence_info']
                    logger.info(f"使用 sentence_info 格式解析，数量: {len(sentence_info) if sentence_info else 0}")
                    if sentence_info:
                        for item in sentence_info:
                            if isinstance(item, dict):
                                start_ms = item.get('start', 0)
                                end_ms = item.get('end', 0)
                                # 转换为秒
                                segments.append((start_ms / 1000.0, end_ms / 1000.0))
                                logger.info(f"  片段: {start_ms}ms - {end_ms}ms")

                # 方式2: result 是字典，包含 'value' 键
                elif isinstance(result, dict) and 'value' in result:
                    value = result['value']
                    logger.info(f"使用 value 格式解析，数量: {len(value) if value else 0}")
                    if value:
                        for segment in value:
                            if isinstance(segment, dict):
                                start_ms = segment.get('start', 0)
                                end_ms = segment.get('end', 0)
                                segments.append((start_ms / 1000.0, end_ms / 1000.0))
                                logger.info(f"  片段: {start_ms}ms - {end_ms}ms")

                # 方式3: result 是列表
                elif isinstance(result, list):
                    logger.info(f"使用列表格式解析，数量: {len(result)}")
                    for segment in result:
                        if isinstance(segment, dict):
                            start_ms = segment.get('start', 0)
                            end_ms = segment.get('end', 0)
                            segments.append((start_ms / 1000.0, end_ms / 1000.0))
                            logger.info(f"  片段: {start_ms}ms - {end_ms}ms")

                # 方式4: result 可能直接就是时间戳列表
                else:
                    logger.warning(f"未知的 VAD 结果格式: {type(result)}")
                    # 尝试将整个音频作为一个片段
                    total_duration = len(waveform) / sample_rate
                    segments = [(0.0, total_duration)]
                    logger.info(f"将整个音频作为单一片段，时长: {total_duration:.2f}秒")

            logger.info(f"fsmn-vad 解析后检测到 {len(segments)} 个语音片段")
            for i, (s, e) in enumerate(segments[:10]):  # 只打印前10个
                logger.info(f"  片段 {i+1}: {s:.2f}s - {e:.2f}s (时长: {e-s:.2f}s)")
            if len(segments) > 10:
                logger.info(f"  ... (还有 {len(segments) - 10} 个片段)")

            return segments

        except ImportError:
            raise RuntimeError("需要安装 funasr 和 soundfile 来使用 fsmn-vad")
        except Exception as e:
            logger.exception(f"VAD 检测失败: {audio_path}")
            raise RuntimeError(f"VAD 检测失败: {str(e)}")

    return await asyncio.get_event_loop().run_in_executor(None, _detect)


async def split_audio_by_vad(
    audio_path: Path,
    output_dir: Path,
    min_duration: int = 180,
    max_duration: int = 300,
    silence_threshold: float = 0.5
) -> List[Dict]:
    """
    根据 VAD 结果切分音频
    策略：以 5 分钟为单位，找出最大间隔进行切分

    Args:
        audio_path: 音频文件路径
        output_dir: 输出目录
        min_duration: 最小片段时长（秒），默认 180 秒（3 分钟）
        max_duration: 最大片段时长（秒），默认 300 秒（5 分钟）
        silence_threshold: 静音阈值（秒），默认 0.5 秒

    Returns:
        List[Dict]: 切分后的片段信息列表，每个元素包含:
            - index: 片段索引
            - start_time: 开始时间（秒）
            - end_time: 结束时间（秒）
            - duration: 时长（秒）
            - audio_path: 音频文件路径
    """
    if ffmpeg is None:
        raise RuntimeError("ffmpeg-python 模块未安装")

    output_dir.mkdir(parents=True, exist_ok=True)

    # 使用 fsmn-vad 检测语音活动
    speech_segments = await detect_speech_activity(audio_path, threshold=silence_threshold)

    if not speech_segments:
        # 如果没有检测到语音活动，获取整个音频时长
        duration = await get_audio_duration(audio_path)
        speech_segments = [(0.0, duration)]

    # 合并和切分片段
    # 策略：以 5 分钟为单位，找出最大间隔进行切分
    final_segments = _merge_segments_to_duration(
        speech_segments,
        min_duration=min_duration,
        max_duration=max_duration
    )

    # 使用 ffmpeg 切分音频
    for i, seg in enumerate(final_segments):
        output_path = output_dir / f"segment_{i:04d}.wav"
        await _extract_segment(audio_path, seg['start_time'], seg['end_time'], output_path)
        seg['audio_path'] = str(output_path)
        seg['index'] = i

    return final_segments


def _merge_segments_to_duration(
    speech_segments: List[Tuple[float, float]],
    min_duration: int = 180,
    max_duration: int = 300
) -> List[Dict]:
    """
    将语音片段合并为目标时长（3-5分钟）
    策略：以 5 分钟（max_duration）为单位，找出最大间隔进行切分

    Args:
        speech_segments: 语音片段列表 [(start, end), ...]
        min_duration: 最小时长（秒）
        max_duration: 最大时长（秒）- 这是我们希望的目标单位

    Returns:
        List[Dict]: 合并后的片段信息
    """
    if not speech_segments:
        return []

    final_segments = []

    # 策略：以 max_duration（5分钟）为单位遍历时间轴
    # 找出每个单位窗口内的所有语音片段，合并它们
    total_end = speech_segments[-1][1]

    window_start = speech_segments[0][0]
    window_end = window_start + max_duration

    i = 0
    while i < len(speech_segments):
        # 收集当前窗口内的所有语音片段
        window_segments = []
        current_window_start = None

        while i < len(speech_segments):
            seg_start, seg_end = speech_segments[i]

            # 如果这个片段的开始时间在当前窗口内
            if seg_start < window_end:
                window_segments.append((seg_start, seg_end))
                if current_window_start is None:
                    current_window_start = seg_start
                i += 1
            else:
                # 这个片段在当前窗口外，需要检查是否可以跨窗口
                # 如果当前窗口已经有足够的语音，就结束当前窗口
                current_window_end = max([s[1] for s in window_segments]) if window_segments else seg_start

                # 计算当前窗口的语音时长
                speech_duration = sum([s[1] - s[0] for s in window_segments])

                # 如果语音时长达到最小时长，或者当前窗口已满
                if speech_duration >= min_duration or (seg_start - window_start) >= max_duration:
                    break
                else:
                    # 继续累积到下一个窗口
                    window_segments.append((seg_start, seg_end))
                    i += 1

        if window_segments:
            # 合并当前窗口的片段为一个输出片段
            merged_start = window_segments[0][0]
            merged_end = window_segments[-1][1]
            merged_duration = merged_end - merged_start

            final_segments.append({
                'start_time': merged_start,
                'end_time': merged_end,
                'duration': merged_duration
            })

        # 移动窗口到下一个单位
        window_start = window_end
        window_end = window_start + max_duration

    return final_segments


async def _extract_segment(
    audio_path: Path,
    start_time: float,
    end_time: float,
    output_path: Path
):
    """
    提取音频片段

    Args:
        audio_path: 源音频文件路径
        start_time: 开始时间（秒）
        end_time: 结束时间（秒）
        output_path: 输出文件路径
    """
    if ffmpeg is None:
        raise RuntimeError("ffmpeg-python 模块未安装")

    def _extract():
        duration = end_time - start_time
        try:
            (
                ffmpeg
                .input(str(audio_path), ss=start_time, t=duration)
                .output(str(output_path), acodec='pcm_s16le', ac=1, ar=16000)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as e:
            stderr = e.stderr.decode('utf-8') if e.stderr else 'Unknown error'
            raise RuntimeError(f"音频片段提取失败: {stderr}")

    await asyncio.get_event_loop().run_in_executor(None, _extract)


async def get_audio_duration(audio_path: Path) -> float:
    """
    获取音频文件时长（秒）

    Args:
        audio_path: 音频文件路径

    Returns:
        float: 音频时长（秒）
    """
    if ffmpeg is None:
        raise RuntimeError("ffmpeg-python 模块未安装")

    def _get_duration():
        try:
            probe = ffmpeg.probe(str(audio_path))
            duration = probe.get('format', {}).get('duration')
            if duration:
                return float(duration)
            # 尝试从流中获取
            streams = probe.get('streams', [])
            for stream in streams:
                if stream.get('codec_type') in ('audio', 'video'):
                    duration = stream.get('duration')
                    if duration:
                        return float(duration)
            return 0.0
        except ffmpeg.Error:
            return 0.0

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_duration)
