# backend/app/services/video.py
"""视频处理服务：缩略图生成、元信息提取"""
import subprocess
from pathlib import Path
from typing import Optional, Dict
import logging
import json

logger = logging.getLogger(__name__)


def generate_thumbnail(video_path: Path, output_path: Path, position: str = "10%") -> Path:
    """
    使用 ffmpeg 从视频中提取一帧作为缩略图

    Args:
        video_path: 视频文件路径
        output_path: 输出缩略图路径
        position: 提取位置，支持百分比（如 "10%"）或时间戳（如 "00:00:05"）

    Returns:
        Path: 生成的缩略图路径
    """
    try:
        # 如果输出文件已存在，先删除
        if output_path.exists():
            output_path.unlink()

        # 构建 ffmpeg 命令
        # 使用 selectfilter 在指定位置提取一帧
        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-vf', f"select=eq(n\\,0)" if position == "first" else f"thumbnail,scale=320:-1",
            '-frames:v', '1',
            '-y',
            str(output_path)
        ]

        # 如果是百分比位置，先获取视频时长
        if '%' in position:
            duration = get_video_duration(video_path)
            if duration > 0:
                seek_time = duration * float(position.replace('%', '')) / 100
                cmd = [
                    'ffmpeg', '-ss', str(seek_time), '-i', str(video_path),
                    '-vframes', '1',
                    '-vf', 'scale=320:-1',
                    '-y',
                    str(output_path)
                ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            logger.error(f"ffmpeg 执行失败：{result.stderr}")
            # 如果缩略图生成失败，创建一个空白占位图
            _create_placeholder_thumbnail(output_path)

        return output_path

    except subprocess.TimeoutExpired:
        logger.error(f"缩略图生成超时：{video_path}")
        _create_placeholder_thumbnail(output_path)
        return output_path
    except Exception as e:
        logger.error(f"缩略图生成失败：{e}")
        _create_placeholder_thumbnail(output_path)
        return output_path


def _create_placeholder_thumbnail(output_path: Path) -> None:
    """创建空白占位缩略图"""
    try:
        cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', 'color=c=black:s=320x180:d=1',
            '-frames:v', '1',
            '-y',
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True, timeout=10)
    except Exception as e:
        logger.error(f"占位图创建失败：{e}")


def get_video_info(video_path: Path) -> Dict:
    """
    获取视频元信息

    Returns:
        Dict: {
            'duration': float,  # 时长（秒）
            'width': int,  # 宽度
            'height': int,  # 高度
            'codec': str,  # 编码格式
            'fps': float,  # 帧率
        }
    """
    try:
        probe = subprocess.run(
            [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams',
                str(video_path)
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if probe.returncode != 0:
            logger.error(f"ffprobe 执行失败")
            return {}

        data = json.loads(probe.stdout)
        video_stream = None
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                video_stream = stream
                break

        if not video_stream:
            return {}

        format_info = data.get('format', {})

        return {
            'duration': float(format_info.get('duration', 0) or video_stream.get('duration', 0) or 0),
            'width': int(video_stream.get('width', 0)),
            'height': int(video_stream.get('height', 0)),
            'codec': video_stream.get('codec_name', ''),
            'fps': float(eval(video_stream.get('r_frame_rate', '0/1')) or 0),
        }

    except subprocess.TimeoutExpired:
        logger.error(f"视频信息获取超时：{video_path}")
        return {}
    except Exception as e:
        logger.error(f"视频信息获取失败：{e}")
        return {}


def get_video_duration(video_path: Path) -> float:
    """获取视频时长（秒）"""
    info = get_video_info(video_path)
    return info.get('duration', 0.0)
