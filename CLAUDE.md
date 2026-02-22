# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 B/S 架构的视频字幕生成系统，使用 FSMN-VAD 进行语音活动检测，Qwen3-ASR-1.7B 进行语音识别，生成带时间戳的 SRT 字幕文件。

- **后端**: Python + FastAPI + SQLite，使用 uv 管理依赖
- **前端**: Vue 3 + TailwindCSS + Pinia，使用 Bun 管理依赖

## 关键注意事项（必须遵守）

### 执行命令的目录要求

⚠️ **非常重要**: 执行命令时必须在正确的目录中：

- **后端命令**（uv、python 等）：必须在 `backend/` 目录中执行
- **前端命令**（bun、npm 等）：必须在 `frontend/` 目录中执行

```bash
# 后端示例
cd backend
uv run python -m app.main
uv sync

# 前端示例
cd frontend
bun run dev
bun run build
```

### Git 提交消息语言

所有 Git 提交消息必须使用**中文**。

## 开发命令

### 后端（在 `backend/` 目录执行）

```bash
# 安装/更新依赖
uv sync

# 启动开发服务器
uv run python -m app.main

# 运行测试
uv run pytest

# 检查 Python 语法
uv run python -m py_compile app/services/asr.py
```

### 前端（在 `frontend/` 目录执行）

```bash
# 安装依赖
bun install

# 启动开发服务器
bun run dev

# 构建生产版本
bun run build
```

## 核心架构

### 字幕生成流程

1. **音频提取** (`services/audio.py`): 使用 ffmpeg 从视频中提取音频，转换为 16kHz WAV 格式
2. **VAD 语音活动检测** (`services/vad.py`): 使用 **FunASR 的 fsmn-vad 模型**检测语音片段
3. **音频切分** (`services/vad.py`): 以 5 分钟为单位，找出最大间隔进行切分，目标时长 3-5 分钟
4. **ASR 语音识别** (`services/asr.py`): 使用 **qwen-asr 包的 Qwen3ASRModel** + **Qwen3ForcedAligner** 识别语音并获取字符级时间戳
5. **时间戳转换** (`services/asr.py`): 将字符级时间戳按标点符号合并成句子级
6. **SRT 生成** (`services/srt.py`): 生成 SRT 格式字幕文件，包含合并短字幕、分割长字幕等处理

### 关键技术实现

#### FSMN-VAD 使用方式

```python
from funasr import AutoModel

model = AutoModel(model="fsmn-vad", model_revision="v2.0.4")
vad_result = model.generate(input=[waveform], batch_size_s=300)
# 实际返回格式: [{'value': [[start_ms, end_ms], ...]}]
# 注意: value 是嵌套列表，每个元素是 [start_ms, end_ms]
# 也可能支持字典格式: {'value': [{'start': ms, 'end': ms}, ...]}
# 解析时需要同时处理两种格式
```

#### Qwen3-ASR 使用方式

```python
from qwen_asr import Qwen3ASRModel

model = Qwen3ASRModel.from_pretrained(
    "Qwen/Qwen3-ASR-1.7B",
    forced_aligner="Qwen/Qwen3-ForcedAligner-0.6B",
    dtype=torch.float16,
    device_map="cuda:0",
)

results = model.transcribe(
    audio=str(audio_path),
    language="Chinese",
    return_time_stamps=True,  # 启用时间戳
)

# result.time_stamps 是 ForcedAlignItem 列表
# 每个 ForcedAlignItem 包含: text, start_time, end_time
```

### 数据库模型

使用 **同步 SQLAlchemy**（非 async），位于 `models/` 目录：
- `Task`: 任务表
- `Segment`: 音频片段表
- `Subtitle`: 字幕表
- `Log`: 日志表

### 模型存储路径

所有模型权重文件存放在 `/home/ubuntu/workspace/checkpoints/<owner>/<model_name>/`：
- FSMN-VAD: 自动从远程下载
- Qwen3-ASR-1.7B: `/home/ubuntu/workspace/checkpoints/Qwen/Qwen3-ASR-1.7B`
- Qwen3-ForcedAligner-0.6B: `/home/ubuntu/workspace/checkpoints/Qwen/Qwen3-ForcedAligner-0.6B`

### 任务处理流程

1. 用户上传视频 → 创建 Task 记录（状态: pending）
2. 后台任务处理器 → 更新状态为 processing
3. SSE 实时推送进度事件
4. 完成后生成 SRT 文件 → 状态更新为 completed
5. 失败时记录错误信息 → 状态更新为 failed

### API 路由

- `POST /api/upload/`: 上传视频文件
- `GET/POST /api/tasks/`: 获取/创建任务
- `GET /api/tasks/{id}`: 获取单个任务详情
- `GET /api/tasks/{id}/events`: SSE 实时进度推送
- `GET /api/tasks/{id}/download`: 下载 SRT 字幕文件
- `GET /health`: 健康检查

### 前端路由

- `/`: 上传页面
- `/processing`: 处理进度页面（SSE 实时更新）
- `/preview`: 字幕预览和搜索页面

### 配置参数

在 `backend/app/core/config.py` 中：
- `SEGMENT_MIN_DURATION`: 60 秒（1 分钟）
- `SEGMENT_MAX_DURATION`: 180 秒（3 分钟）
- `SUBTITLE_MIN_DURATION`: 2.0 秒
- `SUBTITLE_MAX_DURATION`: 8.0 秒
- `SUBTITLE_MERGE_THRESHOLD`: 1.5 秒（合并短字幕阈值）
- `MAX_RETRY_ATTEMPTS`: 3（ASR 识别失败重试次数）

## 复杂算法验证规范

当遇到复杂的算法实现或不确定模型返回格式时，**必须先编写独立的验证脚本**进行测试，验证通过后再集成到正式功能中。

### 适用场景

- 新的模型 API 调用（如 VAD、ASR 等模型）
- 不确定的数据格式解析
- 复杂的时间戳处理算法
- 音频/视频处理逻辑

### 验证脚本规范

1. **脚本位置**: 放在 `backend/` 目录根目录，命名格式为 `<功能>_test.py`
2. **脚本内容**:
   - 独立运行，不依赖服务框架
   - 包含详细的日志输出
   - 测试真实数据文件
   - 输出完整的结果分析

3. **示例参考**: `backend/vad_test.py` - VAD 语音活动检测验证脚本

### 验证流程

```bash
# 1. 编写验证脚本
# 例如: backend/vad_test.py

# 2. 运行验证脚本
cd backend
uv run python vad_test.py

# 3. 分析输出结果，确认算法正确

# 4. 将验证通过的代码集成到正式模块
# 例如: app/services/vad.py

# 5. 验证脚本可保留作为文档和回归测试
```

### 典型案例：VAD 格式解析

 fsmn-vad 模型返回的实际格式是嵌套列表 `{'value': [[start_ms, end_ms], ...]}`，而非文档中描述的字典格式。通过编写 `vad_test.py` 验证脚本发现了这个差异，从而正确实现了解析逻辑。
