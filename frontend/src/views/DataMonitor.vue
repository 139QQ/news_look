<template>
  <div class="data-monitor">
    <!-- 实时指标 -->
    <el-row :gutter="20" class="mb-20">
      <el-col :span="6">
        <el-card class="metric-card">
          <el-statistic 
            title="实时新闻数" 
            :value="realtimeStats.newsCount"
            suffix="条"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric-card">
          <el-statistic 
            title="活跃爬虫" 
            :value="realtimeStats.activeCrawlers"
            suffix="个"
            value-style="color: #67c23a"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric-card">
          <el-statistic 
            title="成功率" 
            :value="realtimeStats.successRate"
            suffix="%"
            :value-style="getSuccessRateStyle(realtimeStats.successRate)"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric-card">
          <el-statistic 
            title="错误数" 
            :value="realtimeStats.errorCount"
            suffix="次"
            value-style="color: #f56c6c"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 监控图表 -->
    <el-row :gutter="20" class="mb-20">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="flex-between">
              <span>实时爬取速度</span>
              <el-switch 
                v-model="autoRefresh" 
                active-text="自动刷新"
                @change="handleAutoRefresh"
              />
            </div>
          </template>
          <div ref="speedChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>爬虫状态分布</span>
          </template>
          <div ref="statusChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 详细监控表格 -->
    <el-card>
      <template #header>
        <div class="flex-between">
          <span>爬虫详细状态</span>
          <el-button type="primary" @click="refreshData">
            <el-icon><Refresh /></el-icon>
            刷新数据
          </el-button>
        </div>
      </template>
      
      <el-table :data="crawlerDetails" style="width: 100%">
        <el-table-column prop="name" label="爬虫名称" />
        <el-table-column label="状态">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="speed" label="抓取速度">
          <template #default="{ row }">
            {{ row.speed }} 条/分钟
          </template>
        </el-table-column>
        <el-table-column prop="successRate" label="成功率">
          <template #default="{ row }">
            <el-progress 
              :percentage="row.successRate" 
              :status="getProgressStatus(row.successRate)"
              :stroke-width="8"
            />
          </template>
        </el-table-column>
        <el-table-column prop="lastUpdate" label="最后更新">
          <template #default="{ row }">
            {{ formatTime(row.lastUpdate) }}
          </template>
        </el-table-column>
        <el-table-column prop="errorMsg" label="错误信息">
          <template #default="{ row }">
            <el-text v-if="row.errorMsg" type="danger" :line-clamp="1">
              {{ row.errorMsg }}
            </el-text>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import dayjs from 'dayjs'

// 响应式数据
const autoRefresh = ref(true)
const realtimeStats = reactive({
  newsCount: 1250,
  activeCrawlers: 3,
  successRate: 92,
  errorCount: 12
})

const crawlerDetails = ref([
  {
    name: '新浪财经',
    status: 'running',
    speed: 45,
    successRate: 95,
    lastUpdate: new Date(),
    errorMsg: ''
  },
  {
    name: '东方财富',
    status: 'running', 
    speed: 38,
    successRate: 88,
    lastUpdate: new Date(),
    errorMsg: ''
  },

  {
    name: '网易财经',
    status: 'error',
    speed: 0,
    successRate: 78,
    lastUpdate: dayjs().subtract(1, 'hour').toDate(),
    errorMsg: '连接超时'
  }
])

// 图表引用
const speedChartRef = ref(null)
const statusChartRef = ref(null)

// 图表实例
let speedChart = null
let statusChart = null
let refreshTimer = null

// 样式函数
const getSuccessRateStyle = (rate) => {
  if (rate >= 90) return { color: '#67c23a' }
  if (rate >= 70) return { color: '#409eff' }
  if (rate >= 50) return { color: '#e6a23c' }
  return { color: '#f56c6c' }
}

const getStatusType = (status) => {
  const typeMap = {
    'running': 'success',
    'stopped': 'info',
    'error': 'danger'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    'running': '运行中',
    'stopped': '已停止',
    'error': '错误'
  }
  return textMap[status] || '未知'
}

const getProgressStatus = (rate) => {
  if (rate >= 90) return 'success'
  if (rate >= 70) return ''
  if (rate >= 50) return 'warning'
  return 'exception'
}

const formatTime = (time) => {
  return dayjs(time).format('HH:mm:ss')
}

// 初始化速度图表
const initSpeedChart = () => {
  if (!speedChartRef.value) return
  
  speedChart = echarts.init(speedChartRef.value)
  
  // 生成最近30分钟的数据
  const times = []
  const speeds = []
  
  for (let i = 29; i >= 0; i--) {
    times.push(dayjs().subtract(i, 'minute').format('HH:mm'))
    speeds.push(Math.floor(Math.random() * 30) + 20)
  }
  
  const option = {
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: times
    },
    yAxis: {
      type: 'value',
      name: '条/分钟'
    },
    series: [
      {
        name: '抓取速度',
        data: speeds,
        type: 'line',
        smooth: true,
        areaStyle: {
          opacity: 0.3
        }
      }
    ]
  }
  
  speedChart.setOption(option)
}

// 初始化状态图表
const initStatusChart = () => {
  if (!statusChartRef.value) return
  
  statusChart = echarts.init(statusChartRef.value)
  
  const option = {
    tooltip: {
      trigger: 'item'
    },
    series: [
      {
        name: '爬虫状态',
        type: 'pie',
        radius: '60%',
        data: [
          { value: 2, name: '运行中' },
          { value: 1, name: '已停止' },
          { value: 1, name: '错误' }
        ],
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  }
  
  statusChart.setOption(option)
}

// 刷新数据
const refreshData = () => {
  // 模拟数据更新
  realtimeStats.newsCount += Math.floor(Math.random() * 10)
  realtimeStats.successRate = Math.floor(Math.random() * 20) + 80
  
  // 更新图表数据
  if (speedChart) {
    const option = speedChart.getOption()
    const newTime = dayjs().format('HH:mm')
    const newSpeed = Math.floor(Math.random() * 30) + 20
    
    option.xAxis[0].data.push(newTime)
    option.xAxis[0].data.shift()
    
    option.series[0].data.push(newSpeed)
    option.series[0].data.shift()
    
    speedChart.setOption(option)
  }
}

// 自动刷新控制
const handleAutoRefresh = (enabled) => {
  if (enabled) {
    refreshTimer = setInterval(refreshData, 10000) // 10秒刷新一次
  } else {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }
}

// 窗口大小改变
const handleResize = () => {
  speedChart?.resize()
  statusChart?.resize()
}

// 生命周期
onMounted(async () => {
  await nextTick()
  initSpeedChart()
  initStatusChart()
  
  // 开启自动刷新
  if (autoRefresh.value) {
    handleAutoRefresh(true)
  }
  
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  speedChart?.dispose()
  statusChart?.dispose()
  
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="scss">
.data-monitor {
  .metric-card {
    text-align: center;
    margin-bottom: 20px;
  }
  
  .chart-container {
    height: 300px;
    width: 100%;
  }
}
</style> 