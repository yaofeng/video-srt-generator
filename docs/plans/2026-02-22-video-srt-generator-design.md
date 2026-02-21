# 视频字幕生成系统 - 设计文档

**日期**: 2026-02-22
**版本**: 1.0
**状态**: 已批准

---

## 1. 概述

本系统是一个 B/S 架构的视频字幕生成系统，使用 fsmn-vad 进行语音活动检测，结合 Qwen3-ASR-1.7B 模型进行语音识别，自动生成带时间戳的 SRT 字幕文件。

### 1.1 技术栈

| 层级 | 技术选择 |
|------|---------|
| 后端框架 | FastAPI |
| 虚拟环境 | uv |
| 音频处理 | ffmpeg |
| VAD 模型 | fsmn-vad |
| ASR 模型 | Qwen3-ASR-1.7B |
| 数据库 | SQLite |
| 前端框架 | Vue 3 + Composition API |
| 包管理器 | Bun |
| 样式 | TailwindCSS |
| 实时通信 | SSE (Server-Sent Events) |
| 路由 | Vue Router |
| 状态管理 | Pinia |

---

## 2. 系统架构

### 2.1 整体架构

```
video-srt-generator/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 配置、安全
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   │   ├── audio.py    # 音频提取
│   │   │   ├── vad.py      # 语音活动检测
│   │   │   ├── asr.py      # 语音识别
│   │   │   └── srt.py      # SRT 生成
│   │   └── main.py         # 应用入口
│   ├── uploads/            # 上传文件临时存储
│   ├── outputs/            # 生成的字幕文件
│   ├── static/             # 前端静态文件（生产环境）
│   └── pyproject.toml      # uv 依赖管理
│
└── frontend/               # Vue3 前端
    ├── src/
    │   ├── components/     # 组件
    │   ├── views/          # 页面
    │   ├── router/         # 路由配置
    │   ├── stores/         # Pinia 状态管理
    │   └── assets/         # 静态资源
    ├── package.json        # Bun 依赖管理
    └── tailwind.config.js
```

### 2.2 架构图

```
┌─────────────────────────────────────────────────────────┐
│                     浏览器                               │
│              Vue3 + TailwindCSS                         │
├─────────────────────────────────────────────────────────┤
│                     FastAPI                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  API 路由   │  │ SSE 推送    │  │  后台任务队列   │  │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
│         │                │                   │          │
│         └────────────────┴───────────────────┘          │
│                          │                              │
│  ┌─────────────┐  ┌──────▼──────┐  ┌─────────────────┐  │
│  │   SQLite    │  │ 文件存储    │  │   AI 模型       │  │
│  │   数据库     │  │ uploads/    │  │ fsmn-vad        │  │
│  │             │  │ outputs/    │  │ qwen3-asr       │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 数据库设计

### 3.1 表结构

```sql
-- 任务表
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    status TEXT NOT NULL,             -- pending/processing/completed/failed
    progress INTEGER DEFAULT 0,
    current_step TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER
);

-- 字幕表
CREATE TABLE subtitles (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    index INTEGER NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    text TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- 切分片段表
CREATE TABLE segments (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    index INTEGER NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    audio_path TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- 日志表
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    level TEXT NOT NULL,              -- info/warning/error
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
```

---

## 4. 核心业务流程

```
用户上传视频
    │
    ▼
创建任务记录 (status: pending)
    │
    ▼
ffmpeg 提取音频
    │
    ▼
fsmn-vad 检测语音活动
    │
    ▼
智能切分音频片段
- 优先在静音处切分
- 单段 3-5 分钟
    │
    ▼
遍历片段执行 ASR
- qwen3-asr-1.7B (token 级别时间戳)
- 失败重试 3 次，全部失败则跳过
    │
    ▼
时间戳转换 & 合并
- token → 句子级别
- 按标点切分
- 时长平衡 2-8 秒
- 合并短字幕
    │
    ▼
生成 SRT 文件
格式: <filename>_字幕.srt
    │
    ▼
保存到数据库 (status: completed)
    │
    ▼
用户可预览/下载
```

---

## 5. API 接口设计

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/tasks/upload` | 上传视频，创建任务 |
| GET | `/api/tasks` | 获取任务列表 |
| GET | `/api/tasks/{id}` | 获取任务详情 |
| POST | `/api/tasks/{id}/start` | 开始生成字幕 |
| GET | `/api/tasks/{id}/events` | SSE 订阅进度事件 |
| GET | `/api/tasks/{id}/subtitles` | 获取字幕列表（分页） |
| GET | `/api/tasks/{id}/subtitles/search` | 搜索字幕（正则） |
| GET | `/api/tasks/{id}/subtitles/filter` | 按时间范围筛选 |
| GET | `/api/tasks/{id}/download` | 下载 SRT 文件 |
| DELETE | `/api/tasks/{id}` | 删除任务及文件 |

### 5.1 SSE 事件格式

```
event: progress
data: {"progress": 45, "step": "正在识别 (3/12)...", "eta": 180}

event: log
data: {"level": "info", "message": "开始处理片段 #3"}

event: complete
data: {"task_id": "xxx", "srt_path": "/outputs/xxx_字幕.srt"}

event: error
data: {"error": "处理失败: xxx"}
```

---

## 6. 前端页面设计

### 6.1 路由结构

```
/                    → 首页（重定向到 /upload）
/upload              → 上传页面
/processing/{id}     → 处理进度页面
/preview/{id}        → 字幕预览页面
```

### 6.2 页面功能

**上传页面** (`/upload`)
- 拖拽上传区域
- 文件选择按钮
- 支持的格式提示

**处理进度页面** (`/processing/:id`)
- 进度环形图 + 百分比
- 当前步骤显示
- 预估剩余时间
- 实时日志终端（可展开/折叠）
- 完成后跳转到预览页面

**预览页面** (`/preview/:id`)
- 顶部：视频播放器 + 字幕同步高亮
- 中部：字幕列表（可滚动）
  - 时间轴、序号、文本
  - 搜索框（正则支持）
  - 时间范围筛选器
- 底部：下载按钮

---

## 7. UI 设计规范

### 7.1 色彩系统

```css
/* 主色调 - 深邃星空 */
--bg-primary: #0a0e1a;          /* 星空黑 */
--bg-secondary: #0f172a;        /* 次级背景 */
--bg-gradient: linear-gradient(135deg, #0a0e1a 0%, #1a1f35 100%);

/* 品牌色 */
--brand-blue: #3b82f6;          /* 科技蓝 - 主色 */
--brand-cyan: #06b6d4;          /* 智慧青 - 辅助 */
--brand-orange: #f97316;        /* 活力橙 - 强调 */
--brand-green: #10b981;         /* 增长绿 - 数据 */

/* 语义色 */
--success: #10b981;
--warning: #f59e0b;
--error: #ef4444;
--info: #3b82f6;

/* 文字色 */
--text-primary: #f1f5f9;
--text-secondary: #94a3b8;
--text-muted: #64748b;
```

### 7.2 视觉效果

- **粒子效果背景**: Canvas 绘制动态粒子，缓慢漂浮
- **玻璃效果**: 半透明背景 + 背景模糊
- **光晕效果**: 蓝色光晕阴影
- **激光脉冲动画**: 按钮和强调元素

### 7.3 响应式断点

```javascript
screens: {
  'xs': '475px',   'sm': '640px',   'md': '768px',
  'lg': '1024px',  'xl': '1280px',  '2xl': '1536px',  '3xl': '1920px'
}
```

---

## 8. 配置参数

### 8.1 后端配置

| 参数 | 值 | 说明 |
|------|-----|------|
| SEGMENT_MIN_DURATION | 180 | 片段最短 3 分钟 |
| SEGMENT_MAX_DURATION | 300 | 片段最长 5 分钟 |
| SUBTITLE_MIN_DURATION | 2.0 | 字幕最短 2 秒 |
| SUBTITLE_MAX_DURATION | 8.0 | 字幕最长 8 秒 |
| SUBTITLE_MERGE_THRESHOLD | 1.5 | 短字幕合并阈值 |
| MAX_RETRY_ATTEMPTS | 3 | 最大重试次数 |
| COMPLETED_RETENTION_HOURS | 24 | 完成任务保留时间 |
| FAILED_RETENTION_HOURS | 6 | 失败任务保留时间 |

### 8.2 前端配置

| 参数 | 值 | 说明 |
|------|-----|------|
| upload.maxSize | 2GB | 最大上传文件大小 |
| upload.allowedTypes | video/* | 支持的视频格式 |
| upload.chunkSize | 5MB | 分块上传大小 |

---

## 9. 部署架构

```bash
# 启动脚本 start.sh
1. 激活 uv 虚拟环境
2. 启动 FastAPI 后台运行
3. 编译 Vue3 前端
4. 复制前端静态文件到 backend/static/
5. FastAPI 服务静态文件

# 单一入口
http://localhost:8000
```

---

## 10. 开发工作流

```bash
# 后端开发
cd backend
uv sync
uv run uvicorn app.main:app --reload

# 前端开发
cd frontend
bun install
bun run dev

# 生产构建
./scripts/build.sh
```

---

## 11. 错误处理

| 错误类型 | 处理策略 |
|---------|---------|
| CUDA OOM | 跳过片段，日志记录 |
| 网络错误 | 重试 3 次 |
| 无效音频 | 跳过片段，日志记录 |
| 模型加载错误 | 终止任务，返回错误 |

---

*文档结束*
