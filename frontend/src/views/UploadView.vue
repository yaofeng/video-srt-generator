<template>
  <div class="upload-view">
    <div class="container">
      <!-- 标题区域 -->
      <div class="header">
        <h1 class="title">
          <span class="title-icon">🎬</span>
          视频字幕生成系统
        </h1>
        <p class="subtitle">上传视频，自动生成带时间戳的 SRT 字幕</p>
      </div>

      <!-- 上传区域 -->
      <div
        class="upload-zone"
        :class="{ 'drag-over': isDragOver, 'uploading': isUploading }"
        @dragenter.prevent="handleDragEnter"
        @dragleave.prevent="handleDragLeave"
        @dragover.prevent
        @drop.prevent="handleDrop"
        @click="selectFile"
      >
        <input
          ref="fileInput"
          type="file"
          accept="video/*"
          @change="handleFileSelect"
          style="display: none"
        />

        <div class="upload-content">
          <div class="upload-icon" :class="{ 'pulse': isUploading }">
            <svg v-if="!isUploading" width="80" height="80" viewBox="0 0 80 80" fill="none">
              <path d="M40 20V50M40 50L30 40M40 50L50 40" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M20 60C20 60 25 55 40 55C55 55 60 60 60 60" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
            </svg>
            <svg v-else width="80" height="80" viewBox="0 0 80 80" fill="none" class="spin">
              <circle cx="40" cy="40" r="35" stroke="currentColor" stroke-width="3" stroke-opacity="0.3"/>
              <path d="M40 5A35 35 0 0 1 75 40" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
            </svg>
          </div>

          <h2 class="upload-title">
            {{ isUploading ? '正在上传...' : (isDragOver ? '释放文件开始上传' : '拖拽视频到这里') }}
          </h2>

          <p class="upload-hint">
            或点击选择文件
          </p>

          <p class="upload-formats">
            支持格式：MP4, AVI, MOV, MKV, FLV, WMV
          </p>

          <p class="upload-limit">
            最大文件大小：2GB
          </p>
        </div>

        <!-- 上传进度 -->
        <div v-if="isUploading" class="upload-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
          </div>
          <p class="progress-text">{{ uploadProgress }}%</p>
        </div>
      </div>

      <!-- 错误提示 -->
      <div v-if="errorMessage" class="error-message">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
        </svg>
        <span>{{ errorMessage }}</span>
      </div>

      <!-- 功能说明 -->
      <div class="features">
        <div class="feature-item">
          <div class="feature-icon">🎯</div>
          <h3>智能识别</h3>
          <p>基于 Qwen3-ASR 模型，支持中文语音识别</p>
        </div>

        <div class="feature-item">
          <div class="feature-icon">⚡</div>
          <h3>实时进度</h3>
          <p>SSE 实时推送处理进度和日志</p>
        </div>

        <div class="feature-item">
          <div class="feature-icon">📝</div>
          <h3>精确时间戳</h3>
          <p>Token 级别时间戳，自动合并优化</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const fileInput = ref(null)
const isDragOver = ref(false)
const isUploading = ref(false)
const uploadProgress = ref(0)
const errorMessage = ref('')

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

// 处理拖拽进入
const handleDragEnter = (e) => {
  isDragOver.value = true
}

// 处理拖拽离开
const handleDragLeave = (e) => {
  isDragOver.value = false
}

// 处理文件拖放
const handleDrop = (e) => {
  isDragOver.value = false
  const files = e.dataTransfer.files

  if (files.length > 0) {
    handleFile(files[0])
  }
}

// 选择文件
const selectFile = () => {
  if (isUploading.value) return
  fileInput.value?.click()
}

// 处理文件选择
const handleFileSelect = (e) => {
  const files = e.target.files
  if (files.length > 0) {
    handleFile(files[0])
  }
}

// 处理文件上传
const handleFile = async (file) => {
  // 清除错误信息
  errorMessage.value = ''

  // 验证文件类型
  if (!file.type.startsWith('video/')) {
    errorMessage.value = '请选择视频文件'
    return
  }

  // 验证文件大小 (2GB)
  const maxSize = 2 * 1024 * 1024 * 1024
  if (file.size > maxSize) {
    errorMessage.value = '文件大小超过 2GB 限制'
    return
  }

  try {
    isUploading.value = true
    uploadProgress.value = 0

    const formData = new FormData()
    formData.append('file', file)

    const response = await axios.post(`${API_BASE}/api/tasks/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        uploadProgress.value = progress
      }
    })

    // 上传成功，跳转到处理进度页面
    const taskId = response.data.task_id
    router.push(`/processing/${taskId}`)

  } catch (error) {
    console.error('上传失败:', error)
    errorMessage.value = error.response?.data?.detail || '上传失败，请重试'
    isUploading.value = false
    uploadProgress.value = 0
  }
}
</script>

<style scoped>
.upload-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.container {
  max-width: 800px;
  width: 100%;
}

.header {
  text-align: center;
  margin-bottom: 3rem;
}

.title {
  font-size: 3rem;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0 0 1rem 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
}

.title-icon {
  font-size: 3rem;
}

.subtitle {
  font-size: 1.125rem;
  color: var(--text-secondary);
  margin: 0;
}

.upload-zone {
  position: relative;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(20px);
  border: 2px dashed rgba(59, 130, 246, 0.5);
  border-radius: 1.5rem;
  padding: 4rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  overflow: hidden;
}

.upload-zone::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at center, rgba(59, 130, 246, 0.1) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.upload-zone:hover {
  border-color: var(--brand-blue);
  box-shadow: 0 0 40px rgba(59, 130, 246, 0.3);
}

.upload-zone:hover::before {
  opacity: 1;
}

.upload-zone.drag-over {
  border-color: var(--brand-cyan);
  background: rgba(6, 182, 212, 0.1);
  transform: scale(1.02);
}

.upload-zone.uploading {
  cursor: not-allowed;
  border-style: solid;
}

.upload-content {
  position: relative;
  z-index: 1;
}

.upload-icon {
  color: var(--brand-blue);
  margin-bottom: 1.5rem;
  transition: all 0.3s ease;
}

.upload-icon.pulse {
  animation: pulse 2s ease-in-out infinite;
}

.upload-icon.spin svg {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.1); opacity: 0.8; }
}

.upload-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 0.5rem 0;
}

.upload-hint {
  font-size: 1rem;
  color: var(--text-secondary);
  margin: 0 0 2rem 0;
}

.upload-formats,
.upload-limit {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin: 0.5rem 0;
}

.upload-progress {
  margin-top: 2rem;
}

.progress-bar {
  height: 8px;
  background: rgba(59, 130, 246, 0.2);
  border-radius: 9999px;
  overflow: hidden;
  margin-bottom: 0.5rem;
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

.progress-text {
  font-size: 0.875rem;
  color: var(--brand-cyan);
  font-weight: 600;
  margin: 0;
}

.error-message {
  margin-top: 1.5rem;
  padding: 1rem 1.5rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 0.75rem;
  color: var(--error);
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.875rem;
}

.features {
  margin-top: 4rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 2rem;
}

.feature-item {
  text-align: center;
  padding: 2rem 1rem;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  border: 1px solid rgba(59, 130, 246, 0.2);
  transition: all 0.3s ease;
}

.feature-item:hover {
  transform: translateY(-4px);
  border-color: var(--brand-blue);
  box-shadow: 0 10px 40px rgba(59, 130, 246, 0.2);
}

.feature-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.feature-item h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.5rem 0;
}

.feature-item p {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.6;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .upload-view {
    padding: 1rem;
  }

  .title {
    font-size: 2rem;
    flex-direction: column;
    gap: 0.5rem;
  }

  .upload-zone {
    padding: 3rem 1.5rem;
  }

  .features {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .feature-item {
    padding: 1.5rem 1rem;
  }
}
</style>
