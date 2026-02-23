<template>
  <div class="processing-view">
    <div class="container">
      <!-- 进度浮窗组件 -->
      <ProgressFloatWindow
        ref="progressWindow"
        :task-id="taskId"
        :initial-progress="0"
        :initial-step="'准备中...'"
        @close="handleProgressClose"
        @minimize="handleProgressMinimize"
        @expand="handleProgressExpand"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ProgressFloatWindow from '../components/ProgressFloatWindow.vue'

const router = useRouter()
const route = useRoute()

const taskId = route.params.id
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const progressWindow = ref(null)
const taskStatus = ref('processing')
const errorMessage = ref('')

let eventSource = null

// 处理进度浮窗关闭
const handleProgressClose = () => {
  // 关闭后仍然保持 SSE 连接，任务继续在后台处理
  progressWindow.value?.minimize()
}

const handleProgressMinimize = () => {
  // 最小化时的回调
}

const handleProgressExpand = () => {
  // 展开时的回调
}

// 连接 SSE
const connectSSE = () => {
  eventSource = new EventSource(`${API_BASE}/api/tasks/${taskId}/events`)

  eventSource.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data)
    progressWindow.value?.updateProgress(data.progress, data.step)
  })

  eventSource.addEventListener('log', (e) => {
    const data = JSON.parse(e.data)
    progressWindow.value?.addLog(data.message, data.level)
  })

  eventSource.addEventListener('complete', (e) => {
    const data = JSON.parse(e.data)
    taskStatus.value = 'completed'
    progressWindow.value?.updateProgress(100, '处理完成')
    progressWindow.value?.addLog('字幕生成完成！', 'success')

    // 2 秒后跳转到预览页面
    setTimeout(() => {
      router.push(`/preview/${taskId}`)
    }, 2000)
  })

  eventSource.addEventListener('error', (e) => {
    const data = JSON.parse(e.data)
    taskStatus.value = 'failed'
    errorMessage.value = data.error || '处理失败，请重试'
    progressWindow.value?.addLog(`错误：${errorMessage.value}`, 'error')
    eventSource.close()
  })

  eventSource.onerror = (e) => {
    console.error('SSE 连接错误:', e)
    progressWindow.value?.addLog('连接断开，正在重连...', 'error')
  }
}

onMounted(async () => {
  progressWindow.value?.addLog(`开始处理任务：${taskId}`, 'info')

  // 先获取任务状态
  try {
    const taskResponse = await fetch(`${API_BASE}/api/tasks/${taskId}`)
    if (taskResponse.ok) {
      const task = await taskResponse.json()

      // 如果任务已经是 processing 或 completed 状态，不需要再次启动
      if (task.status === 'processing' || task.status === 'completed') {
        progressWindow.value?.addLog(`任务状态：${task.status}，直接连接监控...`, 'info')
      } else if (task.status === 'pending') {
        //  pending 状态需要启动任务
        const response = await fetch(`${API_BASE}/api/tasks/${taskId}/start`, {
          method: 'POST'
        })
        if (!response.ok) {
          throw new Error('启动任务失败')
        }
        progressWindow.value?.addLog('任务已启动，开始处理...', 'info')
      } else if (task.status === 'failed') {
        progressWindow.value?.addLog(`任务已失败：${task.error_message || '未知错误'}`, 'error')
        return
      }
    } else {
      throw new Error('获取任务状态失败')
    }
  } catch (error) {
    progressWindow.value?.addLog(`启动任务失败：${error.message}`, 'error')
  }

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
</style>
