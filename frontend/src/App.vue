<template>
  <div id="app" class="app">
    <ParticleBackground />
    <router-view />
  </div>
</template>

<script setup>
import ParticleBackground from './components/ParticleBackground.vue'
</script>

<style>
.app {
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  position: relative;
}
</style>
