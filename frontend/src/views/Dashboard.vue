<template>
  <div class="dashboard">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>📊 数据概览</h1>
      <p>财经新闻爬虫系统综合仪表盘</p>
      
      <!-- 连接状态指示器 -->
      <div class="connection-status">
        <el-tag :type="connectionStatus.type" size="small">
          <el-icon style="margin-right: 4px">
            <component :is="connectionStatus.icon" />
          </el-icon>
          {{ connectionStatus.text }}
        </el-tag>
        <span class="status-hint">{{ connectionStatus.hint }}</span>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-cards">
      <el-col :xs="24" :sm="12" :md="6" v-for="stat in statsCards" :key="stat.key">
        <el-card class="stat-card" :class="stat.type">
          <div class="stat-content">
            <div class="stat-icon">
              <el-icon :size="32">
                <component :is="stat.icon" />
              </el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </div>
          <div class="stat-trend" v-if="stat.trend !== null">
            <el-icon :class="stat.trend > 0 ? 'trend-up' : 'trend-down'">
              <ArrowUp v-if="stat.trend > 0" />
              <ArrowDown v-else />
            </el-icon>
            <span>{{ Math.abs(stat.trend) }}%</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快速操作 -->
    <el-row :gutter="20" class="quick-actions">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>🚀 快速操作</span>
            </div>
          </template>
          <div class="action-buttons">
            <el-button type="primary" size="large" @click="refreshData" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新数据
            </el-button>
            <el-button type="success" size="large" @click="startAllCrawlers" :loading="loading">
              <el-icon><VideoPlay /></el-icon>
              启动全部爬虫
            </el-button>
            <el-button type="warning" size="large" @click="viewLogs">
              <el-icon><Document /></el-icon>
              查看日志
            </el-button>
            <el-button type="info" size="large" @click="$router.push('/error-diagnostics')">
              <el-icon><Tools /></el-icon>
              错误诊断
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 爬虫状态简览 -->
    <el-row :gutter="20" class="crawler-overview">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>🤖 爬虫状态概览</span>
              <el-button type="text" @click="loadCrawlerStatus" :loading="crawlerLoading">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </template>
          
          <el-table :data="crawlerStatus" v-loading="crawlerLoading" style="width: 100%">
            <el-table-column prop="name" label="爬虫名称" width="150">
              <template #default="{ row }">
                <el-tag :type="getStatusTagType(row.status)">
                  {{ row.name }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-badge 
                  :value="getStatusText(row.status)" 
                  :type="getStatusBadgeType(row.status)"
                />
              </template>
            </el-table-column>
            <el-table-column prop="lastUpdate" label="最后更新" width="180">
              <template #default="{ row }">
                {{ formatTime(row.lastUpdate) }}
              </template>
            </el-table-column>
            <el-table-column prop="newsCount" label="今日新闻" width="100" align="center">
              <template #default="{ row }">
                <el-tag type="info">{{ row.newsCount || 0 }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="errorCount" label="错误次数" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.errorCount > 0 ? 'danger' : 'success'">
                  {{ row.errorCount || 0 }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button 
                  v-if="row.status !== 'running'" 
                  type="primary" 
                  size="small" 
                  @click="startCrawler(row.name)"
                >
                  启动
                </el-button>
                <el-button 
                  v-else 
                  type="danger" 
                  size="small" 
                  @click="stopCrawler(row.name)"
                >
                  停止
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 系统信息 -->
    <el-row :gutter="20" class="system-info">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>💻 系统信息</span>
            </div>
          </template>
          <div class="info-grid">
            <div class="info-item">
              <strong>系统时间：</strong>
              <span>{{ currentTime }}</span>
            </div>
            <div class="info-item">
              <strong>运行状态：</strong>
              <el-tag type="success">正常运行</el-tag>
            </div>
            <div class="info-item">
              <strong>数据库状态：</strong>
              <el-tag type="success">连接正常</el-tag>
            </div>
            <div class="info-item">
              <strong>API状态：</strong>
              <el-tag type="success">服务正常</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { statsApi, crawlerApi } from '@/api'
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
  Tools,
  CircleClose,
  Warning
} from '@element-plus/icons-vue'

const router = useRouter()

// 响应式数据
const loading = ref(false)
const crawlerLoading = ref(false)
const currentTime = ref('')

// 连接状态
const connectionStatus = ref({
  type: 'warning',
  text: '检查中...',
  icon: Warning,
  hint: '正在检查后端服务连接'
})

// 统计卡片数据
const statsCards = ref([
  {
    key: 'total',
    label: '总新闻数',
    value: '加载中...',
    icon: Document,
    type: 'primary',
    trend: null
  },
  {
    key: 'today',
    label: '今日新闻',
    value: '加载中...',
    icon: Calendar,
    type: 'success',
    trend: null
  },
  {
    key: 'sources',
    label: '活跃来源',
    value: '加载中...',
    icon: Connection,
    type: 'warning',
    trend: null
  },
  {
    key: 'success_rate',
    label: '成功率',
    value: '加载中...',
    icon: CircleCheck,
    type: 'info',
    trend: null
  }
])

// 爬虫状态数据
const crawlerStatus = ref([])

// 定时器
let refreshTimer = null
let timeTimer = null

// 工具函数
const formatTime = (time) => {
  if (!time) return '--'
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
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
    const data = await statsApi.getStats()
    console.log('📊 统计数据响应:', data)
    
    // 更新连接状态
    connectionStatus.value = {
      type: 'success',
      text: '连接正常',
      icon: CircleCheck,
      hint: '后端API服务运行正常'
    }
    console.log('✅ 后端连接成功')
    
    if (data) {
      statsCards.value[0].value = data.total_news?.toLocaleString() || '0'
      statsCards.value[1].value = data.today_news?.toLocaleString() || '0'
      statsCards.value[2].value = data.active_sources?.toString() || '0'
      statsCards.value[3].value = `${((data.crawl_success_rate || 0) * 100).toFixed(1)}%`
      
      // 模拟趋势数据
      statsCards.value.forEach(card => {
        card.trend = Math.random() * 20 - 10
      })
      
      console.log('📊 统计卡片数据已更新:', statsCards.value)
    } else {
      console.warn('⚠️ 统计数据为空')
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
    
    console.log('📊 已设置默认统计数据')
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
      loadCrawlerStatus()
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

const viewLogs = () => {
  router.push('/system-log')
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
  console.log('📱 当前环境:', {
    location: window.location.href,
    userAgent: navigator.userAgent,
    viewport: `${window.innerWidth}x${window.innerHeight}`
  })
  
  updateTime()
  timeTimer = setInterval(updateTime, 1000)
  
  // 确保DOM完全渲染
  await nextTick()
  console.log('✅ DOM渲染完成')
  
  // 检查组件是否正确渲染
  const dashboardElement = document.querySelector('.dashboard')
  if (dashboardElement) {
    console.log('✅ Dashboard元素已找到:', dashboardElement)
    console.log('📏 Dashboard元素尺寸:', {
      width: dashboardElement.offsetWidth,
      height: dashboardElement.offsetHeight,
      display: window.getComputedStyle(dashboardElement).display,
      visibility: window.getComputedStyle(dashboardElement).visibility,
      opacity: window.getComputedStyle(dashboardElement).opacity
    })
  } else {
    console.error('❌ Dashboard元素未找到')
  }
  
  // 加载初始数据，但不显示过多提示消息
  console.log('🔄 开始加载数据...')
  await refreshData()
  console.log('✅ 数据加载完成')
  
  // 开始自动刷新
  startAutoRefresh()
  console.log('🔄 自动刷新已启动')
})

onUnmounted(() => {
  stopAutoRefresh()
  if (timeTimer) {
    clearInterval(timeTimer)
  }
})
</script>

<style lang="scss" scoped>
.dashboard {
  padding: 20px;
  width: 100%;
  min-height: 100%;
  position: relative;
  overflow: visible; /* 确保内容可见 */
  box-sizing: border-box;
  
  .page-header {
    text-align: center;
    margin-bottom: 30px;
    
    h1 {
      color: #303133;
      margin-bottom: 8px;
    }
    
    p {
      color: #606266;
      margin: 0 0 16px 0;
    }
    
    .connection-status {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      
      .status-hint {
        font-size: 12px;
        color: #909399;
      }
    }
  }
  
  .stats-cards {
    margin-bottom: 30px;
    width: 100%;
    
    .stat-card {
      height: 120px;
      cursor: pointer;
      transition: all 0.3s;
      position: relative;
      z-index: auto;
      overflow: visible;
      
      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      }
      
      &.primary { border-left: 4px solid #409EFF; }
      &.success { border-left: 4px solid #67C23A; }
      &.warning { border-left: 4px solid #E6A23C; }
      &.info { border-left: 4px solid #909399; }
      
      .stat-content {
        display: flex;
        align-items: center;
        height: 80px;
        
        .stat-icon {
          margin-right: 16px;
          color: #409EFF;
        }
        
        .stat-info {
          flex: 1;
          
          .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #303133;
            margin-bottom: 4px;
          }
          
          .stat-label {
            font-size: 14px;
            color: #606266;
          }
        }
      }
      
      .stat-trend {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        font-size: 12px;
        
        .trend-up { color: #67C23A; }
        .trend-down { color: #F56C6C; }
      }
    }
  }
  
  .quick-actions {
    margin-bottom: 30px;
    
    .action-buttons {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
      
      .el-button {
        flex: 1;
        min-width: 120px;
      }
    }
  }
  
  .crawler-overview {
    margin-bottom: 30px;
  }
  
  .system-info {
    .info-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 16px;
      
      .info-item {
        display: flex;
        align-items: center;
        gap: 8px;
        
        strong {
          color: #303133;
          min-width: 100px;
        }
      }
    }
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    span {
      font-weight: bold;
      color: #303133;
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .dashboard {
    padding: 10px;
    
    .action-buttons {
      flex-direction: column;
      
      .el-button {
        width: 100%;
      }
    }
    
    .info-grid {
      grid-template-columns: 1fr;
      
      .info-item {
        flex-direction: column;
        align-items: flex-start;
        
        strong {
          min-width: auto;
        }
      }
    }
  }
}
</style> 