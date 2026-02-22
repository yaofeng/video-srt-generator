# backend/app/services/vad.py
import asyncio
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

try:
    import numpy as np
except ImportError:
    logger.error("numpy 未安装")
    np = None

try:
    import librosa
except ImportError:
    logger.warning("librosa 未安装，将使用简化的 VAD 实现")
    librosa = None

try:
    import ffmpeg
except ImportError:
    logger.error("ffmpeg-python 未安装")
    ffmpeg = None


async def detect_speech_activity(
    audio_path: Path,
    threshold: float = 0.5
) -> List[Tuple[float, float]]:
    """
    检测语音活动

    Args:
        audio_path: 音频文件路径
        threshold: 语音概率阈值

    Returns:
        List[Tuple[float, float]]: [(start_time, end_time), ...] 语音片段列表
    """
    if np is None:
        raise RuntimeError("numpy 模块未安装")

    return await _energy_based_vad(audio_path, threshold)


async def _energy_based_vad(
    audio_path: Path,
    threshold: float
) -> List[Tuple[float, float]]:
    """
    基于能量的简单 VAD 算法

    使用短时能量（STE）进行语音活动检测
    """
    if np is None:
        raise RuntimeError("numpy 模块未安装")

    def _detect():
        # 加载音频
        if librosa is not None:
            y, sr = librosa.load(str(audio_path), sr=16000)
        else:
            # 如果没有 librosa，使用 soundfile 或 scipy
            try:
                import soundfile as sf
                y, sr = sf.read(str(audio_path))
                if len(y.shape) > 1:
                    y = y[:, 0]  # 取第一个声道
                if sr != 16000:
                    # 简单的重采样
                    from scipy import signal
                    number_of_samples = round(len(y) * float(16000) / sr)
                    y = signal.resample(y, number_of_samples)
                    sr = 16000
            except ImportError:
                raise RuntimeError("需要安装 librosa 或 soundfile 来处理音频文件")

        # 参数设置
        frame_length = int(0.025 * sr)  # 25ms 帧长
        hop_length = int(0.010 * sr)    # 10ms 帧移

        # 计算短时能量
        energy = []
        for i in range(0, len(y) - frame_length, hop_length):
            frame = y[i:i + frame_length]
            energy.append(np.sum(frame ** 2))

        energy = np.array(energy)

        # 归一化能量
        if len(energy) > 0 and np.max(energy) > 0:
            energy = energy / np.max(energy)

        # 阈值检测
        speech_frames = energy > threshold

        # 转换为时间片段
        segments = []
        start_time = None

        for i, is_speech in enumerate(speech_frames):
            time = i * hop_length / sr

            if is_speech and start_time is None:
                start_time = time
            elif not is_speech and start_time is not None:
                # 只有当静音持续超过一定时间时才切分
                segments.append((start_time, time))
                start_time = None

        # 添加最后一个片段
        if start_time is not None:
            segments.append((start_time, len(y) / sr))

        # 合并相邻的短片段
        if segments:
            merged = []
            current_start, current_end = segments[0]

            for start, end in segments[1:]:
                if start - current_end < 0.5:  # 间隔小于 0.5 秒则合并
                    current_end = end
                else:
                    merged.append((current_start, current_end))
                    current_start, current_end = start, end

            merged.append((current_start, current_end))
            segments = merged

        return segments

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

    # 检测语音活动
    speech_segments = await detect_speech_activity(audio_path, threshold=silence_threshold)

    if not speech_segments:
        # 如果没有检测到语音活动，使用整个音频
        speech_segments = [(0.0, await get_audio_duration(audio_path))]

    # 合并和切分片段
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

    Args:
        speech_segments: 语音片段列表 [(start, end), ...]
        min_duration: 最小时长
        max_duration: 最大时长

    Returns:
        List[Dict]: 合并后的片段信息
    """
    if not speech_segments:
        return []

    final_segments = []
    current_start = speech_segments[0][0]
    current_end = speech_segments[0][1]

    for i in range(1, len(speech_segments)):
        seg_start, seg_end = speech_segments[i]
        gap = seg_start - current_end

        # 检查当前累积时长
        current_duration = current_end - current_start

        # 如果当前片段已达到或超过最大时长，或者遇到长静音且当前片段满足最小时长
        if (current_duration >= max_duration) or \
           (gap >= 1.0 and current_duration >= min_duration):

            final_segments.append({
                'start_time': current_start,
                'end_time': current_end,
                'duration': current_end - current_start
            })
            current_start = seg_start
            current_end = seg_end
        else:
            # 继续累积
            current_end = seg_end

    # 添加最后一个片段
    if current_end > current_start:
        final_segments.append({
            'start_time': current_start,
            'end_time': current_end,
            'duration': current_end - current_start
        })

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
