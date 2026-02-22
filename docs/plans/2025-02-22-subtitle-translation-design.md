# 字幕翻译功能设计文档

**创建日期**: 2025-02-22
**作者**: Claude Code
**状态**: 设计阶段

---

## 1. 概述

### 1.1 目标

在现有视频字幕生成系统基础上，增加字幕翻译功能，支持将生成的字幕翻译成多种语言，并允许用户在预览时切换查看不同语言版本。

### 1.2 核心需求

- 将字幕内容按时间间隔进行分组（每组3-5句）
- 使用大语言模型（LLM）进行批量翻译
- 支持多种语言同时存储和切换显示
- 在字幕预览页面可以切换原始语言和翻译后的语言
- LLM 配置通过环境变量管理（`llm_api_base`、`llm_api_key`、`model_name`）

### 1.3 用户交互流程

1. **上传阶段**：用户勾选"自动翻译"选项
2. **生成阶段**：字幕生成完成后，自动创建翻译任务
3. **翻译阶段**：后台异步执行翻译，通过 SSE 推送进度
4. **预览阶段**：用户可以切换语言查看字幕
5. **下载阶段**：用户可选择下载原始字幕或翻译后的字幕

---

## 2. 架构设计

### 2.1 整体架构

采用**独立翻译任务**架构，将翻译功能作为独立的后台任务，与字幕生成任务分离。

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  上传视频    │ ───> │  字幕生成任务  │ ───> │  字幕完成    │
└─────────────┘      └──────────────┘      └─────────────┘
                                                  │
                                                  ▼
                                         ┌──────────────┐
                                         │  翻译任务     │
                                         │  (独立任务)   │
                                         └──────────────┘
                                                  │
                    ┌─────────────────────────────┼─────────────────────────────┐
                    ▼                             ▼                             ▼
             ┌─────────────┐              ┌─────────────┐              ┌─────────────┐
             │  英语翻译    │              │  日语翻译    │              │  其他语言    │
             └─────────────┘              └─────────────┘              └─────────────┘
```

### 2.2 核心组件

| 组件 | 职责 | 文件位置 |
|-----|-----|---------|
| 翻译服务 | 处理 LLM 调用和字幕分组 | `backend/app/services/translation.py` |
| 翻译任务处理器 | 管理翻译任务生命周期 | `backend/app/services/task_processor.py` |
| 翻译 API | 提供 REST 接口 | `backend/app/api/translation.py` |
| 数据库模型 | 翻译任务和多语言字段 | `backend/app/models/` |
| 前端翻译组件 | UI 交互和进度显示 | `frontend/src/components/` |
| 配置管理 | LLM 配置和翻译参数 | `backend/app/core/config.py` |

---

## 3. 数据库设计

### 3.1 subtitles 表扩展

为现有的 `subtitles` 表添加多语言字段：

```sql
ALTER TABLE subtitles ADD COLUMN translated_text_en TEXT;
ALTER TABLE subtitles ADD COLUMN translated_text_ja TEXT;
ALTER TABLE subtitles ADD COLUMN translated_text_ko TEXT;
ALTER TABLE subtitles ADD COLUMN translated_text_fr TEXT;
ALTER TABLE subtitles ADD COLUMN translated_text_de TEXT;
ALTER TABLE subtitles ADD COLUMN translated_text_es TEXT;
ALTER TABLE subtitles ADD COLUMN translated_text_zh_hant TEXT;
ALTER TABLE subtitles ADD COLUMN translation_languages TEXT; -- JSON数组，存储已翻译的语言列表
```

**字段说明**：
- `translated_text_en`: 英语翻译
- `translated_text_ja`: 日语翻译
- `translated_text_ko`: 韩语翻译
- `translated_text_fr`: 法语翻译
- `translated_text_de`: 德语翻译
- `translated_text_es`: 西班牙语翻译
- `translated_text_zh_hant`: 繁体中文翻译
- `translation_languages`: JSON 数组，如 `["en", "ja"]`

### 3.2 translation_tasks 表（新增）

```sql
CREATE TABLE translation_tasks (
    id VARCHAR(36) PRIMARY KEY,
    parent_task_id VARCHAR(36) NOT NULL,
    target_language VARCHAR(10) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    current_step VARCHAR(100),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (parent_task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX idx_translation_tasks_parent ON translation_tasks(parent_task_id);
CREATE INDEX idx_translation_tasks_status ON translation_tasks(status);
```

**字段说明**：
- `id`: 翻译任务唯一标识（UUID）
- `parent_task_id`: 关联的原始字幕生成任务 ID
- `target_language`: 目标语言代码（en, ja, ko 等）
- `status`: 任务状态（pending/processing/completed/failed）
- `progress`: 翻译进度（0-100）
- `current_step`: 当前步骤描述
- `started_at`: 开始时间
- `completed_at`: 完成时间
- `error_message`: 错误信息（失败时）

---

## 4. 后端设计

### 4.1 翻译服务 (`translation.py`)

#### 4.1.1 字幕分组策略

按**时间间隔**进行分组：

```python
async def group_subtitles_by_interval(
    subtitles: List[Subtitle],
    interval_threshold: float = 3.0
) -> List[List[Subtitle]]:
    """
    按时间间隔分组字幕

    Args:
        subtitles: 字幕列表
        interval_threshold: 时间间隔阈值（秒）

    Returns:
        分组后的字幕列表
    """
    groups = []
    current_group = [subtitles[0]]

    for i in range(1, len(subtitles)):
        interval = subtitles[i].start_time - subtitles[i-1].end_time

        if interval >= interval_threshold or len(current_group) >= 5:
            # 时间间隔超过阈值或已达到最大句数，结束当前组
            groups.append(current_group)
            current_group = [subtitles[i]]
        else:
            # 继续累积到当前组
            current_group.append(subtitles[i])

    if current_group:
        groups.append(current_group)

    return groups
```

#### 4.1.2 LLM 翻译调用

使用 OpenAI 兼容 API：

```python
async def translate_with_llm(
    texts: List[str],
    target_language: str,
    api_base: str,
    api_key: str,
    model: str
) -> List[str]:
    """
    使用 LLM 翻译文本

    Args:
        texts: 待翻译文本列表
        target_language: 目标语言
        api_base: API Base URL
        api_key: API Key
        model: 模型名称

    Returns:
        翻译结果列表
    """
    import openai

    client = openai.AsyncOpenAI(
        base_url=api_base,
        api_key=api_key
    )

    # 构建提示词
    language_names = {
        'en': '英语', 'ja': '日语', 'ko': '韩语',
        'fr': '法语', 'de': '德语', 'es': '西班牙语'
    }

    prompt = f"""请将以下字幕翻译成{language_names.get(target_language, target_language)}，要求：
1. 保持原文的语气和风格
2. 准确传达原意，不要意译
3. 只返回翻译结果，每行对应一句原文

原文：
{chr(10).join(texts)}

翻译："""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个专业的字幕翻译助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            timeout=30
        )

        result = response.choices[0].message.content.strip()
        return result.split('\n')

    except asyncio.TimeoutError:
        raise TranslationError("翻译请求超时")
    except Exception as e:
        raise TranslationError(f"翻译失败: {str(e)}")
```

#### 4.1.3 翻译任务处理

```python
async def process_translation_task(
    translation_task_id: str,
    parent_task_id: str,
    target_language: str,
    db: Session,
    progress_queue: asyncio.Queue
) -> dict:
    """处理翻译任务"""

    # 1. 获取原始字幕
    subtitles = get_subtitles_by_task(db, parent_task_id)

    # 2. 分组
    groups = await group_subtitles_by_interval(
        subtitles,
        settings.TRANSLATION_GROUP_INTERVAL
    )

    await _log(db, translation_task_id, 'info',
               f'字幕已分为 {len(groups)} 组', progress_queue)

    # 3. 逐组翻译
    translated_count = 0
    failed_groups = []

    for i, group in enumerate(groups):
        await progress_queue.put(ProgressEvent('progress', {
            'progress': int(100 * i / len(groups)),
            'step': f'正在翻译第 {i+1}/{len(groups)} 组...'
        }))

        texts = [s.text for s in group]

        # 重试逻辑
        for attempt in range(settings.TRANSLATION_RETRY_ATTEMPTS):
            try:
                translations = await translate_with_llm(
                    texts, target_language,
                    settings.LLM_API_BASE,
                    settings.LLM_API_KEY,
                    settings.LLM_MODEL
                )

                # 保存翻译结果
                for subtitle, translation in zip(group, translations):
                    field_name = f'translated_text_{target_language}'
                    setattr(subtitle, field_name, translation)

                translated_count += len(group)
                break

            except Exception as e:
                if attempt == settings.TRANSLATION_RETRY_ATTEMPTS - 1:
                    failed_groups.append(i)
                    await _log(db, translation_task_id, 'error',
                              f'第 {i+1} 组翻译失败: {str(e)}', progress_queue)
                else:
                    await asyncio.sleep(2 ** attempt)

    # 4. 更新字幕的翻译语言列表
    update_translation_languages(db, parent_task_id, target_language)

    # 5. 生成翻译后的 SRT 文件
    srt_path = await generate_translated_srt(
        db, parent_task_id, target_language
    )

    return {
        'status': 'completed',
        'translated_count': translated_count,
        'failed_groups': failed_groups,
        'srt_path': srt_path
    }
```

### 4.2 API 端点设计

```python
# backend/app/api/translation.py

from fastapi import APIRouter, HTTPException
from ..services.translation import process_translation_task

router = APIRouter()

@router.post("/tasks/{task_id}/translate")
async def create_translation_task(
    task_id: str,
    target_language: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    创建翻译任务

    Args:
        task_id: 原始任务 ID
        target_language: 目标语言（en, ja, ko 等）

    Returns:
        翻译任务信息
    """

    # 1. 验证原始任务存在且已完成
    parent_task = get_task(db, task_id)
    if not parent_task or parent_task.status != 'completed':
        raise HTTPException(400, "原始任务不存在或未完成")

    # 2. 检查是否已存在相同语言的翻译任务
    existing = get_translation_task(db, task_id, target_language)
    if existing and existing.status != 'failed':
        raise HTTPException(400, f"已存在 {target_language} 语言的翻译任务")

    # 3. 创建翻译任务
    translation_task_id = str(uuid.uuid4())
    translation_task = TranslationTask(
        id=translation_task_id,
        parent_task_id=task_id,
        target_language=target_language,
        status='pending'
    )
    db.add(translation_task)
    db.commit()

    # 4. 启动后台翻译任务
    progress_queue = asyncio.Queue()
    background_tasks.add_task(
        process_translation_task,
        translation_task_id, task_id, target_language,
        db, progress_queue
    )

    return {
        "translation_task_id": translation_task_id,
        "status": "pending",
        "message": "翻译任务已创建"
    }

@router.get("/tasks/{task_id}/translations")
async def get_translations(task_id: str, db: Session = Depends(get_db)):
    """获取任务的所有翻译"""
    translations = db.query(TranslationTask).filter(
        TranslationTask.parent_task_id == task_id
    ).all()

    return {
        "translations": [
            {
                "language": t.target_language,
                "status": t.status,
                "created_at": t.created_at,
                "progress": t.progress
            }
            for t in translations
        ]
    }

@router.get("/tasks/{task_id}/stream-translation")
async def stream_translation_progress(
    task_id: str,
    target_language: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """SSE 流式推送翻译进度"""
    # 复用现有 SSE 机制

@router.get("/tasks/{task_id}/download-srt")
async def download_translated_srt(
    task_id: str,
    lang: str = None,
    db: Session = Depends(get_db)
):
    """下载指定语言的 SRT 文件"""
    if not lang:
        # 返回原始字幕 SRT
        pass
    else:
        # 返回翻译后的 SRT
        pass
```

### 4.3 配置扩展

```python
# backend/app/core/config.py

class Settings(BaseSettings):
    # ... 现有配置 ...

    # LLM API 配置
    LLM_API_BASE: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""

    # 翻译配置
    DEFAULT_TARGET_LANGUAGE: str = "en"
    TRANSLATION_GROUP_INTERVAL: float = 3.0
    TRANSLATION_MAX_SENTENCES_PER_GROUP: int = 5
    TRANSLATION_RETRY_ATTEMPTS: int = 3
    TRANSLATION_TIMEOUT: int = 30

    # 支持的语言列表
    SUPPORTED_LANGUAGES: List[dict] = [
        {"code": "en", "name": "英语"},
        {"code": "ja", "name": "日语"},
        {"code": "ko", "name": "韩语"},
        {"code": "fr", "name": "法语"},
        {"code": "de", "name": "德语"},
        {"code": "es", "name": "西班牙语"},
        {"code": "zh_hant", "name": "繁体中文"}
    ]
```

---

## 5. 前端设计

### 5.1 上传页面修改

**文件**: `frontend/src/views/UploadView.vue`

在表单中添加：
```vue
<div class="upload-options">
  <label class="checkbox-label">
    <input type="checkbox" v-model="autoTranslate" />
    <span>自动翻译为 {{ config.defaultTargetLanguage }}</span>
  </label>
</div>
```

### 5.2 预览页面修改

**文件**: `frontend/src/views/PreviewView.vue`

添加语言切换器和下载选项：

```vue
<template>
  <div class="header">
    <!-- 语言切换器 -->
    <div class="language-tabs">
      <button
        v-for="lang in availableLanguages"
        :key="lang.code"
        :class="['tab', { active: currentLanguage === lang.code }]"
        @click="switchLanguage(lang.code)"
      >
        {{ lang.name }}
      </button>
    </div>

    <!-- 下载按钮改为下拉菜单 -->
    <div class="download-dropdown">
      <button @click="toggleDownloadMenu" class="download-button">
        下载 SRT
        <svg>▼</svg>
      </button>
      <div v-if="showDownloadMenu" class="download-menu">
        <button @click="downloadSrt('original')">下载原文</button>
        <button
          v-for="lang in translatedLanguages"
          :key="lang"
          @click="downloadSrt(lang)"
        >
          下载{{ getLanguageName(lang) }}
        </button>
      </div>
    </div>

    <!-- 翻译按钮（如果没有翻译） -->
    <button
      v-if="!hasTranslation"
      @click="startTranslation"
      class="translate-button"
    >
      翻译字幕
    </button>
  </div>

  <!-- 翻译进度模态框 -->
  <div v-if="translationInProgress" class="translation-modal">
    <div class="modal-content">
      <h3>正在翻译...</h3>
      <div class="progress-bar">
        <div class="progress" :style="{ width: translationProgress + '%' }"></div>
      </div>
      <p>{{ translationStep }}</p>
    </div>
  </div>
</template>

<script setup>
const currentLanguage = ref('original')
const availableLanguages = ref([
  { code: 'original', name: '原文' },
  { code: 'en', name: '英语' },
  { code: 'ja', name: '日语' }
])

const switchLanguage = (lang) => {
  currentLanguage.value = lang
  // 重新加载字幕数据
  loadSubtitles(lang)
}

const loadSubtitles = async (lang) => {
  const response = await axios.get(
    `${API_BASE}/api/tasks/${taskId}/subtitles?lang=${lang}`
  )
  subtitles.value = response.data.subtitles
}
</script>
```

### 5.3 配置页面扩展

**文件**: `frontend/src/views/ConfigView.vue`

添加翻译配置区域：

```vue
<section class="config-section">
  <h2>翻译配置</h2>

  <!-- 目标语言 -->
  <div class="config-item">
    <label>默认目标语言</label>
    <select v-model="form.defaultTargetLanguage">
      <option value="en">英语</option>
      <option value="ja">日语</option>
      <option value="ko">韩语</option>
      <option value="fr">法语</option>
      <option value="de">德语</option>
      <option value="es">西班牙语</option>
    </select>
  </div>

  <!-- LLM API 配置 -->
  <div class="config-item">
    <label>LLM API Base URL</label>
    <input type="text" v-model="form.llmApiBase" placeholder="https://api.openai.com/v1" />
  </div>

  <div class="config-item">
    <label>LLM API Key</label>
    <input type="password" v-model="form.llmApiKey" placeholder="sk-..." />
  </div>

  <div class="config-item">
    <label>模型名称</label>
    <input type="text" v-model="form.llmModel" placeholder="gpt-4" />
  </div>

  <!-- 分组配置 -->
  <div class="config-item">
    <label>分组时间间隔 (秒): {{ form.translationGroupInterval }}</label>
    <input
      type="range"
      v-model.number="form.translationGroupInterval"
      min="1"
      max="10"
      step="0.5"
    />
  </div>

  <div class="config-item">
    <label>每组最大句数: {{ form.translationMaxSentences }}</label>
    <input
      type="range"
      v-model.number="form.translationMaxSentences"
      min="3"
      max="8"
    />
  </div>
</section>
```

---

## 6. 错误处理

### 6.1 翻译失败处理

| 场景 | 处理策略 |
|-----|---------|
| 单组翻译失败 | 记录失败组索引，跳过继续翻译下一组 |
| 超过30%组失败 | 标记整个翻译任务为失败 |
| API 调用超时 | 自动重试，最多3次 |
| API Key 无效 | 立即终止任务，提示用户检查配置 |
| LLM 服务不可用 | 显示友好错误提示，提供重试按钮 |

### 6.2 降级策略

- 保留已翻译的部分，支持断点续传
- 提供手动重新翻译功能
- 翻译失败不影响原始字幕的使用

---

## 7. 实施计划

### 7.1 开发阶段

1. **数据库迁移**
   - 执行表结构变更
   - 创建翻译任务表

2. **后端开发**
   - 实现翻译服务
   - 添加 API 端点
   - 扩展配置管理

3. **前端开发**
   - 修改上传页面
   - 扩展预览页面
   - 更新配置页面

4. **测试验证**
   - 单元测试
   - 集成测试
   - 端到端测试

### 7.2 依赖库

后端新增依赖：
```
openai>=1.0.0
```

---

## 8. 附录

### 8.1 语言代码对照表

| 代码 | 语言 | 字段后缀 |
|-----|-----|---------|
| en | 英语 | `_en` |
| ja | 日语 | `_ja` |
| ko | 韩语 | `_ko` |
| fr | 法语 | `_fr` |
| de | 德语 | `_de` |
| es | 西班牙语 | `_es` |
| zh_hant | 繁体中文 | `_zh_hant` |

### 8.2 环境变量

```bash
# LLM API 配置
export llm_api_base="https://api.openai.com/v1"
export llm_api_key="sk-..."
export model_name="gpt-4"
```

---

> **下一步**: 使用 `superpowers:writing-plans` 创建详细的实施计划。
