<template>
  <div class="preview-view">
    <div class="container">
      <!-- 头部 -->
      <div class="header">
        <button @click="goBack" class="back-button">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clip-rule="evenodd"/>
          </svg>
          返回
        </button>

        <h1 class="title">字幕预览</h1>

        <button @click="downloadSrt" class="download-button">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd"/>
          </svg>
          下载 SRT
        </button>
      </div>

      <!-- 主内容区域：左右布局 -->
      <div class="main-content">
        <!-- 视频播放器 -->
        <div class="video-section">
          <video
            ref="videoPlayer"
            :src="videoUrl"
            @timeupdate="handleTimeUpdate"
            controls
            class="video-player"
          >
            您的浏览器不支持视频播放
          </video>
        </div>

        <!-- 字幕列表 -->
        <div class="subtitles-section">
        <!-- 工具栏 -->
        <div class="toolbar">
          <div class="search-box">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/>
            </svg>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索字幕（支持正则）"
              class="search-input"
            />
          </div>

          <div class="time-filter">
            <input
              v-model="timeFilterStart"
              type="text"
              placeholder="开始时间 (如: 00:01:30)"
              class="time-input"
            />
            <span class="time-separator">-</span>
            <input
              v-model="timeFilterEnd"
              type="text"
              placeholder="结束时间 (如: 00:05:00)"
              class="time-input"
            />
            <button @click="applyTimeFilter" class="filter-button">筛选</button>
            <button @click="clearFilters" class="clear-button">清除</button>
          </div>

          <div class="stats">
            <span class="stat-item">
              <strong>{{ filteredSubtitles.length }}</strong> 条字幕
            </span>
            <span class="stat-item">
              时长: <strong>{{ formatDuration(task.duration_seconds) }}</strong>
            </span>
          </div>
        </div>

        <!-- 字幕列表 -->
        <div class="subtitles-list" ref="subtitlesList">
          <div
            v-for="subtitle in filteredSubtitles"
            :key="subtitle.id"
            :class="['subtitle-item', { active: isSubtitleActive(subtitle) }]"
            @click="seekToSubtitle(subtitle)"
          >
            <div class="subtitle-index">{{ subtitle.index }}</div>

            <div class="subtitle-content">
              <div class="subtitle-time">
                {{ formatTime(subtitle.start_time) }} → {{ formatTime(subtitle.end_time) }}
              </div>
              <div class="subtitle-text">{{ subtitle.text }}</div>
            </div>
          </div>

          <div v-if="filteredSubtitles.length === 0" class="empty-state">
            <svg width="64" height="64" viewBox="0 0 64 64" fill="currentColor">
              <path d="M32 8a4 4 0 100 8 4 4 0 000-8zM20 24a4 4 0 100 8 4 4 0 000-8zM44 24a4 4 0 100 8 4 4 0 000-8zM20 40a4 4 0 100 8 4 4 0 000-8zM44 40a4 4 0 100 8 4 4 0 000-8zM32 56a4 4 0 100 8 4 4 0 000-8z" opacity="0.5"/>
            </svg>
            <p>没有找到匹配的字幕</p>
          </div>
        </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const route = useRoute()

const taskId = route.params.id
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const videoPlayer = ref(null)
const subtitlesList = ref(null)
const task = ref({})
const subtitles = ref([])
const currentTime = ref(0)
const searchQuery = ref('')
const timeFilterStart = ref('')
const timeFilterEnd = ref('')

const videoUrl = computed(() => {
  if (task.value.file_path) {
    return `${API_BASE}/api/tasks/${taskId}/video`
  }
  return ''
})

// 过滤后的字幕
const filteredSubtitles = computed(() => {
  let result = [...subtitles.value]

  // 搜索过滤
  if (searchQuery.value) {
    try {
      const regex = new RegExp(searchQuery.value, 'i')
      result = result.filter(s => regex.test(s.text))
    } catch (e) {
      // 无效正则，使用简单搜索
      result = result.filter(s => s.text.toLowerCase().includes(searchQuery.value.toLowerCase()))
    }
  }

  // 时间过滤
  if (timeFilterStart.value || timeFilterEnd.value) {
    result = result.filter(s => {
      const start = timeFilterStart.value ? parseTime(timeFilterStart.value) : 0
      const end = timeFilterEnd.value ? parseTime(timeFilterEnd.value) : Infinity
      return s.start_time >= start && s.end_time <= end
    })
  }

  return result
})

// 判断字幕是否激活
const isSubtitleActive = (subtitle) => {
  return currentTime.value >= subtitle.start_time && currentTime.value <= subtitle.end_time
}

// 处理时间更新
const handleTimeUpdate = () => {
  if (videoPlayer.value) {
    currentTime.value = videoPlayer.value.currentTime
  }
}

// 跳转到字幕时间
const seekToSubtitle = (subtitle) => {
  if (videoPlayer.value) {
    videoPlayer.value.currentTime = subtitle.start_time
    videoPlayer.value.play()

    // 滚动到对应位置
    const index = filteredSubtitles.value.findIndex(s => s.id === subtitle.id)
    if (index !== -1 && subtitlesList.value) {
      const items = subtitlesList.value.querySelectorAll('.subtitle-item')
      if (items[index]) {
        items[index].scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
  }
}

// 格式化时间
const formatTime = (seconds) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 1000)

  if (hours > 0) {
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')},${String(ms).padStart(3, '0')}`
  }
  return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')},${String(ms).padStart(3, '0')}`
}

// 解析时间字符串
const parseTime = (timeStr) => {
  const parts = timeStr.split(':')
  if (parts.length === 3) {
    const [hours, minutes, seconds] = parts.map(Number)
    return hours * 3600 + minutes * 60 + seconds
  } else if (parts.length === 2) {
    const [minutes, seconds] = parts.map(Number)
    return minutes * 60 + seconds
  }
  return 0
}

// 格式化时长
const formatDuration = (seconds) => {
  if (!seconds) return '0:00'

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  }
  return `${minutes}:${String(secs).padStart(2, '0')}`
}

// 应用时间过滤
const applyTimeFilter = () => {
  // 触发计算属性重新计算
}

// 清除过滤
const clearFilters = () => {
  searchQuery.value = ''
  timeFilterStart.value = ''
  timeFilterEnd.value = ''
}

// 返回上传页面
const goBack = () => {
  router.push('/upload')
}

// 下载 SRT 文件
const downloadSrt = async () => {
  try {
    const response = await axios.get(`${API_BASE}/api/tasks/${taskId}/download`, {
      responseType: 'blob'
    })

    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${task.value.filename}_字幕.srt`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('下载失败:', error)
    alert('下载失败，请重试')
  }
}

// 加载任务数据
const loadTaskData = async () => {
  try {
    const [taskRes, subtitlesRes] = await Promise.all([
      axios.get(`${API_BASE}/api/tasks/${taskId}`),
      axios.get(`${API_BASE}/api/tasks/${taskId}/subtitles`)
    ])

    task.value = taskRes.data
    subtitles.value = subtitlesRes.data.subtitles || []
  } catch (error) {
    console.error('加载数据失败:', error)
    alert('加载数据失败，请重试')
  }
}

onMounted(() => {
  loadTaskData()
})
</script>

<style scoped>
.preview-view {
  min-height: 100vh;
  padding: 2rem;
}

.container {
  max-width: 1800px;
  margin: 0 auto;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.title {
  font-size: 2rem;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0;
  flex: 1;
  text-align: center;
}

.back-button,
.download-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
}

.back-button {
  background: rgba(59, 130, 246, 0.1);
  color: var(--brand-blue);
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.back-button:hover {
  background: rgba(59, 130, 246, 0.2);
}

.download-button {
  background: linear-gradient(135deg, var(--brand-blue), var(--brand-cyan));
  color: white;
}

.download-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(59, 130, 246, 0.3);
}

/* 主内容区域：左右布局 */
.main-content {
  display: flex;
  gap: 2rem;
  align-items: flex-start;
}

.video-section {
  flex: 0 0 60%;
  position: sticky;
  top: 2rem;
}

.video-player {
  width: 100%;
  border-radius: 1rem;
  background: #000;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.subtitles-section {
  flex: 1;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 1rem;
  overflow: hidden;
  position: sticky;
  top: 2rem;
  max-height: calc(100vh - 4rem);
  display: flex;
  flex-direction: column;
}

.toolbar {
  padding: 1.5rem;
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
  align-items: center;
}

.search-box {
  flex: 1;
  min-width: 250px;
  position: relative;
  display: flex;
  align-items: center;
}

.search-box svg {
  position: absolute;
  left: 1rem;
  color: var(--text-muted);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 0.75rem 1rem 0.75rem 3rem;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 0.5rem;
  color: var(--text-primary);
  font-size: 0.875rem;
  transition: all 0.3s ease;
}

.search-input:focus {
  outline: none;
  border-color: var(--brand-blue);
  background: rgba(59, 130, 246, 0.15);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.time-filter {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.time-input {
  padding: 0.75rem 1rem;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 0.5rem;
  color: var(--text-primary);
  font-size: 0.875rem;
  width: 150px;
  transition: all 0.3s ease;
}

.time-input:focus {
  outline: none;
  border-color: var(--brand-blue);
  background: rgba(59, 130, 246, 0.15);
}

.time-separator {
  color: var(--text-muted);
}

.filter-button,
.clear-button {
  padding: 0.75rem 1.25rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
}

.filter-button {
  background: linear-gradient(135deg, var(--brand-blue), var(--brand-cyan));
  color: white;
}

.filter-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 5px 20px rgba(59, 130, 246, 0.3);
}

.clear-button {
  background: rgba(239, 68, 68, 0.1);
  color: var(--error);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.clear-button:hover {
  background: rgba(239, 68, 68, 0.2);
}

.stats {
  display: flex;
  gap: 1.5rem;
  margin-left: auto;
}

.stat-item {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.stat-item strong {
  color: var(--brand-cyan);
}

.subtitles-list {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  min-height: 0;
}

.subtitles-list::-webkit-scrollbar {
  width: 8px;
}

.subtitles-list::-webkit-scrollbar-track {
  background: rgba(59, 130, 246, 0.1);
  border-radius: 4px;
}

.subtitles-list::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.3);
  border-radius: 4px;
}

.subtitles-list::-webkit-scrollbar-thumb:hover {
  background: rgba(59, 130, 246, 0.5);
}

.subtitle-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid transparent;
}

.subtitle-item:hover {
  background: rgba(59, 130, 246, 0.05);
  border-color: rgba(59, 130, 246, 0.2);
}

.subtitle-item.active {
  background: rgba(6, 182, 212, 0.1);
  border-color: var(--brand-cyan);
  box-shadow: 0 0 20px rgba(6, 182, 212, 0.2);
}

.subtitle-index {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--brand-blue), var(--brand-cyan));
  color: white;
  border-radius: 0.5rem;
  font-weight: 700;
  font-size: 0.875rem;
  flex-shrink: 0;
}

.subtitle-content {
  flex: 1;
  min-width: 0;
}

.subtitle-time {
  font-size: 0.75rem;
  color: var(--brand-cyan);
  font-weight: 600;
  margin-bottom: 0.5rem;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

.subtitle-text {
  color: var(--text-secondary);
  line-height: 1.6;
  word-break: break-word;
}

.subtitle-item.active .subtitle-text {
  color: var(--text-primary);
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: var(--text-muted);
}

.empty-state svg {
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-state p {
  margin: 0;
  font-size: 1rem;
}

/* 响应式设计 */
@media (max-width: 1280px) {
  .main-content {
    flex-direction: column;
  }

  .video-section,
  .subtitles-section {
    flex: none;
    position: static;
    width: 100%;
  }

  .subtitles-section {
    max-height: 600px;
  }

  .subtitles-list {
    max-height: 600px;
  }
}

@media (max-width: 1024px) {
  .header {
    flex-direction: column;
  }

  .title {
    order: -1;
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .search-box,
  .time-input {
    min-width: 100%;
  }

  .time-filter {
    flex-direction: column;
  }

  .stats {
    margin-left: 0;
  }
}

@media (max-width: 768px) {
  .preview-view {
    padding: 1rem;
  }

  .title {
    font-size: 1.5rem;
  }

  .back-button,
  .download-button {
    padding: 0.625rem 1rem;
    font-size: 0.813rem;
  }

  .subtitles-section {
    max-height: 400px;
  }

  .subtitles-list {
    max-height: 400px;
  }
}
</style>
