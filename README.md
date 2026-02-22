# 视频字幕生成系统

基于 AI 的智能视频字幕生成系统，支持语音识别、字幕编辑和 SRT 格式导出。

## 功能特性

### 核心功能
- **视频上传**: 支持常见视频格式（MP4、AVI、MOV、MKV 等）
- **自动语音识别**: 使用 Faster-Whisper 模型进行高精度语音转文字
- **智能断句**: 自动识别句子边界，生成合理的字幕分段
- **字幕编辑器**: 可视化编辑界面，支持调整时间轴和文本内容
- **SRT 导出**: 生成标准 SRT 格式字幕文件，可直接用于视频播放器
- **任务管理**: 支持多任务并行处理，实时查看处理进度
- **历史记录**: 保存处理历史，支持重新下载和编辑

### 技术亮点
- 前后端分离架构
- RESTful API 设计
- 响应式 UI，支持移动端
- 异步任务处理，支持大文件处理
- SQLite 数据持久化
- 环境变量配置管理

## 技术栈

### 前端
- **Vue 3** - 渐进式 JavaScript 框架
- **Vite** - 下一代前端构建工具
- **Tailwind CSS** - 实用优先的 CSS 框架
- **Vue Router** - 官方路由管理
- **Pinia** - Vue 3 状态管理
- **Axios** - HTTP 客户端

### 后端
- **FastAPI** - 现代高性能 Python Web 框架
- **Faster-Whisper** - 快速语音识别模型
- **SQLAlchemy** - ORM 数据库工具
- **SQLite** - 轻量级数据库
- **FFmpeg** - 多媒体处理工具
- **Uvicorn** - ASGI 服务器

### 开发工具
- **Bun** - 快速 JavaScript 运行时和包管理器
- **Python 3.10+** - 后端开发语言
- **Git** - 版本控制

## 快速开始

### 环境要求

- Python 3.10 或更高版本
- Node.js 18+ 或 Bun
- FFmpeg（用于音视频处理）
- Git

### 安装 FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
下载 [FFmpeg](https://ffmpeg.org/download.html) 并添加到系统 PATH

### 1. 克隆项目

```bash
git clone <repository-url>
cd video-srt-generator
```

### 2. 安装后端依赖

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
cd ..
```

### 3. 安装前端依赖

```bash
cd frontend
bun install  # 或 npm install
cd ..
```

### 4. 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env` 文件，配置必要的参数：

```env
# 应用配置
APP_NAME=视频字幕生成系统
APP_VERSION=1.0.0
DEBUG=True

# 服务器配置
HOST=0.0.0.0
PORT=8000

# 模型配置
# 选择: tiny, base, small, medium, large-v2, large-v3
WHISPER_MODEL=base
# 设备: cpu, cuda
WHISPER_DEVICE=cpu
# 计算精度: float16, int8, int8_float16
WHISPER_COMPUTE_TYPE=int8

# 文件配置
MAX_FILE_SIZE=500
ALLOWED_VIDEO_EXTENSIONS=mp4,avi,mov,mkv,flv,wmv,webm
ALLOWED_AUDIO_EXTENSIONS=mp3,wav,aac,flac,m4a,ogg,wma

# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./srt_generator.db
```

### 5. 构建和启动

#### 方式一：使用脚本（推荐）

```bash
# 构建前端
bash scripts/build.sh

# 启动服务
bash scripts/start.sh
```

#### 方式二：手动启动

**开发模式（前端热更新）：**
```bash
# 终端 1 - 启动后端
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 终端 2 - 启动前端
cd frontend
bun run dev
```

**生产模式：**
```bash
# 构建前端
cd frontend
bun run build
cd ..

# 复制构建产物到后端
rm -rf backend/static/*
cp -r frontend/dist/* backend/static/

# 启动后端
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 6. 访问应用

- **应用首页**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **ReDoc 文档**: http://localhost:8000/redoc

## 使用说明

### 生成字幕流程

1. **上传视频/音频**
   - 点击首页的"选择文件"按钮
   - 或拖拽文件到上传区域
   - 支持的格式：MP4、AVI、MOV、MKV、MP3、WAV 等

2. **选择识别语言**
   - 中文（zh）
   - 英文（en）
   - 日语（ja）
   - 韩语（ko）
   - 等多种语言

3. **开始识别**
   - 点击"开始识别"按钮
   - 等待处理完成（大文件可能需要较长时间）
   - 可以在"任务列表"中查看进度

4. **编辑字幕**
   - 识别完成后自动进入编辑器
   - 可以调整每个字幕块的开始/结束时间
   - 可以修改文本内容
   - 可以删除或添加字幕块

5. **导出 SRT**
   - 点击"导出 SRT"按钮
   - 下载标准格式的字幕文件

### 任务管理

- 在"任务列表"页面查看所有处理记录
- 支持重新编辑已完成的任务
- 支持重新下载 SRT 文件
- 可以删除不需要的任务记录

## 项目结构

```
video-srt-generator/
├── backend/                 # 后端目录
│   ├── app/                # 应用代码
│   │   ├── api/           # API 路由
│   │   ├── core/          # 核心配置
│   │   ├── models/        # 数据模型
│   │   ├── schemas/       # Pydantic 模式
│   │   ├── services/      # 业务逻辑
│   │   └── main.py        # FastAPI 应用入口
│   ├── static/            # 前端构建产物（自动生成）
│   ├── uploads/           # 上传文件存储
│   ├── outputs/           # 输出文件存储
│   ├── tests/             # 测试代码
│   ├── .venv/             # Python 虚拟环境
│   └── pyproject.toml     # Python 项目配置
├── frontend/              # 前端目录
│   ├── src/              # 源代码
│   │   ├── components/   # Vue 组件
│   │   ├── router/       # 路由配置
│   │   ├── stores/       # Pinia 状态管理
│   │   └── main.js       # 应用入口
│   ├── public/           # 静态资源
│   ├── dist/             # 构建产物（自动生成）
│   └── package.json      # Node.js 依赖配置
├── scripts/              # 构建和启动脚本
│   ├── build.sh         # 构建脚本
│   └── start.sh         # 启动脚本
├── docs/                # 项目文档
├── .gitignore          # Git 忽略文件
└── README.md           # 项目说明
```

## 配置说明

### Whisper 模型选择

系统支持多种 Whisper 模型，权衡速度和准确度：

| 模型 | 参数量 | 速度 | 准确度 | 内存占用 |
|------|--------|------|--------|----------|
| tiny | 39M | 最快 | 一般 | ~1GB |
| base | 74M | 快 | 良好 | ~1GB |
| small | 244M | 中等 | 很好 | ~2GB |
| medium | 769M | 慢 | 优秀 | ~5GB |
| large-v2 | 1550M | 很慢 | 卓越 | ~10GB |
| large-v3 | 1550M | 很慢 | 最佳 | ~10GB |

推荐：日常使用选择 `base` 或 `small`，需要高准确度时选择 `medium`。

### 设备选择

- **CPU**: 兼容性好，速度较慢
- **CUDA**: 需要 NVIDIA GPU，速度最快

### 文件大小限制

默认最大 500MB，可在 `.env` 中调整 `MAX_FILE_SIZE` 配置。

## API 文档

启动服务后访问 http://localhost:8000/docs 查看完整的 API 文档（Swagger UI）。

主要 API 端点：

- `POST /api/v1/upload` - 上传文件
- `POST /api/v1/transcribe` - 开始语音识别
- `GET /api/v1/tasks` - 获取任务列表
- `GET /api/v1/tasks/{id}` - 获取任务详情
- `GET /api/v1/tasks/{id}/subtitles` - 获取字幕内容
- `PUT /api/v1/tasks/{id}/subtitles` - 更新字幕内容
- `GET /api/v1/tasks/{id}/download` - 下载 SRT 文件
- `DELETE /api/v1/tasks/{id}` - 删除任务

## 故障排除

### FFmpeg 未找到

**错误**: `ffmpeg: command not found`

**解决**: 安装 FFmpeg 并确保在系统 PATH 中

### CUDA 不可用

**错误**: `CUDA is not available`

**解决**:
1. 检查 NVIDIA 驱动是否安装: `nvidia-smi`
2. 安装 CUDA Toolkit
3. 或在 `.env` 中设置 `WHISPER_DEVICE=cpu`

### 端口被占用

**错误**: `Address already in use`

**解决**:
```bash
# 使用不同端口
PORT=8001 bash scripts/start.sh

# 或杀死占用进程
lsof -ti:8000 | xargs kill -9
```

### 内存不足

**错误**: `Out of memory`

**解决**:
1. 使用更小的模型（tiny/base）
2. 减小音频文件大小
3. 增加系统内存或使用交换空间

## 开发指南

### 前端开发

```bash
cd frontend
bun run dev
```

访问 http://localhost:5173

### 后端开发

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 运行测试

```bash
cd backend
source .venv/bin/activate
pytest
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题或建议，请通过 Issue 联系。
