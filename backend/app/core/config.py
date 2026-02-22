# backend/app/core/config.py
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "Video SRT Generator"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 路径配置
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "outputs"
    CHECKPOINTS_DIR: Path = Path("/home/ubuntu/workspace/checkpoints")

    # 模型配置
    FSMN_VAD_MODEL: str = "fsmn-vad"
    QWEN_ASR_MODEL: str = "Qwen/Qwen3-ASR-1.7B"
    QWEN_ALIGNER_MODEL: str = "Qwen/Qwen3-ForcedAligner-0.6B"

    # 音频切分配置
    SEGMENT_MIN_DURATION: int = 180
    SEGMENT_MAX_DURATION: int = 300
    VAD_SILENCE_THRESHOLD: float = 0.5

    # 字幕生成配置
    SUBTITLE_MIN_DURATION: float = 2.0
    SUBTITLE_MAX_DURATION: float = 8.0
    SUBTITLE_MERGE_THRESHOLD: float = 1.5

    # 重试配置
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_BASE_DELAY: float = 1.0
    RETRY_MAX_DELAY: float = 10.0

    # 文件清理配置
    AUTO_CLEANUP: bool = True
    COMPLETED_RETENTION_HOURS: int = 24
    FAILED_RETENTION_HOURS: int = 6

    # CORS 配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://172.16.2.68:3000",
        "http://172.16.2.68:5173",
        "http://172.16.2.68:8000",
    ]

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
