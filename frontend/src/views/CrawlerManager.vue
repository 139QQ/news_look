<template>
  <div class="crawler-manager">
    <el-card class="mb-20">
      <template #header>
        <div class="flex-between">
          <div class="header-left">
            <span class="header-title">爬虫管理</span>
            <el-tag 
              :type="wsConnected ? 'success' : 'warning'"
              size="small"
              class="ml-10"
            >
              <el-icon class="mr-5">
                <Connection v-if="wsConnected" />
                <Warning v-else />
              </el-icon>
              {{ wsConnected ? '实时连接' : '轮询模式' }}
            </el-tag>
          </div>
          <div class="header-actions">
            <el-button 
              type="success" 
              :loading="isStartingAll"
              @click="startAllCrawlers"
              :disabled="crawlerStore.activeCrawlers === crawlerStore.totalCrawlers"
            >
              <el-icon><CaretRight /></el-icon>
              启动全部
            </el-button>
            <el-button 
              type="danger" 
              :loading="isStoppingAll"
              @click="stopAllCrawlers"
              :disabled="crawlerStore.activeCrawlers === 0"
            >
              <el-icon><VideoPause /></el-icon>
              停止全部
            </el-button>
            <el-button 
              type="primary" 
              @click="refreshStatus"
              :loading="crawlerStore.isLoading"
            >
              <el-icon><Refresh /></el-icon>
              刷新状态
            </el-button>
          </div>
        </div>
      </template>
      
      <el-table 
        :data="crawlerStore.crawlers" 
        style="width: 100%"
        :loading="crawlerStore.isLoading"
        v-loading="crawlerStore.isLoading"
      >
        <el-table-column prop="display_name" label="爬虫名称" width="150">
          <template #default="{ row }">
            <div class="flex">
              <el-icon class="mr-10">
                <component :is="getSourceIcon(row.name)" />
              </el-icon>
              {{ row.display_name }}
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag 
              :type="getStatusType(row.status)"
              size="small"
            >
              <el-icon class="mr-5">
                <component :is="getStatusIcon(row.status)" />
              </el-icon>
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="success_rate" label="成功率" width="120">
          <template #default="{ row }">
            <div class="progress-container">
              <el-progress 
                :percentage="row.success_rate" 
                :status="getProgressStatus(row.success_rate)"
                :stroke-width="12"
                :show-text="false"
                class="enhanced-progress"
              />
              <span class="progress-text" :style="getSuccessRateStyle(row.success_rate)">
                {{ row.success_rate }}%
              </span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="last_run" label="最后运行时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.last_run) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                v-if="row.status !== 'running'"
                type="success" 
                size="small"
                :loading="loadingStates[row.name]?.starting"
                @click="startCrawler(row.name)"
              >
                <el-icon><CaretRight /></el-icon>
                启动
              </el-button>
              
              <el-button 
                v-if="row.status === 'running'"
                type="danger" 
                size="small"
                :loading="loadingStates[row.name]?.stopping"
                @click="stopCrawler(row.name)"
              >
                <el-icon><VideoPause /></el-icon>
                停止
              </el-button>
              
              <el-button 
                type="primary" 
                size="small"
                @click="showConfig(row)"
              >
                <el-icon><Setting /></el-icon>
                配置
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 爬虫统计 -->
    <el-row :gutter="20">
      <el-col :xs="24" :sm="8" :md="8" :lg="8">
        <el-card class="stat-card">
          <el-statistic 
            title="总爬虫数" 
            :value="crawlerStore.totalCrawlers"
          >
            <template #suffix>
              <el-icon><Lightning /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="8" :md="8" :lg="8">
        <el-card class="stat-card">
          <el-statistic 
            title="运行中" 
            :value="crawlerStore.activeCrawlers"
            value-style="color: #67c23a"
          >
            <template #suffix>
              <el-icon><CaretRight /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="8" :md="8" :lg="8">
        <el-card class="stat-card">
          <el-statistic 
            title="平均成功率" 
            :value="crawlerStore.averageSuccessRate"
            suffix="%"
            :value-style="getSuccessRateStyle(crawlerStore.averageSuccessRate)"
          >
            <template #suffix>
              <span>%</span>
              <el-icon><TrendCharts /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>

    <!-- 爬虫配置对话框 -->
    <el-dialog 
      v-model="configDialogVisible" 
      title="爬虫配置"
      width="600px"
    >
      <el-form :model="configForm" label-width="120px">
        <el-form-item label="爬虫名称">
          <el-input v-model="configForm.name" disabled />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="configForm.display_name" />
        </el-form-item>
        <el-form-item label="抓取间隔">
          <el-input-number 
            v-model="configForm.interval" 
            :min="1" 
            :max="3600"
            suffix="秒"
          />
        </el-form-item>
        <el-form-item label="超时时间">
          <el-input-number 
            v-model="configForm.timeout" 
            :min="5" 
            :max="300"
            suffix="秒"
          />
        </el-form-item>
        <el-form-item label="重试次数">
          <el-input-number 
            v-model="configForm.retry_count" 
            :min="0" 
            :max="10"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveConfig">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useCrawlerStore } from '@/store'
import { crawlerApi } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import message from '@/utils/message'
import wsManager from '@/utils/websocket'
import dayjs from 'dayjs'

// Store
const crawlerStore = useCrawlerStore()

// 加载状态
const isStartingAll = ref(false)
const isStoppingAll = ref(false)
const loadingStates = ref({})

// 配置对话框
const configDialogVisible = ref(false)
const configForm = reactive({
  name: '',
  display_name: '',
  interval: 60,
  timeout: 30,
  retry_count: 3
})

// 状态类型映射
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

const getStatusIcon = (status) => {
  const iconMap = {
    'running': 'CaretRight',
    'stopped': 'VideoPause',
    'error': 'Warning'
  }
  return iconMap[status] || 'QuestionFilled'
}

const getSourceIcon = (name) => {
  const iconMap = {
    'sina': 'Notebook',
    'eastmoney': 'TrendCharts', 
    'tencent': 'ChatDotRound',
    'netease': 'Headset',
    'ifeng': 'Promotion'
  }
  return iconMap[name] || 'Document'
}

// 获取进度条状态
const getProgressStatus = (rate) => {
  if (rate >= 90) return 'success'
  if (rate >= 70) return ''
  if (rate >= 50) return 'warning'
  return 'exception'
}

// 获取成功率样式
const getSuccessRateStyle = (rate) => {
  if (rate >= 90) return { color: '#67c23a' }
  if (rate >= 70) return { color: '#409eff' }
  if (rate >= 50) return { color: '#e6a23c' }
  return { color: '#f56c6c' }
}

// 时间格式化
const formatTime = (time) => {
  if (!time) return '-'
  return dayjs(time).format('MM-DD HH:mm')
}

// 启动单个爬虫
const startCrawler = async (name) => {
  const crawler = crawlerStore.crawlers.find(c => c.name === name)
  const displayName = crawler?.display_name || name
  
  try {
    await message.withFeedback(
      () => crawlerStore.startCrawler(name),
      {
        loadingText: `正在启动 ${displayName}...`,
        successTitle: '启动成功',
        successMessage: `${displayName} 已成功启动`,
        errorTitle: '启动失败'
      }
    )
  } catch (error) {
    console.error(`启动爬虫 ${name} 失败:`, error)
  }
}

// 停止单个爬虫
const stopCrawler = async (name) => {
  const crawler = crawlerStore.crawlers.find(c => c.name === name)
  const displayName = crawler?.display_name || name
  
  // 确认对话框
  const confirmed = await message.confirm(
    '停止爬虫',
    `确定要停止 ${displayName} 吗？`,
    {
      confirmButtonText: '停止',
      confirmButtonClass: 'el-button--warning'
    }
  )
  
  if (!confirmed) return
  
  try {
    await message.withFeedback(
      () => crawlerStore.stopCrawler(name),
      {
        loadingText: `正在停止 ${displayName}...`,
        successTitle: '停止成功',
        successMessage: `${displayName} 已成功停止`,
        errorTitle: '停止失败'
      }
    )
  } catch (error) {
    console.error(`停止爬虫 ${name} 失败:`, error)
  }
}

// 启动所有爬虫
const startAllCrawlers = async () => {
  const confirmed = await message.confirm(
    '批量启动确认',
    `确定要启动所有 ${crawlerStore.totalCrawlers} 个爬虫吗？`,
    {
      confirmButtonText: '启动全部',
      confirmButtonClass: 'el-button--success'
    }
  )
  
  if (!confirmed) return
  
  try {
    isStartingAll.value = true
    await message.withFeedback(
      async () => {
        await crawlerApi.startAllCrawlers()
        await crawlerStore.fetchCrawlerStatus()
      },
      {
        loadingText: '正在启动所有爬虫...',
        successTitle: '批量启动成功',
        successMessage: `已成功启动 ${crawlerStore.totalCrawlers} 个爬虫`,
        errorTitle: '批量启动失败',
        showLoading: false // 使用自定义加载状态
      }
    )
  } catch (error) {
    console.error('批量启动失败:', error)
  } finally {
    isStartingAll.value = false
  }
}

// 停止所有爬虫
const stopAllCrawlers = async () => {
  const runningCount = crawlerStore.activeCrawlers
  
  if (runningCount === 0) {
    message.warning('没有正在运行的爬虫')
    return
  }
  
  const confirmed = await message.confirmWithCountdown(
    '批量停止确认',
    `确定要停止所有 ${runningCount} 个正在运行的爬虫吗？`,
    '停止全部',
    3
  )
  
  if (!confirmed) return
  
  try {
    isStoppingAll.value = true
    await message.withFeedback(
      async () => {
        await crawlerApi.stopAllCrawlers()
        await crawlerStore.fetchCrawlerStatus()
      },
      {
        loadingText: '正在停止所有爬虫...',
        successTitle: '批量停止成功',
        successMessage: `已成功停止 ${runningCount} 个爬虫`,
        errorTitle: '批量停止失败',
        showLoading: false // 使用自定义加载状态
      }
    )
  } catch (error) {
    console.error('批量停止失败:', error)
  } finally {
    isStoppingAll.value = false
  }
}

// WebSocket连接状态
const wsConnected = ref(false)

// WebSocket事件处理
const handleWebSocketMessage = (data) => {
  switch (data.type) {
    case 'crawler_status_changed':
      // 爬虫状态变化时自动更新
      crawlerStore.fetchCrawlerStatus()
      break
    case 'crawler_started':
      message.success(`${data.crawler_name} 已启动`)
      crawlerStore.fetchCrawlerStatus()
      break
    case 'crawler_stopped':
      message.info(`${data.crawler_name} 已停止`)
      crawlerStore.fetchCrawlerStatus()
      break
    case 'crawler_error':
      message.error(`${data.crawler_name} 发生错误: ${data.error}`)
      crawlerStore.fetchCrawlerStatus()
      break
  }
}

// 刷新状态（增强版）
const refreshStatus = async () => {
  try {
    await message.withFeedback(
      () => crawlerStore.fetchCrawlerStatus(),
      {
        loadingText: '正在刷新状态...',
        successTitle: '状态已更新',
        errorTitle: '刷新失败',
        showSuccess: false // 静默成功
      }
    )
  } catch (error) {
    console.error('刷新状态失败:', error)
  }
}

// 自动刷新
const autoRefreshTimer = ref(null)
const autoRefreshInterval = ref(10000) // 10秒

const startAutoRefresh = () => {
  if (autoRefreshTimer.value) return
  
  autoRefreshTimer.value = setInterval(() => {
    // 如果WebSocket未连接才进行轮询
    if (!wsConnected.value) {
      crawlerStore.fetchCrawlerStatus()
    }
  }, autoRefreshInterval.value)
}

const stopAutoRefresh = () => {
  if (autoRefreshTimer.value) {
    clearInterval(autoRefreshTimer.value)
    autoRefreshTimer.value = null
  }
}

// 显示配置
const showConfig = (crawler) => {
  Object.assign(configForm, {
    name: crawler.name,
    display_name: crawler.display_name,
    interval: 60,
    timeout: 30,
    retry_count: 3
  })
  configDialogVisible.value = true
}

// 保存配置
const saveConfig = async () => {
  try {
    await message.withFeedback(
      () => {
        // 这里应该调用实际的配置保存API
        return new Promise(resolve => setTimeout(resolve, 1000))
      },
      {
        loadingText: '正在保存配置...',
        successTitle: '配置保存成功',
        errorTitle: '配置保存失败'
      }
    )
    configDialogVisible.value = false
  } catch (error) {
    console.error('保存配置失败:', error)
  }
}

// 生命周期钩子
onMounted(async () => {
  // 初始化数据
  await crawlerStore.fetchCrawlerStatus()
  
  // 启动WebSocket连接
  wsManager.connect()
  wsManager.on('connected', () => {
    wsConnected.value = true
    console.log('爬虫管理页面: WebSocket已连接')
    stopAutoRefresh() // 停止轮询，使用WebSocket
  })
  
  wsManager.on('disconnected', () => {
    wsConnected.value = false
    console.log('爬虫管理页面: WebSocket已断开，启动轮询')
    startAutoRefresh() // 启动轮询作为备用
  })
  
  wsManager.on('crawler_update', handleWebSocketMessage)
  
  // 如果WebSocket未连接，启动轮询
  if (!wsConnected.value) {
    startAutoRefresh()
  }
})

onUnmounted(() => {
  // 清理资源
  stopAutoRefresh()
  wsManager.off('crawler_update', handleWebSocketMessage)
  wsManager.disconnect()
})
</script>

<style scoped lang="scss">
.crawler-manager {
  .stat-card {
    margin-bottom: 20px;
    transition: all 0.3s ease;
    border-radius: 8px;
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
  }
  
  .flex {
    display: flex;
    align-items: center;
  }
  
  .flex-between {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .header-left {
    display: flex;
    align-items: center;
    
    .header-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }
  }
  
  .header-actions {
    display: flex;
    gap: 8px;
    
    .el-button {
      transition: all 0.2s ease;
      
      &:hover {
        transform: translateY(-1px);
      }
      
      &:active {
        transform: translateY(0);
      }
    }
  }
  
  .progress-container {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .enhanced-progress {
      flex: 1;
      
      :deep(.el-progress-bar__outer) {
        border-radius: 6px;
        background: var(--el-fill-color-light);
      }
      
      :deep(.el-progress-bar__inner) {
        border-radius: 6px;
        transition: all 0.3s ease;
        
        &.is-success {
          background: linear-gradient(90deg, #67c23a, #85ce61);
        }
        
        &.is-warning {
          background: linear-gradient(90deg, #e6a23c, #f0c061);
        }
        
        &.is-exception {
          background: linear-gradient(90deg, #f56c6c, #f89898);
        }
      }
    }
    
    .progress-text {
      font-size: 12px;
      font-weight: 600;
      min-width: 35px;
      text-align: right;
    }
  }
  
  .mr-5 {
    margin-right: 5px;
  }
  
  .mr-10 {
    margin-right: 10px;
  }
  
  .ml-10 {
    margin-left: 10px;
  }
  
  .mb-20 {
    margin-bottom: 20px;
  }
  
  // 表格行悬停效果
  :deep(.el-table tbody tr) {
    transition: background-color 0.2s ease;
    
    &:hover {
      background-color: var(--el-fill-color-lighter) !important;
    }
  }
  
  // 状态标签动画
  :deep(.el-tag) {
    transition: all 0.2s ease;
    
    &:hover {
      transform: scale(1.05);
    }
  }
  
  // 按钮组增强
  :deep(.el-button-group) {
    .el-button {
      border-radius: 4px;
      
      &:first-child {
        border-top-right-radius: 0;
        border-bottom-right-radius: 0;
      }
      
      &:last-child {
        border-top-left-radius: 0;
        border-bottom-left-radius: 0;
      }
      
      &:not(:first-child):not(:last-child) {
        border-radius: 0;
      }
    }
  }
  
  // 加载状态动画
  .loading-row {
    opacity: 0.6;
    pointer-events: none;
  }
  
  // 响应式设计
  @media (max-width: 768px) {
    .header-left,
    .header-actions {
      flex-direction: column;
      gap: 8px;
    }
    
    .flex-between {
      flex-direction: column;
      align-items: stretch;
      gap: 12px;
    }
    
    .progress-container {
      .progress-text {
        min-width: 30px;
      }
    }
    
    :deep(.el-table) {
      font-size: 12px;
    }
    
    :deep(.el-button) {
      padding: 8px 12px;
      font-size: 12px;
    }
  }
  
  @media (max-width: 480px) {
    .header-actions {
      .el-button {
        width: 100%;
        justify-content: center;
      }
    }
    
    :deep(.el-table__body-wrapper) {
      overflow-x: auto;
    }
  }
}

// 动画关键帧
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// 运行状态指示器动画
:deep(.el-tag.el-tag--success) {
  .el-icon {
    animation: pulse 2s infinite;
  }
}

// 页面进入动画
.crawler-manager {
  animation: slideIn 0.4s ease-out;
}
</style> 