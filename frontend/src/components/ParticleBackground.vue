<template>
  <canvas ref="canvas" class="particle-canvas"></canvas>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const canvas = ref(null)

let ctx = null
let animationFrame = null
let particles = []
let mouseX = 0
let mouseY = 0

// 粒子类
class Particle {
  constructor(canvas) {
    this.canvas = canvas
    this.reset()
  }

  reset() {
    this.x = Math.random() * this.canvas.width
    this.y = Math.random() * this.canvas.height
    this.size = Math.random() * 2 + 0.5
    this.speedX = (Math.random() - 0.5) * 0.5
    this.speedY = (Math.random() - 0.5) * 0.5
    this.opacity = Math.random() * 0.5 + 0.2
    this.opacitySpeed = (Math.random() - 0.5) * 0.01
    this.hue = Math.random() * 60 + 200 // 蓝色到青色范围
  }

  update() {
    // 移动
    this.x += this.speedX
    this.y += this.speedY

    // 鼠标交互
    const dx = mouseX - this.x
    const dy = mouseY - this.y
    const distance = Math.sqrt(dx * dx + dy * dy)

    if (distance < 100) {
      const force = (100 - distance) / 100
      this.speedX -= (dx / distance) * force * 0.02
      this.speedY -= (dy / distance) * force * 0.02
    }

    // 透明度变化
    this.opacity += this.opacitySpeed
    if (this.opacity > 0.7 || this.opacity < 0.1) {
      this.opacitySpeed *= -1
    }

    // 边界检测
    if (this.x < 0 || this.x > this.canvas.width) {
      this.speedX *= -1
    }
    if (this.y < 0 || this.y > this.canvas.height) {
      this.speedY *= -1
    }
  }

  draw() {
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)

    // 创建渐变
    const gradient = ctx.createRadialGradient(
      this.x, this.y, 0,
      this.x, this.y, this.size
    )
    gradient.addColorStop(0, `hsla(${this.hue}, 80%, 60%, ${this.opacity})`)
    gradient.addColorStop(1, `hsla(${this.hue}, 80%, 60%, 0)`)

    ctx.fillStyle = gradient
    ctx.fill()
  }
}

// 连接粒子
const connectParticles = () => {
  const maxDistance = 150

  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x
      const dy = particles[i].y - particles[j].y
      const distance = Math.sqrt(dx * dx + dy * dy)

      if (distance < maxDistance) {
        const opacity = (1 - distance / maxDistance) * 0.15

        ctx.beginPath()
        ctx.strokeStyle = `rgba(59, 130, 246, ${opacity})`
        ctx.lineWidth = 0.5
        ctx.moveTo(particles[i].x, particles[i].y)
        ctx.lineTo(particles[j].x, particles[j].y)
        ctx.stroke()
      }
    }
  }
}

// 初始化粒子
const initParticles = () => {
  particles = []
  const particleCount = Math.floor((canvas.value.width * canvas.value.height) / 15000)

  for (let i = 0; i < particleCount; i++) {
    particles.push(new Particle(canvas.value))
  }
}

// 动画循环
const animate = () => {
  ctx.clearRect(0, 0, canvas.value.width, canvas.value.height)

  particles.forEach(particle => {
    particle.update()
    particle.draw()
  })

  connectParticles()

  animationFrame = requestAnimationFrame(animate)
}

// 调整画布大小
const resizeCanvas = () => {
  canvas.value.width = window.innerWidth
  canvas.value.height = window.innerHeight

  initParticles()
}

// 鼠标移动
const handleMouseMove = (e) => {
  mouseX = e.clientX
  mouseY = e.clientY
}

onMounted(() => {
  ctx = canvas.value.getContext('2d')
  resizeCanvas()
  animate()

  window.addEventListener('resize', resizeCanvas)
  window.addEventListener('mousemove', handleMouseMove)
})

onUnmounted(() => {
  if (animationFrame) {
    cancelAnimationFrame(animationFrame)
  }

  window.removeEventListener('resize', resizeCanvas)
  window.removeEventListener('mousemove', handleMouseMove)
})
</script>

<style scoped>
.particle-canvas {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
  pointer-events: none;
}
</style>
