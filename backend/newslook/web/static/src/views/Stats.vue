<template>
  <div class="stats-container">
    <div class="page-header">
      <n-h1>统计概览</n-h1>
      <n-text depth="3">系统数据统计和分析</n-text>
    </div>
    
    <n-space vertical size="large">
      <!-- 关键指标 -->
      <n-grid :cols="4" :x-gap="16">
        <n-grid-item v-for="stat in keyStats" :key="stat.key">
          <n-card hoverable>
            <n-statistic
              :label="stat.label"
              :value="stat.value"
              :precision="stat.precision"
            >
              <template #prefix>
                <n-icon size="24" :color="stat.color">
                  <component :is="stat.icon" />
                </n-icon>
              </template>
              <template #suffix>{{ stat.suffix }}</template>
            </n-statistic>
          </n-card>
        </n-grid-item>
      </n-grid>
      
      <!-- 图表区域 -->
      <n-card title="数据趋势" hoverable>
        <div ref="chartContainer" style="height: 400px"></div>
      </n-card>
    </n-space>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import {
  DocumentTextOutline,
  TrendingUpOutline,
  TimeOutline,
  CheckmarkCircleOutline
} from '@vicons/ionicons5'

const keyStats = ref([
  {
    key: 'totalNews',
    label: '总新闻数',
    value: 15420,
    suffix: '条',
    color: '#18a058',
    icon: DocumentTextOutline
  },
  {
    key: 'todayNews',
    label: '今日新增',
    value: 268,
    suffix: '条',
    color: '#2080f0',
    icon: TrendingUpOutline
  },
  {
    key: 'avgTime',
    label: '平均响应时间',
    value: 1.2,
    precision: 1,
    suffix: 's',
    color: '#f0a020',
    icon: TimeOutline
  },
  {
    key: 'successRate',
    label: '成功率',
    value: 98.5,
    precision: 1,
    suffix: '%',
    color: '#18a058',
    icon: CheckmarkCircleOutline
  }
])

const chartContainer = ref(null)

onMounted(() => {
  // 这里可以初始化图表
  console.log('Stats page mounted')
})
</script>

<style scoped>
.stats-container {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}
</style> 