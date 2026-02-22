# backend/app/api/config.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class ConfigResponse(BaseModel):
    """配置响应"""
    # 音频切分配置
    segment_min_duration: int = Field(description="最小片段时长（秒）")
    segment_max_duration: int = Field(description="最大片段时长（秒）")
    vad_silence_threshold: float = Field(description="静音阈值（秒）")

    # 字幕生成配置
    subtitle_min_duration: float = Field(description="最短字幕时长（秒）")
    subtitle_max_duration: float = Field(description="最长字幕时长（秒）")
    subtitle_merge_threshold: float = Field(description="短字幕合并阈值（秒）")

    # 重试配置
    max_retry_attempts: int = Field(description="最大重试次数")
    retry_base_delay: float = Field(description="重试基础延迟（秒）")
    retry_max_delay: float = Field(description="重试最大延迟（秒）")

    # 文件清理配置
    auto_cleanup: bool = Field(description="自动清理文件")
    completed_retention_hours: int = Field(description="已完成任务保留时长（小时）")
    failed_retention_hours: int = Field(description="失败任务保留时长（小时）")


class ConfigUpdate(BaseModel):
    """配置更新"""
    segment_min_duration: Optional[int] = Field(None, ge=30, le=600, description="最小片段时长（秒）")
    segment_max_duration: Optional[int] = Field(None, ge=60, le=1800, description="最大片段时长（秒）")
    vad_silence_threshold: Optional[float] = Field(None, ge=0.1, le=5.0, description="静音阈值（秒）")

    subtitle_min_duration: Optional[float] = Field(None, ge=0.5, le=10.0, description="最短字幕时长（秒）")
    subtitle_max_duration: Optional[float] = Field(None, ge=1.0, le=30.0, description="最长字幕时长（秒）")
    subtitle_merge_threshold: Optional[float] = Field(None, ge=0.1, le=5.0, description="短字幕合并阈值（秒）")

    max_retry_attempts: Optional[int] = Field(None, ge=1, le=10, description="最大重试次数")
    retry_base_delay: Optional[float] = Field(None, ge=0.5, le=60.0, description="重试基础延迟（秒）")
    retry_max_delay: Optional[float] = Field(None, ge=1.0, le=300.0, description="重试最大延迟（秒）")

    auto_cleanup: Optional[bool] = Field(None, description="自动清理文件")
    completed_retention_hours: Optional[int] = Field(None, ge=1, le=168, description="已完成任务保留时长（小时）")
    failed_retention_hours: Optional[int] = Field(None, ge=1, le=72, description="失败任务保留时长（小时）")


@router.get("/", response_model=ConfigResponse)
async def get_config():
    """获取当前配置"""
    return ConfigResponse(
        segment_min_duration=settings.SEGMENT_MIN_DURATION,
        segment_max_duration=settings.SEGMENT_MAX_DURATION,
        vad_silence_threshold=settings.VAD_SILENCE_THRESHOLD,

        subtitle_min_duration=settings.SUBTITLE_MIN_DURATION,
        subtitle_max_duration=settings.SUBTITLE_MAX_DURATION,
        subtitle_merge_threshold=settings.SUBTITLE_MERGE_THRESHOLD,

        max_retry_attempts=settings.MAX_RETRY_ATTEMPTS,
        retry_base_delay=settings.RETRY_BASE_DELAY,
        retry_max_delay=settings.RETRY_MAX_DELAY,

        auto_cleanup=settings.AUTO_CLEANUP,
        completed_retention_hours=settings.COMPLETED_RETENTION_HOURS,
        failed_retention_hours=settings.FAILED_RETENTION_HOURS,
    )


@router.post("/")
async def update_config(config: ConfigUpdate):
    """更新配置"""
    # 更新配置（注意：这只是临时更新，重启后会恢复原值）
    # 要永久更新配置，应该修改 .env 文件或配置文件

    updated_fields = []

    if config.segment_min_duration is not None:
        settings.SEGMENT_MIN_DURATION = config.segment_min_duration
        updated_fields.append("segment_min_duration")

    if config.segment_max_duration is not None:
        settings.SEGMENT_MAX_DURATION = config.segment_max_duration
        updated_fields.append("segment_max_duration")

    if config.vad_silence_threshold is not None:
        settings.VAD_SILENCE_THRESHOLD = config.vad_silence_threshold
        updated_fields.append("vad_silence_threshold")

    if config.subtitle_min_duration is not None:
        settings.SUBTITLE_MIN_DURATION = config.subtitle_min_duration
        updated_fields.append("subtitle_min_duration")

    if config.subtitle_max_duration is not None:
        settings.SUBTITLE_MAX_DURATION = config.subtitle_max_duration
        updated_fields.append("subtitle_max_duration")

    if config.subtitle_merge_threshold is not None:
        settings.SUBTITLE_MERGE_THRESHOLD = config.subtitle_merge_threshold
        updated_fields.append("subtitle_merge_threshold")

    if config.max_retry_attempts is not None:
        settings.MAX_RETRY_ATTEMPTS = config.max_retry_attempts
        updated_fields.append("max_retry_attempts")

    if config.retry_base_delay is not None:
        settings.RETRY_BASE_DELAY = config.retry_base_delay
        updated_fields.append("retry_base_delay")

    if config.retry_max_delay is not None:
        settings.RETRY_MAX_DELAY = config.retry_max_delay
        updated_fields.append("retry_max_delay")

    if config.auto_cleanup is not None:
        settings.AUTO_CLEANUP = config.auto_cleanup
        updated_fields.append("auto_cleanup")

    if config.completed_retention_hours is not None:
        settings.COMPLETED_RETENTION_HOURS = config.completed_retention_hours
        updated_fields.append("completed_retention_hours")

    if config.failed_retention_hours is not None:
        settings.FAILED_RETENTION_HOURS = config.failed_retention_hours
        updated_fields.append("failed_retention_hours")

    logger.info(f"配置已更新: {', '.join(updated_fields)}")

    return {
        "message": "配置更新成功",
        "updated_fields": updated_fields,
        "note": "注意：配置修改仅在服务运行期间有效，重启后将恢复为原值。要永久修改配置，请更新 .env 文件。"
    }
