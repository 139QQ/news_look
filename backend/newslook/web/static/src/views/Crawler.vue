<template>
  <div class="crawler-container">
    <div class="page-header">
      <n-h1>爬虫管理</n-h1>
      <n-text depth="3">管理和监控新闻爬虫状态</n-text>
    </div>
    
    <n-card title="爬虫管理" hoverable>
      <n-empty description="爬虫管理功能开发中" />
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

onMounted(() => {
  console.log('Crawler page mounted')
})
</script>

<style scoped>
.crawler-container {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}
</style> 