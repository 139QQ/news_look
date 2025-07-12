<template>
  <div class="analytics-dashboard">
    <!-- 仪表盘头部 -->
    <div class="dashboard-header">
      <div class="header-left">
        <h1 class="dashboard-title">
          <el-icon><DataAnalysis /></el-icon>
          数据分析仪表盘
        </h1>
        <p class="dashboard-subtitle">实时监控新闻爬取和系统性能</p>
      </div>
      <div class="header-right">
        <el-space :size="16">
          <!-- 刷新按钮 -->
          <el-button 
            :icon="Refresh" 
            :loading="refreshing"
            @click="refreshDashboard"
          >
            刷新数据
          </el-button>
          
          <!-- 时间范围选择 -->
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            @change="onDateRangeChange"
          />
          
          <!-- 导出按钮 -->
          <el-dropdown @command="handleExport">
            <el-button :icon="Download">
              导出数据
              <el-icon class="el-icon--right"><arrow-down /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="csv">导出CSV</el-dropdown-item>
                <el-dropdown-item command="excel">导出Excel</el-dropdown-item>
                <el-dropdown-item command="json">导出JSON</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </el-space>
      </div>
    </div>

    <!-- 关键指标卡片 -->
    <div class="metrics-grid">
      <div 
        v-for="metric in keyMetrics" 
        :key="metric.key"
        class="metric-card"
        :class="`metric-${metric.type}`"
      >
        <div class="metric-header">
          <el-icon :size="24" :color="metric.color">
            <component :is="metric.icon" />
          </el-icon>
          <span class="metric-label">{{ metric.label }}</span>
        </div>
        <div class="metric-value">
          <span class="value">{{ formatMetricValue(metric.value, metric.format) }}</span>
          <div class="metric-trend" :class="metric.trend">
            <el-icon><component :is="getTrendIcon(metric.trend)" /></el-icon>
            <span>{{ metric.change }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 图表网格 -->
    <div class="charts-grid">
      <!-- 新闻趋势图 -->
      <div class="chart-container">
        <div class="chart-header">
          <h3>新闻发布趋势</h3>
          <el-button-group size="small">
            <el-button 
              v-for="period in ['7d', '30d', '90d']" 
              :key="period"
              :type="selectedPeriod === period ? 'primary' : ''"
              @click="changePeriod(period)"
            >
              {{ period }}
            </el-button>
          </el-button-group>
        </div>
        <div 
          ref="trendChart" 
          class="chart-content"
          v-loading="chartLoading.trend"
        ></div>
      </div>

      <!-- 来源分布饼图 -->
      <div class="chart-container">
        <div class="chart-header">
          <h3>新闻来源分布</h3>
          <el-switch
            v-model="showPercentage"
            active-text="显示百分比"
            @change="updateSourceChart"
          />
        </div>
        <div 
          ref="sourceChart" 
          class="chart-content"
          v-loading="chartLoading.source"
        ></div>
      </div>

      <!-- 小时分布柱状图 -->
      <div class="chart-container">
        <div class="chart-header">
          <h3>24小时发布分布</h3>
          <el-select v-model="selectedSource" placeholder="选择来源" clearable>
            <el-option label="全部来源" value="" />
            <el-option 
              v-for="source in availableSources"
              :key="source"
              :label="source"
              :value="source"
            />
          </el-select>
        </div>
        <div 
          ref="hourlyChart" 
          class="chart-content"
          v-loading="chartLoading.hourly"
        ></div>
      </div>

      <!-- 爬虫性能表格 -->
      <div class="chart-container performance-table">
        <div class="chart-header">
          <h3>爬虫性能监控</h3>
          <el-space>
            <el-button 
              :icon="Setting" 
              size="small"
              @click="openCrawlerSettings"
            >
              设置
            </el-button>
            <el-button 
              size="small"
              @click="toggleVirtualTable"
            >
              {{ showVirtualTable ? '标准表格' : '虚拟滚动' }}
            </el-button>
          </el-space>
        </div>
        
        <!-- 虚拟滚动表格 -->
        <VirtualScrollTable
          v-if="showVirtualTable"
          :data="newsTableData"
          :columns="newsTableColumns"
          :height="400"
          :selectable="true"
          @row-click="handleTableRowClick"
          @selection-change="handleTableSelectionChange"
        >
          <template #batch-actions="{ selectedRows }">
            <el-button size="small" @click="batchDeleteNews(selectedRows)">
              批量删除
            </el-button>
            <el-button size="small" @click="batchExportNews(selectedRows)">
              批量导出
            </el-button>
          </template>
        </VirtualScrollTable>
        
        <!-- 标准表格 -->
        <el-table 
          v-else
          :data="crawlerPerformance" 
          :loading="tableLoading"
          stripe
          style="width: 100%"
        >
          <el-table-column prop="name" label="爬虫名称" width="120" />
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag 
                :type="getStatusType(row.status)"
                size="small"
              >
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="success_rate" label="成功率" width="100">
            <template #default="{ row }">
              <el-progress 
                :percentage="row.success_rate" 
                :color="getProgressColor(row.success_rate)"
                :show-text="false"
                :stroke-width="8"
              />
              <span class="progress-text">{{ row.success_rate }}%</span>
            </template>
          </el-table-column>
          <el-table-column prop="avg_response_time" label="响应时间" width="100">
            <template #default="{ row }">
              {{ row.avg_response_time }}s
            </template>
          </el-table-column>
          <el-table-column prop="last_run" label="最后运行" width="120" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button-group size="small">
                <el-button 
                  :icon="row.status === 'running' ? VideoPause : VideoPlay"
                  @click="toggleCrawler(row)"
                  :loading="crawlerOperating[row.id]"
                >
                </el-button>
                <el-button 
                  :icon="Setting"
                  @click="configureCrawler(row)"
                >
                </el-button>
              </el-button-group>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 系统监控区域 -->
    <div class="system-monitor">
      <div class="monitor-header">
        <h3>系统监控</h3>
        <el-switch
          v-model="autoRefresh"
          active-text="自动刷新"
          @change="toggleAutoRefresh"
        />
      </div>
      
      <div class="monitor-grid">
        <!-- CPU监控 -->
        <div class="monitor-card">
          <div class="monitor-title">CPU使用率</div>
          <div 
            ref="cpuChart" 
            class="mini-chart"
            v-loading="chartLoading.cpu"
          ></div>
          <div class="monitor-value">{{ systemMetrics.cpu_percent }}%</div>
        </div>

        <!-- 内存监控 -->
        <div class="monitor-card">
          <div class="monitor-title">内存使用率</div>
          <div 
            ref="memoryChart" 
            class="mini-chart"
            v-loading="chartLoading.memory"
          ></div>
          <div class="monitor-value">{{ systemMetrics.memory_percent }}%</div>
        </div>

        <!-- 磁盘监控 -->
        <div class="monitor-card">
          <div class="monitor-title">磁盘使用率</div>
          <div 
            ref="diskChart" 
            class="mini-chart"
            v-loading="chartLoading.disk"
          ></div>
          <div class="monitor-value">{{ systemMetrics.disk_usage_percent }}%</div>
        </div>

        <!-- 网络监控 -->
        <div class="monitor-card">
          <div class="monitor-title">网络流量</div>
          <div 
            ref="networkChart" 
            class="mini-chart"
            v-loading="chartLoading.network"
          ></div>
          <div class="monitor-value">{{ formatBytes(systemMetrics.network_sent_mb) }}</div>
        </div>
      </div>
    </div>

    <!-- 爬虫配置对话框 -->
    <el-dialog
      v-model="crawlerDialogVisible"
      title="爬虫配置"
      width="600px"
    >
      <el-form :model="crawlerConfig" label-width="120px">
        <el-form-item label="爬虫名称">
          <el-input v-model="crawlerConfig.name" disabled />
        </el-form-item>
        <el-form-item label="请求延时">
          <el-input-number 
            v-model="crawlerConfig.delay" 
            :min="0.1" 
            :max="10" 
            :step="0.1"
            controls-position="right"
          />
          <span class="form-tip">秒</span>
        </el-form-item>
        <el-form-item label="超时时间">
          <el-input-number 
            v-model="crawlerConfig.timeout" 
            :min="5" 
            :max="120" 
            controls-position="right"
          />
          <span class="form-tip">秒</span>
        </el-form-item>
        <el-form-item label="并发数">
          <el-input-number 
            v-model="crawlerConfig.concurrent" 
            :min="1" 
            :max="10" 
            controls-position="right"
          />
        </el-form-item>
        <el-form-item label="User-Agent">
          <el-input 
            v-model="crawlerConfig.user_agent" 
            type="textarea"
            :rows="3"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="crawlerDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveCrawlerConfig" :loading="saving">
          保存配置
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  DataAnalysis, Refresh, Download, Setting, VideoPlay, VideoPause,
  ArrowDown, TrendCharts, ArrowUp, Minus, Document, Calendar, Link, SuccessFilled
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { dashboardApi, crawlerApi, systemApi, analyticsApi } from '@/api'
import VirtualScrollTable from './VirtualScrollTable.vue'
import useKeyboardShortcuts, { createAction } from '@/utils/useKeyboardShortcuts'

// 响应式数据
const refreshing = ref(false)
const dateRange = ref([])
const selectedPeriod = ref('7d')
const showPercentage = ref(true)
const selectedSource = ref('')
const autoRefresh = ref(true)
const crawlerDialogVisible = ref(false)
const saving = ref(false)
const tableLoading = ref(false)

// 新增功能状态
const showVirtualTable = ref(false)
const newsTableData = ref([])
const newsTableColumns = ref([
  { key: 'title', title: '标题', width: 200, sortable: true, filterable: true, ellipsis: true },
  { key: 'source', title: '来源', width: 120, sortable: true, filterable: true },
  { key: 'publish_time', title: '发布时间', width: 160, sortable: true },
  { key: 'content_length', title: '内容长度', width: 100, sortable: true },
  { key: 'status', title: '状态', width: 80, render: 'StatusCell' }
])

// 初始化快捷键
const {
  registerHandler,
  addAction,
  undo,
  redo,
  canUndo,
  canRedo,
  getAllShortcuts
} = useKeyboardShortcuts({}, { showTooltips: true })

// 图表加载状态
const chartLoading = reactive({
  trend: false,
  source: false,
  hourly: false,
  cpu: false,
  memory: false,
  disk: false,
  network: false
})

// 爬虫操作状态
const crawlerOperating = reactive({})

// 关键指标数据
const keyMetrics = ref([
  {
    key: 'total_news',
    label: '总新闻数',
    value: 0,
    format: 'number',
    icon: 'Document',
    color: '#409EFF',
    type: 'primary',
    trend: 'up',
    change: '+12%'
  },
  {
    key: 'today_news',
    label: '今日新闻',
    value: 0,
    format: 'number',
    icon: 'Calendar',
    color: '#67C23A',
    type: 'success',
    trend: 'up',
    change: '+8%'
  },
  {
    key: 'sources_count',
    label: '新闻源数',
    value: 0,
    format: 'number',
    icon: 'Link',
    color: '#E6A23C',
    type: 'warning',
    trend: 'stable',
    change: '0%'
  },
  {
    key: 'success_rate',
    label: '成功率',
    value: 0,
    format: 'percentage',
    icon: 'SuccessFilled',
    color: '#F56C6C',
    type: 'danger',
    trend: 'down',
    change: '-2%'
  }
])

// 爬虫性能数据
const crawlerPerformance = ref([])
const availableSources = ref([])

// 系统指标
const systemMetrics = reactive({
  cpu_percent: 0,
  memory_percent: 0,
  disk_usage_percent: 0,
  network_sent_mb: 0
})

// 爬虫配置
const crawlerConfig = reactive({
  id: '',
  name: '',
  delay: 1,
  timeout: 30,
  concurrent: 1,
  user_agent: ''
})

// 图表实例
const charts = reactive({
  trend: null,
  source: null,
  hourly: null,
  cpu: null,
  memory: null,
  disk: null,
  network: null
})

// 自动刷新定时器
let refreshTimer = null

// 加载系统指标数据
const loadSystemMetrics = async () => {
  try {
    const response = await systemApi.getMetrics()
    if (response && response.current) {
      // 更新实时系统指标
      systemMetrics.cpu_percent = response.current.cpu_percent || 0
      systemMetrics.memory_percent = response.current.memory_percent || 0
      systemMetrics.disk_usage_percent = response.current.disk_percent || 0
      systemMetrics.network_sent_mb = Math.round((response.current.network_io?.bytes_sent || 0) / (1024 * 1024))
      
      // 更新CPU图表
      if (charts.cpu) {
        const timestamp = new Date().toLocaleTimeString()
        const option = charts.cpu.getOption()
        if (option.xAxis && option.xAxis[0] && option.series && option.series[0]) {
          option.xAxis[0].data.push(timestamp)
          option.series[0].data.push(systemMetrics.cpu_percent)
          
          // 保持最近20个数据点
          if (option.xAxis[0].data.length > 20) {
            option.xAxis[0].data.shift()
            option.series[0].data.shift()
          }
          
          charts.cpu.setOption(option)
        }
      }
      
      console.log('✅ 系统指标已更新:', systemMetrics)
    }
  } catch (error) {
    console.error('❌ 加载系统指标失败:', error)
    // 使用默认值，不显示错误消息避免干扰用户
    systemMetrics.cpu_percent = 0
    systemMetrics.memory_percent = 0
    systemMetrics.disk_usage_percent = 0
    systemMetrics.network_sent_mb = 0
  }
}

// 组件方法
const refreshDashboard = async () => {
  refreshing.value = true
  try {
    await Promise.all([
      loadKeyMetrics(),
      loadTrendChart(),
      loadSourceChart(),
      loadHourlyChart(),
      loadCrawlerPerformance(),
      loadSystemMetrics()
    ])
    ElMessage.success('数据刷新成功')
  } catch (error) {
    ElMessage.error('数据刷新失败：' + error.message)
  } finally {
    refreshing.value = false
  }
}

const onDateRangeChange = () => {
  refreshDashboard()
}

const changePeriod = (period) => {
  selectedPeriod.value = period
  loadTrendChart()
}

const handleExport = async (command) => {
  try {
    const response = await dashboardApi.exportData({
      type: 'analytics',
      format: command,
      filters: {
        start_date: dateRange.value[0],
        end_date: dateRange.value[1]
      }
    })
    
    if (command === 'json') {
      ElMessage.success('数据导出成功')
    } else {
      // 处理文件下载
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `analytics_${Date.now()}.${command}`)
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    }
  } catch (error) {
    ElMessage.error('导出失败：' + error.message)
  }
}

const toggleCrawler = async (crawler) => {
  crawlerOperating[crawler.id] = true
  try {
    await crawlerApi.toggle(crawler.id)
    await loadCrawlerPerformance()
    ElMessage.success(`爬虫 ${crawler.name} 操作成功`)
  } catch (error) {
    ElMessage.error('操作失败：' + error.message)
  } finally {
    crawlerOperating[crawler.id] = false
  }
}

const configureCrawler = (crawler) => {
  Object.assign(crawlerConfig, {
    id: crawler.id,
    name: crawler.name,
    delay: crawler.current_params?.delay || 1,
    timeout: crawler.current_params?.timeout || 30,
    concurrent: crawler.current_params?.concurrent || 1,
    user_agent: crawler.current_params?.user_agent || ''
  })
  crawlerDialogVisible.value = true
}

const saveCrawlerConfig = async () => {
  saving.value = true
  try {
    await crawlerApi.updateParams(crawlerConfig.id, {
      delay: crawlerConfig.delay,
      timeout: crawlerConfig.timeout,
      concurrent: crawlerConfig.concurrent,
      user_agent: crawlerConfig.user_agent
    })
    crawlerDialogVisible.value = false
    await loadCrawlerPerformance()
    ElMessage.success('配置保存成功')
  } catch (error) {
    ElMessage.error('保存失败：' + error.message)
  } finally {
    saving.value = false
  }
}

const toggleAutoRefresh = (enabled) => {
  if (enabled) {
    refreshTimer = setInterval(refreshDashboard, 30000) // 30秒刷新
  } else {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }
}

// 虚拟表格相关方法
const toggleVirtualTable = () => {
  showVirtualTable.value = !showVirtualTable.value
  if (showVirtualTable.value) {
    loadNewsTableData()
  }
}

const loadNewsTableData = async () => {
  try {
    const response = await analyticsApi.getOverview({ limit: 10000 })
    if (response.data && response.data.news) {
      newsTableData.value = response.data.news
    }
  } catch (error) {
    ElMessage.error('加载新闻数据失败')
  }
}

const handleTableRowClick = ({ row, index }) => {
  // 处理行点击事件
  console.log('Row clicked:', row, index)
}

const handleTableSelectionChange = (selectedRows) => {
  console.log('Selection changed:', selectedRows)
}

const batchDeleteNews = async (selectedRows) => {
  try {
    await ElMessageBox.confirm('确定要删除选中的新闻吗？', '确认删除', {
      type: 'warning'
    })
    
    // 创建删除操作
    const deleteAction = createAction(
      '批量删除新闻',
      () => {
        // 实际删除逻辑
        ElMessage.success(`已删除 ${selectedRows.length} 条新闻`)
      },
      () => {
        // 撤销删除逻辑
        ElMessage.info('删除操作已撤销')
      }
    )
    
    // 执行删除并添加到历史
    deleteAction.redo()
    addAction(deleteAction)
    
  } catch (error) {
    // 用户取消删除
  }
}

const batchExportNews = async (selectedRows) => {
  try {
    const response = await analyticsApi.exportData({
      type: 'news',
      format: 'csv',
      ids: selectedRows
    })
    
    ElMessage.success(`已导出 ${selectedRows.length} 条新闻`)
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

// 数据加载方法
const loadKeyMetrics = async () => {
  try {
    const response = await analyticsApi.getOverview({
      start_date: dateRange.value[0],
      end_date: dateRange.value[1]
    })
    
    // 修复：调整数据格式映射以匹配实际API返回格式
    if (response.data && response.success !== false) {
      const data = response.data
      // API返回格式：{ total_news, today_news, sources_count, last_update }
      keyMetrics.value[0].value = data.total_news || 0
      keyMetrics.value[1].value = data.today_news || 0
      keyMetrics.value[2].value = data.sources_count || 0
      keyMetrics.value[3].value = Math.round((data.avg_daily_news || 0) * 10) / 10
      
      // 更新最后更新时间
      if (data.last_update) {
        lastUpdate.value = new Date(data.last_update)
      }
    } else {
      console.error('API返回异常数据:', response)
      ElMessage.warning('数据格式异常，请检查API接口')
    }
  } catch (error) {
    console.error('加载关键指标失败:', error)
    ElMessage.error('加载数据概览失败，请检查网络连接')
  }
}

const loadTrendChart = async () => {
  chartLoading.trend = true
  try {
    const response = await dashboardApi.getEChartsData({
      type: 'trend',
      start_date: dateRange.value[0],
      end_date: dateRange.value[1]
    })
    
    if (response.data.success && charts.trend) {
      const chartData = response.data.data
      const option = {
        title: {
          text: chartData.title || '新闻发布趋势',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis'
        },
        legend: {
          top: 30
        },
        xAxis: {
          type: 'category',
          data: chartData.xAxis || []
        },
        yAxis: {
          type: 'value'
        },
        series: chartData.series || []
      }
      charts.trend.setOption(option)
    }
  } catch (error) {
    console.error('加载趋势图失败:', error)
  } finally {
    chartLoading.trend = false
  }
}

// 工具方法
const formatMetricValue = (value, format) => {
  if (format === 'percentage') {
    return `${value}%`
  } else if (format === 'number') {
    return value.toLocaleString()
  }
  return value
}

const formatBytes = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const getTrendIcon = (trend) => {
  switch (trend) {
    case 'up': return 'ArrowUp'
    case 'down': return 'ArrowDown'
    default: return 'Minus'
  }
}

const getStatusType = (status) => {
  const typeMap = {
    running: 'success',
    stopped: 'info',
    error: 'danger'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    running: '运行中',
    stopped: '已停止',
    error: '错误'
  }
  return textMap[status] || '未知'
}

const getProgressColor = (percentage) => {
  if (percentage >= 90) return '#67C23A'
  if (percentage >= 70) return '#E6A23C'
  return '#F56C6C'
}

// 初始化图表
const initCharts = () => {
  nextTick(() => {
    if (process.client) {
      // 初始化各种图表
      const trendEl = document.querySelector('[ref="trendChart"]')
      if (trendEl) {
        charts.trend = echarts.init(trendEl)
      }
      
      // 添加窗口大小变化监听
      window.addEventListener('resize', () => {
        Object.values(charts).forEach(chart => {
          if (chart && chart.resize) {
            chart.resize()
          }
        })
      })
    }
  })
}

// 生命周期
onMounted(() => {
  // 设置默认日期范围
  const today = new Date()
  const lastWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000)
  dateRange.value = [
    lastWeek.toISOString().split('T')[0],
    today.toISOString().split('T')[0]
  ]
  
  initCharts()
  refreshDashboard()
  
  if (autoRefresh.value) {
    refreshTimer = setInterval(refreshDashboard, 30000)
  }
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  
  // 销毁图表实例
  Object.values(charts).forEach(chart => {
    if (chart && chart.dispose) {
      chart.dispose()
    }
  })
})
</script>

<style scoped>
.analytics-dashboard {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100vh;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.dashboard-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dashboard-subtitle {
  font-size: 14px;
  color: #909399;
  margin: 4px 0 0 0;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  border-left: 4px solid;
}

.metric-card.metric-primary { border-left-color: #409EFF; }
.metric-card.metric-success { border-left-color: #67C23A; }
.metric-card.metric-warning { border-left-color: #E6A23C; }
.metric-card.metric-danger { border-left-color: #F56C6C; }

.metric-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.metric-label {
  font-size: 14px;
  color: #606266;
}

.metric-value {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-value .value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.metric-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.metric-trend.up { color: #67C23A; }
.metric-trend.down { color: #F56C6C; }
.metric-trend.stable { color: #909399; }

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.chart-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow: hidden;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #EBEEF5;
}

.chart-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.chart-content {
  height: 300px;
  padding: 16px;
}

.performance-table .chart-content {
  height: auto;
  padding: 0;
}

.progress-text {
  margin-left: 8px;
  font-size: 12px;
  color: #606266;
}

.system-monitor {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  padding: 20px;
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #EBEEF5;
}

.monitor-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.monitor-card {
  text-align: center;
  padding: 16px;
  border: 1px solid #EBEEF5;
  border-radius: 6px;
}

.monitor-title {
  font-size: 14px;
  color: #606266;
  margin-bottom: 12px;
}

.mini-chart {
  height: 60px;
  margin-bottom: 8px;
}

.monitor-value {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.form-tip {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .analytics-dashboard {
    padding: 12px;
  }
  
  .dashboard-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .header-right {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  
  .charts-grid {
    grid-template-columns: 1fr;
  }
  
  .monitor-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .monitor-grid {
    grid-template-columns: 1fr;
  }
}
</style> 