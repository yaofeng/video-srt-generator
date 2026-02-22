<template>
  <div class="tasks-view">
    <div class="container">
      <!-- 头部 -->
      <div class="header">
        <h1 class="title">
          <span class="title-icon">📋</span>
          任务历史
        </h1>
        <button @click="goToUpload" class="upload-button">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10 5v10M5 10h5v5l5-5h-5V5l-5 5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          </svg>
          上传新视频
        </button>
      </div>

      <!-- 过滤器 -->
      <div class="filters">
        <button
          v-for="filter in filters"
          :key="filter.value"
          :class="['filter-btn', { active: currentFilter === filter.value }]"
          @click="currentFilter = filter.value"
        >
          {{ filter.label }}
          <span class="count" v-if="getCount(filter.value) > 0">{{ getCount(filter.value) }}</span>
        </button>
      </div>

      <!-- 任务列表 -->
      <div class="tasks-list" v-if="tasks.length > 0">
        <div
          v-for="task in filteredTasks"
          :key="task.id"
          class="task-card"
          @click="viewTask(task)"
        >
          <div class="task-status" :class="`status-${task.status}`">
            <svg v-if="task.status === 'completed'" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <svg v-else-if="task.status === 'processing'" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"/>
            </svg>
            <svg v-else-if="task.status === 'failed'" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
            </svg>
            <svg v-else width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clip-rule="evenodd"/>
            </svg>
          </div>

          <div class="task-info">
            <h3 class="task-filename">{{ task.filename }}</h3>
            <div class="task-meta">
              <span class="task-size">{{ formatFileSize(task.file_size) }}</span>
              <span class="task-date">{{ formatDate(task.created_at) }}</span>
            </div>
            <div class="task-progress" v-if="task.status === 'processing'">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: task.progress + '%' }"></div>
              </div>
              <span class="progress-text">{{ task.progress }}%</span>
            </div>
            <div class="task-step" v-if="task.current_step">
              {{ task.current_step }}
            </div>
            <div class="task-error" v-if="task.status === 'failed' && task.error_message">
              {{ task.error_message }}
            </div>
          </div>

          <div class="task-actions" @click.stop>
            <button
              v-if="task.status === 'completed'"
              @click="previewTask(task)"
              class="action-btn preview-btn"
              title="预览字幕"
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="currentColor">
                <path d="M9 3c-3.314 0-6 2.686-6 6s2.686 6 6 6 6-2.686 6-6-2.686-6-6-6zm0 10c-2.209 0-4-1.791-4-4s1.791-4 4-4 4 1.791 4 4-1.791 4-4 4zm0-6c-1.105 0-2 .895-2 2s.895 2 2 2 2-.895 2-2-.895-2-2-2z"/>
              </svg>
            </button>
            <button
              v-if="task.status === 'failed'"
              @click="retryTask(task)"
              class="action-btn retry-btn"
              title="重试"
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="currentColor">
                <path d="M9 3L5 7h3v5h2V7h3L9 3zm0 12l4-4h-3V6H9v5H6l3 4z"/>
              </svg>
            </button>
            <button
              @click="deleteTask(task)"
              class="action-btn delete-btn"
              title="删除"
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="currentColor">
                <path d="M6 4l1 12h4l1-12H6zm2 1h2l-.5 10H8.5L8 5zM4 2h10v2H4V2zm1 0h8V1H5v1z"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <div class="empty-icon">📭</div>
        <h3>暂无任务</h3>
        <p>上传您的第一个视频开始生成字幕</p>
        <button @click="goToUpload" class="upload-primary-button">上传视频</button>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const tasks = ref([])
const loading = ref(false)
const currentFilter = ref('all')

const filters = [
  { label: '全部', value: 'all' },
  { label: '处理中', value: 'processing' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' },
  { label: '待处理', value: 'pending' }
]

const filteredTasks = computed(() => {
  if (currentFilter.value === 'all') {
    return tasks.value
  }
  return tasks.value.filter(task => task.status === currentFilter.value)
})

const getCount = (status) => {
  if (status === 'all') return tasks.value.length
  return tasks.value.filter(t => t.status === status).length
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''

  // 解析日期字符串，确保正确处理时区
  const date = new Date(dateStr)

  // 检查日期是否有效
  if (isNaN(date.getTime())) return ''

  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffHours < 24) return `${diffHours}小时前`
  if (diffDays < 7) return `${diffDays}天前`

  // 显示完整的本地日期和时间
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const loadTasks = async () => {
  loading.value = true
  try {
    const response = await axios.get(`${API_BASE}/api/tasks/`, {
      params: { page: 1, page_size: 100 }
    })
    tasks.value = response.data.tasks || []
  } catch (error) {
    console.error('加载任务失败:', error)
  } finally {
    loading.value = false
  }
}

const viewTask = (task) => {
  if (task.status === 'processing' || task.status === 'pending') {
    router.push(`/processing/${task.id}`)
  } else if (task.status === 'completed') {
    router.push(`/preview/${task.id}`)
  }
}

const previewTask = (task) => {
  router.push(`/preview/${task.id}`)
}

const retryTask = async (task) => {
  try {
    await axios.post(`${API_BASE}/api/tasks/${task.id}/start`)
    // 刷新任务列表
    await loadTasks()
  } catch (error) {
    console.error('重试任务失败:', error)
    alert('重试失败: ' + (error.response?.data?.detail || error.message))
  }
}

const deleteTask = async (task) => {
  if (!confirm(`确定要删除任务 "${task.filename}" 吗？`)) {
    return
  }

  try {
    await axios.delete(`${API_BASE}/api/tasks/${task.id}`)
    // 从列表中移除
    tasks.value = tasks.value.filter(t => t.id !== task.id)
  } catch (error) {
    console.error('删除任务失败:', error)
    alert('删除失败: ' + (error.response?.data?.detail || error.message))
  }
}

const goToUpload = () => {
  router.push('/upload')
}

onMounted(() => {
  loadTasks()
  // 定期刷新处理中的任务
  const interval = setInterval(() => {
    const hasProcessing = tasks.value.some(t => t.status === 'processing' || t.status === 'pending')
    if (hasProcessing) {
      loadTasks()
    }
  }, 5000)

  // 组件卸载时清除定时器
  return () => clearInterval(interval)
})
</script>

<style scoped>
.tasks-view {
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

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2rem;
}

.title {
  font-size: 2rem;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.title-icon {
  font-size: 2rem;
}

.upload-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, var(--brand-blue), var(--brand-cyan));
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(59, 130, 246, 0.3);
}

.filters {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 0.5rem 1rem;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 0.5rem;
  color: var(--text-secondary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-btn:hover {
  border-color: var(--brand-blue);
  background: rgba(59, 130, 246, 0.1);
}

.filter-btn.active {
  background: linear-gradient(135deg, var(--brand-blue), var(--brand-cyan));
  border-color: transparent;
  color: white;
}

.count {
  background: rgba(0, 0, 0, 0.2);
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.filter-btn.active .count {
  background: rgba(255, 255, 255, 0.2);
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.task-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem 1.5rem;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.task-card:hover {
  border-color: var(--brand-blue);
  box-shadow: 0 10px 40px rgba(59, 130, 246, 0.2);
  transform: translateX(4px);
}

.task-status {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-completed {
  background: rgba(16, 185, 129, 0.2);
  color: var(--brand-green);
}

.status-processing {
  background: rgba(59, 130, 246, 0.2);
  color: var(--brand-blue);
}

.status-failed {
  background: rgba(239, 68, 68, 0.2);
  color: var(--error);
}

.status-pending {
  background: rgba(251, 191, 36, 0.2);
  color: var(--brand-orange);
}

.task-info {
  flex: 1;
  min-width: 0;
}

.task-filename {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.25rem 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.875rem;
  color: var(--text-muted);
}

.task-progress {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: rgba(59, 130, 246, 0.2);
  border-radius: 9999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--brand-blue), var(--brand-cyan));
  border-radius: 9999px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.75rem;
  color: var(--brand-cyan);
  font-weight: 600;
  min-width: 35px;
  text-align: right;
}

.task-step {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.task-error {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: var(--error);
}

.task-actions {
  display: flex;
  gap: 0.5rem;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.task-card:hover .task-actions {
  opacity: 1;
}

.action-btn {
  width: 36px;
  height: 36px;
  border-radius: 0.5rem;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.preview-btn {
  background: rgba(16, 185, 129, 0.2);
  color: var(--brand-green);
}

.preview-btn:hover {
  background: rgba(16, 185, 129, 0.3);
  transform: scale(1.1);
}

.retry-btn {
  background: rgba(251, 191, 36, 0.2);
  color: var(--brand-orange);
}

.retry-btn:hover {
  background: rgba(251, 191, 36, 0.3);
  transform: scale(1.1);
}

.delete-btn {
  background: rgba(239, 68, 68, 0.2);
  color: var(--error);
}

.delete-btn:hover {
  background: rgba(239, 68, 68, 0.3);
  transform: scale(1.1);
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.empty-state h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 0.5rem 0;
}

.empty-state p {
  color: var(--text-secondary);
  margin: 0 0 2rem 0;
}

.upload-primary-button {
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

.upload-primary-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(59, 130, 246, 0.3);
}

.loading-state {
  text-align: center;
  padding: 4rem 2rem;
}

.spinner {
  width: 40px;
  height: 40px;
  margin: 0 auto 1rem;
  border: 3px solid rgba(59, 130, 246, 0.2);
  border-top-color: var(--brand-blue);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-state p {
  color: var(--text-secondary);
  margin: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .tasks-view {
    padding: 1rem;
  }

  .header {
    flex-direction: column;
    gap: 1rem;
  }

  .title {
    font-size: 1.5rem;
  }

  .task-card {
    padding: 1rem;
  }

  .task-actions {
    opacity: 1;
  }
}
</style>
