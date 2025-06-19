<template>
  <div class="settings-container">
    <div class="page-header">
      <n-h1>系统设置</n-h1>
      <n-text depth="3">配置系统参数和偏好设置</n-text>
    </div>
    
    <SettingsPanel />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import SettingsPanel from '../components/SettingsPanel.vue'

onMounted(() => {
  console.log('Settings page mounted')
})
</script>

<style scoped>
.settings-container {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}
</style> 