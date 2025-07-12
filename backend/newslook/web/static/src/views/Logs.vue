<template>
  <div class="logs-container">
    <div class="page-header">
      <n-h1>日志监控</n-h1>
      <n-text depth="3">查看系统运行日志和错误信息</n-text>
    </div>
    
    <n-card title="日志监控" hoverable>
      <n-empty description="日志监控功能开发中" />
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

onMounted(() => {
  console.log('Logs page mounted')
})
</script>

<style scoped>
.logs-container {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}
</style> 