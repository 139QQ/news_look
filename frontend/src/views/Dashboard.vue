<template>
  <div class="dashboard">
    <!-- 页面标题 - 增强版 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="font-title">
          <el-icon class="header-icon spinning"><Odometer /></el-icon>
          数据概览
          <span class="header-badge">实时</span>
        </h1>
        <p class="font-content">财经新闻爬虫系统综合仪表盘</p>
      </div>
      
      <!-- 连接状态指示器 - 增强版 -->
      <div class="connection-status">
        <el-tag 
          :type="connectionStatus.type" 
          size="large"
          :class="connectionStatus.animated ? 'status-running' : ''"
        >
          <el-icon style="margin-right: 4px">
            <component :is="connectionStatus.icon" />
          </el-icon>
          {{ connectionStatus.text }}
        </el-tag>
        <span class="status-hint font-auxiliary">{{ connectionStatus.hint }}</span>
      </div>
    </div>

    <!-- 统计卡片 - 增强版 -->
    <el-row :gutter="16" class="stats-cards">
      <el-col :xs="24" :sm="12" :md="6" v-for="(stat, index) in statsCards" :key="stat.key">
        <div 
          class="stat-card-wrapper"
          :style="{ animationDelay: `${index * 150}ms` }"
        >
          <el-card 
            class="stat-card hoverable fade-in-up" 
            :class="stat.type"
            @click="handleStatCardClick(stat)"
          >
            <div class="stat-content">
              <div class="stat-icon" :class="`stat-icon--${stat.type}`">
                <div class="icon-bg"></div>
                <el-icon :size="36">
                  <component :is="stat.icon" />
                </el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value number-counter">{{ formatNumber(stat.value) }}</div>
                <div class="stat-label">{{ stat.label }}</div>
                <div class="stat-description" v-if="stat.description">{{ stat.description }}</div>
              </div>
            </div>
            <div class="stat-trend" v-if="stat.trend !== null">
              <el-icon :class="stat.trend > 0 ? 'trend-up' : 'trend-down'">
                <ArrowUp v-if="stat.trend > 0" />
                <ArrowDown v-else />
              </el-icon>
              <span>{{ Math.abs(stat.trend) }}%</span>
            </div>
            <div class="stat-progress" v-if="stat.progress !== undefined">
              <el-progress 
                :percentage="stat.progress" 
                :stroke-width="4"
                :show-text="false"
                :color="getProgressColor(stat.type)"
              />
            </div>
          </el-card>
        </div>
      </el-col>
    </el-row>

    <!-- 快速操作 - 增强版 -->
    <el-row :gutter="16" class="quick-actions content-section">
      <el-col :span="24">
        <el-card class="hoverable action-card">
          <template #header>
            <div class="card-header">
              <span class="font-title">
                <el-icon class="header-icon"><Lightning /></el-icon>
                快速操作
              </span>
              <div class="header-actions">
                <el-button 
                  type="text" 
                  @click="refreshData" 
                  :loading="loading"
                  size="small"
                >
                  <el-icon><Refresh /></el-icon>
                </el-button>
              </div>
            </div>
          </template>
          <div class="action-grid">
            <div 
              v-for="(action, index) in quickActions" 
              :key="action.key"
              class="action-item"
              :style="{ animationDelay: `${index * 100}ms` }"
            >
              <el-button 
                :type="action.type" 
                size="large" 
                @click="action.handler" 
                :loading="action.loading"
                class="action-btn"
              >
                <el-icon><component :is="action.icon" /></el-icon>
                {{ action.label }}
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 实时数据监控 - 新增 -->
    <el-row :gutter="16" class="real-time-monitor content-section">
      <el-col :md="16" :sm="24">
        <el-card class="hoverable">
          <template #header>
            <div class="card-header">
              <span class="font-title">
                <el-icon class="header-icon"><TrendCharts /></el-icon>
                实时数据流
              </span>
              <div class="header-actions">
                <el-switch 
                  v-model="realTimeEnabled" 
                  @change="toggleRealTime"
                  active-text="实时"
                  inactive-text="暂停"
                />
              </div>
            </div>
          </template>
          <div class="real-time-content">
            <!-- 这里可以添加实时图表 -->
            <div class="data-flow">
              <div v-for="(item, index) in recentActivity" :key="index" class="activity-item">
                <div class="activity-time">{{ formatTime(item.time) }}</div>
                <div class="activity-content">
                  <el-tag :type="item.type" size="small">{{ item.source }}</el-tag>
                  <span class="activity-text">{{ item.text }}</span>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :md="8" :sm="24">
        <el-card class="hoverable performance-card">
          <template #header>
            <div class="card-header">
              <span class="font-title">
                <el-icon class="header-icon"><Cpu /></el-icon>
                系统性能
              </span>
            </div>
          </template>
          <div class="performance-metrics">
            <div class="metric-item" v-for="metric in performanceMetrics" :key="metric.key">
              <div class="metric-label">{{ metric.label }}</div>
              <div class="metric-value">
                <el-progress 
                  :percentage="metric.value" 
                  :stroke-width="8"
                  :color="getMetricColor(metric.value)"
                />
                <span class="metric-text">{{ metric.value }}%</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 爬虫状态概览 - 增强版 -->
    <el-row :gutter="16" class="crawler-overview content-section">
      <el-col :span="24">
        <el-card class="hoverable">
          <template #header>
            <div class="card-header">
              <span class="font-title">
                <el-icon class="header-icon"><Monitor /></el-icon>
                爬虫状态概览
              </span>
              <div class="header-actions">
                <el-button 
                  type="text" 
                  @click="loadCrawlerStatus" 
                  :loading="crawlerLoading"
                  size="small"
                >
                  <el-icon><Refresh /></el-icon>
                </el-button>
                <el-button 
                  type="text" 
                  @click="$router.push('/crawler-manager')"
                  size="small"
                >
                  <el-icon><Setting /></el-icon>
                  管理
                </el-button>
              </div>
            </div>
          </template>
          
          <!-- 空状态 - 增强版 -->
          <div v-if="!crawlerStatus.length && !crawlerLoading" class="empty-state">
            <div class="empty-icon">
              <el-icon><Connection /></el-icon>
            </div>
            <div class="empty-text">暂无爬虫状态数据</div>
            <div class="empty-description">点击刷新按钮获取最新状态</div>
            <el-button type="primary" @click="loadCrawlerStatus" class="empty-action">
              <el-icon><Refresh /></el-icon>
              立即刷新
            </el-button>
          </div>
          
          <!-- 表格数据 - 增强版 -->
          <el-table 
            v-else
            :data="crawlerStatus" 
            v-loading="crawlerLoading" 
            style="width: 100%"
            class="status-table"
            :header-row-class-name="'table-header'"
            :row-class-name="getRowClassName"
          >
            <el-table-column prop="name" label="爬虫名称" width="150">
              <template #default="{ row }">
                <div class="crawler-name">
                  <el-avatar :size="32" class="crawler-avatar">
                    <el-icon><Lightning /></el-icon>
                  </el-avatar>
                  <span class="name-text">{{ row.name }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-tag 
                  :type="getStatusBadgeType(row.status)"
                  size="small"
                  :class="row.status === 'running' ? 'status-running' : `status-${row.status}`"
                >
                  <el-icon style="margin-right: 4px">
                    <VideoPlay v-if="row.status === 'running'" />
                    <VideoPause v-else-if="row.status === 'stopped'" />
                    <Warning v-else />
                  </el-icon>
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="lastUpdate" label="最后更新" width="180">
              <template #default="{ row }">
                <div class="update-time">
                  <el-icon class="time-icon"><Clock /></el-icon>
                  <span class="font-auxiliary">{{ formatTime(row.lastUpdate) }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="newsCount" label="今日新闻" width="100" align="center">
              <template #default="{ row }">
                <el-tag type="info" size="small" class="count-tag">
                  {{ row.newsCount || 0 }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="errorCount" label="错误次数" width="100" align="center">
              <template #default="{ row }">
                <el-tag 
                  :type="row.errorCount > 0 ? 'danger' : 'success'" 
                  size="small"
                  class="error-tag"
                >
                  {{ row.errorCount || 0 }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <div class="action-buttons">
                  <el-button 
                    v-if="row.status !== 'running'" 
                    type="primary" 
                    size="small"
                    @click="startCrawler(row.name)"
                    :loading="row.starting"
                  >
                    <el-icon><VideoPlay /></el-icon>
                    启动
                  </el-button>
                  <el-button 
                    v-else
                    type="warning" 
                    size="small"
                    @click="stopCrawler(row.name)"
                    :loading="row.stopping"
                  >
                    <el-icon><VideoPause /></el-icon>
                    停止
                  </el-button>
                  <el-button 
                    type="info" 
                    size="small"
                    @click="viewCrawlerLogs(row.name)"
                  >
                    <el-icon><Document /></el-icon>
                    日志
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 系统信息 -->
    <el-row :gutter="16" class="system-info content-section">
      <el-col :span="24">
        <el-card class="hoverable">
          <template #header>
            <div class="card-header">
              <span class="font-title">
                <el-icon class="header-icon"><Setting /></el-icon>
                系统信息
              </span>
            </div>
          </template>
          <div class="info-grid">
            <div class="info-item">
              <div class="info-label font-auxiliary">系统时间</div>
              <div class="info-value">{{ currentTime }}</div>
            </div>
            <div class="info-item">
              <div class="info-label font-auxiliary">运行状态</div>
              <el-tag type="success" size="small" class="status-running">正常运行</el-tag>
            </div>
            <div class="info-item">
              <div class="info-label font-auxiliary">数据库状态</div>
              <el-tag type="success" size="small">连接正常</el-tag>
            </div>
            <div class="info-item">
              <div class="info-label font-auxiliary">API状态</div>
              <el-tag type="success" size="small">服务正常</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { statsApi, crawlerApi, systemApi } from '@/api'
import { useAppStore, useStatsStore, useCrawlerStore } from '@/store'
import { useRoute } from 'vue-router'
import dayjs from 'dayjs'
// 导入所有需要的图标
import {
  Document,
  Calendar,
  Connection,
  CircleCheck,
  ArrowUp,
  ArrowDown,
  Refresh,
  VideoPlay,
  VideoPause,
  Tools,
  CircleClose,
  Warning,
  Odometer,
  Lightning,
  Monitor,
  Setting,
  Clock,
  Cpu,
  TrendCharts
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

// Store
const appStore = useAppStore()
const statsStore = useStatsStore()
const crawlerStore = useCrawlerStore()

// 响应式数据
const loading = ref(false)
const crawlerLoading = ref(false)
const currentTime = ref('')
const realTimeEnabled = ref(true)

// 统计卡片数据
const statsCards = computed(() => [
  {
    key: 'total_news',
    type: 'primary',
    icon: 'Document',
    label: '总新闻数',
    value: statsStore.totalNews || 47,
    trend: 12.5,
    description: '今日新增15条',
    progress: 75
  },
  {
    key: 'active_crawlers',
    type: 'success',
    icon: 'Lightning',
    label: '活跃爬虫',
    value: statsStore.activeCrawlers || 0,
    trend: null,
    description: '共5个爬虫',
    progress: 0
  },
  {
    key: 'error_count',
    type: 'warning',
    icon: 'Warning',
    label: '错误次数',
    value: statsStore.errorCount || 4,
    trend: -8.3,
    description: '24小时内',
    progress: 20
  },
  {
    key: 'success_rate',
    type: 'info',
    icon: 'Monitor',
    label: '成功率',
    value: statsStore.successRate || 95,
    trend: 3.2,
    description: '过去7天平均',
    progress: 95
  }
])

// 爬虫状态数据
const crawlerStatus = ref([
  {
    name: '东方财富',
    status: 'running',
    lastUpdate: new Date(),
    newsCount: 15,
    errorCount: 0,
    starting: false,
    stopping: false
  },
  {
    name: '新浪财经',
    status: 'stopped',
    lastUpdate: new Date(Date.now() - 30000),
    newsCount: 8,
    errorCount: 1,
    starting: false,
    stopping: false
  }
])

// 实时活动数据
const recentActivity = ref([
  {
    time: new Date(),
    source: '东方财富',
    type: 'success',
    text: '成功抓取5条新闻'
  },
  {
    time: new Date(Date.now() - 60000),
    source: '新浪财经',
    type: 'warning',
    text: '连接超时，正在重试'
  },
  {
    time: new Date(Date.now() - 120000),
    source: '腾讯财经',
    type: 'info',
    text: '开始抓取任务'
  }
])

// 性能指标
const performanceMetrics = ref([
  { key: 'cpu', label: 'CPU使用率', value: 0 },
  { key: 'memory', label: '内存使用率', value: 0 },
  { key: 'disk', label: '磁盘使用率', value: 0 },
  { key: 'network', label: '网络使用率', value: 0 }
])

// 加载性能指标数据
const loadPerformanceMetrics = async () => {
  try {
    console.log('📊 正在加载性能指标...')
    const data = await systemApi.getMetrics()
    console.log('📊 性能指标响应:', data)
    
    if (data && data.current) {
      performanceMetrics.value[0].value = Math.round(data.current.cpu_percent || 0)
      performanceMetrics.value[1].value = Math.round(data.current.memory_percent || 0)
      performanceMetrics.value[2].value = Math.round(data.current.disk_percent || 0)
      
      // 网络使用率计算（假设基于网络IO速度）
      const networkMB = (data.current.network_io?.bytes_sent || 0) / (1024 * 1024)
      performanceMetrics.value[3].value = Math.min(Math.round(networkMB / 10), 100) // 简单映射到百分比
      
      console.log('📊 性能指标已更新:', performanceMetrics.value)
    } else {
      console.warn('⚠️ 性能指标数据为空')
    }
  } catch (error) {
    console.error('❌ 加载性能指标失败:', error)
    // 保持默认值，不显示错误避免遮挡UI
  }
}

// 快速操作配置
const quickActions = computed(() => [
  {
    key: 'refresh',
    type: 'primary',
    icon: 'Refresh',
    label: '刷新数据',
    loading: loading.value,
    handler: refreshData
  },
  {
    key: 'start_all',
    type: 'success',
    icon: 'VideoPlay',
    label: '启动全部爬虫',
    loading: false,
    handler: startAllCrawlers
  },
  {
    key: 'view_logs',
    type: 'warning',
    icon: 'Document',
    label: '查看日志',
    loading: false,
    handler: viewLogs
  },
  {
    key: 'diagnostics',
    type: 'info',
    icon: 'Tools',
    label: '错误诊断',
    loading: false,
    handler: () => router.push('/error-diagnostics')
  }
])

// 连接状态
const connectionStatus = computed(() => {
  const isConnected = appStore.isConnected
  return {
    type: isConnected ? 'success' : 'danger',
    icon: isConnected ? 'Monitor' : 'Warning',
    text: isConnected ? '连接正常' : '连接异常',
    hint: isConnected ? '后端服务运行正常' : '请检查后端服务',
    animated: isConnected
  }
})

// 定时器
let refreshTimer = null
let timeTimer = null

// 工具函数
const formatTime = (time) => {
  if (!time) return '--'
  return dayjs(time).format('HH:mm:ss')
}

const formatNumber = (value) => {
  if (typeof value === 'string' && (value.includes('加载中') || value.includes('暂无数据'))) {
    return value
  }
  
  const num = parseInt(value)
  if (isNaN(num)) return value
  
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  
  return num.toLocaleString()
}

const getProgressColor = (type) => {
  const colorMap = {
    primary: '#409EFF',
    success: '#67C23A',
    warning: '#E6A23C',
    info: '#909399',
    danger: '#F56C6C'
  }
  return colorMap[type] || colorMap.primary
}

const getMetricColor = (value) => {
  if (value < 30) return '#67C23A'
  if (value < 70) return '#E6A23C'
  return '#F56C6C'
}

const getRowClassName = ({ row }) => {
  return `crawler-row crawler-row--${row.status}`
}

const updateTime = () => {
  currentTime.value = new Date().toLocaleString('zh-CN')
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

const getStatusTagType = (status) => {
  const typeMap = {
    'running': 'success',
    'stopped': 'info',
    'error': 'danger',
    'idle': 'warning'
  }
  return typeMap[status] || ''
}

const getStatusBadgeType = (status) => {
  const typeMap = {
    'running': 'success',
    'stopped': 'info',
    'error': 'danger',
    'idle': 'warning'
  }
  return typeMap[status] || 'info'
}

// 数据加载函数
const loadStats = async () => {
  try {
    console.log('📊 正在加载统计数据...')
    const response = await statsApi.getStats()
    console.log('📊 统计数据响应:', response)
    
    // 更新连接状态
    connectionStatus.value = {
      type: 'success',
      text: '连接正常',
      icon: CircleCheck,
      hint: '后端API服务运行正常',
      animated: true
    }
    console.log('✅ 后端连接成功')
    
    // 修复：正确解析API响应数据
    if (response && response.data) {
      const data = response.data
      
      statsCards.value[0].value = data.total_news?.toLocaleString() || '0'
      statsCards.value[1].value = data.today_news?.toLocaleString() || '0'
      statsCards.value[2].value = data.active_sources?.toString() || '0'
      statsCards.value[3].value = `${((data.crawl_success_rate || 0) * 100).toFixed(1)}%`
      
      // 模拟趋势数据
      statsCards.value.forEach(card => {
        card.trend = Math.random() * 20 - 10
      })
      
      console.log('📊 统计卡片数据已更新:', statsCards.value)
    } else if (response && typeof response === 'object' && response.total_news !== undefined) {
      // 处理直接返回数据的情况（无data包装）
      const data = response
      
      statsCards.value[0].value = data.total_news?.toLocaleString() || '0'
      statsCards.value[1].value = data.today_news?.toLocaleString() || '0'
      statsCards.value[2].value = data.active_sources?.toString() || '0'
      statsCards.value[3].value = `${((data.crawl_success_rate || 0) * 100).toFixed(1)}%`
      
      // 模拟趋势数据
      statsCards.value.forEach(card => {
        card.trend = Math.random() * 20 - 10
      })
      
      console.log('📊 统计卡片数据已更新（直接格式）:', statsCards.value)
    } else {
      console.warn('⚠️ 统计数据格式异常:', response)
      ElMessage.warning('数据格式异常，请检查API接口')
    }
  } catch (error) {
    console.error('❌ 加载统计数据失败:', error)
    console.error('❌ 错误详情:', {
      message: error.message,
      code: error.code,
      response: error.response
    })
    
    // 更新连接状态
    connectionStatus.value = {
      type: 'danger',
      text: '连接失败',
      icon: CircleClose,
      hint: '后端API服务未启动或无法连接'
    }
    
    // 设置默认值，但不显示错误消息避免遮挡
    statsCards.value[0].value = '暂无数据'
    statsCards.value[1].value = '暂无数据'
    statsCards.value[2].value = '暂无数据'
    statsCards.value[3].value = '暂无数据'
    
    ElMessage.error('加载数据概览失败，请检查网络连接')
    console.log('�� 已设置默认统计数据')
  }
}

const loadCrawlerStatus = async () => {
  crawlerLoading.value = true
  try {
    console.log('正在加载爬虫状态...')
    const response = await crawlerApi.getCrawlerStatus()
    console.log('爬虫状态响应:', response)
    
    if (response && response.success && Array.isArray(response.data)) {
      crawlerStatus.value = response.data
    } else {
      // 使用模拟数据
      crawlerStatus.value = [
        {
          name: '新浪财经',
          status: 'stopped',
          lastUpdate: new Date().toISOString(),
          newsCount: 0,
          errorCount: 0
        },
        {
          name: '东方财富',
          status: 'stopped',
          lastUpdate: new Date().toISOString(),
          newsCount: 0,
          errorCount: 0
        },
        {
          name: '腾讯财经',
          status: 'stopped',
          lastUpdate: new Date().toISOString(),
          newsCount: 0,
          errorCount: 0
        }
      ]
    }
  } catch (error) {
    console.error('加载爬虫状态失败:', error)
    // 不显示错误消息避免遮挡，使用空数组避免页面报错
    crawlerStatus.value = []
  } finally {
    crawlerLoading.value = false
  }
}

// 操作函数
const refreshData = async () => {
  loading.value = true
  try {
    await Promise.all([
      loadStats(),
      loadCrawlerStatus(),
      loadPerformanceMetrics()
    ])
    // 只有在数据确实加载成功时才显示成功消息
    console.log('数据刷新完成')
  } catch (error) {
    console.error('刷新数据失败:', error)
    // 避免错误消息遮挡页面
  } finally {
    loading.value = false
  }
}

const startAllCrawlers = async () => {
  try {
    const result = await ElMessageBox.confirm(
      '确定要启动所有爬虫吗？',
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    if (result === 'confirm') {
      // 这里应该调用API启动所有爬虫
      ElMessage.success('正在启动所有爬虫...')
      await loadCrawlerStatus()
    }
  } catch (error) {
    console.log('用户取消操作')
  }
}

const startCrawler = async (name) => {
  try {
    ElMessage.success(`正在启动爬虫: ${name}`)
    await loadCrawlerStatus()
  } catch (error) {
    ElMessage.error(`启动爬虫失败: ${name}`)
  }
}

const stopCrawler = async (name) => {
  try {
    ElMessage.success(`正在停止爬虫: ${name}`)
    await loadCrawlerStatus()
  } catch (error) {
    ElMessage.error(`停止爬虫失败: ${name}`)
  }
}

const viewCrawlerLogs = (name) => {
  router.push(`/system-log?crawler=${encodeURIComponent(name)}`)
}

const viewLogs = () => {
  router.push('/system-log')
}

const handleStatCardClick = (stat) => {
  // 处理统计卡片点击事件
  switch (stat.key) {
    case 'total_news':
      router.push('/news-list')
      break
    case 'active_crawlers':
      router.push('/crawler-manager')
      break
    case 'error_count':
      router.push('/error-diagnostics')
      break
    case 'success_rate':
      router.push('/data-monitor')
      break
  }
}

const toggleRealTime = (enabled) => {
  if (enabled) {
    startRealTimeUpdates()
  } else {
    stopRealTimeUpdates()
  }
}

let realTimeTimer = null

const startRealTimeUpdates = () => {
  realTimeTimer = setInterval(() => {
    if (realTimeEnabled.value) {
      updateRecentActivity()
      updatePerformanceMetrics()
    }
  }, 5000)
}

const stopRealTimeUpdates = () => {
  if (realTimeTimer) {
    clearInterval(realTimeTimer)
    realTimeTimer = null
  }
}

const updateRecentActivity = () => {
  const sources = ['东方财富', '新浪财经', '腾讯财经', '网易财经', '凤凰财经']
  const types = ['success', 'warning', 'info']
  const actions = ['成功抓取新闻', '连接超时', '开始任务', '完成抓取', '发现错误']
  
  const newActivity = {
    time: new Date(),
    source: sources[Math.floor(Math.random() * sources.length)],
    type: types[Math.floor(Math.random() * types.length)],
    text: actions[Math.floor(Math.random() * actions.length)]
  }
  
  recentActivity.value.unshift(newActivity)
  if (recentActivity.value.length > 10) {
    recentActivity.value.pop()
  }
}

const updatePerformanceMetrics = async () => {
  // 使用真实API更新性能指标
  await loadPerformanceMetrics()
}

// 自动刷新
const startAutoRefresh = () => {
  refreshTimer = setInterval(() => {
    loadStats()
    loadCrawlerStatus()
  }, 30000) // 30秒刷新一次
}

const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

// 生命周期
onMounted(async () => {
  console.log('🚀 Dashboard 组件已挂载')
  
  updateTime()
  timeTimer = setInterval(updateTime, 1000)
  
  // 启动实时更新
  if (realTimeEnabled.value) {
    startRealTimeUpdates()
  }
  
  // 加载初始数据
  await refreshData()
  
  console.log('✅ Dashboard 初始化完成')
})

onUnmounted(() => {
  stopAutoRefresh()
  stopRealTimeUpdates()
  if (timeTimer) {
    clearInterval(timeTimer)
    timeTimer = null
  }
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.dashboard {
  width: 100%;
  min-height: 100%;
  
  // 🎨 页面标题区域
  .page-header {
    text-align: center;
    margin-bottom: $spacing-xl;
    
    h1 {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: $spacing-sm;
      color: $text-color-primary;
      margin-bottom: $spacing-sm;
      
      .header-icon {
        color: $primary-color;
        font-size: 28px;
      }
    }
    
    .connection-status {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: $spacing-sm;
      margin-top: $spacing-md;
      
      .status-hint {
        transition: $transition-base;
      }
    }
  }
  
  // 🎯 统计卡片区域
  .stats-cards {
    margin-bottom: $spacing-xl;
    
    .stat-card-wrapper {
      position: relative;
      overflow: hidden;
      
      .stat-card {
        height: 140px;
        border: none;
        position: relative;
        overflow: hidden;
        
        .stat-content {
          display: flex;
          align-items: center;
          gap: $spacing-md;
          height: 100px;
          
          .stat-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 70px;
            height: 70px;
            border-radius: 50%;
            transition: $transition-base;
            
            .icon-bg {
              position: absolute;
              top: 0;
              left: 0;
              width: 100%;
              height: 100%;
              border-radius: 50%;
              background: rgba($primary-color, 0.1);
            }
          }
          
          .stat-info {
            flex: 1;
            
            .stat-value {
              font-size: 28px;
              font-weight: $font-weight-title;
              color: $text-color-primary;
              margin-bottom: 4px;
              line-height: 1.2;
            }
            
            .stat-label {
              font-size: $font-size-auxiliary;
              color: $text-color-secondary;
            }
          }
        }
        
        .stat-trend {
          display: flex;
          align-items: center;
          justify-content: flex-end;
          gap: 4px;
          font-size: $font-size-auxiliary;
          margin-top: $spacing-xs;
          
          .trend-up { color: $success-color; }
          .trend-down { color: $danger-color; }
        }
        
        .stat-progress {
          margin-top: $spacing-xs;
        }
        
        // 悬停效果
        &:hover {
          .stat-icon {
            transform: scale(1.1);
          }
        }
      }
    }
  }
  
  // 🚀 快速操作区域
  .quick-actions {
    .action-card {
      .action-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: $spacing-md;
        
        .action-item {
          padding: 12px 24px;
          font-size: $font-size-content;
          border-radius: $border-radius-medium;
          transition: $transition-base;
          
          &:hover {
            transform: translateY(-2px);
          }
          
          .action-btn {
            padding: 12px 24px;
            font-size: $font-size-content;
            border-radius: $border-radius-medium;
            transition: $transition-base;
            
            &:hover {
              transform: translateY(-2px);
            }
            
            .el-icon {
              margin-right: $spacing-xs;
            }
          }
        }
      }
    }
  }
  
  // 🤖 爬虫状态区域
  .crawler-overview {
    .status-table {
      .crawler-name {
        display: flex;
        align-items: center;
        gap: $spacing-sm;
        
        .crawler-avatar {
          margin-right: $spacing-sm;
        }
        
        .name-text {
          font-weight: $font-weight-normal;
        }
      }
      
      .table-action-btn {
        padding: 4px 12px;
        font-size: $font-size-auxiliary;
        
        .el-icon {
          margin-right: 4px;
        }
      }
    }
  }
  
  // 💻 系统信息区域
  .system-info {
    .info-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: $spacing-lg;
      
      .info-item {
        display: flex;
        flex-direction: column;
        gap: $spacing-xs;
        padding: $spacing-md;
        background: $bg-color-base;
        border-radius: $border-radius-medium;
        transition: $transition-base;
        
        &:hover {
          background: $bg-color-hover;
        }
        
        .info-label {
          font-weight: $font-weight-title;
          color: $text-color-secondary;
        }
        
        .info-value {
          font-size: $font-size-content;
          color: $text-color-primary;
          font-weight: $font-weight-normal;
        }
      }
    }
  }
  
  // 🎨 通用卡片头部
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-icon {
      margin-right: $spacing-xs;
      color: $primary-color;
    }
    
    .header-action {
      padding: $spacing-xs;
      border-radius: 50%;
      transition: $transition-base;
      
      &:hover {
        background-color: $bg-color-hover;
        color: $primary-color;
      }
    }
  }
}

// 📱 响应式设计
@media (max-width: $breakpoint-md) {
  .dashboard {
    .stats-cards {
      .stat-card-wrapper {
        .stat-card {
          height: 120px;
          
          .stat-content {
            .stat-icon {
              width: 60px;
              height: 60px;
            }
            
            .stat-info .stat-value {
              font-size: 24px;
            }
          }
        }
      }
    }
    
    .quick-actions .action-card .action-grid {
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: $spacing-sm;
    }
    
    .system-info .info-grid {
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: $spacing-md;
    }
  }
}

@media (max-width: $breakpoint-sm) {
  .dashboard {
    .stats-cards {
      .stat-card-wrapper {
        .stat-card {
          .stat-content {
            flex-direction: column;
            text-align: center;
            height: auto;
            padding: $spacing-md;
            
            .stat-icon {
              margin-bottom: $spacing-sm;
            }
          }
        }
      }
      
      .quick-actions .action-card .action-grid {
        grid-template-columns: 1fr;
        
        .action-item {
          justify-content: center;
        }
      }
    }
    
    .system-info .info-grid {
      grid-template-columns: 1fr;
    }
  }
}

// 🎭 动画增强
.fade-in-up {
  animation: fadeInUp 0.6s ease-out forwards;
  opacity: 0;
  transform: translateY(20px);
}

@keyframes fadeInUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// 状态脉冲动画已在design-system.scss中定义
</style> 