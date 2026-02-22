<template>
  <div class="processing-view">
    <div class="container">
      <!-- 进度环形图 -->
      <div class="progress-section">
        <div class="progress-ring">
          <svg width="280" height="280" viewBox="0 0 280 280">
            <!-- 背景圆环 -->
            <circle
              cx="140"
              cy="140"
              r="120"
              fill="none"
              stroke="rgba(59, 130, 246, 0.2)"
              stroke-width="12"
            />

            <!-- 进度圆环 -->
            <circle
              cx="140"
              cy="140"
              r="120"
              fill="none"
              :stroke="progressColor"
              stroke-width="12"
              stroke-linecap="round"
              :stroke-dasharray="circumference"
              :stroke-dashoffset="strokeDashoffset"
              transform="rotate(-90 140 140)"
              class="progress-circle"
            />

            <!-- 内部装饰圆 -->
            <circle
              cx="140"
              cy="140"
              r="100"
              fill="none"
              stroke="rgba(6, 182, 212, 0.1)"
              stroke-width="2"
            />

            <circle
              cx="140"
              cy="140"
              r="80"
              fill="none"
              stroke="rgba(6, 182, 212, 0.05)"
              stroke-width="1"
            />
          </svg>

          <!-- 中心百分比 -->
          <div class="progress-center">
            <span class="progress-percent">{{ progress }}%</span>
            <span class="progress-label">{{ statusLabel }}</span>
          </div>
        </div>

        <!-- 当前步骤 -->
        <div class="step-info">
          <div class="step-icon">
            <component :is="stepIcon" />
          </div>
          <h2 class="step-title">{{ currentStep || '准备中...' }}</h2>
          <p v-if="eta" class="step-eta">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 0a8 8 0 100 16A8 8 0 008 0zM7 4.5a.5.5 0 011 0v3.793l2.146 2.147a.5.5 0 01-.708.708L7 8.707V4.5z"/>
            </svg>
            预计剩余时间：{{ formatEta(eta) }}
          </p>
        </div>
      </div>

      <!-- 日志终端 -->
      <div class="logs-section">
        <div class="logs-header" @click="toggleLogs">
          <h3>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M2 5a2 2 0 012-2h12a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V5zm3.293 1.293a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 01-1.414-1.414L7.586 10 5.293 7.707a1 1 0 010-1.414zM11 12a1 1 0 100 2h3a1 1 0 100-2h-3z" clip-rule="evenodd"/>
            </svg>
            处理日志
          </h3>
          <svg
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="currentColor"
            :class="{ 'rotate': logsExpanded }"
            class="expand-icon"
          >
            <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
          </svg>
        </div>

        <div v-show="logsExpanded" class="logs-container" ref="logsContainer">
          <div
            v-for="(log, index) in logs"
            :key="index"
            :class="['log-entry', `log-${log.level}`]"
          >
            <span class="log-time">{{ formatTime(log.timestamp) }}</span>
            <span class="log-level">{{ log.level.toUpperCase() }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>

          <div v-if="logs.length === 0" class="logs-empty">
            等待日志...
          </div>
        </div>
      </div>

      <!-- 完成提示 -->
      <div v-if="taskStatus === 'completed'" class="completion-message">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="currentColor">
          <circle cx="24" cy="24" r="22" stroke="currentColor" stroke-width="2" fill="none"/>
          <path d="M14 24l7 7 14-14" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        </svg>
        <h3>字幕生成完成！</h3>
        <p>正在跳转到预览页面...</p>
      </div>

      <!-- 错误提示 -->
      <div v-if="taskStatus === 'failed'" class="error-message">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="currentColor">
          <circle cx="24" cy="24" r="22" stroke="currentColor" stroke-width="2" fill="none"/>
          <path d="M15 15l18 18M33 15l-18 18" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
        </svg>
        <h3>处理失败</h3>
        <p>{{ errorMessage }}</p>
        <button @click="goBack" class="back-button">返回上传</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const taskId = route.params.id
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const progress = ref(0)
const currentStep = ref('')
const eta = ref(null)
const taskStatus = ref('processing')
const errorMessage = ref('')
const logs = ref([])
const logsExpanded = ref(true)
const logsContainer = ref(null)

const circumference = 2 * Math.PI * 120

let eventSource = null

// 进度圆环偏移量
const strokeDashoffset = computed(() => {
  return circumference - (progress.value / 100) * circumference
})

// 进度颜色
const progressColor = computed(() => {
  if (taskStatus.value === 'completed') return 'var(--brand-green)'
  if (taskStatus.value === 'failed') return 'var(--error)'
  return 'url(#gradient)'
})

// 状态标签
const statusLabel = computed(() => {
  switch (taskStatus.value) {
    case 'processing': return '处理中'
    case 'completed': return '已完成'
    case 'failed': return '失败'
    default: return '准备中'
  }
})

// 步骤图标
const stepIcon = computed(() => {
  // 这里可以返回不同的 SVG 组件
  return 'div'
})

// 切换日志展开
const toggleLogs = () => {
  logsExpanded.value = !logsExpanded.value
}

// 格式化 ETA
const formatEta = (seconds) => {
  if (!seconds) return ''

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  } else if (minutes > 0) {
    return `${minutes}分钟${secs}秒`
  } else {
    return `${secs}秒`
  }
}

// 格式化时间戳
const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 添加日志
const addLog = (log) => {
  logs.value.push(log)

  // 自动滚动到底部
  nextTick(() => {
    if (logsContainer.value) {
      logsContainer.value.scrollTop = logsContainer.value.scrollHeight
    }
  })
}

// 返回上传页面
const goBack = () => {
  router.push('/upload')
}

// 连接 SSE
const connectSSE = () => {
  eventSource = new EventSource(`${API_BASE}/api/tasks/${taskId}/events`)

  eventSource.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data)
    progress.value = data.progress
    currentStep.value = data.step
    eta.value = data.eta
  })

  eventSource.addEventListener('log', (e) => {
    const data = JSON.parse(e.data)
    addLog({
      level: data.level,
      message: data.message,
      timestamp: new Date().toISOString()
    })
  })

  eventSource.addEventListener('complete', (e) => {
    const data = JSON.parse(e.data)
    taskStatus.value = 'completed'
    progress.value = 100
    currentStep.value = '处理完成'

    // 2秒后跳转到预览页面
    setTimeout(() => {
      router.push(`/preview/${taskId}`)
    }, 2000)
  })

  eventSource.addEventListener('error', (e) => {
    const data = JSON.parse(e.data)
    taskStatus.value = 'failed'
    errorMessage.value = data.error || '处理失败，请重试'
    eventSource.close()
  })

  eventSource.onerror = (e) => {
    console.error('SSE 连接错误:', e)
    addLog({
      level: 'error',
      message: '连接断开，正在重连...',
      timestamp: new Date().toISOString()
    })
  }
}

onMounted(() => {
  addLog({
    level: 'info',
    message: `开始处理任务: ${taskId}`,
    timestamp: new Date().toISOString()
  })

  connectSSE()
})

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
  }
})
</script>

<style scoped>
.processing-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.container {
  max-width: 900px;
  width: 100%;
}

.progress-section {
  text-align: center;
  margin-bottom: 3rem;
}

.progress-ring {
  position: relative;
  display: inline-block;
  margin-bottom: 2rem;
}

.progress-ring svg {
  filter: drop-shadow(0 0 20px rgba(59, 130, 246, 0.3));
}

.progress-circle {
  transition: stroke-dashoffset 0.5s ease;
}

.progress-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.progress-percent {
  display: block;
  font-size: 3.5rem;
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1;
}

.progress-label {
  display: block;
  font-size: 1rem;
  color: var(--text-secondary);
  margin-top: 0.5rem;
}

.step-info {
  max-width: 500px;
  margin: 0 auto;
}

.step-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 1rem;
  background: linear-gradient(135deg, var(--brand-blue), var(--brand-cyan));
  border-radius: 9999px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.step-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 0.5rem 0;
}

.step-eta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 0;
}

.logs-section {
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 1rem;
  overflow: hidden;
}

.logs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  cursor: pointer;
  user-select: none;
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
  transition: background 0.2s ease;
}

.logs-header:hover {
  background: rgba(59, 130, 246, 0.05);
}

.logs-header h3 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.expand-icon {
  transition: transform 0.3s ease;
}

.expand-icon.rotate {
  transform: rotate(180deg);
}

.logs-container {
  max-height: 400px;
  overflow-y: auto;
  padding: 1rem;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.875rem;
}

.logs-container::-webkit-scrollbar {
  width: 8px;
}

.logs-container::-webkit-scrollbar-track {
  background: rgba(59, 130, 246, 0.1);
  border-radius: 4px;
}

.logs-container::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.3);
  border-radius: 4px;
}

.logs-container::-webkit-scrollbar-thumb:hover {
  background: rgba(59, 130, 246, 0.5);
}

.log-entry {
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.25rem;
  border-radius: 0.375rem;
  display: flex;
  gap: 1rem;
  line-height: 1.6;
}

.log-entry:hover {
  background: rgba(59, 130, 246, 0.05);
}

.log-time {
  color: var(--text-muted);
  flex-shrink: 0;
}

.log-level {
  color: var(--brand-cyan);
  font-weight: 600;
  flex-shrink: 0;
  min-width: 50px;
}

.log-message {
  color: var(--text-secondary);
  flex: 1;
  word-break: break-word;
}

.log-info .log-level {
  color: var(--brand-blue);
}

.log-warning .log-level {
  color: var(--brand-orange);
}

.log-error .log-level {
  color: var(--error);
}

.log-error {
  background: rgba(239, 68, 68, 0.05);
}

.logs-empty {
  text-align: center;
  color: var(--text-muted);
  padding: 2rem;
}

.completion-message,
.error-message {
  text-align: center;
  padding: 2rem;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 1rem;
}

.completion-message {
  border-color: rgba(16, 185, 129, 0.3);
}

.completion-message svg {
  color: var(--brand-green);
  margin-bottom: 1rem;
}

.error-message {
  border-color: rgba(239, 68, 68, 0.3);
}

.error-message svg {
  color: var(--error);
  margin-bottom: 1rem;
}

.completion-message h3,
.error-message h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 0.5rem 0;
}

.completion-message p,
.error-message p {
  color: var(--text-secondary);
  margin: 0 0 1.5rem 0;
}

.back-button {
  padding: 0.75rem 2rem;
  background: linear-gradient(135deg, var(--brand-blue), var(--brand-cyan));
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(59, 130, 246, 0.3);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .processing-view {
    padding: 1rem;
  }

  .progress-ring svg {
    width: 220px;
    height: 220px;
  }

  .progress-percent {
    font-size: 2.5rem;
  }

  .step-title {
    font-size: 1.25rem;
  }

  .logs-container {
    max-height: 300px;
  }
}
</style>
