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

        <div class="header-actions">
          <!-- 翻译按钮 -->
          <button
            v-if="!hasTranslation && !translationInProgress"
            @click="showTranslationModal = true"
            class="translate-button"
          >
            <svg width="18" height="18" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M7 2a1 1 0 00-.707.293l-4 4a1 1 0 000 1.414l4 4A1 1 0 107.414 9.414L6.414 7H11a7 7 0 017 7v2a7 7 0 01-14 0H2a9 9 0 0118 0v-2a9 9 0 00-9-9h-.586l3.293-3.293a1 1 0 10-1.414-1.414l-5 5a1 1 0 000 1.414l5 5a1 1 0 101.414-1.414L8.414 7H7z" clip-rule="evenodd"/>
            </svg>
            翻译字幕
          </button>

          <!-- 下载按钮（下拉菜单） -->
          <div class="download-dropdown" ref="downloadDropdown">
            <button @click="toggleDownloadMenu" class="download-button">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd"/>
              </svg>
              下载 SRT
              <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                <path d="M6 8L2 4h8L6 8z"/>
              </svg>
            </button>
            <div v-if="showDownloadMenu" class="download-menu">
              <button @click="downloadSrt('original')">
                <span class="flag">🎬</span> 下载原文
              </button>
              <button
                v-for="lang in translatedLanguages"
                :key="lang"
                @click="downloadSrt(lang)"
              >
                <span class="flag">{{ getLanguageFlag(lang) }}</span>
                下载{{ getLanguageName(lang) }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 语言切换器 -->
      <div class="language-tabs" v-if="availableLanguages.length > 1">
        <button
          v-for="lang in availableLanguages"
          :key="lang.code"
          :class="['tab', { active: currentLanguage === lang.code }]"
          @click="switchLanguage(lang.code)"
        >
          {{ lang.flag }} {{ lang.name }}
        </button>
      </div>

      <!-- 翻译模态框 -->
      <div v-if="showTranslationModal" class="modal-overlay" @click="showTranslationModal = false">
        <div class="modal-content" @click.stop>
          <h2>选择翻译语言</h2>
          <div class="language-grid">
            <div v-for="lang in supportedLanguages" :key="lang.code" class="language-item">
              <button
                @click="startTranslation(lang.code)"
                class="language-option"
                :class="{ disabled: isLanguageTranslated(lang.code) && !retranslateLanguage }"
                :disabled="isLanguageTranslated(lang.code) && retranslateLanguage !== lang.code"
              >
                <span class="flag">{{ languageFlags[lang.code] || '🌐' }}</span>
                <span class="name">{{ lang.name }}</span>
                <span v-if="isLanguageTranslated(lang.code)" class="status">✓</span>
              </button>
              <button
                v-if="isLanguageTranslated(lang.code)"
                @click="retranslateLanguage = lang.code; showTranslationModal = false"
                class="retranslate-btn"
                title="重新翻译"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M8 3L5 6h2v4h2V6h2L8 3zm0 10l3-3h-2V6h-2v4H5l3 3z"/>
                </svg>
                重新翻译
              </button>
            </div>
          </div>
          <button @click="showTranslationModal = false; retranslateLanguage = null" class="modal-close">取消</button>
        </div>
      </div>

      <!-- 重新翻译确认模态框 -->
      <div v-if="retranslateLanguage" class="modal-overlay" @click="retranslateLanguage = null">
        <div class="modal-content small" @click.stop>
          <h2>重新翻译</h2>
          <p>确定要重新翻译成{{ getLanguageName(retranslateLanguage) }}吗？</p>
          <p class="hint">这将覆盖现有的翻译结果。</p>
          <div class="modal-actions">
            <button @click="confirmRetranslate" class="confirm-btn">确定重新翻译</button>
            <button @click="retranslateLanguage = null" class="cancel-btn">取消</button>
          </div>
        </div>
      </div>

      <!-- 翻译进度模态框 -->
      <div v-if="translationInProgress" class="modal-overlay">
        <div class="modal-content translation-progress">
          <h2>正在翻译...</h2>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: translationProgress + '%' }"></div>
          </div>
          <p class="progress-text">{{ translationStep }}</p>
          <p class="progress-percent">{{ translationProgress }}%</p>
        </div>
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const route = useRoute()

const taskId = route.params.id
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const videoPlayer = ref(null)
const subtitlesList = ref(null)
const downloadDropdown = ref(null)
const task = ref({})
const subtitles = ref([])
const translations = ref([])
const currentTime = ref(0)
const searchQuery = ref('')
const timeFilterStart = ref('')
const timeFilterEnd = ref('')

// 翻译相关状态
const currentLanguage = ref('original')
const showDownloadMenu = ref(false)
const showTranslationModal = ref(false)
const translationInProgress = ref(false)
const translationProgress = ref(0)
const translationStep = ref('')
const retranslateLanguage = ref(null)  // 重新翻译的目标语言

// 支持的语言（从配置 API 动态获取）
const supportedLanguages = ref([])

// 语言代码到国旗的映射
const languageFlags = {
  'zh': '🇨🇳',
  'en': '🇬🇧',
  'ja': '🇯🇵',
  'ko': '🇰🇷',
  'fr': '🇫🇷',
  'de': '🇩🇪',
  'es': '🇪🇸',
  'zh_hant': '🇹🇼',
}

// 可用的语言列表（包括原文和已翻译的语言）
const availableLanguages = computed(() => {
  const langs = [{ code: 'original', name: '原文', flag: '🎬' }]
  translations.value.forEach(t => {
    if (t.status === 'completed') {
      const langInfo = supportedLanguages.value.find(l => l.code === t.language)
      if (langInfo) {
        langs.push({ code: t.language, name: langInfo.name, flag: languageFlags[t.language] || '🌐' })
      }
    }
  })
  return langs
})

// 已翻译的语言列表
const translatedLanguages = computed(() => {
  return translations.value
    .filter(t => t.status === 'completed')
    .map(t => t.language)
})

// 是否有任何翻译
const hasTranslation = computed(() => {
  return translations.value.some(t => t.status === 'completed')
})

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
const downloadSrt = async (lang = null) => {
  try {
    const url = lang
      ? `${API_BASE}/api/tasks/${taskId}/download-srt?lang=${lang}`
      : `${API_BASE}/api/tasks/${taskId}/download-srt`

    const response = await axios.get(url, { responseType: 'blob' })

    const blob = new Blob([response.data])
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl

    // 确定文件名
    let filename = task.value.filename || 'video'
    const baseName = filename.replace(/\.[^/.]+$/, '')
    if (lang) {
      const langName = getLanguageName(lang)
      link.setAttribute('download', `${baseName}_字幕_${langName}.srt`)
    } else {
      link.setAttribute('download', `${baseName}_字幕.srt`)
    }

    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(downloadUrl)

    showDownloadMenu.value = false
  } catch (error) {
    console.error('下载失败:', error)
    alert('下载失败，请重试')
  }
}

// 切换下载菜单
const toggleDownloadMenu = () => {
  showDownloadMenu.value = !showDownloadMenu.value
}

// 获取语言名称
const getLanguageName = (code) => {
  const lang = supportedLanguages.value.find(l => l.code === code)
  return lang ? lang.name : code
}

// 获取语言标志
const getLanguageFlag = (code) => {
  return languageFlags[code] || '🌐'
}

// 加载支持的语言列表
const loadSupportedLanguages = async () => {
  try {
    const response = await axios.get(`${API_BASE}/api/config/`)
    supportedLanguages.value = response.data.supported_languages || []
  } catch (error) {
    console.error('加载支持的语言列表失败:', error)
    // 使用默认值
    supportedLanguages.value = [
      { code: 'zh', name: '中文' },
      { code: 'en', name: '英语' }
    ]
  }
}

// 检查语言是否已翻译
const isLanguageTranslated = (code) => {
  return translations.value.some(t => t.language === code && t.status === 'completed')
}

// 切换语言
const switchLanguage = async (lang) => {
  currentLanguage.value = lang
  await loadSubtitles(lang)
}

// 加载字幕数据
const loadSubtitles = async (lang = null) => {
  try {
    const url = lang
      ? `${API_BASE}/api/tasks/${taskId}/subtitles?lang=${lang}`
      : `${API_BASE}/api/tasks/${taskId}/subtitles`

    const response = await axios.get(url)
    subtitles.value = response.data.subtitles || []
  } catch (error) {
    console.error('加载字幕失败:', error)
  }
}

// 开始翻译
const startTranslation = async (targetLanguage, force = false) => {
  showTranslationModal.value = false
  translationInProgress.value = true
  translationProgress.value = 0
  translationStep.value = force ? '正在重新翻译...' : '正在创建翻译任务...'

  try {
    // 创建翻译任务
    const response = await axios.post(`${API_BASE}/api/tasks/${taskId}/translate`, {
      target_language: targetLanguage,
      force: force
    })

    const translationTaskId = response.data.translation_task_id

    // 轮询翻译状态
    pollTranslationStatus(translationTaskId, targetLanguage)
  } catch (error) {
    console.error('翻译失败:', error)
    alert(error.response?.data?.detail || '翻译失败，请重试')
    translationInProgress.value = false
  }
}

// 确认重新翻译
const confirmRetranslate = () => {
  const targetLanguage = retranslateLanguage.value
  retranslateLanguage.value = null
  startTranslation(targetLanguage, true)  // 传递 force=true
}

// 轮询翻译状态
const pollTranslationStatus = async (translationTaskId, targetLanguage) => {
  const pollInterval = setInterval(async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/tasks/${taskId}/translations`)
      const translation = response.data.translations.find(
        t => t.id === translationTaskId
      )

      if (!translation) {
        clearInterval(pollInterval)
        translationInProgress.value = false
        return
      }

      translationProgress.value = translation.progress || 0

      if (translation.status === 'completed') {
        clearInterval(pollInterval)
        translationInProgress.value = false
        translationProgress.value = 100

        // 重新加载翻译列表和字幕
        await loadTranslations()
        await loadSubtitles(currentLanguage.value)

        // 如果当前不在该语言，切换到翻译后的语言
        if (currentLanguage.value === 'original') {
          currentLanguage.value = targetLanguage
          await loadSubtitles(targetLanguage)
        }
      } else if (translation.status === 'failed') {
        clearInterval(pollInterval)
        translationInProgress.value = false
        alert('翻译失败: ' + (translation.error_message || '未知错误'))
      }
    } catch (error) {
      console.error('获取翻译状态失败:', error)
    }
  }, 2000)
}

// 加载翻译列表
const loadTranslations = async () => {
  try {
    const response = await axios.get(`${API_BASE}/api/tasks/${taskId}/translations`)
    translations.value = response.data.translations || []
  } catch (error) {
    console.error('加载翻译列表失败:', error)
  }
}

// 加载任务数据
const loadTaskData = async () => {
  try {
    const taskRes = await axios.get(`${API_BASE}/api/tasks/${taskId}`)
    task.value = taskRes.data

    // 并行加载字幕和翻译列表
    await Promise.all([
      loadSubtitles(),
      loadTranslations()
    ])
  } catch (error) {
    console.error('加载数据失败:', error)
    alert('加载数据失败，请重试')
  }
}

// 点击外部关闭下载菜单
const handleClickOutside = (event) => {
  if (downloadDropdown.value && !downloadDropdown.value.contains(event.target)) {
    showDownloadMenu.value = false
  }
}

onMounted(async () => {
  await loadSupportedLanguages()
  await loadTaskData()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.preview-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 1.5rem 2rem;
  overflow: hidden;
}

.container {
  max-width: 1800px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  gap: 1rem;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.title {
  font-size: 1.75rem;
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
  padding: 0.625rem 1.25rem;
  border-radius: 0.5rem;
  font-size: 0.813rem;
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

/* 主内容区域：左右布局，占满剩余空间 */
.main-content {
  display: flex;
  gap: 1.5rem;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.video-section {
  flex: 0 0 60%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-player {
  width: 100%;
  max-height: 100%;
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
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.toolbar {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  align-items: center;
  flex-shrink: 0;
}

.search-box {
  flex: 1;
  min-width: 200px;
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
  .preview-view {
    height: auto;
    min-height: 100vh;
    overflow: auto;
  }

  .container {
    height: auto;
    overflow: visible;
  }

  .main-content {
    flex-direction: column;
    overflow: visible;
  }

  .video-section,
  .subtitles-section {
    flex: none;
    width: 100%;
  }

  .video-section {
    margin-bottom: 1.5rem;
  }

  .subtitles-section {
    max-height: 600px;
  }

  .subtitles-list {
    max-height: none;
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

/* 翻译相关样式 */
.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.translate-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  background: rgba(6, 182, 212, 0.1);
  color: var(--brand-cyan);
  border: 1px solid rgba(6, 182, 212, 0.3);
  border-radius: 0.5rem;
  font-size: 0.813rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.translate-button:hover {
  background: rgba(6, 182, 212, 0.2);
  transform: translateY(-2px);
}

.download-dropdown {
  position: relative;
}

.download-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  background: linear-gradient(135deg, var(--brand-blue), var(--brand-cyan));
  color: white;
  border-radius: 0.5rem;
  font-size: 0.813rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
}

.download-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(59, 130, 246, 0.3);
}

.download-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 0.5rem;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 0.5rem;
  min-width: 180px;
  z-index: 100;
  overflow: hidden;
}

.download-menu button {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.download-menu button:hover {
  background: rgba(59, 130, 246, 0.1);
  color: var(--text-primary);
}

.download-menu .flag {
  font-size: 1.125rem;
}

.language-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.tab {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 0.5rem;
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.tab:hover {
  border-color: var(--brand-blue);
  background: rgba(59, 130, 246, 0.1);
}

.tab.active {
  background: linear-gradient(135deg, var(--brand-blue), var(--brand-cyan));
  border-color: transparent;
  color: white;
  box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(5px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 1rem;
  padding: 2rem;
  max-width: 500px;
  width: 100%;
}

.modal-content h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 1.5rem 0;
}

.language-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.language-item {
  display: flex;
  gap: 0.5rem;
  align-items: stretch;
}

.language-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 0.75rem;
  background: rgba(59, 130, 246, 0.05);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
  flex: 1;
}

.language-option:hover:not(.disabled) {
  background: rgba(59, 130, 246, 0.15);
  border-color: var(--brand-blue);
  transform: translateY(-2px);
}

.language-option.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.language-option .flag {
  font-size: 2rem;
}

.language-option .name {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.language-option .status {
  font-size: 1rem;
  color: var(--brand-cyan);
}

.retranslate-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 0.5rem;
  color: var(--brand-red);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.retranslate-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: var(--brand-red);
  transform: translateY(-1px);
}

.modal-content.small {
  max-width: 400px;
}

.modal-content.small h2 {
  font-size: 1.25rem;
  margin-bottom: 1rem;
}

.modal-content.small p {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}

.modal-content.small .hint {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-bottom: 1.5rem;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

.confirm-btn {
  padding: 0.625rem 1.25rem;
  background: linear-gradient(135deg, var(--brand-red), #dc2626);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.confirm-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
}

.cancel-btn {
  padding: 0.625rem 1.25rem;
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.cancel-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.3);
}

.modal-close {
  width: 100%;
  padding: 0.75rem;
  background: rgba(239, 68, 68, 0.1);
  color: var(--error);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.modal-close:hover {
  background: rgba(239, 68, 68, 0.2);
}

.translation-progress {
  text-align: center;
}

.translation-progress h2 {
  margin-bottom: 2rem;
}

.translation-progress .progress-bar {
  width: 100%;
  height: 12px;
  background: rgba(59, 130, 246, 0.2);
  border-radius: 9999px;
  overflow: hidden;
  margin-bottom: 1rem;
}

.translation-progress .progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--brand-blue), var(--brand-cyan));
  border-radius: 9999px;
  transition: width 0.3s ease;
}

.translation-progress .progress-text {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 0 0 0.5rem 0;
}

.translation-progress .progress-percent {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--brand-cyan);
  margin: 0;
}
</style>
