<template>
  <div class="library-view">
    <div class="container">
      <!-- 头部 -->
      <div class="header">
        <div>
          <h1 class="title">
            <span class="title-icon">📺</span>
            视频库
          </h1>
          <p class="subtitle">管理所有上传的视频，生成字幕</p>
        </div>
        <button @click="goToUpload" class="upload-button">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="currentColor">
            <path d="M9 0a9 9 0 100 18 9 9 0 000-18zm4.5 9.75h-3.75v3.75h-1.5V9.75H4.5V8.25h3.75V4.5h1.5v3.75h3.75v1.5z"/>
          </svg>
          上传视频
        </button>
      </div>

      <!-- 视频网格 -->
      <div class="video-grid">
        <div
          v-for="video in videos"
          :key="video.id"
          class="video-card"
          @click="goToPreview(video.id)"
        >
          <!-- 缩略图 -->
          <div class="thumbnail-container">
            <img
              :src="`${API_BASE}${video.thumbnail_url}`"
              :alt="video.filename"
              class="video-thumbnail"
              @error="handleThumbnailError"
            />
            <!-- 时长标签 -->
            <div v-if="video.video_info?.duration" class="duration-badge">
              {{ formatDuration(video.video_info.duration) }}
            </div>
            <!-- 播放按钮 -->
            <div class="play-overlay">
              <svg width="48" height="48" viewBox="0 0 48 48" fill="currentColor">
                <path d="M16 8v32l28-16L16 8z"/>
              </svg>
            </div>
          </div>

          <!-- 视频信息 -->
          <div class="video-info">
            <h3 class="video-title">{{ video.filename }}</h3>
            <div class="video-meta">
              <span class="file-size">{{ formatFileSize(video.file_size) }}</span>
              <span class="status-badge" :class="video.status">
                <span class="status-dot"></span>
                {{ getStatusText(video.status) }}
              </span>
            </div>
            <div class="video-date">
              {{ formatDate(video.created_at) }}
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="card-actions">
            <button
              v-if="video.status === 'pending' || video.status === 'failed'"
              @click.stop="generateSubtitles(video.id)"
              class="action-button generate"
              title="生成字幕"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 0a8 8 0 100 16A8 8 0 008 0zm3.5 8.5h-3v3h-1v-3h-3v-1h3v-3h1v3h3v1z"/>
              </svg>
            </button>
            <button
              v-if="video.status === 'completed'"
              @click.stop="goToPreview(video.id)"
              class="action-button view"
              title="查看字幕"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 3a5 5 0 100 10A5 5 0 008 3zm0 8a3 3 0 110-6 3 3 0 010 6zm0-7a1 1 0 00-1 1v1H6a1 1 0 000 2h1v1a1 1 0 002 0v-1h1a1 1 0 000-2h-1V5a1 1 0 00-1-1z"/>
              </svg>
            </button>
            <button
              @click.stop="deleteVideo(video.id)"
              class="action-button delete"
              title="删除"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M5.5 5.5A.5.5 0 016 6v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm2.5 0a.5.5 0 01.5.5v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm3 .5a.5.5 0 00-1 0v6a.5.5 0 001 0V6z"/>
                <path d="M14.5 3a1 1 0 01-1 1H13v9a2 2 0 01-2 2H5a2 2 0 01-2-2V4h-.5a1 1 0 01-1-1V2a1 1 0 011-1H6a1 1 0 011-1h2a1 1 0 011 1h3.5a1 1 0 011 1v1zM4.118 4L4 4.059V13a1 1 0 001 1h6a1 1 0 001-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="videos.length === 0" class="empty-state">
          <svg width="80" height="80" viewBox="0 0 80 80" fill="currentColor">
            <path d="M40 10C23.4 10 10 23.4 10 40s13.4 30 30 30 30-13.4 30-30S56.6 10 40 10zm0 54c-13.3 0-24-10.7-24-24s10.7-24 24-24 24 10.7 24 24-10.7 24-24 24z"/>
            <path d="M32 28l24 12-24 12V28z"/>
          </svg>
          <h2>还没有视频</h2>
          <p>点击上方"上传视频"按钮上传您的第一个视频</p>
          <button @click="goToUpload" class="upload-hint-button">
            上传视频
          </button>
        </div>

        <!-- 加载中 -->
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>加载中...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const videos = ref([])
const loading = ref(true)

// 加载视频库
const loadVideos = async () => {
  try {
    loading.value = true
    const response = await fetch(`${API_BASE}/api/tasks/library?page=1&page_size=50`)
    if (response.ok) {
      const data = await response.json()
      videos.value = data.videos || []
    }
  } catch (error) {
    console.error('加载视频库失败:', error)
  } finally {
    loading.value = false
  }
}

// 生成字幕
const generateSubtitles = async (taskId) => {
  if (!confirm('确定要为此视频生成字幕吗？')) return

  try {
    const response = await fetch(`${API_BASE}/api/tasks/${taskId}/generate-subtitles`, {
      method: 'POST'
    })
    if (response.ok) {
      router.push(`/processing/${taskId}`)
    } else {
      const error = await response.json()
      alert(error.detail || '生成字幕失败')
    }
  } catch (error) {
    console.error('生成字幕失败:', error)
    alert('生成字幕失败，请重试')
  }
}

// 删除视频
const deleteVideo = async (taskId) => {
  if (!confirm('确定要删除这个视频吗？此操作不可撤销。')) return

  try {
    const response = await fetch(`${API_BASE}/api/tasks/${taskId}`, {
      method: 'DELETE'
    })
    if (response.ok) {
      await loadVideos()
    } else {
      const error = await response.json()
      alert(error.detail || '删除失败')
    }
  } catch (error) {
    console.error('删除失败:', error)
    alert('删除失败，请重试')
  }
}

// 格式化时长
const formatDuration = (seconds) => {
  if (!seconds) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${String(secs).padStart(2, '0')}`
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i]
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`

  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric'
  })
}

// 获取状态文本
const getStatusText = (status) => {
  const statusMap = {
    'pending': '待处理',
    'processing': '处理中',
    'completed': '已完成',
    'failed': '失败'
  }
  return statusMap[status] || status
}

// 缩略图加载失败处理
const handleThumbnailError = (e) => {
  e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIwIiBoZWlnaHQ9IjE4MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMWUyOTNiIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjI0IiBmaWxsPSIjNDc1NTY5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+8J+TYPC7PC90ZXh0Pjwvc3ZnPg=='
}

// 跳转
const goToUpload = () => {
  router.push('/upload')
}

const goToPreview = (taskId) => {
  router.push(`/preview/${taskId}`)
}

onMounted(() => {
  loadVideos()
})
</script>

<style scoped>
.library-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  padding: 2rem;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2rem;
}

.title {
  font-size: 2.5rem;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.title-icon {
  font-size: 2.5rem;
}

.subtitle {
  font-size: 1.125rem;
  color: var(--text-secondary);
  margin: 0.5rem 0 0 0;
}

.upload-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.5rem;
  background: linear-gradient(135deg, var(--brand-blue), var(--brand-cyan));
  color: white;
  border: none;
  border-radius: 0.75rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(59, 130, 246, 0.4);
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.video-card {
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 1rem;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
}

.video-card:hover {
  transform: translateY(-4px);
  border-color: var(--brand-blue);
  box-shadow: 0 20px 40px rgba(59, 130, 246, 0.2);
}

.thumbnail-container {
  position: relative;
  aspect-ratio: 16/9;
  overflow: hidden;
  background: #000;
}

.video-thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.video-card:hover .video-thumbnail {
  transform: scale(1.05);
}

.duration-badge {
  position: absolute;
  bottom: 0.5rem;
  right: 0.5rem;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  font-family: monospace;
}

.play-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
  opacity: 0;
  transition: opacity 0.3s ease;
  color: white;
}

.video-card:hover .play-overlay {
  opacity: 1;
}

.video-info {
  padding: 1rem;
}

.video-title {
  font-size: 0.938rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.75rem 0;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.4;
}

.video-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.file-size {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.625rem;
  border-radius: 9999px;
  font-size: 0.688rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.pending {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
}

.status-badge.processing {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.status-badge.completed {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.status-badge.failed {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.video-date {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 0.5rem;
}

.card-actions {
  display: flex;
  gap: 0.5rem;
  padding: 0 1rem 1rem;
}

.action-button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  border: none;
  border-radius: 0.5rem;
  font-size: 0.813rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-button.generate {
  background: linear-gradient(135deg, var(--brand-blue), var(--brand-cyan));
  color: white;
}

.action-button.generate:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.action-button.view {
  background: rgba(59, 130, 246, 0.1);
  color: var(--brand-blue);
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.action-button.view:hover {
  background: rgba(59, 130, 246, 0.2);
}

.action-button.delete {
  background: rgba(239, 68, 68, 0.1);
  color: var(--brand-red);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.action-button.delete:hover {
  background: rgba(239, 68, 68, 0.2);
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 4rem 2rem;
  color: var(--text-muted);
}

.empty-state svg {
  margin-bottom: 1.5rem;
  opacity: 0.3;
}

.empty-state h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-secondary);
  margin: 0 0 0.5rem 0;
}

.empty-state p {
  font-size: 0.938rem;
  color: var(--text-muted);
  margin: 0 0 1.5rem 0;
}

.upload-hint-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: rgba(59, 130, 246, 0.1);
  color: var(--brand-blue);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-hint-button:hover {
  background: rgba(59, 130, 246, 0.2);
  transform: translateY(-1px);
}

.loading-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 4rem 2rem;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(59, 130, 246, 0.2);
  border-top-color: var(--brand-blue);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-state p {
  font-size: 0.938rem;
  color: var(--text-secondary);
  margin: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .library-view {
    padding: 1rem;
  }

  .header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }

  .title {
    font-size: 1.75rem;
    flex-direction: column;
  }

  .video-grid {
    grid-template-columns: 1fr;
  }
}
</style>
