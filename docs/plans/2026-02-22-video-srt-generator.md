# 视频字幕生成系统实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 构建一个基于 FastAPI + Vue3 的视频字幕生成系统，使用 fsmn-vad 进行语音活动检测，Qwen3-ASR-1.7B 进行语音识别，自动生成 SRT 字幕文件。

**架构:** 单体应用架构，FastAPI 后端提供 API 和静态文件服务，Vue3 前端通过 SSE 接收实时进度，使用 AI 模型进行本地推理。

**技术栈:**
- 后端: FastAPI + uv + SQLite + ffmpeg + fsmn-vad + Qwen3-ASR
- 前端: Vue 3 + Bun + TailwindCSS + Pinia + Vue Router

---

## Phase 1: 项目初始化

### Task 1: 创建项目目录结构

**Files:**
- Create: `backend/`, `frontend/`, `docs/`, `scripts/`

**Step 1: 创建后端目录结构**

```bash
cd /home/ubuntu/workspace/video-srt-generator
mkdir -p backend/app/{api,core,models,services}
mkdir -p backend/{uploads,outputs,static}
mkdir -p backend/tests
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/core/__init__.py
touch backend/app/models/__init__.py
touch backend/app/services/__init__.py
```

**Step 2: 创建前端目录结构**

```bash
mkdir -p frontend/src/{components,views,router,stores,assets,styles}
mkdir -p frontend/public
```

**Step 3: 验证目录结构**

```bash
tree -L 3 -I 'node_modules|.venv|__pycache__'
```

Expected: 目录树显示完整的项目结构

**Step 4: Commit**

```bash
git add .
git commit -m "feat: initialize project directory structure"
```

---

### Task 2: 初始化后端项目

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/app/core/config.py`

**Step 1: 创建 pyproject.toml**

```toml
# backend/pyproject.toml
[project]
name = "video-srt-generator"
version = "1.0.0"
description = "Video subtitle generation system"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "sqlalchemy>=2.0.0",
    "aiosqlite>=0.20.0",
    "python-multipart>=0.0.12",
    "ffmpeg-python>=0.2.0",
    "numpy>=1.24.0",
    "torch>=2.0.0",
    "transformers>=4.40.0",
    "accelerate>=0.30.0",
    "faster-whisper>=0.10.0",
    "pydub>=0.25.0",
    "httpx>=0.27.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
]
```

**Step 2: 创建 .env.example**

```bash
# backend/.env.example
APP_NAME=Video SRT Generator
DEBUG=false
HOST=0.0.0.0
PORT=8000

CHECKPOINTS_DIR=/home/ubuntu/workspace/checkpoints
SEGMENT_MIN_DURATION=180
SEGMENT_MAX_DURATION=300
SUBTITLE_MIN_DURATION=2.0
SUBTITLE_MAX_DURATION=8.0
SUBTITLE_MERGE_THRESHOLD=1.5
MAX_RETRY_ATTEMPTS=3
COMPLETED_RETENTION_HOURS=24
FAILED_RETENTION_HOURS=6

CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

**Step 3: 创建配置模块**

```python
# backend/app/core/config.py
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

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
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"

settings = Settings()
```

**Step 4: 同步依赖**

```bash
cd backend
uv sync
```

Expected: 依赖安装成功，无错误

**Step 5: Commit**

```bash
git add backend/
git commit -m "feat: initialize backend project with dependencies"
```

---

### Task 3: 初始化前端项目

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`
- Create: `frontend/tailwind.config.js`

**Step 1: 创建 package.json**

```json
{
  "name": "video-srt-generator-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.5.0",
    "vue-router": "^4.5.0",
    "pinia": "^2.2.0",
    "@vueuse/core": "^11.0.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^6.0.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

**Step 2: 创建 vite.config.js**

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

**Step 3: 创建 tailwind.config.js**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#0a0e1a',
        secondary: '#0f172a',
        brand: {
          blue: '#3b82f6',
          cyan: '#06b6d4',
          orange: '#f97316',
          green: '#10b981'
        }
      },
      animation: {
        'pulse-laser': 'laser-pulse 2s infinite',
      },
      keyframes: {
        'laser-pulse': {
          '0%': { boxShadow: '0 0 0 0 rgba(59, 130, 246, 0.7)' },
          '70%': { boxShadow: '0 0 0 10px rgba(59, 130, 246, 0)' },
          '100%': { boxShadow: '0 0 0 0 rgba(59, 130, 246, 0)' },
        }
      }
    },
  },
  plugins: [],
}
```

**Step 4: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Video SRT Generator</title>
</head>
<body class="bg-primary text-text-primary">
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
```

**Step 5: 创建 main.js**

```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

**Step 6: 创建 App.vue**

```vue
<template>
  <div id="app" class="min-h-screen bg-gradient-to-br from-primary to-secondary">
    <RouterView />
  </div>
</template>

<script setup>
import { RouterView } from 'vue-router'
</script>
```

**Step 7: 创建样式文件**

```css
/* frontend/src/styles/main.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg-primary: #0a0e1a;
  --bg-secondary: #0f172a;
  --brand-blue: #3b82f6;
  --brand-cyan: #06b6d4;
  --brand-orange: #f97316;
  --brand-green: #10b981;
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
}

body {
  font-family: system-ui, -apple-system, sans-serif;
}

.glass {
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.glow {
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.3);
}
```

**Step 8: 安装依赖**

```bash
cd frontend
bun install
```

Expected: 依赖安装成功

**Step 9: Commit**

```bash
git add frontend/
git commit -m "feat: initialize frontend project with Vue3 + TailwindCSS"
```

---

## Phase 2: 后端核心功能

### Task 4: 创建数据库模型和连接

**Files:**
- Create: `backend/app/core/database.py`
- Create: `backend/app/models/task.py`
- Create: `backend/app/models/subtitle.py`
- Create: `backend/app/models/segment.py`
- Create: `backend/app/models/log.py`

**Step 1: 创建数据库连接模块**

```python
# backend/app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from pathlib import Path
from .config import settings

# 确保数据库目录存在
settings.BASE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite+aiosqlite:///{settings.BASE_DIR}/srt_generator.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False}
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

**Step 2: 创建任务模型**

```python
# backend/app/models/task.py
from sqlalchemy import Column, String, Integer, Float, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from ..core.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending/processing/completed/failed
    progress = Column(Integer, default=0)
    current_step = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # 关系
    subtitles = relationship("Subtitle", back_populates="task", cascade="all, delete-orphan")
    segments = relationship("Segment", back_populates="task", cascade="all, delete-orphan")
    logs = relationship("Log", back_populates="task", cascade="all, delete-orphan")
```

**Step 3: 创建字幕模型**

```python
# backend/app/models/subtitle.py
from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from ..core.database import Base

class Subtitle(Base):
    __tablename__ = "subtitles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)

    # 关系
    task = relationship("Task", back_populates="subtitles")
```

**Step 4: 创建片段模型**

```python
# backend/app/models/segment.py
from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from ..core.database import Base

class Segment(Base):
    __tablename__ = "segments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    audio_path = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending/processing/completed/failed
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # 关系
    task = relationship("Task", back_populates="segments")
```

**Step 5: 创建日志模型**

```python
# backend/app/models/log.py
from sqlalchemy import Column, String, Text, ForeignKey, Integer, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base

class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    level = Column(String, nullable=False)  # info/warning/error
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # 关系
    task = relationship("Task", back_populates="logs")
```

**Step 6: 更新 models/__init__.py**

```python
# backend/app/models/__init__.py
from .task import Task
from .subtitle import Subtitle
from .segment import Segment
from .log import Log

__all__ = ["Task", "Subtitle", "Segment", "Log"]
```

**Step 7: 测试数据库初始化**

```bash
cd backend
uv run python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
```

Expected: 数据库文件创建成功，无错误

**Step 8: Commit**

```bash
git add backend/app/models/ backend/app/core/database.py
git commit -m "feat: add database models and connection"
```

---

### Task 5: 创建 FastAPI 主应用

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/api/deps.py`

**Step 1: 创建依赖注入模块**

```python
# backend/app/api/deps.py
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db

async def get_db_session():
    """获取数据库会话"""
    async for session in get_db():
        yield session
```

**Step 2: 创建主应用**

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .core.config import settings
from .core.database import init_db
from pathlib import Path

# 确保必要的目录存在
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    await init_db()
    yield
    # 关闭时的清理工作

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务（生产环境）
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

# 注册路由
from .api import tasks, upload

app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(upload.router, prefix="/api", tags=["upload"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.VERSION}
```

**Step 3: 创建占位路由**

```python
# backend/app/api/tasks.py
from fastapi import APIRouter, HTTPException
from ..models.task import Task

router = APIRouter()

@router.get("/")
async def list_tasks():
    return {"tasks": []}

@router.get("/{task_id}")
async def get_task(task_id: str):
    return {"task_id": task_id}
```

```python
# backend/app/api/upload.py
from fastapi import APIRouter, UploadFile

router = APIRouter()

@router.post("/upload")
async def upload_video(file: UploadFile):
    return {"filename": file.filename}
```

**Step 4: 测试应用启动**

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Expected: 服务器启动在 http://localhost:8000，访问 /health 返回 ok

**Step 5: 测试 API**

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","version":"1.0.0"}`

**Step 6: Commit**

```bash
git add backend/app/main.py backend/app/api/
git commit -m "feat: add FastAPI main application with basic routes"
```

---

### Task 6: 实现文件上传功能

**Files:**
- Create: `backend/app/services/file_manager.py`
- Modify: `backend/app/api/upload.py`

**Step 1: 创建文件管理服务**

```python
# backend/app/services/file_manager.py
import aiofiles
import os
from pathlib import Path
from fastapi import UploadFile, HTTPException
from ..core.config import settings
import uuid

ALLOWED_VIDEO_TYPES = [
    "video/mp4",
    "video/avi",
    "video/x-msvideo",
    "video/mkv",
    "video/x-matroska",
    "video/quicktime",
    "video/x-ms-wmv",
    "video/webm"
]

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB

async def save_upload_file(upload_file: UploadFile) -> tuple[str, Path]:
    """
    保存上传的文件

    Returns:
        tuple: (task_id, file_path)
    """
    # 验证文件类型
    if upload_file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {upload_file.content_type}"
        )

    # 生成任务 ID 和文件路径
    task_id = str(uuid.uuid4())
    file_extension = Path(upload_file.filename).suffix
    file_path = settings.UPLOAD_DIR / f"{task_id}{file_extension}"

    # 保存文件
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            content = await upload_file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"文件过大，最大支持 {MAX_FILE_SIZE // (1024**3)}GB"
                )
            await f.write(content)
    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    return task_id, file_path

async def delete_file(file_path: Path) -> bool:
    """删除文件"""
    try:
        if file_path.exists():
            os.remove(file_path)
        return True
    except Exception:
        return False
```

**Step 2: 实现上传 API**

```python
# backend/app/api/upload.py
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.task import Task
from ..services.file_manager import save_upload_file
from .deps import get_db_session
from datetime import datetime

router = APIRouter()

@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session)
):
    """上传视频文件并创建任务"""
    task_id, file_path = await save_upload_file(file)

    # 创建任务记录
    task = Task(
        id=task_id,
        filename=file.filename,
        file_path=str(file_path),
        file_size=file_path.stat().st_size,
        status="pending"
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    return {
        "task_id": task_id,
        "filename": file.filename,
        "status": "pending",
        "created_at": task.created_at
    }
```

**Step 3: 测试上传功能**

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@test.mp4" \
  -H "Content-Type: multipart/form-data"
```

Expected: 返回任务 ID 和文件信息

**Step 4: Commit**

```bash
git add backend/app/services/file_manager.py backend/app/api/upload.py
git commit -m "feat: add file upload functionality"
```

---

### Task 7: 实现音频提取服务

**Files:**
- Create: `backend/app/services/audio.py`
- Create: `backend/tests/test_audio.py`

**Step 1: 编写测试**

```python
# backend/tests/test_audio.py
import pytest
from pathlib import Path
from app.services.audio import extract_audio

@pytest.mark.asyncio
async def test_extract_audio():
    """测试音频提取"""
    # 准备测试视频文件
    video_path = Path("tests/fixtures/test_video.mp4")
    output_path = Path("tests/fixtures/test_audio.wav")

    # 调用提取函数
    result = await extract_audio(video_path, output_path)

    # 验证结果
    assert result == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0

    # 清理
    if output_path.exists():
        output_path.unlink()
```

**Step 2: 运行测试验证失败**

```bash
cd backend
pytest tests/test_audio.py -v
```

Expected: FAIL - ModuleNotFoundError 或函数不存在

**Step 3: 实现音频提取服务**

```python
# backend/app/services/audio.py
import asyncio
from pathlib import Path
import ffmpeg
from ..core.config import settings

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
    """
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
            raise RuntimeError(f"音频提取失败: {e.stderr.decode()}")

    # 在线程池中执行 ffmpeg
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _extract)

    return output_path

async def get_video_duration(video_path: Path) -> float:
    """获取视频时长（秒）"""
    def _get_duration():
        try:
            probe = ffmpeg.probe(str(video_path))
            return float(probe['format']['duration'])
        except ffmpeg.Error as e:
            raise RuntimeError(f"无法获取视频时长: {e.stderr.decode()}")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_duration)
```

**Step 4: 运行测试验证通过**

```bash
cd backend
pytest tests/test_audio.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/audio.py backend/tests/test_audio.py
git commit -f "feat: add audio extraction service"
```

---

### Task 8: 实现 VAD 服务

**Files:**
- Create: `backend/app/services/vad.py`
- Create: `backend/tests/test_vad.py`

**Step 1: 编写测试**

```python
# backend/tests/test_vad.py
import pytest
from pathlib import Path
from app.services.vad import detect_speech_activity, split_audio_by_vad

@pytest.mark.asyncio
async def test_detect_speech_activity():
    """测试语音活动检测"""
    audio_path = Path("tests/fixtures/test_audio.wav")

    # 调用检测函数
    segments = await detect_speech_activity(audio_path)

    # 验证结果
    assert isinstance(segments, list)
    assert len(segments) > 0
    assert all(isinstance(seg, tuple) and len(seg) == 2 for seg in segments)

@pytest.mark.asyncio
async def test_split_audio_by_vad():
    """测试音频切分"""
    audio_path = Path("tests/fixtures/test_audio.wav")
    output_dir = Path("tests/fixtures/segments")

    # 调用切分函数
    segments = await split_audio_by_vad(
        audio_path,
        output_dir,
        min_duration=180,
        max_duration=300
    )

    # 验证结果
    assert isinstance(segments, list)
    assert all(s['end_time'] - s['start_time'] >= 180 for s in segments)
    assert all(s['end_time'] - s['start_time'] <= 300 for s in segments)
```

**Step 2: 运行测试验证失败**

```bash
cd backend
pytest tests/test_vad.py -v
```

Expected: FAIL - 模块或函数不存在

**Step 3: 实现 VAD 服务**

```python
# backend/app/services/vad.py
import asyncio
from pathlib import Path
from typing import List, Dict
import numpy as np
import torch
from transformers import AutoModelForAudioClassification, AutoFeatureExtractor
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class VADModel:
    """VAD 模型单例"""
    _model = None
    _feature_extractor = None
    _device = None

    @classmethod
    def get_model(cls):
        """获取模型实例"""
        if cls._model is None:
            model_path = settings.CHECKPOINTS_DIR / settings.FSMN_VAD_MODEL
            if not model_path.exists():
                logger.warning(f"VAD 模型不存在，使用默认配置")
                # 这里可以实现自动下载逻辑
                cls._device = "cpu"
                cls._model = None
            else:
                cls._device = "cuda" if torch.cuda.is_available() else "cpu"
                cls._model = AutoModelForAudioClassification.from_pretrained(
                    str(model_path),
                    torch_dtype=torch.float16 if cls._device == "cuda" else torch.float32
                ).to(cls._device)
                cls._feature_extractor = AutoFeatureExtractor.from_pretrained(str(model_path))
        return cls._model, cls._feature_extractor, cls._device

async def detect_speech_activity(
    audio_path: Path,
    threshold: float = 0.5
) -> List[tuple[float, float]]:
    """
    检测语音活动

    Args:
        audio_path: 音频文件路径
        threshold: 语音概率阈值

    Returns:
        List[tuple]: [(start_time, end_time), ...]
    """
    model, feature_extractor, device = await asyncio.get_event_loop().run_in_executor(
        None, VADModel.get_model
    )

    if model is None:
        # 如果没有模型，使用简单的能量检测
        return await _simple_vad(audio_path, threshold)

    # 这里实现基于模型的 VAD
    # 简化版本：使用能量检测
    return await _simple_vad(audio_path, threshold)

async def _simple_vad(
    audio_path: Path,
    threshold: float
) -> List[tuple[float, float]]:
    """
    简单的基于能量的 VAD
    """
    import librosa

    def _detect():
        # 加载音频
        y, sr = librosa.load(str(audio_path), sr=16000)

        # 计算能量
        frame_length = int(0.025 * sr)  # 25ms
        hop_length = int(0.010 * sr)    # 10ms

        # 计算短时能量
        energy = np.array([
            np.sum(y[i:i+frame_length]**2)
            for i in range(0, len(y) - frame_length, hop_length)
        ])

        # 归一化
        energy = energy / (np.max(energy) + 1e-8)

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
                segments.append((start_time, time))
                start_time = None

        if start_time is not None:
            segments.append((start_time, len(y) / sr))

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
        min_duration: 最小片段时长（秒）
        max_duration: 最大片段时长（秒）
        silence_threshold: 静音阈值（秒）

    Returns:
        List[Dict]: 切分后的片段信息
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 检测语音活动
    speech_segments = await detect_speech_activity(audio_path)

    # 合并和切分片段
    final_segments = []
    current_start = speech_segments[0][0] if speech_segments else 0

    for i, (seg_start, seg_end) in enumerate(speech_segments):
        # 检查与上一片段的间隔
        if i > 0:
            prev_end = speech_segments[i-1][1]
            gap = seg_start - prev_end

            # 如果当前片段累积超过 max_duration，或在静音处切分
            current_duration = seg_end - current_start

            if current_duration >= max_duration or (
                gap >= silence_threshold and
                (seg_end - current_start) >= min_duration
            ):
                final_segments.append({
                    'start_time': current_start,
                    'end_time': seg_end,
                    'duration': seg_end - current_start
                })
                current_start = seg_start

    # 添加最后一个片段
    if speech_segments:
        final_segments.append({
            'start_time': current_start,
            'end_time': speech_segments[-1][1],
            'duration': speech_segments[-1][1] - current_start
        })

    # 使用 ffmpeg 切分音频
    for i, seg in enumerate(final_segments):
        output_path = output_dir / f"segment_{i:04d}.wav"
        await _extract_segment(audio_path, seg['start_time'], seg['end_time'], output_path)
        seg['audio_path'] = str(output_path)
        seg['index'] = i

    return final_segments

async def _extract_segment(
    audio_path: Path,
    start_time: float,
    end_time: float,
    output_path: Path
):
    """提取音频片段"""
    import ffmpeg

    def _extract():
        duration = end_time - start_time
        (
            ffmpeg
            .input(str(audio_path), ss=start_time, t=duration)
            .output(str(output_path), acodec='pcm_s16le', ac=1, ar=16000)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )

    await asyncio.get_event_loop().run_in_executor(None, _extract)
```

**Step 4: 运行测试验证通过**

```bash
cd backend
pytest tests/test_vad.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/vad.py backend/tests/test_vad.py
git commit -m "feat: add VAD service for audio segmentation"
```

---

### Task 9: 实现 ASR 服务

**Files:**
- Create: `backend/app/services/asr.py`
- Create: `backend/tests/test_asr.py`

**Step 1: 编写测试**

```python
# backend/tests/test_asr.py
import pytest
from pathlib import Path
from app.services.asr import transcribe_audio

@pytest.mark.asyncio
async def test_transcribe_audio():
    """测试语音识别"""
    audio_path = Path("tests/fixtures/test_audio.wav")

    # 调用识别函数
    result = await transcribe_audio(audio_path)

    # 验证结果
    assert 'text' in result
    assert 'segments' in result
    assert len(result['segments']) > 0
    assert all('start' in s and 'end' in s and 'text' in s for s in result['segments'])
```

**Step 2: 运行测试验证失败**

```bash
cd backend
pytest tests/test_asr.py -v
```

Expected: FAIL

**Step 3: 实现 ASR 服务**

```python
# backend/app/services/asr.py
import asyncio
from pathlib import Path
from typing import List, Dict
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class ASRModel:
    """ASR 模型单例"""
    _model = None
    _processor = None
    _device = None

    @classmethod
    def get_model(cls):
        """获取模型实例"""
        if cls._model is None:
            model_path = settings.CHECKPOINTS_DIR / cls._QWEN_ASR_MODEL

            if not model_path.exists():
                raise RuntimeError(f"ASR 模型不存在: {model_path}")

            cls._device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if cls._device == "cuda" else torch.float32

            cls._model = AutoModelForSpeechSeq2Seq.from_pretrained(
                str(model_path),
                torch_dtype=dtype,
                low_cpu_mem_usage=True
            ).to(cls._device).eval()

            cls._processor = AutoProcessor.from_pretrained(str(model_path))

            if cls._device == "cuda":
                cls._model = torch.compile(cls._model)

        return cls._model, cls._processor, cls._device

async def transcribe_audio(
    audio_path: Path,
    language: str = "zh",
    task: str = "transcribe"
) -> Dict:
    """
    语音识别

    Args:
        audio_path: 音频文件路径
        language: 语言代码
        task: 任务类型 (transcribe/translate)

    Returns:
        Dict: {
            'text': str,
            'segments': [
                {'start': float, 'end': float, 'text': str},
                ...
            ]
        }
    """
    model, processor, device = await asyncio.get_event_loop().run_in_executor(
        None, ASRModel.get_model
    )

    def _transcribe():
        import torchaudio

        # 加载音频
        waveform, sample_rate = torchaudio.load(str(audio_path))

        # 重采样到 16000Hz
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)
            sample_rate = 16000

        # 准备输入
        inputs = processor(
            waveform.squeeze().numpy(),
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
                do_sample=False
            )

        # 解码结果
        decoded = processor.decode(output[0], skip_special_tokens=True)

        # 提取时间戳
        # Qwen3-ASR 返回 token 级别的时间戳
        # 这里需要根据实际输出格式调整
        segments = _extract_segments_with_timestamps(
            decoded,
            output,
            processor.tokenizer
        )

        return {
            'text': decoded.get('text', ''),
            'segments': segments
        }

    return await asyncio.get_event_loop().run_in_executor(None, _transcribe)

def _extract_segments_with_timestamps(
    decoded: Dict,
    output: torch.Tensor,
    tokenizer
) -> List[Dict]:
    """
    从模型输出中提取带时间戳的片段

    Qwen3-ASR 返回 token 级别的时间戳，需要转换
    """
    segments = []

    if 'tokens' not in decoded or 'timestamp' not in decoded:
        return segments

    tokens = decoded['tokens']
    timestamps = decoded['timestamp']

    # 这里需要根据 Qwen3-ASR 的实际输出格式来解析
    # 以下是通用逻辑

    current_segment = None
    chunk_tokens = []
    chunk_start = None

    for i, (token, timestamp) in enumerate(zip(tokens, timestamps)):
        chunk_tokens.append(token)

        if chunk_start is None:
            chunk_start = timestamp[0]

        # 检测句子边界
        is_sentence_end = (
            token in [tokenizer.eos_token_id] or
            token == tokenizer.encode('。')[0] or
            token == tokenizer.encode('？')[0] or
            token == tokenizer.encode('！')[0]
        )

        if is_sentence_end or (timestamp[1] - chunk_start > 8):
            # 结束当前片段
            text = tokenizer.decode(chunk_tokens)
            segments.append({
                'start': chunk_start,
                'end': timestamp[1],
                'text': text.strip()
            })

            chunk_tokens = []
            chunk_start = None

    # 处理剩余的 tokens
    if chunk_tokens and timestamps:
        text = tokenizer.decode(chunk_tokens)
        segments.append({
            'start': timestamps[0][0] if timestamps else 0,
            'end': timestamps[-1][1] if timestamps else 0,
            'text': text.strip()
        })

    return segments
```

**Step 4: 更新配置**

```python
# backend/app/services/asr.py 中添加
ASRModel._QWEN_ASR_MODEL = "Qwen/Qwen3-ASR-1.7B"
```

**Step 5: 运行测试验证通过**

```bash
cd backend
pytest tests/test_asr.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add backend/app/services/asr.py backend/tests/test_asr.py
git commit -m "feat: add ASR service using Qwen3-ASR"
```

---

### Task 10: 实现 SRT 生成服务

**Files:**
- Create: `backend/app/services/srt.py`
- Create: `backend/tests/test_srt.py`

**Step 1: 编写测试**

```python
# backend/tests/test_srt.py
import pytest
from pathlib import Path
from app.services.srt import generate_srt, merge_short_subtitles

@pytest.mark.asyncio
async def test_generate_srt():
    """测试 SRT 生成"""
    segments = [
        {'start': 0.0, 'end': 2.5, 'text': '第一条字幕'},
        {'start': 3.0, 'end': 5.5, 'text': '第二条字幕'},
    ]
    output_path = Path("tests/fixtures/test_output.srt")

    # 调用生成函数
    await generate_srt(segments, output_path)

    # 验证结果
    assert output_path.exists()
    content = output_path.read_text(encoding='utf-8')
    assert '1' in content
    assert '00:00:00,000' in content
    assert '第一条字幕' in content

@pytest.mark.asyncio
async def test_merge_short_subtitles():
    """测试字幕合并"""
    subtitles = [
        {'start': 0.0, 'end': 0.8, 'text': '短一'},
        {'start': 1.0, 'end': 1.5, 'text': '短二'},
        {'start': 2.0, 'end': 6.0, 'text': '长字幕不应该合并'},
    ]

    result = merge_short_subtitles(subtitles, threshold=1.5)

    # 验证短字幕被合并
    assert len(result) == 2
    assert result[0]['text'] == '短一 短二'
```

**Step 2: 运行测试验证失败**

```bash
cd backend
pytest tests/test_srt.py -v
```

Expected: FAIL

**Step 3: 实现 SRT 生成服务**

```python
# backend/app/services/srt.py
from pathlib import Path
from typing import List, Dict
import re

async def generate_srt(
    segments: List[Dict],
    output_path: Path,
    min_duration: float = 2.0,
    max_duration: float = 8.0,
    merge_threshold: float = 1.5
):
    """
    生成 SRT 字幕文件

    Args:
        segments: ASR 结果片段列表
        output_path: 输出文件路径
        min_duration: 最短字幕时长
        max_duration: 最长字幕时长
        merge_threshold: 短字幕合并阈值
    """
    # 转换为句子级别的时间戳
    subtitles = _convert_to_sentence_level(segments)

    # 合并短字幕
    subtitles = merge_short_subtitles(subtitles, merge_threshold)

    # 分割过长的字幕
    subtitles = _split_long_subtitles(subtitles, max_duration)

    # 生成 SRT 内容
    srt_content = _format_srt(subtitles)

    # 写入文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(srt_content, encoding='utf-8')

def _convert_to_sentence_level(
    segments: List[Dict]
) -> List[Dict]:
    """
    将 token 级别时间戳转换为句子级别

    策略：按标点符号切分，确保时长在 2-8 秒
    """
    subtitles = []

    for seg in segments:
        text = seg['text']
        start = seg['start']
        end = seg['end']

        # 按标点切分
        sentences = re.split(r'([。！？.!?])', text)

        current_sentence = ''
        sentence_start = start
        duration = end - start

        # 如果时长适中，直接使用
        if min_duration <= duration <= max_duration:
            subtitles.append({
                'start': start,
                'end': end,
                'text': text.strip()
            })
            continue

        # 处理长片段
        if duration > max_duration:
            # 按标点重新切分
            for i in range(0, len(sentences), 2):
                if i + 1 < len(sentences):
                    sentence = sentences[i] + sentences[i + 1]
                    if sentence.strip():
                        # 根据字符数估算时间
                        char_ratio = (end - start) / len(text)
                        sentence_end = sentence_start + len(sentence) * char_ratio

                        subtitles.append({
                            'start': sentence_start,
                            'end': sentence_end,
                            'text': sentence.strip()
                        })
                        sentence_start = sentence_end
        else:
            # 短片段也保留
            subtitles.append({
                'start': start,
                'end': end,
                'text': text.strip()
            })

    return subtitles

def merge_short_subtitles(
    subtitles: List[Dict],
    threshold: float
) -> List[Dict]:
    """
    合并短字幕

    Args:
        subtitles: 字幕列表
        threshold: 合并阈值，相邻短字幕间隔小于此值时合并

    Returns:
        合并后的字幕列表
    """
    if not subtitles:
        return []

    merged = []
    current = subtitles[0].copy()

    for next_sub in subtitles[1:]:
        gap = next_sub['start'] - current['end']
        current_duration = current['end'] - current['start']

        # 如果当前字幕很短且与下一个字幕很近，合并
        if current_duration < threshold and gap < threshold:
            current['end'] = next_sub['end']
            current['text'] += ' ' + next_sub['text']
        else:
            merged.append(current)
            current = next_sub.copy()

    merged.append(current)
    return merged

def _split_long_subtitles(
    subtitles: List[Dict],
    max_duration: float
) -> List[Dict]:
    """
    分割过长的字幕
    """
    result = []

    for sub in subtitles:
        duration = sub['end'] - sub['start']

        if duration <= max_duration:
            result.append(sub)
            continue

        # 按字符数均分
        text = sub['text']
        chars = len(text)
        split_count = int(duration / max_duration) + 1
        chars_per_split = chars // split_count

        start_time = sub['start']
        time_per_split = duration / split_count

        for i in range(split_count):
            start_idx = i * chars_per_split
            end_idx = start_idx + chars_per_split if i < split_count - 1 else chars

            result.append({
                'start': start_time + i * time_per_split,
                'end': start_time + (i + 1) * time_per_split,
                'text': text[start_idx:end_idx].strip()
            })

    return result

def _format_srt(subtitles: List[Dict]) -> str:
    """
    格式化为 SRT 文件内容
    """
    lines = []

    for i, sub in enumerate(subtitles, 1):
        start_time = _format_timestamp(sub['start'])
        end_time = _format_timestamp(sub['end'])

        lines.append(str(i))
        lines.append(f"{start_time} --> {end_time}")
        lines.append(sub['text'])
        lines.append("")  # 空行分隔

    return '\n'.join(lines)

def _format_timestamp(seconds: float) -> str:
    """
    格式化时间戳为 SRT 格式: HH:MM:SS,mmm
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
```

**Step 4: 运行测试验证通过**

```bash
cd backend
pytest tests/test_srt.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/srt.py backend/tests/test_srt.py
git commit -m "feat: add SRT generation service"
```

---

### Task 11: 实现任务处理流程和 SSE 推送

**Files:**
- Create: `backend/app/services/task_processor.py`
- Modify: `backend/app/api/tasks.py`

**Step 1: 创建任务处理器**

```python
# backend/app/services/task_processor.py
import asyncio
from pathlib import Path
from typing import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.task import Task
from ..models.segment import Segment
from ..models.subtitle import Subtitle
from ..models.log import Log
from .audio import extract_audio, get_video_duration
from .vad import split_audio_by_vad
from .asr import transcribe_audio
from .srt import generate_srt
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class ProgressEvent:
    """进度事件"""
    def __init__(self, event_type: str, data: dict):
        self.event_type = event_type
        self.data = data

    def to_sse(self) -> str:
        """转换为 SSE 格式"""
        return f"event: {self.event_type}\ndata: {self.data}\n\n"

async def process_task(
    task_id: str,
    db: AsyncSession,
    progress_queue: asyncio.Queue
) -> dict:
    """
    处理字幕生成任务

    Args:
        task_id: 任务 ID
        db: 数据库会话
        progress_queue: 进度队列

    Returns:
        dict: 处理结果
    """
    try:
        # 获取任务
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            await progress_queue.put(ProgressEvent('error', {'error': '任务不存在'}))
            return {'status': 'error', 'message': '任务不存在'}

        # 更新任务状态
        task.status = 'processing'
        task.started_at = datetime.utcnow()
        await db.commit()

        await progress_queue.put(ProgressEvent('progress', {
            'progress': 0,
            'step': '开始处理...'
        }))

        # 1. 提取音频
        await _log(db, task_id, 'info', '开始提取音频...')
        audio_path = settings.OUTPUT_DIR / f"{task_id}_audio.wav"
        await extract_audio(Path(task.file_path), audio_path)
        await _log(db, task_id, 'info', '音频提取完成')

        # 2. 获取视频时长
        duration = await get_video_duration(Path(task.file_path))
        task.duration_seconds = int(duration)
        await db.commit()

        # 3. VAD 切分
        await _log(db, task_id, 'info', '开始语音活动检测...')
        await progress_queue.put(ProgressEvent('progress', {
            'progress': 10,
            'step': '正在进行语音活动检测...'
        }))

        segments_dir = settings.OUTPUT_DIR / f"{task_id}_segments"
        segments = await split_audio_by_vad(
            audio_path,
            segments_dir,
            min_duration=settings.SEGMENT_MIN_DURATION,
            max_duration=settings.SEGMENT_MAX_DURATION
        )

        await _log(db, task_id, 'info', f'检测到 {len(segments)} 个音频片段')

        # 4. 保存片段信息到数据库
        for seg in segments:
            segment = Segment(
                task_id=task_id,
                index=seg['index'],
                start_time=seg['start_time'],
                end_time=seg['end_time'],
                audio_path=seg['audio_path']
            )
            db.add(segment)
        await db.commit()

        # 5. ASR 识别
        await _log(db, task_id, 'info', '开始语音识别...')
        all_segments = []

        for i, seg_info in enumerate(segments):
            await progress_queue.put(ProgressEvent('progress', {
                'progress': 20 + int(60 * i / len(segments)),
                'step': f'正在识别 ({i+1}/{len(segments)})...'
            }))

            # 更新片段状态
            result = await db.execute(
                select(Segment).where(
                    Segment.task_id == task_id,
                    Segment.index == seg_info['index']
                )
            )
            segment = result.scalar_one_or_none()
            if segment:
                segment.status = 'processing'
                await db.commit()

            # 重试逻辑
            for attempt in range(settings.MAX_RETRY_ATTEMPTS):
                try:
                    asr_result = await transcribe_audio(Path(seg_info['audio_path']))
                    all_segments.extend(asr_result['segments'])

                    if segment:
                        segment.status = 'completed'
                        await db.commit()

                    await _log(db, task_id, 'info', f'片段 {i+1} 识别完成')
                    break

                except Exception as e:
                    if attempt == settings.MAX_RETRY_ATTEMPTS - 1:
                        await _log(db, task_id, 'error', f'片段 {i+1} 识别失败: {str(e)}')
                        if segment:
                            segment.status = 'failed'
                            segment.retry_count = settings.MAX_RETRY_ATTEMPTS
                            segment.error_message = str(e)
                            await db.commit()
                    else:
                        await _log(db, task_id, 'warning', f'片段 {i+1} 重试 ({attempt+1}/{settings.MAX_RETRY_ATTEMPTS})')
                        if segment:
                            segment.retry_count = attempt + 1
                            await db.commit()
                        await asyncio.sleep(settings.RETRY_BASE_DELAY * (2 ** attempt))

        # 6. 生成 SRT
        await progress_queue.put(ProgressEvent('progress', {
            'progress': 85,
            'step': '正在生成字幕...'
        }))

        await _log(db, task_id, 'info', '开始生成 SRT 文件...')
        srt_path = settings.OUTPUT_DIR / f"{Path(task.filename).stem}_字幕.srt"
        await generate_srt(all_segments, srt_path)

        # 7. 保存字幕到数据库
        await _save_subtitles(db, task_id, all_segments)

        # 8. 更新任务状态
        task.status = 'completed'
        task.completed_at = datetime.utcnow()
        task.progress = 100
        await db.commit()

        await progress_queue.put(ProgressEvent('complete', {
            'task_id': task_id,
            'srt_path': str(srt_path)
        }))

        await _log(db, task_id, 'info', '任务完成')

        return {
            'status': 'completed',
            'srt_path': str(srt_path),
            'subtitle_count': len(all_segments)
        }

    except Exception as e:
        logger.exception(f"任务处理失败: {task_id}")

        # 更新任务状态
        task.status = 'failed'
        task.error_message = str(e)
        await db.commit()

        await progress_queue.put(ProgressEvent('error', {
            'error': f'处理失败: {str(e)}'
        }))

        await _log(db, task_id, 'error', f'任务失败: {str(e)}')

        return {'status': 'error', 'message': str(e)}

async def _log(db: AsyncSession, task_id: str, level: str, message: str):
    """记录日志"""
    log = Log(task_id=task_id, level=level, message=message)
    db.add(log)
    await db.commit()

async def _save_subtitles(db: AsyncSession, task_id: str, segments: list):
    """保存字幕到数据库"""
    for i, seg in enumerate(segments):
        subtitle = Subtitle(
            task_id=task_id,
            index=i + 1,
            start_time=seg['start'],
            end_time=seg['end'],
            text=seg['text']
        )
        db.add(subtitle)
    await db.commit()
```

**Step 2: 更新任务 API**

```python
# backend/app/api/tasks.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from pathlib import Path
import asyncio
from ..models.task import Task
from ..models.subtitle import Subtitle
from ..models.log import Log
from ..services.task_processor import process_task
from ..core.config import settings
from .deps import get_db_session

router = APIRouter()

# 存储任务进度队列
_task_queues: dict[str, asyncio.Queue] = {}

@router.get("/")
async def list_tasks(
    status: str = None,
    db: AsyncSession = Depends(get_db_session)
):
    """获取任务列表"""
    query = select(Task)
    if status:
        query = query.where(Task.status == status)
    query = query.order_by(Task.created_at.desc())

    result = await db.execute(query)
    tasks = result.scalars().all()

    return {
        "tasks": [
            {
                "id": t.id,
                "filename": t.filename,
                "status": t.status,
                "progress": t.progress,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None
            }
            for t in tasks
        ]
    }

@router.get("/{task_id}")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """获取任务详情"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "id": task.id,
        "filename": task.filename,
        "status": task.status,
        "progress": task.progress,
        "current_step": task.current_step,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "duration_seconds": task.duration_seconds
    }

@router.post("/{task_id}/start")
async def start_task(
    task_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """开始处理任务"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "pending":
        raise HTTPException(status_code=400, detail="任务已开始或已完成")

    # 创建进度队列
    _task_queues[task_id] = asyncio.Queue()

    # 启动后台任务
    asyncio.create_task(process_task(task_id, db, _task_queues[task_id]))

    return {"message": "任务已开始", "task_id": task_id}

@router.get("/{task_id}/events")
async def task_events(task_id: str):
    """SSE 实时进度推送"""
    from fastapi import Request
    from fastapi.responses import StreamingResponse

    async def event_stream():
        queue = _task_queues.get(task_id)
        if not queue:
            queue = asyncio.Queue()
            _task_queues[task_id] = queue

        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"event: {event.event_type}\ndata: {event.data}\n\n"

                if event.event_type in ['complete', 'error']:
                    break
        except asyncio.TimeoutError:
            yield "event: heartbeat\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@router.get("/{task_id}/subtitles")
async def get_subtitles(
    task_id: str,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db_session)
):
    """获取字幕列表"""
    result = await db.execute(
        select(Subtitle)
        .where(Subtitle.task_id == task_id)
        .order_by(Subtitle.index)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    subtitles = result.scalars().all()

    return {
        "subtitles": [
            {
                "index": s.index,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "text": s.text
            }
            for s in subtitles
        ],
        "page": page,
        "page_size": page_size
    }

@router.get("/{task_id}/subtitles/search")
async def search_subtitles(
    task_id: str,
    q: str,
    db: AsyncSession = Depends(get_db_session)
):
    """搜索字幕（支持正则）"""
    import re

    result = await db.execute(
        select(Subtitle)
        .where(Subtitle.task_id == task_id)
        .order_by(Subtitle.index)
    )
    subtitles = result.scalars().all()

    # 正则搜索
    pattern = re.compile(q, re.IGNORECASE)
    matched = [
        {
            "index": s.index,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "text": s.text
        }
        for s in subtitles
        if pattern.search(s.text)
    ]

    return {"subtitles": matched}

@router.get("/{task_id}/subtitles/filter")
async def filter_subtitles_by_time(
    task_id: str,
    start: float,
    end: float,
    db: AsyncSession = Depends(get_db_session)
):
    """按时间范围筛选字幕"""
    result = await db.execute(
        select(Subtitle)
        .where(
            Subtitle.task_id == task_id,
            Subtitle.start_time >= start,
            Subtitle.end_time <= end
        )
        .order_by(Subtitle.index)
    )
    subtitles = result.scalars().all()

    return {
        "subtitles": [
            {
                "index": s.index,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "text": s.text
            }
            for s in subtitles
        ]
    }

@router.get("/{task_id}/download")
async def download_subtitle(
    task_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """下载 SRT 文件"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task or task.status != 'completed':
        raise HTTPException(status_code=404, detail="字幕文件不存在")

    srt_path = settings.OUTPUT_DIR / f"{Path(task.filename).stem}_字幕.srt"

    if not srt_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=srt_path,
        filename=f"{Path(task.filename).stem}_字幕.srt",
        media_type="text/plain"
    )

@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """删除任务"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 删除文件
    from ..services.file_manager import delete_file
    await delete_file(Path(task.file_path))

    # 删除字幕文件
    srt_path = settings.OUTPUT_DIR / f"{Path(task.filename).stem}_字幕.srt"
    await delete_file(srt_path)

    # 删除片段目录
    segments_dir = settings.OUTPUT_DIR / f"{task_id}_segments"
    if segments_dir.exists():
        import shutil
        shutil.rmtree(segments_dir)

    # 删除数据库记录（级联删除相关记录）
    await db.execute(delete(Task).where(Task.id == task_id))
    await db.commit()

    # 清理进度队列
    if task_id in _task_queues:
        del _task_queues[task_id]

    return {"message": "任务已删除"}
```

**Step 3: 测试 API**

```bash
# 启动服务器
cd backend
uv run uvicorn app.main:app --reload
```

测试端点：
- `GET /api/tasks` - 获取任务列表
- `POST /api/tasks/{id}/start` - 开始任务
- `GET /api/tasks/{id}/events` - SSE 进度

**Step 4: Commit**

```bash
git add backend/app/services/task_processor.py backend/app/api/tasks.py
git commit -m "feat: add task processor and SSE progress streaming"
```

---

## Phase 3: 前端核心功能

### Task 12: 创建前端路由和页面骨架

**Files:**
- Create: `frontend/src/router/index.js`
- Create: `frontend/src/views/UploadView.vue`
- Create: `frontend/src/views/ProcessingView.vue`
- Create: `frontend/src/views/PreviewView.vue`

**Step 1: 创建路由配置**

```javascript
// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/upload'
  },
  {
    path: '/upload',
    name: 'Upload',
    component: () => import('@/views/UploadView.vue')
  },
  {
    path: '/processing/:id',
    name: 'Processing',
    component: () => import('@/views/ProcessingView.vue'),
    props: true
  },
  {
    path: '/preview/:id',
    name: 'Preview',
    component: () => import('@/views/PreviewView.vue'),
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
```

**Step 2: 创建上传页面骨架**

```vue
<!-- frontend/src/views/UploadView.vue -->
<template>
  <div class="min-h-screen flex items-center justify-center p-4">
    <div class="glass rounded-2xl p-8 w-full max-w-2xl glow">
      <h1 class="text-3xl font-bold text-center mb-8 text-brand-blue">
        上传视频文件
      </h1>

      <div
        class="border-2 border-dashed border-brand-cyan rounded-xl p-12 text-center cursor-pointer hover:border-brand-blue transition-colors"
        @click="selectFile"
        @dragover.prevent
        @drop.prevent="handleDrop"
      >
        <svg class="w-16 h-16 mx-auto mb-4 text-brand-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p class="text-text-secondary mb-2">拖拽视频文件到此处</p>
        <p class="text-text-muted">或点击选择文件</p>
        <p class="text-xs text-text-muted mt-4">支持 MP4, AVI, MKV, MOV, WEBM</p>
      </div>

      <input
        ref="fileInput"
        type="file"
        class="hidden"
        accept="video/*"
        @change="handleFileSelect"
      />

      <div v-if="selectedFile" class="mt-6 p-4 bg-secondary rounded-lg">
        <p class="text-text-primary">{{ selectedFile.name }}</p>
        <p class="text-text-muted text-sm">{{ formatFileSize(selectedFile.size) }}</p>
      </div>

      <button
        v-if="selectedFile"
        @click="uploadFile"
        :disabled="uploading"
        class="w-full mt-6 py-3 bg-brand-blue hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg font-medium text-white animate-pulse-laser transition-all"
      >
        {{ uploading ? '上传中...' : '上传并开始处理' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const fileInput = ref(null)
const selectedFile = ref(null)
const uploading = ref(false)

function selectFile() {
  fileInput.value.click()
}

function handleFileSelect(e) {
  const file = e.target.files[0]
  if (file) selectedFile.value = file
}

function handleDrop(e) {
  const file = e.dataTransfer.files[0]
  if (file && file.type.startsWith('video/')) {
    selectedFile.value = file
  }
}

function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) {
    return (bytes / 1024).toFixed(1) + ' KB'
  }
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function uploadFile() {
  if (!selectedFile.value) return

  uploading.value = true
  const formData = new FormData()
  formData.append('file', selectedFile.value)

  try {
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    })
    const data = await response.json()

    if (response.ok) {
      // 跳转到处理页面
      router.push(`/processing/${data.task_id}`)
    } else {
      alert(data.detail || '上传失败')
    }
  } catch (error) {
    alert('上传失败: ' + error.message)
  } finally {
    uploading.value = false
  }
}
</script>
```

**Step 3: 创建处理进度页面骨架**

```vue
<!-- frontend/src/views/ProcessingView.vue -->
<template>
  <div class="min-h-screen flex items-center justify-center p-4">
    <div class="glass rounded-2xl p-8 w-full max-w-2xl glow">
      <h1 class="text-2xl font-bold text-center mb-8 text-brand-blue">
        正在处理视频
      </h1>

      <!-- 进度环形图 -->
      <div class="flex justify-center mb-8">
        <div class="relative w-48 h-48">
          <svg class="w-full h-full transform -rotate-90">
            <circle
              cx="96"
              cy="96"
              r="88"
              stroke="#1e293b"
              stroke-width="12"
              fill="none"
            />
            <circle
              cx="96"
              cy="96"
              r="88"
              :stroke-dasharray="circumference"
              :stroke-dashoffset="progressOffset"
              stroke="url(#gradient)"
              stroke-width="12"
              fill="none"
              stroke-linecap="round"
              class="transition-all duration-500"
            />
            <defs>
              <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#3b82f6" />
                <stop offset="100%" stop-color="#06b6d4" />
              </linearGradient>
            </defs>
          </svg>
          <div class="absolute inset-0 flex items-center justify-center">
            <span class="text-4xl font-bold text-brand-blue">{{ progress }}%</span>
          </div>
        </div>
      </div>

      <!-- 当前步骤 -->
      <div class="text-center mb-6">
        <p class="text-text-secondary">{{ currentStep }}</p>
        <p v-if="eta" class="text-text-muted text-sm mt-2">预计剩余: {{ formatTime(eta) }}</p>
      </div>

      <!-- 日志终端 -->
      <div class="bg-secondary rounded-lg p-4 h-64 overflow-y-auto font-mono text-sm">
        <div
          v-for="(log, index) in logs"
          :key="index"
          :class="{
            'text-brand-green': log.level === 'info',
            'text-brand-orange': log.level === 'warning',
            'text-red-400': log.level === 'error'
          }"
        >
          <span class="text-text-muted">[{{ log.time }}]</span>
          <span :class="{
            'text-brand-green': log.level === 'info',
            'text-brand-orange': log.level === 'warning',
            'text-red-400': log.level === 'error'
          }">[{{ log.level }}]</span>
          {{ log.message }}
        </div>
      </div>

      <!-- 完成后跳转按钮 -->
      <button
        v-if="status === 'completed'"
        @click="goToPreview"
        class="w-full mt-6 py-3 bg-brand-blue hover:bg-blue-600 rounded-lg font-medium text-white animate-pulse-laser"
      >
        查看字幕
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id

const progress = ref(0)
const currentStep = ref('准备中...')
const eta = ref(0)
const logs = ref([])
const status = ref('processing')

const circumference = 2 * Math.PI * 88
const progressOffset = computed(() => {
  return circumference * (1 - progress.value / 100)
})

let eventSource = null

onMounted(() => {
  connectSSE()
})

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
  }
})

function connectSSE() {
  eventSource = new EventSource(`/api/tasks/${taskId}/events`)

  eventSource.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data)
    progress.value = data.progress
    currentStep.value = data.step
    addLog('info', data.step)
  })

  eventSource.addEventListener('log', (e) => {
    const data = JSON.parse(e.data)
    addLog(data.level, data.message)
  })

  eventSource.addEventListener('complete', (e) => {
    const data = JSON.parse(e.data)
    status.value = 'completed'
    progress.value = 100
    currentStep.value = '处理完成'
    addLog('info', '处理完成')
  })

  eventSource.addEventListener('error', (e) => {
    const data = JSON.parse(e.data)
    status.value = 'failed'
    currentStep.value = '处理失败'
    addLog('error', data.error)
  })

  eventSource.onerror = () => {
    status.value = 'failed'
    addLog('error', '连接中断')
  }
}

function addLog(level, message) {
  const now = new Date()
  const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
  logs.value.push({ time, level, message })
  // 自动滚动到底部
  setTimeout(() => {
    const terminal = document.querySelector('.overflow-y-auto')
    if (terminal) terminal.scrollTop = terminal.scrollHeight
  }, 100)
}

function formatTime(seconds) {
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${minutes}分${secs}秒`
}

function goToPreview() {
  router.push(`/preview/${taskId}`)
}
</script>
```

**Step 4: 创建预览页面骨架**

```vue
<!-- frontend/src/views/PreviewView.vue -->
<template>
  <div class="min-h-screen p-4">
    <div class="max-w-6xl mx-auto">
      <div class="glass rounded-2xl p-6 glow">
        <!-- 头部 -->
        <div class="flex items-center justify-between mb-6">
          <h1 class="text-2xl font-bold text-brand-blue">字幕预览</h1>
          <button
            @click="downloadSrt"
            class="px-6 py-2 bg-brand-blue hover:bg-blue-600 rounded-lg font-medium text-white animate-pulse-laser"
          >
            下载字幕
          </button>
        </div>

        <!-- 视频播放器和字幕列表 -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- 视频播放器 -->
          <div>
            <video
              ref="videoPlayer"
              :src="videoUrl"
              controls
              class="w-full rounded-lg"
              @timeupdate="onTimeUpdate"
            />
            <p class="text-center text-text-muted mt-2">当前字幕将高亮显示</p>
          </div>

          <!-- 字幕列表 -->
          <div>
            <!-- 搜索框 -->
            <div class="mb-4 flex gap-2">
              <input
                v-model="searchQuery"
                type="text"
                placeholder="搜索字幕（支持正则）..."
                class="flex-1 px-4 py-2 bg-secondary border border-brand-cyan rounded-lg text-text-primary focus:outline-none focus:border-brand-blue"
                @keyup.enter="searchSubtitles"
              />
              <button
                @click="searchSubtitles"
                class="px-4 py-2 bg-brand-cyan hover:bg-cyan-600 rounded-lg font-medium text-white"
              >
                搜索
              </button>
            </div>

            <!-- 时间筛选 -->
            <div class="mb-4 flex gap-2">
              <input
                v-model.number="filterStart"
                type="number"
                placeholder="开始时间（秒）"
                class="flex-1 px-4 py-2 bg-secondary border border-brand-cyan rounded-lg text-text-primary focus:outline-none focus:border-brand-blue"
              />
              <input
                v-model.number="filterEnd"
                type="number"
                placeholder="结束时间（秒）"
                class="flex-1 px-4 py-2 bg-secondary border border-brand-cyan rounded-lg text-text-primary focus:outline-none focus:border-brand-blue"
              />
              <button
                @click="filterByTime"
                class="px-4 py-2 bg-brand-cyan hover:bg-cyan-600 rounded-lg font-medium text-white"
              >
                筛选
              </button>
            </div>

            <!-- 字幕列表 -->
            <div class="h-96 overflow-y-auto space-y-2 pr-2">
              <div
                v-for="subtitle in displaySubtitles"
                :key="subtitle.index"
                :ref="el => el && subtitleRefs.set(subtitle.index, el)"
                @click="seekTo(subtitle.start_time)"
                :class="[
                  'p-3 rounded-lg cursor-pointer transition-all',
                  subtitle.index === currentSubtitleIndex
                    ? 'bg-brand-blue text-white'
                    : 'bg-secondary hover:bg-slate-700'
                ]"
              >
                <div class="flex items-center gap-3">
                  <span class="text-xs text-text-muted w-12">{{ formatTime(subtitle.start_time) }}</span>
                  <span class="flex-1">{{ subtitle.text }}</span>
                  <span class="text-xs text-text-muted">{{ subtitle.index }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id

const videoPlayer = ref(null)
const videoUrl = ref('')
const subtitles = ref([])
const displaySubtitles = ref([])
const subtitleRefs = new Map()
const currentSubtitleIndex = ref(-1)

const searchQuery = ref('')
const filterStart = ref(null)
const filterEnd = ref(null)

onMounted(async () => {
  await loadTaskInfo()
  await loadSubtitles()
})

async function loadTaskInfo() {
  const response = await fetch(`/api/tasks/${taskId}`)
  const data = await response.json()

  // 这里需要后端提供视频预览接口
  // 暂时留空
}

async function loadSubtitles() {
  const response = await fetch(`/api/tasks/${taskId}/subtitles`)
  const data = await response.json()
  subtitles.value = data.subtitles
  displaySubtitles.value = data.subtitles
}

function onTimeUpdate() {
  if (!videoPlayer.value) return

  const currentTime = videoPlayer.value.currentTime
  const index = subtitles.value.findIndex(
    s => currentTime >= s.start_time && currentTime <= s.end_time
  )

  if (index !== currentSubtitleIndex.value) {
    currentSubtitleIndex.value = index
    // 滚动到当前字幕
    if (index >= 0 && subtitleRefs.has(index)) {
      subtitleRefs.get(index)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }
}

function seekTo(time) {
  if (videoPlayer.value) {
    videoPlayer.value.currentTime = time
  }
}

function formatTime(seconds) {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}

async function searchSubtitles() {
  if (!searchQuery.value) {
    displaySubtitles.value = subtitles.value
    return
  }

  try {
    const response = await fetch(`/api/tasks/${taskId}/subtitles/search?q=${encodeURIComponent(searchQuery.value)}`)
    const data = await response.json()
    displaySubtitles.value = data.subtitles
  } catch (error) {
    alert('搜索失败: ' + error.message)
  }
}

async function filterByTime() {
  if (filterStart.value === null || filterEnd.value === null) {
    displaySubtitles.value = subtitles.value
    return
  }

  try {
    const response = await fetch(`/api/tasks/${taskId}/subtitles/filter?start=${filterStart.value}&end=${filterEnd.value}`)
    const data = await response.json()
    displaySubtitles.value = data.subtitles
  } catch (error) {
    alert('筛选失败: ' + error.message)
  }
}

async function downloadSrt() {
  window.open(`/api/tasks/${taskId}/download`, '_blank')
}
</script>
```

**Step 5: 测试前端**

```bash
cd frontend
bun run dev
```

访问 http://localhost:5173

**Step 6: Commit**

```bash
git add frontend/src/router/ frontend/src/views/
git commit -m "feat: add frontend views and routing"
```

---

### Task 13: 添加粒子效果背景

**Files:**
- Create: `frontend/src/components/ParticleBackground.vue`

**Step 1: 创建粒子背景组件**

```vue
<!-- frontend/src/components/ParticleBackground.vue -->
<template>
  <canvas
    ref="canvas"
    class="fixed inset-0 pointer-events-none"
  />
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const canvas = ref(null)
let ctx = null
let particles = []
let animationId = null

class Particle {
  constructor(width, height) {
    this.x = Math.random() * width
    this.y = Math.random() * height
    this.vx = (Math.random() - 0.5) * 0.5
    this.vy = (Math.random() - 0.5) * 0.5
    this.size = Math.random() * 2 + 1
    this.opacity = Math.random() * 0.5 + 0.2

    // 随机选择颜色
    const colors = ['#3b82f6', '#06b6d4']
    this.color = colors[Math.floor(Math.random() * colors.length)]
  }

  update(width, height) {
    this.x += this.vx
    this.y += this.vy

    // 边界检测
    if (this.x < 0 || this.x > width) this.vx *= -1
    if (this.y < 0 || this.y > height) this.vy *= -1
  }

  draw(ctx) {
    ctx.globalAlpha = this.opacity
    ctx.fillStyle = this.color
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fill()
    ctx.globalAlpha = 1
  }
}

function init() {
  const width = canvas.value.width = window.innerWidth
  const height = canvas.value.height = window.innerHeight

  particles = []
  const particleCount = Math.floor((width * height) / 15000)

  for (let i = 0; i < particleCount; i++) {
    particles.push(new Particle(width, height))
  }
}

function animate() {
  const width = canvas.value.width
  const height = canvas.value.height

  ctx.clearRect(0, 0, width, height)

  particles.forEach(particle => {
    particle.update(width, height)
    particle.draw(ctx)
  })

  animationId = requestAnimationFrame(animate)
}

onMounted(() => {
  ctx = canvas.value.getContext('2d')
  init()
  animate()

  window.addEventListener('resize', init)
})

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  window.removeEventListener('resize', init)
})
</script>
```

**Step 2: 在 App.vue 中使用**

```vue
<!-- frontend/src/App.vue -->
<template>
  <div id="app" class="min-h-screen bg-gradient-to-br from-primary to-secondary relative">
    <ParticleBackground />
    <RouterView />
  </div>
</template>

<script setup>
import { RouterView } from 'vue-router'
import ParticleBackground from '@/components/ParticleBackground.vue'
</script>
```

**Step 3: Commit**

```bash
git add frontend/src/components/ParticleBackground.vue frontend/src/App.vue
git commit -m "feat: add particle background effect"
```

---

## Phase 4: 构建和部署

### Task 14: 创建构建脚本

**Files:**
- Create: `scripts/build.sh`
- Create: `scripts/start.sh`

**Step 1: 创建构建脚本**

```bash
#!/bin/bash
# scripts/build.sh

set -e

echo "🔨 构建前端..."
cd frontend
bun run build

echo "📁 复制静态文件..."
cd ..
rm -rf backend/static
mkdir -p backend/static
cp -r frontend/dist/* backend/static/

echo "✅ 构建完成！"
```

**Step 2: 创建启动脚本**

```bash
#!/bin/bash
# scripts/start.sh

set -e

echo "🚀 启动视频字幕生成系统..."

# 检查是否需要构建
if [ ! -d "backend/static" ] || [ ! -f "backend/static/index.html" ]; then
    echo "📦 首次启动，正在构建..."
    ./scripts/build.sh
fi

cd backend

# 激活虚拟环境并启动
echo "🎯 启动后端服务..."
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

echo "✅ 服务已启动: http://localhost:8000"
```

**Step 3: 添加执行权限**

```bash
chmod +x scripts/build.sh
chmod +x scripts/start.sh
```

**Step 4: 测试构建**

```bash
./scripts/build.sh
```

Expected: 前端构建完成，静态文件复制到 backend/static/

**Step 5: 测试启动**

```bash
./scripts/start.sh
```

Expected: 服务启动，访问 http://localhost:8000

**Step 6: Commit**

```bash
git add scripts/
git commit -m "feat: add build and start scripts"
```

---

### Task 15: 添加 README 文档

**Files:**
- Create: `README.md`

**Step 1: 创建 README**

```markdown
# 视频字幕生成系统

基于 FastAPI + Vue3 的视频字幕自动生成系统，使用 fsmn-vad 进行语音活动检测，Qwen3-ASR-1.7B 进行语音识别。

## 功能特性

- 🎬 支持多种视频格式（MP4、AVI、MKV、MOV、WEBM）
- 🎙️ 智能语音活动检测，自动切分音频片段
- 🤖 基于大模型的语音识别
- ⏱️ 实时进度显示和日志输出
- 📝 字幕预览、搜索（支持正则）和时间筛选
- 💾 一键下载 SRT 字幕文件
- 🎨 深色科技主题 UI

## 技术栈

- 后端: FastAPI + uv + SQLite
- 前端: Vue 3 + TailwindCSS + Bun
- AI 模型: fsmn-vad + Qwen3-ASR-1.7B
- 音频处理: ffmpeg

## 快速开始

### 环境要求

- Python 3.10+
- Bun
- ffmpeg

### 安装

1. 克隆项目
```bash
git clone <repository-url>
cd video-srt-generator
```

2. 安装后端依赖
```bash
cd backend
uv sync
```

3. 安装前端依赖
```bash
cd frontend
bun install
```

### 运行

#### 开发模式

```bash
# 后端（终端 1）
cd backend
uv run uvicorn app.main:app --reload

# 前端（终端 2）
cd frontend
bun run dev
```

#### 生产模式

```bash
./scripts/start.sh
```

访问 http://localhost:8000

## 使用说明

1. 上传视频文件
2. 系统自动处理并生成字幕
3. 实时查看处理进度
4. 预览和搜索字幕
5. 下载 SRT 文件

## 配置

编辑 `backend/.env` 文件修改配置：

- `CHECKPOINTS_DIR`: 模型权重目录
- `SEGMENT_MIN_DURATION`: 最小切分时长（秒）
- `SEGMENT_MAX_DURATION`: 最大切分时长（秒）
- `SUBTITLE_MIN_DURATION`: 字幕最短时长（秒）
- `SUBTITLE_MAX_DURATION`: 字幕最长时长（秒）

## 目录结构

```
video-srt-generator/
├── backend/          # FastAPI 后端
├── frontend/         # Vue3 前端
├── scripts/          # 构建和启动脚本
├── docs/            # 文档
└── README.md
```

## 许可证

MIT
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README documentation"
```

---

## 完成检查清单

- [ ] 项目目录结构创建
- [ ] 后端初始化（uv + FastAPI）
- [ ] 前端初始化（Vue3 + TailwindCSS）
- [ ] 数据库模型创建
- [ ] 文件上传功能
- [ ] 音频提取服务
- [ ] VAD 服务
- [ ] ASR 服务
- [ ] SRT 生成服务
- [ ] 任务处理流程
- [ ] SSE 进度推送
- [ ] 前端路由和页面
- [ ] 粒子效果背景
- [ ] 构建和启动脚本
- [ ] README 文档

---

*实现计划完成*
