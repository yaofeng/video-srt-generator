<template>
  <div class="progress-float-window" :class="{ minimized: isMinimized }">
    <!-- 展开状态 -->
    <div v-if="!isMinimized" class="progress-content">
      <div class="progress-header">
        <div class="progress-title">
          <svg class="spinner-icon" width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="2" stroke-opacity="0.3"/>
            <path d="M8 1A7 7 0 0 1 15 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <span>处理进度</span>
        </div>
        <div class="progress-actions">
          <button @click="minimize" class="minimize-btn" title="最小化">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M2 8a.5.5 0 01.5-.5H13a.5.5 0 010 1H2.5A.5.5 0 012 8z"/>
            </svg>
          </button>
          <button @click="close" class="close-btn" title="关闭">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M4.646 4.646a.5.5 0 01.708 0L8 7.293l2.646-2.647a.5.5 0 01.708.708L8.707 8l2.647 2.646a.5.5 0 01-.708.708L8 8.707l-2.646 2.647a.5.5 0 01-.708-.708L7.293 8 4.646 5.354a.5.5 0 010-.708z"/>
            </svg>
          </button>
        </div>
      </div>

      <div class="progress-body">
        <div class="progress-bar-container">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progress + '%' }"></div>
          </div>
          <span class="progress-percent">{{ progress }}%</span>
        </div>

        <div class="current-step">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 15A7 7 0 118 1a7 7 0 010 14zm0 1A8 8 0 108 0a8 8 0 000 16z"/>
            <path d="M4.285 9.567a.5.5 0 01.653.278 3.5 3.5 0 006.124 0 .5.5 0 11.92.378 4.5 4.5 0 01-7.85 0 .5.5 0 01.153-.656zM5.5 7a2.5 2.5 0 115 0 2.5 2.5 0 01-5 0z"/>
          </svg>
          <span>{{ currentStep || '准备中...' }}</span>
        </div>

        <div class="logs-container" ref="logsContainer">
          <div
            v-for="(log, index) in visibleLogs"
            :key="index"
            :class="['log-item', `log-${log.level}`]"
          >
            <span class="log-time">{{ log.time }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 最小化状态 -->
    <div v-else class="minimized-container">
      <button @click="expand" class="expand-button" title="展开进度">
        <svg class="pulse-icon" width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
          <path d="M8 15A7 7 0 118 1a7 7 0 010 14zm0 1A8 8 0 108 0a8 8 0 000 16z"/>
          <path d="M4.285 9.567a.5.5 0 01.653.278 3.5 3.5 0 006.124 0 .5.5 0 11.92.378 4.5 4.5 0 01-7.85 0 .5.5 0 01.153-.656zM5.5 7a2.5 2.5 0 115 0 2.5 2.5 0 01-5 0z"/>
        </svg>
        <span class="progress-badge">{{ progress }}%</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  taskId: {
    type: String,
    required: true
  },
  initialProgress: {
    type: Number,
    default: 0
  },
  initialStep: {
    type: String,
    default: '准备中...'
  }
})

const emit = defineEmits(['close', 'minimize', 'expand'])

const isMinimized = ref(false)
const progress = ref(props.initialProgress)
const currentStep = ref(props.initialStep)
const logs = ref([])
const logsContainer = ref(null)

// 可见的日志列表（最多显示 50 条）
const visibleLogs = computed(() => {
  return logs.value.slice(-50)
})

// 添加日志
const addLog = (message, level = 'info') => {
  const now = new Date()
  const time = now.toLocaleTimeString('zh-CN', { hour12: false })
  logs.value.push({ time, message, level })
}

// 更新进度
const updateProgress = (newProgress, step) => {
  progress.value = newProgress
  if (step) {
    currentStep.value = step
  }
}

// 最小化
const minimize = () => {
  isMinimized.value = true
  emit('minimize')
}

// 展开
const expand = () => {
  isMinimized.value = false
  emit('expand')
}

// 关闭
const close = () => {
  emit('close')
}

// 监听进度变化，自动滚动到底部
watch(visibleLogs, () => {
  if (!isMinimized.value && logsContainer.value) {
    setTimeout(() => {
      logsContainer.value.scrollTop = logsContainer.value.scrollHeight
    }, 100)
  }
})

// 暴露方法给父组件
defineExpose({
  updateProgress,
  addLog,
  minimize,
  expand
})
</script>

<style scoped>
.progress-float-window {
  position: fixed;
  top: 1.5rem;
  right: 1.5rem;
  width: 380px;
  max-height: 500px;
  z-index: 1000;
  transition: all 0.3s ease;
}

.progress-float-window.minimized {
  width: auto;
  max-height: none;
}

.progress-content {
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 1rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
}

.progress-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
}

.spinner-icon {
  animation: spin 2s linear infinite;
  color: var(--brand-blue);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-actions {
  display: flex;
  gap: 0.25rem;
}

.minimize-btn,
.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: transparent;
  border: none;
  border-radius: 0.375rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.minimize-btn:hover {
  background: rgba(59, 130, 246, 0.1);
  color: var(--text-primary);
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  color: var(--brand-red);
}

.progress-body {
  padding: 1rem;
  max-height: 420px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.progress-bar-container {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: rgba(59, 130, 246, 0.2);
  border-radius: 9999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--brand-blue), var(--brand-cyan));
  border-radius: 9999px;
  transition: width 0.3s ease;
  position: relative;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.progress-percent {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--brand-cyan);
  min-width: 45px;
  text-align: right;
}

.current-step {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.813rem;
  color: var(--text-secondary);
  margin-bottom: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: rgba(59, 130, 246, 0.05);
  border-radius: 0.5rem;
}

.current-step svg {
  color: var(--brand-blue);
  flex-shrink: 0;
}

.logs-container {
  flex: 1;
  overflow-y: auto;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 0.5rem;
  padding: 0.75rem;
  min-height: 200px;
}

.logs-container::-webkit-scrollbar {
  width: 6px;
}

.logs-container::-webkit-scrollbar-track {
  background: rgba(59, 130, 246, 0.1);
  border-radius: 3px;
}

.logs-container::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.3);
  border-radius: 3px;
}

.logs-container::-webkit-scrollbar-thumb:hover {
  background: rgba(59, 130, 246, 0.5);
}

.log-item {
  display: flex;
  gap: 0.5rem;
  font-size: 0.75rem;
  margin-bottom: 0.375rem;
  line-height: 1.5;
}

.log-time {
  color: var(--text-muted);
  font-family: monospace;
  flex-shrink: 0;
}

.log-message {
  color: var(--text-secondary);
  word-break: break-word;
}

.log-info .log-message {
  color: var(--text-secondary);
}

.log-success .log-message {
  color: #22c55e;
}

.log-warning .log-message {
  color: #fbbf24;
}

.log-error .log-message {
  color: #ef4444;
}

/* 最小化状态 */
.minimized-container {
  display: flex;
  justify-content: flex-end;
}

.expand-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 3rem;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.expand-button:hover {
  background: rgba(15, 23, 42, 1);
  border-color: var(--brand-blue);
  transform: translateY(-2px);
  box-shadow: 0 15px 40px rgba(59, 130, 246, 0.3);
}

.pulse-icon {
  color: var(--brand-cyan);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.1); }
}

.progress-badge {
  font-size: 0.813rem;
  font-weight: 700;
  color: var(--brand-cyan);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .progress-float-window {
    top: 0.75rem;
    right: 0.75rem;
    left: 0.75rem;
    width: auto !important;
  }

  .progress-content {
    max-height: 60vh;
  }
}
</style>
