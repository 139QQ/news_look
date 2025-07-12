<template>
  <div class="log-viewer">
    <el-card class="log-card" shadow="hover">
      <!-- 日志控制台头部 -->
      <template #header>
        <div class="log-header">
          <div class="log-title">
            <el-icon><Document /></el-icon>
            系统日志
            <el-badge 
              :value="newLogCount" 
              :max="99" 
              :hidden="newLogCount === 0"
              class="ml-10"
            />
          </div>
          
          <div class="log-controls">
            <!-- 日志级别筛选 -->
            <el-select
              v-model="selectedLevels"
              multiple
              placeholder="日志级别"
              size="small"
              style="width: 120px"
              @change="handleLevelFilter"
            >
              <el-option
                v-for="level in logLevels"
                :key="level.value"
                :label="level.label"
                :value="level.value"
              >
                <span class="level-option">
                  <el-tag 
                    :type="level.type" 
                    size="small"
                    style="margin-right: 8px;"
                  >
                    {{ level.label }}
                  </el-tag>
                </span>
              </el-option>
            </el-select>
            
            <!-- 搜索框 -->
            <el-input
              v-model="searchKeyword"
              placeholder="搜索日志内容..."
              size="small"
              :prefix-icon="Search"
              clearable
              style="width: 200px"
              @input="handleSearch"
            />
            
            <!-- 控制按钮 -->
            <el-button-group size="small">
              <el-button 
                :type="autoScroll ? 'primary' : ''"
                @click="toggleAutoScroll"
                :icon="autoScroll ? 'VideoPause' : 'VideoPlay'"
              >
                {{ autoScroll ? '暂停' : '跟随' }}
              </el-button>
              
              <el-button 
                @click="clearLogs"
                icon="Delete"
              >
                清空
              </el-button>
              
              <el-button 
                @click="downloadLogs"
                icon="Download"
              >
                下载
              </el-button>
              
              <el-button 
                @click="refreshLogs"
                :loading="loading"
                icon="Refresh"
              >
                刷新
              </el-button>
            </el-button-group>
          </div>
        </div>
      </template>
      
      <!-- 日志统计信息 -->
      <div class="log-stats">
        <div class="stat-item">
          <span class="stat-label">总计:</span>
          <span class="stat-value">{{ filteredLogs.length }}</span>
        </div>
        <div class="stat-item" v-for="level in logLevels" :key="level.value">
          <span class="stat-label">{{ level.label }}:</span>
          <span class="stat-value" :style="{ color: level.color }">
            {{ getLogCountByLevel(level.value) }}
          </span>
        </div>
        <div class="stat-item">
          <span class="stat-label">时间范围:</span>
          <span class="stat-value">{{ timeRange }}</span>
        </div>
      </div>
      
      <!-- 日志内容区域 -->
      <div 
        ref="logContainer"
        class="log-content"
        :class="{ 'auto-scroll': autoScroll }"
        @scroll="handleScroll"
      >
        <div class="log-virtual-list">
          <div
            v-for="(log, index) in visibleLogs"
            :key="index"
            class="log-entry"
            :class="`log-${log.level.toLowerCase()}`"
          >
            <!-- 日志时间戳 -->
            <div class="log-timestamp">
              {{ formatTime(log.timestamp) }}
            </div>
            
            <!-- 日志级别标签 -->
            <div class="log-level">
              <el-tag 
                :type="getLevelType(log.level)"
                size="small"
                class="level-tag"
              >
                {{ log.level }}
              </el-tag>
            </div>
            
            <!-- 日志来源 -->
            <div class="log-source" v-if="log.source">
              <el-tag 
                type="info" 
                size="small"
                effect="plain"
                class="source-tag"
              >
                {{ log.source }}
              </el-tag>
            </div>
            
            <!-- 日志消息内容 -->
            <div class="log-message">
              <span 
                v-html="highlightKeyword(log.message)"
                class="message-text"
              ></span>
              
              <!-- 展开/收起长消息 -->
              <el-button
                v-if="log.message.length > 200"
                type="text"
                size="small"
                @click="toggleLogExpand(index)"
                class="expand-btn"
              >
                {{ log.expanded ? '收起' : '展开' }}
              </el-button>
            </div>
            
            <!-- 错误堆栈信息 -->
            <div v-if="log.stack && log.expanded" class="log-stack">
              <pre class="stack-trace">{{ log.stack }}</pre>
            </div>
            
            <!-- 日志操作 -->
            <div class="log-actions">
              <el-button
                type="text"
                size="small"
                @click="copyLogEntry(log)"
                icon="DocumentCopy"
                title="复制日志"
              />
              
              <el-button
                type="text"
                size="small"
                @click="filterBySimilar(log)"
                icon="Filter"
                title="筛选相似日志"
              />
            </div>
          </div>
          
          <!-- 加载更多指示器 -->
          <div v-if="hasMore" class="load-more" @click="loadMore">
            <el-button type="text" :loading="loadingMore">
              加载更多日志
            </el-button>
          </div>
          
          <!-- 空状态 -->
          <div v-if="filteredLogs.length === 0" class="empty-logs">
            <el-empty 
              description="暂无日志数据" 
              :image-size="100"
            >
              <el-button type="primary" @click="refreshLogs">
                刷新日志
              </el-button>
            </el-empty>
          </div>
        </div>
      </div>
      
      <!-- 底部状态栏 -->
      <div class="log-footer">
        <div class="footer-left">
          <span class="connection-status">
            <el-icon>
              <Connection v-if="connected" />
              <Warning v-else />
            </el-icon>
            {{ connected ? '实时连接' : '离线模式' }}
          </span>
        </div>
        
        <div class="footer-right">
          <span class="update-time">
            最后更新: {{ lastUpdateTime }}
          </span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { 
  Document, 
  Search, 
  VideoPlay, 
  VideoPause, 
  Delete, 
  Download, 
  Refresh,
  DocumentCopy,
  Filter,
  Connection,
  Warning
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import wsManager from '@/utils/websocket'

// Props
const props = defineProps({
  // 日志来源
  source: {
    type: String,
    default: 'system'
  },
  // 最大日志条数
  maxLogs: {
    type: Number,
    default: 1000
  },
  // 是否启用实时更新
  realtime: {
    type: Boolean,
    default: true
  }
})

// 响应式数据
const logs = ref([])
const filteredLogs = ref([])
const visibleLogs = ref([])
const selectedLevels = ref(['INFO', 'WARN', 'ERROR'])
const searchKeyword = ref('')
const autoScroll = ref(true)
const loading = ref(false)
const loadingMore = ref(false)
const connected = ref(false)
const newLogCount = ref(0)
const hasMore = ref(true)
const currentPage = ref(1)
const pageSize = ref(100)

// DOM引用
const logContainer = ref(null)

// 日志级别配置
const logLevels = [
  { value: 'DEBUG', label: 'DEBUG', type: 'info', color: '#909399' },
  { value: 'INFO', label: 'INFO', type: 'success', color: '#67c23a' },
  { value: 'WARN', label: 'WARN', type: 'warning', color: '#e6a23c' },
  { value: 'ERROR', label: 'ERROR', type: 'danger', color: '#f56c6c' },
  { value: 'FATAL', label: 'FATAL', type: 'danger', color: '#f56c6c' }
]

// 计算属性
const timeRange = computed(() => {
  if (filteredLogs.value.length === 0) return '-'
  
  const first = filteredLogs.value[0]
  const last = filteredLogs.value[filteredLogs.value.length - 1]
  
  return `${formatTime(first.timestamp)} ~ ${formatTime(last.timestamp)}`
})

const lastUpdateTime = computed(() => {
  return dayjs().format('HH:mm:ss')
})

// 方法
const formatTime = (timestamp) => {
  return dayjs(timestamp).format('MM-DD HH:mm:ss.SSS')
}

const getLevelType = (level) => {
  const levelConfig = logLevels.find(l => l.value === level)
  return levelConfig?.type || 'info'
}

const getLogCountByLevel = (level) => {
  return filteredLogs.value.filter(log => log.level === level).length
}

const highlightKeyword = (text) => {
  if (!searchKeyword.value.trim()) return text
  
  const keyword = searchKeyword.value.trim()
  const regex = new RegExp(`(${keyword})`, 'gi')
  return text.replace(regex, '<mark class="highlight">$1</mark>')
}

const handleLevelFilter = () => {
  applyFilters()
}

const handleSearch = debounce(() => {
  applyFilters()
}, 300)

const applyFilters = () => {
  let filtered = logs.value
  
  // 级别筛选
  if (selectedLevels.value.length > 0) {
    filtered = filtered.filter(log => selectedLevels.value.includes(log.level))
  }
  
  // 关键词搜索
  if (searchKeyword.value.trim()) {
    const keyword = searchKeyword.value.trim().toLowerCase()
    filtered = filtered.filter(log => 
      log.message.toLowerCase().includes(keyword) ||
      (log.source && log.source.toLowerCase().includes(keyword))
    )
  }
  
  filteredLogs.value = filtered
  updateVisibleLogs()
}

const updateVisibleLogs = () => {
  const startIndex = 0
  const endIndex = currentPage.value * pageSize.value
  visibleLogs.value = filteredLogs.value.slice(startIndex, endIndex)
}

const toggleAutoScroll = () => {
  autoScroll.value = !autoScroll.value
  if (autoScroll.value) {
    scrollToBottom()
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

const handleScroll = () => {
  const container = logContainer.value
  if (!container) return
  
  const isAtBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 10
  
  // 如果用户手动滚动到非底部，停止自动滚动
  if (!isAtBottom && autoScroll.value) {
    autoScroll.value = false
  }
  
  // 重置新日志计数
  if (isAtBottom) {
    newLogCount.value = 0
  }
}

const clearLogs = async () => {
  try {
    await ElMessageBox.confirm('确定要清空所有日志吗？', '清空确认', {
      type: 'warning'
    })
    
    logs.value = []
    filteredLogs.value = []
    visibleLogs.value = []
    newLogCount.value = 0
    
    ElMessage.success('日志已清空')
  } catch {
    // 用户取消
  }
}

const downloadLogs = () => {
  const logText = filteredLogs.value.map(log => 
    `[${formatTime(log.timestamp)}] [${log.level}] ${log.source ? `[${log.source}] ` : ''}${log.message}${log.stack ? '\n' + log.stack : ''}`
  ).join('\n')
  
  const blob = new Blob([logText], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `logs_${dayjs().format('YYYY-MM-DD_HH-mm-ss')}.txt`
  a.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('日志文件已下载')
}

const refreshLogs = async () => {
  loading.value = true
  try {
    // 这里应该调用实际的API获取日志
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 模拟日志数据
    const mockLogs = generateMockLogs(50)
    logs.value = [...logs.value, ...mockLogs]
    
    applyFilters()
    ElMessage.success('日志已刷新')
  } catch (error) {
    ElMessage.error('刷新日志失败')
  } finally {
    loading.value = false
  }
}

const loadMore = async () => {
  if (loadingMore.value) return
  
  loadingMore.value = true
  try {
    currentPage.value++
    updateVisibleLogs()
    
    if (visibleLogs.value.length >= filteredLogs.value.length) {
      hasMore.value = false
    }
  } finally {
    loadingMore.value = false
  }
}

const toggleLogExpand = (index) => {
  const log = visibleLogs.value[index]
  log.expanded = !log.expanded
}

const copyLogEntry = (log) => {
  const text = `[${formatTime(log.timestamp)}] [${log.level}] ${log.source ? `[${log.source}] ` : ''}${log.message}`
  
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('日志已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

const filterBySimilar = (log) => {
  // 提取日志消息的关键词作为搜索条件
  const words = log.message.split(' ').filter(word => word.length > 3)
  if (words.length > 0) {
    searchKeyword.value = words[0]
    handleSearch()
  }
}

// 生成模拟日志数据
const generateMockLogs = (count) => {
  const mockLogs = []
  const levels = ['DEBUG', 'INFO', 'WARN', 'ERROR']
  const sources = ['crawler', 'web', 'database', 'scheduler']
  const messages = [
    '爬虫任务开始执行',
    '数据库连接成功',
    '网络请求超时',
    '用户登录成功',
    '配置文件加载完成',
    '发现重复数据',
    '内存使用率过高',
    '任务执行失败，准备重试'
  ]
  
  for (let i = 0; i < count; i++) {
    const level = levels[Math.floor(Math.random() * levels.length)]
    const source = sources[Math.floor(Math.random() * sources.length)]
    const message = messages[Math.floor(Math.random() * messages.length)]
    
    mockLogs.push({
      timestamp: new Date(Date.now() - Math.random() * 86400000),
      level,
      source,
      message: `${message} #${Math.floor(Math.random() * 1000)}`,
      stack: level === 'ERROR' ? 'Error stack trace here...' : null,
      expanded: false
    })
  }
  
  return mockLogs.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
}

// WebSocket事件处理
const handleNewLog = (data) => {
  const newLog = {
    timestamp: new Date(),
    level: data.level || 'INFO',
    source: data.source || props.source,
    message: data.message,
    stack: data.stack || null,
    expanded: false
  }
  
  logs.value.push(newLog)
  
  // 限制日志数量
  if (logs.value.length > props.maxLogs) {
    logs.value = logs.value.slice(-props.maxLogs)
  }
  
  applyFilters()
  
  // 增加新日志计数
  if (!autoScroll.value) {
    newLogCount.value++
  }
  
  // 自动滚动到底部
  if (autoScroll.value) {
    scrollToBottom()
  }
}

// 防抖函数
function debounce(func, wait) {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

// 生命周期
onMounted(async () => {
  // 初始化日志数据
  const mockLogs = generateMockLogs(100)
  logs.value = mockLogs
  applyFilters()
  
  // 连接WebSocket
  if (props.realtime) {
    wsManager.connect()
    wsManager.on('connected', () => {
      connected.value = true
    })
    
    wsManager.on('disconnected', () => {
      connected.value = false
    })
    
    wsManager.on('log', handleNewLog)
  }
  
  // 滚动到底部
  await nextTick()
  scrollToBottom()
})

onUnmounted(() => {
  if (props.realtime) {
    wsManager.off('log', handleNewLog)
  }
})

// 监听器
watch(
  () => [logs.value.length, selectedLevels.value, searchKeyword.value],
  () => {
    applyFilters()
  }
)
</script>

<style scoped lang="scss">
.log-viewer {
  .log-card {
    border-radius: 8px;
    height: 600px;
    display: flex;
    flex-direction: column;
    
    :deep(.el-card__body) {
      flex: 1;
      display: flex;
      flex-direction: column;
      padding: 0;
    }
  }
  
  .log-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .log-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }
    
    .log-controls {
      display: flex;
      align-items: center;
      gap: 12px;
      
      .level-option {
        display: flex;
        align-items: center;
      }
    }
  }
  
  .log-stats {
    display: flex;
    gap: 20px;
    padding: 12px 20px;
    background: var(--el-fill-color-extra-light);
    border-bottom: 1px solid var(--el-border-color-light);
    
    .stat-item {
      display: flex;
      gap: 4px;
      font-size: 12px;
      
      .stat-label {
        color: var(--el-text-color-regular);
      }
      
      .stat-value {
        font-weight: 600;
        color: var(--el-text-color-primary);
      }
    }
  }
  
  .log-content {
    flex: 1;
    overflow-y: auto;
    background: #1e1e1e;
    color: #d4d4d4;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.4;
    
    &.auto-scroll {
      scroll-behavior: smooth;
    }
    
    .log-virtual-list {
      padding: 8px;
    }
    
    .log-entry {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      padding: 4px 8px;
      border-radius: 4px;
      margin-bottom: 2px;
      transition: background-color 0.2s ease;
      
      &:hover {
        background: rgba(255, 255, 255, 0.05);
      }
      
      &.log-error {
        background: rgba(244, 67, 54, 0.1);
        border-left: 3px solid #f44336;
      }
      
      &.log-warn {
        background: rgba(255, 152, 0, 0.1);
        border-left: 3px solid #ff9800;
      }
      
      &.log-info {
        background: rgba(76, 175, 80, 0.1);
        border-left: 3px solid #4caf50;
      }
      
      &.log-debug {
        background: rgba(158, 158, 158, 0.1);
        border-left: 3px solid #9e9e9e;
      }
    }
    
    .log-timestamp {
      color: #888;
      white-space: nowrap;
      min-width: 120px;
      font-size: 11px;
    }
    
    .log-level {
      min-width: 60px;
      
      .level-tag {
        font-size: 10px;
        padding: 2px 6px;
      }
    }
    
    .log-source {
      min-width: 80px;
      
      .source-tag {
        font-size: 10px;
        padding: 2px 6px;
      }
    }
    
    .log-message {
      flex: 1;
      word-break: break-word;
      
      .message-text {
        :deep(.highlight) {
          background: #ffeb3b;
          color: #000;
          padding: 1px 2px;
          border-radius: 2px;
        }
      }
      
      .expand-btn {
        margin-left: 8px;
        font-size: 10px;
      }
    }
    
    .log-stack {
      margin-top: 4px;
      padding: 8px;
      background: rgba(0, 0, 0, 0.3);
      border-radius: 4px;
      
      .stack-trace {
        margin: 0;
        font-size: 11px;
        color: #ff6b6b;
        white-space: pre-wrap;
      }
    }
    
    .log-actions {
      display: flex;
      opacity: 0;
      transition: opacity 0.2s ease;
      
      .log-entry:hover & {
        opacity: 1;
      }
      
      .el-button {
        font-size: 10px;
        padding: 2px 4px;
        color: #888;
        
        &:hover {
          color: #fff;
        }
      }
    }
    
    .load-more {
      text-align: center;
      padding: 20px;
      
      .el-button {
        color: #888;
      }
    }
    
    .empty-logs {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 200px;
      color: #888;
    }
  }
  
  .log-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 20px;
    background: var(--el-fill-color-light);
    border-top: 1px solid var(--el-border-color-light);
    font-size: 12px;
    
    .connection-status {
      display: flex;
      align-items: center;
      gap: 4px;
      color: var(--el-text-color-regular);
    }
    
    .update-time {
      color: var(--el-text-color-placeholder);
    }
  }
  
  .ml-10 {
    margin-left: 10px;
  }
  
  // 响应式设计
  @media (max-width: 768px) {
    .log-header {
      flex-direction: column;
      gap: 12px;
      align-items: stretch;
    }
    
    .log-controls {
      flex-wrap: wrap;
      gap: 8px;
    }
    
    .log-stats {
      flex-wrap: wrap;
      gap: 12px;
    }
    
    .log-entry {
      flex-direction: column;
      gap: 4px;
      
      .log-timestamp,
      .log-level,
      .log-source {
        min-width: auto;
      }
    }
  }
}
</style> 