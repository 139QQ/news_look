<template>
  <div class="home-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <n-h1>系统概览</n-h1>
      <n-text depth="3">财经新闻爬虫系统实时状态监控</n-text>
    </div>
    
    <!-- 关键指标卡片 -->
    <n-grid :cols="4" :x-gap="16" :y-gap="16" style="margin-bottom: 24px">
      <n-grid-item>
        <n-card hoverable>
          <n-statistic label="今日新闻数量" :value="stats.todayNews">
            <template #prefix>
              <n-icon size="20" color="#18a058">
                <DocumentTextOutline />
              </n-icon>
            </template>
            <template #suffix>条</template>
          </n-statistic>
        </n-card>
      </n-grid-item>
      
      <n-grid-item>
        <n-card hoverable>
          <n-statistic label="总新闻数量" :value="stats.totalNews">
            <template #prefix>
              <n-icon size="20" color="#2080f0">
                <LibraryOutline />
              </n-icon>
            </template>
            <template #suffix>条</template>
          </n-statistic>
        </n-card>
      </n-grid-item>
      
      <n-grid-item>
        <n-card hoverable>
          <n-statistic label="活跃爬虫" :value="stats.activeCrawlers">
            <template #prefix>
              <n-icon size="20" color="#f0a020">
                <CloudDownloadOutline />
              </n-icon>
            </template>
            <template #suffix>个</template>
          </n-statistic>
        </n-card>
      </n-grid-item>
      
      <n-grid-item>
        <n-card hoverable>
          <n-statistic label="成功率" :value="stats.successRate" :precision="1">
            <template #prefix>
              <n-icon size="20" color="#18a058">
                <CheckmarkCircleOutline />
              </n-icon>
            </template>
            <template #suffix>%</template>
          </n-statistic>
        </n-card>
      </n-grid-item>
    </n-grid>
    
    <!-- 内容区域 -->
    <n-grid :cols="3" :x-gap="16" :y-gap="16">
      <!-- 最新新闻 -->
      <n-grid-item :span="2">
        <n-card title="最新新闻" hoverable>
          <template #header-extra>
            <n-button text @click="refreshNews" :loading="loading.news">
              <template #icon>
                <n-icon><RefreshOutline /></n-icon>
              </template>
              刷新
            </n-button>
          </template>
          
          <n-list v-if="latestNews.length > 0" bordered>
            <n-list-item
              v-for="news in latestNews"
              :key="news.id"
              style="cursor: pointer"
              @click="viewNewsDetail(news.id)"
            >
              <n-thing>
                <template #header>
                  <n-ellipsis style="max-width: 400px">
                    {{ news.title }}
                  </n-ellipsis>
                </template>
                <template #description>
                  <n-space size="small">
                    <n-tag size="small" :type="getSourceType(news.source)">
                      {{ news.source }}
                    </n-tag>
                    <n-text depth="3">
                      {{ formatTime(news.pub_time) }}
                    </n-text>
                  </n-space>
                </template>
                <n-ellipsis :line-clamp="2" style="margin-top: 8px">
                  {{ news.content }}
                </n-ellipsis>
              </n-thing>
            </n-list-item>
          </n-list>
          
          <n-empty v-else description="暂无新闻数据" />
        </n-card>
      </n-grid-item>
      
      <!-- 系统状态 -->
      <n-grid-item>
        <n-card title="系统状态" hoverable style="height: 100%">
          <n-space vertical size="large">
            <!-- 爬虫状态 -->
            <div>
              <n-text strong>爬虫状态</n-text>
              <n-list size="small" style="margin-top: 8px">
                <n-list-item v-for="crawler in crawlerStatus" :key="crawler.name">
                  <n-space justify="space-between" style="width: 100%">
                    <n-text>{{ crawler.name }}</n-text>
                    <n-tag
                      size="small"
                      :type="crawler.status === 'running' ? 'success' : 'default'"
                    >
                      {{ getStatusText(crawler.status) }}
                    </n-tag>
                  </n-space>
                </n-list-item>
              </n-list>
            </div>
            
            <!-- 快速操作 -->
            <div>
              <n-text strong>快速操作</n-text>
              <n-space vertical size="small" style="margin-top: 8px">
                <n-button
                  size="small"
                  block
                  secondary
                  @click="startAllCrawlers"
                  :loading="loading.startCrawlers"
                >
                  启动所有爬虫
                </n-button>
                <n-button
                  size="small"
                  block
                  secondary
                  @click="stopAllCrawlers"
                  :loading="loading.stopCrawlers"
                >
                  停止所有爬虫
                </n-button>
                <n-button
                  size="small"
                  block
                  secondary
                  @click="$router.push('/stats')"
                >
                  查看详细统计
                </n-button>
              </n-space>
            </div>
          </n-space>
        </n-card>
      </n-grid-item>
    </n-grid>
    
    <!-- 趋势图表 -->
    <n-card title="新闻采集趋势" hoverable style="margin-top: 16px">
      <template #header-extra>
        <n-radio-group v-model:value="chartPeriod" size="small">
          <n-radio-button value="7d">7天</n-radio-button>
          <n-radio-button value="30d">30天</n-radio-button>
          <n-radio-button value="90d">90天</n-radio-button>
        </n-radio-group>
      </template>
      
      <div ref="chartContainer" style="height: 300px"></div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  DocumentTextOutline,
  LibraryOutline,
  CloudDownloadOutline,
  CheckmarkCircleOutline,
  RefreshOutline
} from '@vicons/ionicons5'
import { newsApi, crawlerApi } from '../api'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import * as echarts from 'echarts'

const router = useRouter()
const message = useMessage()

// 响应式数据
const stats = ref({
  todayNews: 0,
  totalNews: 0,
  activeCrawlers: 0,
  successRate: 0
})

const latestNews = ref([])
const crawlerStatus = ref([])
const chartPeriod = ref('7d')
const chartContainer = ref(null)

const loading = ref({
  news: false,
  startCrawlers: false,
  stopCrawlers: false
})

let chart = null
let refreshTimer = null

// 方法
const formatTime = (timeStr) => {
  try {
    const date = new Date(timeStr)
    return formatDistanceToNow(date, { 
      locale: zhCN, 
      addSuffix: true 
    })
  } catch {
    return timeStr
  }
}

const getSourceType = (source) => {
  const sourceTypes = {
    '新浪财经': 'info',
    '东方财富': 'success', 
    '腾讯财经': 'warning',
    '网易财经': 'error',
    '凤凰财经': 'default'
  }
  return sourceTypes[source] || 'default'
}

const getStatusText = (status) => {
  const statusMap = {
    'running': '运行中',
    'stopped': '已停止',
    'error': '错误',
    'idle': '空闲'
  }
  return statusMap[status] || status
}

const viewNewsDetail = (id) => {
  router.push(`/news/${id}`)
}

const refreshNews = async () => {
  loading.value.news = true
  try {
    const response = await newsApi.getNewsList({ 
      limit: 10, 
      sort: 'pub_time', 
      order: 'desc' 
    })
    latestNews.value = response.news || []
  } catch (error) {
    message.error('刷新新闻失败')
  } finally {
    loading.value.news = false
  }
}

const loadStats = async () => {
  try {
    const response = await newsApi.getStats()
    stats.value = response
  } catch (error) {
    message.error('加载统计数据失败')
  }
}

const loadCrawlerStatus = async () => {
  try {
    const response = await crawlerApi.getStatus()
    crawlerStatus.value = response.crawlers || []
    stats.value.activeCrawlers = crawlerStatus.value.filter(
      c => c.status === 'running'
    ).length
  } catch (error) {
    message.error('加载爬虫状态失败')
  }
}

const startAllCrawlers = async () => {
  loading.value.startCrawlers = true
  try {
    await crawlerApi.start()
    message.success('正在启动所有爬虫')
    await loadCrawlerStatus()
  } catch (error) {
    message.error('启动爬虫失败')
  } finally {
    loading.value.startCrawlers = false
  }
}

const stopAllCrawlers = async () => {
  loading.value.stopCrawlers = true
  try {
    await crawlerApi.stop()
    message.success('正在停止所有爬虫')
    await loadCrawlerStatus()
  } catch (error) {
    message.error('停止爬虫失败')
  } finally {
    loading.value.stopCrawlers = false
  }
}

const initChart = async () => {
  if (!chartContainer.value) return
  
  await nextTick()
  chart = echarts.init(chartContainer.value)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['新闻数量', '成功率']
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: []
    },
    yAxis: [
      {
        type: 'value',
        name: '数量'
      },
      {
        type: 'value',
        name: '成功率(%)',
        min: 0,
        max: 100
      }
    ],
    series: [
      {
        name: '新闻数量',
        type: 'line',
        smooth: true,
        areaStyle: {},
        data: []
      },
      {
        name: '成功率',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: []
      }
    ]
  }
  
  chart.setOption(option)
  
  // 监听窗口大小变化
  window.addEventListener('resize', () => {
    chart?.resize()
  })
}

const loadTrendData = async () => {
  try {
    const response = await newsApi.getTrends({ period: chartPeriod.value })
    if (chart && response.trends) {
      chart.setOption({
        xAxis: {
          data: response.trends.dates
        },
        series: [
          {
            data: response.trends.newsCount
          },
          {
            data: response.trends.successRate
          }
        ]
      })
    }
  } catch (error) {
    message.error('加载趋势数据失败')
  }
}

// 生命周期
onMounted(async () => {
  await Promise.all([
    loadStats(),
    refreshNews(),
    loadCrawlerStatus()
  ])
  
  await initChart()
  await loadTrendData()
  
  // 设置定时刷新
  refreshTimer = setInterval(() => {
    loadStats()
    loadCrawlerStatus()
  }, 30000) // 30秒刷新一次
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  if (chart) {
    chart.dispose()
  }
  window.removeEventListener('resize', () => {
    chart?.resize()
  })
})

// 监听图表周期变化
watch(chartPeriod, () => {
  loadTrendData()
})
</script>

<style scoped>
.home-container {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.n-card {
  transition: all 0.3s ease;
}

.n-card:hover {
  transform: translateY(-2px);
}

.n-list-item {
  transition: all 0.2s ease;
}

.n-list-item:hover {
  background-color: rgba(24, 160, 88, 0.05);
}
</style> 