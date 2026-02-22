# backend/app/services/audio.py
import asyncio
from pathlib import Path
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

try:
    import ffmpeg
except ImportError:
    logger.error("ffmpeg-python 未安装")
    ffmpeg = None


async def extract_audio(
    video_path: Path,
    output_path: Path,
    sample_rate: int = 16000
) -> Path:
    """
    从视频中提取音频

    Args:
        video_path: 视频文件路径
        output_path: 输出音频文件路径
        sample_rate: 采样率，默认 16000Hz

    Returns:
        Path: 输出音频文件路径

    Raises:
        RuntimeError: 音频提取失败
    """
    if ffmpeg is None:
        raise RuntimeError("ffmpeg-python 模块未安装")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 使用 ffmpeg 提取音频
    def _extract():
        try:
            (
                ffmpeg
                .input(str(video_path))
                .output(
                    str(output_path),
                    acodec='pcm_s16le',
                    ac=1,
                    ar=sample_rate
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            return output_path
        except ffmpeg.Error as e:
            stderr = e.stderr.decode('utf-8') if e.stderr else 'Unknown error'
            raise RuntimeError(f"音频提取失败: {stderr}")

    # 在线程池中执行 ffmpeg
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract)


async def get_video_duration(video_path: Path) -> float:
    """
    获取视频时长（秒）

    Args:
        video_path: 视频文件路径

    Returns:
        float: 视频时长（秒）

    Raises:
        RuntimeError: 无法获取视频时长
    """
    if ffmpeg is None:
        raise RuntimeError("ffmpeg-python 模块未安装")

    def _get_duration():
        try:
            probe = ffmpeg.probe(str(video_path))
            duration = probe.get('format', {}).get('duration')
            if duration is None:
                # 尝试从视频流获取
                streams = probe.get('streams', [])
                for stream in streams:
                    if stream.get('codec_type') == 'video':
                        duration = stream.get('duration')
                        if duration:
                            break
            if duration is None:
                raise RuntimeError("无法从视频文件中获取时长信息")
            return float(duration)
        except ffmpeg.Error as e:
            stderr = e.stderr.decode('utf-8') if e.stderr else 'Unknown error'
            raise RuntimeError(f"无法获取视频时长: {stderr}")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_duration)


async def get_audio_info(audio_path: Path) -> dict:
    """
    获取音频文件信息

    Args:
        audio_path: 音频文件路径

    Returns:
        dict: 包含采样率、声道数、时长等信息
    """
    if ffmpeg is None:
        raise RuntimeError("ffmpeg-python 模块未安装")

    def _get_info():
        try:
            probe = ffmpeg.probe(str(audio_path))
            info = {
                'duration': float(probe.get('format', {}).get('duration', 0)),
                'size': int(probe.get('format', {}).get('size', 0)),
                'bit_rate': int(probe.get('format', {}).get('bit_rate', 0))
            }

            # 获取音频流信息
            streams = probe.get('streams', [])
            for stream in streams:
                if stream.get('codec_type') == 'audio':
                    info['sample_rate'] = int(stream.get('sample_rate', 16000))
                    info['channels'] = int(stream.get('channels', 1))
                    info['codec'] = stream.get('codec_name', 'unknown')
                    break

            return info
        except ffmpeg.Error as e:
            stderr = e.stderr.decode('utf-8') if e.stderr else 'Unknown error'
            raise RuntimeError(f"无法获取音频信息: {stderr}")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_info)


async def convert_audio_format(
    input_path: Path,
    output_path: Path,
    sample_rate: int = 16000,
    channels: int = 1,
    codec: str = 'pcm_s16le'
) -> Path:
    """
    转换音频格式

    Args:
        input_path: 输入音频文件路径
        output_path: 输出音频文件路径
        sample_rate: 采样率
        channels: 声道数
        codec: 编码格式

    Returns:
        Path: 输出音频文件路径
    """
    if ffmpeg is None:
        raise RuntimeError("ffmpeg-python 模块未安装")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    def _convert():
        try:
            (
                ffmpeg
                .input(str(input_path))
                .output(
                    str(output_path),
                    acodec=codec,
                    ac=channels,
                    ar=sample_rate
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            return output_path
        except ffmpeg.Error as e:
            stderr = e.stderr.decode('utf-8') if e.stderr else 'Unknown error'
            raise RuntimeError(f"音频格式转换失败: {stderr}")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _convert)
