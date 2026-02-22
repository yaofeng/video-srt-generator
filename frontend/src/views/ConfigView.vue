<template>
  <div class="config-view">
    <div class="container">
      <!-- 页面标题 -->
      <div class="page-header">
        <button @click="goBack" class="back-button">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clip-rule="evenodd"/>
          </svg>
        </button>
        <div>
          <h1 class="page-title">系统配置</h1>
          <p class="page-subtitle">调整音频处理和字幕生成参数</p>
        </div>
      </div>

      <!-- 配置表单 -->
      <form @submit.prevent="saveConfig" class="config-form">
        <!-- 音频切分配置 -->
        <section class="config-section">
          <div class="section-header">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </svg>
            <h2>音频切分配置</h2>
          </div>

          <div class="config-grid">
            <div class="config-item">
              <label class="config-label">
                最小片段时长
                <span class="config-value">{{ form.segment_min_duration }} 秒</span>
              </label>
              <input
                v-model.number="form.segment_min_duration"
                type="range"
                min="30"
                max="600"
                step="30"
                class="config-slider"
              />
              <p class="config-hint">音频切分的最小时长，避免过短的片段</p>
            </div>

            <div class="config-item">
              <label class="config-label">
                最大片段时长
                <span class="config-value">{{ form.segment_max_duration }} 秒</span>
              </label>
              <input
                v-model.number="form.segment_max_duration"
                type="range"
                min="60"
                max="1800"
                step="60"
                class="config-slider"
              />
              <p class="config-hint">音频切分的最大时长，避免单个片段过长</p>
            </div>

            <div class="config-item">
              <label class="config-label">
                静音阈值
                <span class="config-value">{{ form.vad_silence_threshold }} 秒</span>
              </label>
              <input
                v-model.number="form.vad_silence_threshold"
                type="range"
                min="0.1"
                max="5.0"
                step="0.1"
                class="config-slider"
              />
              <p class="config-hint">VAD 检测静音的阈值，小于此值的间隔会被合并</p>
            </div>
          </div>
        </section>

        <!-- 字幕生成配置 -->
        <section class="config-section">
          <div class="section-header">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M4 4h16v12H5.17L4 17.17V4m0-2c-1.1 0-2 .9-2 2v12l2 2h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
              <path d="M6 8h2v2H6zm0 3h2v2H6zm0 3h2v2H6zm4-6h8v2h-8zm0 3h8v2h-8zm0 3h8v2h-8z"/>
            </svg>
            <h2>字幕生成配置</h2>
          </div>

          <div class="config-grid">
            <div class="config-item">
              <label class="config-label">
                最短字幕时长
                <span class="config-value">{{ form.subtitle_min_duration }} 秒</span>
              </label>
              <input
                v-model.number="form.subtitle_min_duration"
                type="range"
                min="0.5"
                max="10"
                step="0.5"
                class="config-slider"
              />
              <p class="config-hint">单条字幕的最短显示时长</p>
            </div>

            <div class="config-item">
              <label class="config-label">
                最长字幕时长
                <span class="config-value">{{ form.subtitle_max_duration }} 秒</span>
              </label>
              <input
                v-model.number="form.subtitle_max_duration"
                type="range"
                min="1"
                max="30"
                step="1"
                class="config-slider"
              />
              <p class="config-hint">单条字幕的最长显示时长，超过会被切分</p>
            </div>

            <div class="config-item">
              <label class="config-label">
                合并阈值
                <span class="config-value">{{ form.subtitle_merge_threshold }} 秒</span>
              </label>
              <input
                v-model.number="form.subtitle_merge_threshold"
                type="range"
                min="0.1"
                max="5"
                step="0.1"
                class="config-slider"
              />
              <p class="config-hint">短字幕合并的间隔阈值</p>
            </div>
          </div>
        </section>

        <!-- 重试配置 -->
        <section class="config-section">
          <div class="section-header">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
            </svg>
            <h2>重试配置</h2>
          </div>

          <div class="config-grid">
            <div class="config-item">
              <label class="config-label">
                最大重试次数
                <span class="config-value">{{ form.max_retry_attempts }} 次</span>
              </label>
              <input
                v-model.number="form.max_retry_attempts"
                type="range"
                min="1"
                max="10"
                step="1"
                class="config-slider"
              />
              <p class="config-hint">ASR 识别失败时的最大重试次数</p>
            </div>

            <div class="config-item">
              <label class="config-label">
                基础延迟
                <span class="config-value">{{ form.retry_base_delay }} 秒</span>
              </label>
              <input
                v-model.number="form.retry_base_delay"
                type="range"
                min="0.5"
                max="60"
                step="0.5"
                class="config-slider"
              />
              <p class="config-hint">重试的基础等待时间</p>
            </div>

            <div class="config-item">
              <label class="config-label">
                最大延迟
                <span class="config-value">{{ form.retry_max_delay }} 秒</span>
              </label>
              <input
                v-model.number="form.retry_max_delay"
                type="range"
                min="1"
                max="300"
                step="5"
                class="config-slider"
              />
              <p class="config-hint">重试的最大等待时间</p>
            </div>
          </div>
        </section>

        <!-- 文件清理配置 -->
        <section class="config-section">
          <div class="section-header">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
            </svg>
            <h2>文件清理配置</h2>
          </div>

          <div class="config-grid">
            <div class="config-item full-width">
              <label class="checkbox-label">
                <input
                  v-model="form.auto_cleanup"
                  type="checkbox"
                  class="config-checkbox"
                />
                <span>自动清理文件</span>
                <span class="config-value">{{ form.auto_cleanup ? '开启' : '关闭' }}</span>
              </label>
              <p class="config-hint">自动清理过期的任务文件</p>
            </div>

            <div class="config-item">
              <label class="config-label">
                已完成任务保留时长
                <span class="config-value">{{ form.completed_retention_hours }} 小时</span>
              </label>
              <input
                v-model.number="form.completed_retention_hours"
                type="range"
                min="1"
                max="168"
                step="1"
                class="config-slider"
              />
              <p class="config-hint">已完成任务的文件保留时间</p>
            </div>

            <div class="config-item">
              <label class="config-label">
                失败任务保留时长
                <span class="config-value">{{ form.failed_retention_hours }} 小时</span>
              </label>
              <input
                v-model.number="form.failed_retention_hours"
                type="range"
                min="1"
                max="72"
                step="1"
                class="config-slider"
              />
              <p class="config-hint">失败任务的文件保留时间</p>
            </div>
          </div>
        </section>

        <!-- 翻译配置 -->
        <section class="config-section">
          <div class="section-header">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12.87 15.07l-2.54-2.51.03-.03A17.52 17.52 0 0014.07 6H17V4h-7V2H8v2H1v2h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z"/>
            </svg>
            <h2>翻译配置</h2>
          </div>

          <div class="config-grid">
            <div class="config-item full-width">
              <label class="config-label">默认目标语言</label>
              <select v-model="form.default_target_language" class="config-select">
                <option value="en">英语</option>
                <option value="ja">日语</option>
                <option value="ko">韩语</option>
                <option value="fr">法语</option>
                <option value="de">德语</option>
                <option value="es">西班牙语</option>
                <option value="zh_hant">繁体中文</option>
              </select>
              <p class="config-hint">自动翻译时的默认目标语言</p>
            </div>

            <div class="config-item full-width">
              <label class="config-label">LLM API Base URL</label>
              <input
                v-model="form.llm_api_base"
                type="text"
                class="config-input"
                placeholder="https://api.openai.com/v1"
              />
              <p class="config-hint">大语言模型的 API 地址（支持 OpenAI 兼容接口）</p>
            </div>

            <div class="config-item full-width">
              <label class="config-label">LLM API Key</label>
              <input
                v-model="form.llm_api_key"
                type="password"
                class="config-input"
                placeholder="sk-..."
              />
              <p class="config-hint">大语言模型的 API 密钥</p>
            </div>

            <div class="config-item full-width">
              <label class="config-label">模型名称</label>
              <input
                v-model="form.llm_model"
                type="text"
                class="config-input"
                placeholder="gpt-4"
              />
              <p class="config-hint">使用的翻译模型名称</p>
            </div>

            <div class="config-item">
              <label class="config-label">
                分组时间间隔
                <span class="config-value">{{ form.translation_group_interval }} 秒</span>
              </label>
              <input
                v-model.number="form.translation_group_interval"
                type="range"
                min="1"
                max="10"
                step="0.5"
                class="config-slider"
              />
              <p class="config-hint">字幕分组的时间间隔阈值</p>
            </div>

            <div class="config-item">
              <label class="config-label">
                每组最大句数
                <span class="config-value">{{ form.translation_max_sentences }} 句</span>
              </label>
              <input
                v-model.number="form.translation_max_sentences"
                type="range"
                min="3"
                max="8"
                step="1"
                class="config-slider"
              />
              <p class="config-hint">每组字幕的最大句数</p>
            </div>
          </div>
        </section>

        <!-- 操作按钮 -->
        <div class="config-actions">
          <button type="submit" class="save-button" :disabled="saving">
            <svg v-if="!saving" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/>
            </svg>
            <span v-if="saving">保存中...</span>
            <span v-else>保存配置</span>
          </button>

          <button type="button" @click="resetConfig" class="reset-button">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01-.61-1.276z" clip-rule="evenodd"/>
            </svg>
            重置为默认值
          </button>
        </div>

        <!-- 提示信息 -->
        <div class="config-note">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
          </svg>
          <p>配置修改仅在服务运行期间有效，重启后将恢复为原值。要永久修改配置，请更新后端的 .env 文件。</p>
        </div>
      </form>

      <!-- 保存成功提示 -->
      <div v-if="showSuccess" class="success-toast">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
        </svg>
        <span>配置保存成功</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const form = ref({
  segment_min_duration: 60,
  segment_max_duration: 180,
  vad_silence_threshold: 0.5,

  subtitle_min_duration: 2.0,
  subtitle_max_duration: 8.0,
  subtitle_merge_threshold: 1.5,

  max_retry_attempts: 3,
  retry_base_delay: 1.0,
  retry_max_delay: 10.0,

  auto_cleanup: true,
  completed_retention_hours: 24,
  failed_retention_hours: 6,

  // 翻译配置
  default_target_language: 'en',
  llm_api_base: '',
  llm_api_key: '',
  llm_model: '',
  translation_group_interval: 3.0,
  translation_max_sentences: 5,
})

const originalForm = ref({})
const saving = ref(false)
const showSuccess = ref(false)

// 加载配置
const loadConfig = async () => {
  try {
    const response = await fetch(`${API_BASE}/api/config/`)
    if (!response.ok) throw new Error('获取配置失败')
    const config = await response.json()
    form.value = { ...config }
    originalForm.value = { ...config }
  } catch (error) {
    console.error('加载配置失败:', error)
  }
}

// 保存配置
const saveConfig = async () => {
  saving.value = true

  try {
    const response = await fetch(`${API_BASE}/api/config/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(form.value),
    })

    if (!response.ok) throw new Error('保存配置失败')

    const result = await response.json()
    console.log('保存结果:', result)

    // 显示成功提示
    showSuccess.value = true
    setTimeout(() => {
      showSuccess.value = false
    }, 2000)

    // 更新原始配置
    originalForm.value = { ...form.value }
  } catch (error) {
    console.error('保存配置失败:', error)
    alert('保存配置失败: ' + error.message)
  } finally {
    saving.value = false
  }
}

// 重置配置
const resetConfig = () => {
  if (confirm('确定要重置为默认值吗？')) {
    form.value = { ...originalForm.value }
  }
}

// 返回上一页
const goBack = () => {
  router.back()
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.config-view {
  min-height: 100vh;
  padding: 2rem;
}

.container {
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.back-button {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 0.5rem;
  color: var(--brand-blue);
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-button:hover {
  background: rgba(59, 130, 246, 0.2);
  transform: translateX(-2px);
}

.page-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.page-subtitle {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 0.25rem 0 0 0;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.config-section {
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 1rem;
  padding: 1.5rem;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
}

.section-header svg {
  color: var(--brand-cyan);
}

.section-header h2 {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.config-item.full-width {
  grid-column: 1 / -1;
}

.config-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.config-value {
  color: var(--brand-cyan);
  font-weight: 600;
  font-size: 0.875rem;
}

.config-slider {
  width: 100%;
  height: 6px;
  background: rgba(59, 130, 246, 0.2);
  border-radius: 3px;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
}

.config-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  background: linear-gradient(135deg, var(--brand-blue), var(--brand-cyan));
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
  transition: transform 0.2s ease;
}

.config-slider::-webkit-slider-thumb:hover {
  transform: scale(1.1);
}

.config-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  background: linear-gradient(135deg, var(--brand-blue), var(--brand-cyan));
  border: none;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
  transition: transform 0.2s ease;
}

.config-slider::-moz-range-thumb:hover {
  transform: scale(1.1);
}

.config-select,
.config-input {
  width: 100%;
  padding: 0.75rem 1rem;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 0.5rem;
  color: var(--text-primary);
  font-size: 0.875rem;
  transition: all 0.3s ease;
}

.config-select:focus,
.config-input:focus {
  outline: none;
  border-color: var(--brand-blue);
  background: rgba(59, 130, 246, 0.15);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.config-select {
  cursor: pointer;
}

.config-input::placeholder {
  color: var(--text-muted);
}

.config-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin: 0;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: rgba(59, 130, 246, 0.05);
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.checkbox-label:hover {
  background: rgba(59, 130, 246, 0.1);
}

.config-checkbox {
  width: 18px;
  height: 18px;
  accent: var(--brand-blue);
}

.config-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1rem;
}

.save-button,
.reset-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
}

.save-button {
  background: linear-gradient(135deg, var(--brand-blue), var(--brand-cyan));
  color: white;
}

.save-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(59, 130, 246, 0.3);
}

.save-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.reset-button {
  background: rgba(239, 68, 68, 0.1);
  color: var(--error);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.reset-button:hover {
  background: rgba(239, 68, 68, 0.2);
  transform: translateY(-2px);
}

.config-note {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  background: rgba(6, 182, 212, 0.1);
  border: 1px solid rgba(6, 182, 212, 0.2);
  border-radius: 0.5rem;
  color: var(--brand-cyan);
  font-size: 0.875rem;
}

.config-note svg {
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.config-note p {
  margin: 0;
  line-height: 1.6;
}

.success-toast {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 0.5rem;
  color: var(--brand-green);
  font-weight: 500;
  animation: slideIn 0.3s ease;
  z-index: 1000;
}

@keyframes slideIn {
  from {
    transform: translateY(100px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .config-view {
    padding: 1rem;
  }

  .config-grid {
    grid-template-columns: 1fr;
  }

  .config-actions {
    flex-direction: column;
  }

  .save-button,
  .reset-button {
    width: 100%;
    justify-content: center;
  }

  .success-toast {
    left: 1rem;
    right: 1rem;
    bottom: 1rem;
  }
}
</style>
