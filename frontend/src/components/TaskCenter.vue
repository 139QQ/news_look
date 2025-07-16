<template>
  <div class="task-center">
    <div class="task-header">
      <h2 class="task-title">任务中心</h2>
      <div class="task-stats">
        <el-statistic
          v-for="stat in taskStats"
          :key="stat.key"
          :value="stat.value"
          :title="stat.title"
          :suffix="stat.suffix"
          :precision="stat.precision"
          :value-style="stat.valueStyle"
          class="task-stat"
        />
      </div>
    </div>
    
    <div class="task-content">
      <el-tabs 
        v-model="activeTask" 
        type="border-card" 
        class="task-tabs"
        @tab-change="handleTaskChange"
      >
        <!-- 监控爬虫任务 -->
        <el-tab-pane 
          label="监控爬虫" 
          name="crawler-monitor"
          :disabled="!hasPermission('crawler:manage')"
        >
          <div class="task-pane">
            <div class="pane-header">
              <el-icon class="pane-icon">
                <monitor />
              </el-icon>
              <span class="pane-title">爬虫监控</span>
              <el-tag :type="crawlerStatus.type" size="small" class="status-tag">
                {{ crawlerStatus.text }}
              </el-tag>
            </div>
            
            <div class="crawler-dashboard">
              <div class="crawler-grid">
                <!-- 爬虫状态卡片 -->
                <el-card 
                  v-for="crawler in crawlerList" 
                  :key="crawler.id"
                  class="crawler-card"
                  :class="{ 'active': crawler.status === 'running' }"
                  shadow="hover"
                >
                  <div class="crawler-info">
                    <div class="crawler-header">
                      <el-icon class="crawler-icon">
                        <component :is="crawler.icon" />
                      </el-icon>
                      <span class="crawler-name">{{ crawler.name }}</span>
                      <el-tag 
                        :type="getStatusType(crawler.status)" 
                        size="small"
                        class="crawler-status"
                      >
                        {{ getStatusText(crawler.status) }}
                      </el-tag>
                    </div>
                    
                    <div class="crawler-metrics">
                      <div class="metric-item">
                        <span class="metric-label">今日采集</span>
                        <span class="metric-value">{{ crawler.todayCount }}</span>
                      </div>
                      <div class="metric-item">
                        <span class="metric-label">成功率</span>
                        <span class="metric-value">{{ crawler.successRate }}%</span>
                      </div>
                      <div class="metric-item">
                        <span class="metric-label">平均响应</span>
                        <span class="metric-value">{{ crawler.avgResponse }}ms</span>
                      </div>
                    </div>
                    
                    <div class="crawler-actions">
                      <el-button 
                        v-if="crawler.status !== 'running'" 
                        type="primary" 
                        size="small"
                        @click="startCrawler(crawler.id)"
                        :loading="crawler.starting"
                      >
                        启动
                      </el-button>
                      <el-button 
                        v-else 
                        type="danger" 
                        size="small"
                        @click="stopCrawler(crawler.id)"
                        :loading="crawler.stopping"
                      >
                        停止
                      </el-button>
                      <el-button 
                        type="info" 
                        size="small"
                        @click="viewCrawlerDetail(crawler)"
                      >
                        详情
                      </el-button>
                    </div>
                  </div>
                </el-card>
              </div>
              
              <!-- 快速操作 -->
              <div class="quick-actions">
                <el-button 
                  type="primary" 
                  @click="startAllCrawlers"
                  :loading="batchLoading"
                >
                  <el-icon><video-play /></el-icon>
                  启动所有
                </el-button>
                <el-button 
                  type="danger" 
                  @click="stopAllCrawlers"
                  :loading="batchLoading"
                >
                  <el-icon><video-pause /></el-icon>
                  停止所有
                </el-button>
                <el-button 
                  type="info" 
                  @click="refreshCrawlers"
                  :loading="refreshLoading"
                >
                  <el-icon><refresh /></el-icon>
                  刷新状态
                </el-button>
              </div>
            </div>
          </div>
        </el-tab-pane>
        
        <!-- 分析数据任务 -->
        <el-tab-pane 
          label="分析数据" 
          name="data-analysis"
          :disabled="!hasPermission('data:analyze')"
        >
          <div class="task-pane">
            <div class="pane-header">
              <el-icon class="pane-icon">
                <data-analysis />
              </el-icon>
              <span class="pane-title">数据分析</span>
              <el-tag type="success" size="small" class="status-tag">
                实时更新
              </el-tag>
            </div>
            
            <div class="analysis-dashboard">
              <div class="analysis-controls">
                <el-date-picker
                  v-model="analysisDateRange"
                  type="datetimerange"
                  format="YYYY-MM-DD HH:mm"
                  value-format="YYYY-MM-DD HH:mm:ss"
                  range-separator="至"
                  start-placeholder="开始时间"
                  end-placeholder="结束时间"
                  class="date-picker"
                />
                <el-select 
                  v-model="selectedSources" 
                  multiple 
                  placeholder="选择数据源"
                  class="source-select"
                >
                  <el-option
                    v-for="source in dataSources"
                    :key="source.value"
                    :label="source.label"
                    :value="source.value"
                  />
                </el-select>
                <el-button 
                  type="primary" 
                  @click="runAnalysis"
                  :loading="analysisLoading"
                >
                  <el-icon><search /></el-icon>
                  开始分析
                </el-button>
              </div>
              
              <div class="analysis-results">
                <div class="result-grid">
                  <el-card class="result-card" shadow="never">
                    <div class="result-header">
                      <el-icon class="result-icon">
                        <trend-charts />
                      </el-icon>
                      <span class="result-title">趋势分析</span>
                    </div>
                    <div class="result-content">
                      <div class="trend-chart" ref="trendChartRef"></div>
                    </div>
                  </el-card>
                  
                  <el-card class="result-card" shadow="never">
                    <div class="result-header">
                      <el-icon class="result-icon">
                        <pie-chart />
                      </el-icon>
                      <span class="result-title">来源分布</span>
                    </div>
                    <div class="result-content">
                      <div class="pie-chart" ref="pieChartRef"></div>
                    </div>
                  </el-card>
                  
                  <el-card class="result-card" shadow="never">
                    <div class="result-header">
                      <el-icon class="result-icon">
                        <data-board />
                      </el-icon>
                      <span class="result-title">关键指标</span>
                    </div>
                    <div class="result-content">
                      <div class="metrics-grid">
                        <div 
                          v-for="metric in keyMetrics" 
                          :key="metric.key"
                          class="metric-box"
                        >
                          <div class="metric-number">{{ metric.value }}</div>
                          <div class="metric-label">{{ metric.label }}</div>
                          <div class="metric-change" :class="metric.changeType">
                            {{ metric.change }}
                          </div>
                        </div>
                      </div>
                    </div>
                  </el-card>
                </div>
                
                <div class="analysis-actions">
                  <el-button 
                    type="success" 
                    @click="exportAnalysisReport"
                    :loading="exportLoading"
                  >
                    <el-icon><download /></el-icon>
                    导出报告
                  </el-button>
                  <el-button 
                    type="info" 
                    @click="scheduleAnalysis"
                  >
                    <el-icon><timer /></el-icon>
                    定时分析
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>
        
        <!-- 配置规则任务 -->
        <el-tab-pane 
          label="配置规则" 
          name="config-rules"
          :disabled="!hasPermission('system:config')"
        >
          <div class="task-pane">
            <div class="pane-header">
              <el-icon class="pane-icon">
                <setting />
              </el-icon>
              <span class="pane-title">配置规则</span>
              <el-tag type="warning" size="small" class="status-tag">
                需要重启生效
              </el-tag>
            </div>
            
            <div class="config-dashboard">
              <div class="config-categories">
                <el-menu
                  v-model="activeConfigCategory"
                  mode="vertical"
                  class="config-menu"
                  @select="handleConfigCategoryChange"
                >
                  <el-menu-item
                    v-for="category in configCategories"
                    :key="category.key"
                    :index="category.key"
                  >
                    <el-icon>
                      <component :is="category.icon" />
                    </el-icon>
                    <span>{{ category.title }}</span>
                  </el-menu-item>
                </el-menu>
              </div>
              
              <div class="config-content">
                <div class="config-form">
                  <component 
                    :is="getCurrentConfigComponent()"
                    v-model="configData[activeConfigCategory]"
                    @change="handleConfigChange"
                  />
                </div>
                
                <div class="config-actions">
                  <el-button 
                    type="primary" 
                    @click="saveConfig"
                    :loading="saveLoading"
                  >
                    <el-icon><check /></el-icon>
                    保存配置
                  </el-button>
                  <el-button 
                    type="info" 
                    @click="resetConfig"
                  >
                    <el-icon><refresh-left /></el-icon>
                    重置默认
                  </el-button>
                  <el-button 
                    type="warning" 
                    @click="testConfig"
                    :loading="testLoading"
                  >
                    <el-icon><view /></el-icon>
                    测试配置
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useUserStore } from '@/store/user'
import { 
  Monitor, 
  DataAnalysis, 
  Setting, 
  VideoPlay, 
  VideoPause,
  Refresh,
  Search,
  Download,
  Timer,
  Check,
  RefreshLeft,
  View,
  TrendCharts,
  PieChart,
  DataBoard
} from '@element-plus/icons-vue'

export default {
  name: 'TaskCenter',
  components: {
    Monitor,
    DataAnalysis,
    Setting,
    VideoPlay,
    VideoPause,
    Refresh,
    Search,
    Download,
    Timer,
    Check,
    RefreshLeft,
    View,
    TrendCharts,
    PieChart,
    DataBoard
  },
  
  setup() {
    const userStore = useUserStore()
    const activeTask = ref('crawler-monitor')
    const batchLoading = ref(false)
    const refreshLoading = ref(false)
    const analysisLoading = ref(false)
    const exportLoading = ref(false)
    const saveLoading = ref(false)
    const testLoading = ref(false)
    const activeConfigCategory = ref('crawler')
    
    // 任务统计
    const taskStats = ref([
      { key: 'running', title: '运行中', value: 3, suffix: '个', valueStyle: { color: '#67C23A' } },
      { key: 'success', title: '成功率', value: 95.8, suffix: '%', precision: 1, valueStyle: { color: '#409EFF' } },
      { key: 'today', title: '今日采集', value: 1247, suffix: '条', valueStyle: { color: '#E6A23C' } },
      { key: 'total', title: '总计', value: 52.6, suffix: 'K', precision: 1, valueStyle: { color: '#F56C6C' } }
    ])
    
    // 爬虫状态
    const crawlerStatus = computed(() => {
      const runningCount = crawlerList.value.filter(c => c.status === 'running').length
      if (runningCount === 0) return { type: 'info', text: '全部停止' }
      if (runningCount === crawlerList.value.length) return { type: 'success', text: '全部运行' }
      return { type: 'warning', text: `${runningCount}个运行中` }
    })
    
    // 爬虫列表
    const crawlerList = ref([
      {
        id: 'tencent',
        name: '腾讯财经',
        icon: 'Monitor',
        status: 'running',
        todayCount: 324,
        successRate: 98.2,
        avgResponse: 245,
        starting: false,
        stopping: false
      },
      {
        id: 'sina',
        name: '新浪财经',
        icon: 'Monitor',
        status: 'stopped',
        todayCount: 278,
        successRate: 94.7,
        avgResponse: 312,
        starting: false,
        stopping: false
      },
      {
        id: 'eastmoney',
        name: '东方财富',
        icon: 'Monitor',
        status: 'running',
        todayCount: 456,
        successRate: 96.8,
        avgResponse: 289,
        starting: false,
        stopping: false
      },
      {
        id: 'netease',
        name: '网易财经',
        icon: 'Monitor',
        status: 'error',
        todayCount: 89,
        successRate: 78.3,
        avgResponse: 523,
        starting: false,
        stopping: false
      }
    ])
    
    // 数据分析相关
    const analysisDateRange = ref(['2024-01-01 00:00:00', '2024-01-31 23:59:59'])
    const selectedSources = ref(['tencent', 'sina'])
    const dataSources = ref([
      { label: '腾讯财经', value: 'tencent' },
      { label: '新浪财经', value: 'sina' },
      { label: '东方财富', value: 'eastmoney' },
      { label: '网易财经', value: 'netease' }
    ])
    
    const keyMetrics = ref([
      { key: 'articles', label: '文章数量', value: '1,247', change: '+12.3%', changeType: 'positive' },
      { key: 'keywords', label: '关键词', value: '856', change: '+8.7%', changeType: 'positive' },
      { key: 'sentiment', label: '情感分数', value: '7.2', change: '-2.1%', changeType: 'negative' },
      { key: 'quality', label: '质量分数', value: '8.9', change: '+5.4%', changeType: 'positive' }
    ])
    
    // 配置规则相关
    const configCategories = ref([
      { key: 'crawler', title: '爬虫配置', icon: 'Monitor' },
      { key: 'database', title: '数据库配置', icon: 'DataBoard' },
      { key: 'notification', title: '通知配置', icon: 'Bell' },
      { key: 'security', title: '安全配置', icon: 'Lock' }
    ])
    
    const configData = ref({
      crawler: {
        frequency: 'daily',
        timeout: 30,
        retry: 3,
        concurrent: 5
      },
      database: {
        type: 'sqlite',
        path: 'data/db',
        backup: true,
        retention: 90
      },
      notification: {
        email: true,
        webhook: false,
        level: 'error'
      },
      security: {
        rateLimit: 100,
        ipWhitelist: [],
        encryption: true
      }
    })
    
    // 权限检查
    const hasPermission = (permission) => {
      return userStore.hasPermission(permission)
    }
    
    // 方法
    const handleTaskChange = (taskName) => {
      console.log('切换任务:', taskName)
    }
    
    const getStatusType = (status) => {
      const typeMap = {
        'running': 'success',
        'stopped': 'info',
        'error': 'danger',
        'warning': 'warning'
      }
      return typeMap[status] || 'info'
    }
    
    const getStatusText = (status) => {
      const textMap = {
        'running': '运行中',
        'stopped': '已停止',
        'error': '错误',
        'warning': '警告'
      }
      return textMap[status] || '未知'
    }
    
    const startCrawler = async (crawlerId) => {
      const crawler = crawlerList.value.find(c => c.id === crawlerId)
      if (crawler) {
        crawler.starting = true
        // 模拟API调用
        await new Promise(resolve => setTimeout(resolve, 2000))
        crawler.status = 'running'
        crawler.starting = false
      }
    }
    
    const stopCrawler = async (crawlerId) => {
      const crawler = crawlerList.value.find(c => c.id === crawlerId)
      if (crawler) {
        crawler.stopping = true
        // 模拟API调用
        await new Promise(resolve => setTimeout(resolve, 1500))
        crawler.status = 'stopped'
        crawler.stopping = false
      }
    }
    
    const startAllCrawlers = async () => {
      batchLoading.value = true
      // 模拟批量启动
      await new Promise(resolve => setTimeout(resolve, 3000))
      crawlerList.value.forEach(crawler => {
        if (crawler.status !== 'error') {
          crawler.status = 'running'
        }
      })
      batchLoading.value = false
    }
    
    const stopAllCrawlers = async () => {
      batchLoading.value = true
      // 模拟批量停止
      await new Promise(resolve => setTimeout(resolve, 2000))
      crawlerList.value.forEach(crawler => {
        crawler.status = 'stopped'
      })
      batchLoading.value = false
    }
    
    const refreshCrawlers = async () => {
      refreshLoading.value = true
      // 模拟刷新
      await new Promise(resolve => setTimeout(resolve, 1000))
      refreshLoading.value = false
    }
    
    const runAnalysis = async () => {
      analysisLoading.value = true
      // 模拟分析
      await new Promise(resolve => setTimeout(resolve, 3000))
      analysisLoading.value = false
    }
    
    const exportAnalysisReport = async () => {
      exportLoading.value = true
      // 模拟导出
      await new Promise(resolve => setTimeout(resolve, 2000))
      exportLoading.value = false
    }
    
    const saveConfig = async () => {
      saveLoading.value = true
      // 模拟保存
      await new Promise(resolve => setTimeout(resolve, 1500))
      saveLoading.value = false
    }
    
    const testConfig = async () => {
      testLoading.value = true
      // 模拟测试
      await new Promise(resolve => setTimeout(resolve, 2000))
      testLoading.value = false
    }
    
    const getCurrentConfigComponent = () => {
      // 返回当前配置分类对应的组件
      return 'div' // 这里应该返回具体的配置组件
    }
    
    const handleConfigCategoryChange = (key) => {
      activeConfigCategory.value = key
    }
    
    const handleConfigChange = (data) => {
      // 处理配置变更
      console.log('配置变更:', data)
    }
    
    const viewCrawlerDetail = (crawler) => {
      console.log('查看爬虫详情:', crawler)
    }
    
    const scheduleAnalysis = () => {
      console.log('定时分析')
    }
    
    const resetConfig = () => {
      // 重置配置
      console.log('重置配置')
    }
    
    return {
      activeTask,
      taskStats,
      crawlerStatus,
      crawlerList,
      batchLoading,
      refreshLoading,
      analysisLoading,
      exportLoading,
      saveLoading,
      testLoading,
      analysisDateRange,
      selectedSources,
      dataSources,
      keyMetrics,
      activeConfigCategory,
      configCategories,
      configData,
      hasPermission,
      handleTaskChange,
      getStatusType,
      getStatusText,
      startCrawler,
      stopCrawler,
      startAllCrawlers,
      stopAllCrawlers,
      refreshCrawlers,
      runAnalysis,
      exportAnalysisReport,
      saveConfig,
      testConfig,
      getCurrentConfigComponent,
      handleConfigCategoryChange,
      handleConfigChange,
      viewCrawlerDetail,
      scheduleAnalysis,
      resetConfig
    }
  }
}
</script>

<style lang="scss" scoped>
.task-center {
  .task-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    
    .task-title {
      font-size: 24px;
      font-weight: 600;
      color: #303133;
      margin: 0;
    }
    
    .task-stats {
      display: flex;
      gap: 32px;
      
      .task-stat {
        text-align: center;
        min-width: 80px;
      }
    }
  }
  
  .task-content {
    .task-tabs {
      border: 1px solid #E4E7ED;
      border-radius: 8px;
      overflow: hidden;
      
      .task-pane {
        padding: 24px;
        
        .pane-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 24px;
          
          .pane-icon {
            font-size: 20px;
            color: #409EFF;
          }
          
          .pane-title {
            font-size: 18px;
            font-weight: 600;
            color: #303133;
          }
          
          .status-tag {
            margin-left: auto;
          }
        }
      }
    }
  }
  
  // 爬虫监控样式
  .crawler-dashboard {
    .crawler-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
      
      .crawler-card {
        border: 1px solid #E4E7ED;
        border-radius: 8px;
        transition: all 0.3s;
        
        &:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        &.active {
          border-color: #67C23A;
          background: rgba(103, 194, 58, 0.05);
        }
        
        .crawler-info {
          .crawler-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
            
            .crawler-icon {
              font-size: 18px;
              color: #409EFF;
            }
            
            .crawler-name {
              flex: 1;
              font-weight: 500;
              color: #303133;
            }
          }
          
          .crawler-metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 16px;
            
            .metric-item {
              text-align: center;
              
              .metric-label {
                display: block;
                font-size: 12px;
                color: #909399;
                margin-bottom: 4px;
              }
              
              .metric-value {
                font-size: 16px;
                font-weight: 600;
                color: #303133;
              }
            }
          }
          
          .crawler-actions {
            display: flex;
            gap: 8px;
            justify-content: center;
          }
        }
      }
    }
    
    .quick-actions {
      display: flex;
      gap: 12px;
      justify-content: center;
    }
  }
  
  // 数据分析样式
  .analysis-dashboard {
    .analysis-controls {
      display: flex;
      gap: 16px;
      margin-bottom: 24px;
      align-items: center;
      flex-wrap: wrap;
      
      .date-picker {
        width: 300px;
      }
      
      .source-select {
        width: 200px;
      }
    }
    
    .analysis-results {
      .result-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-bottom: 24px;
        
        .result-card {
          border: 1px solid #E4E7ED;
          border-radius: 8px;
          
          .result-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
            
            .result-icon {
              font-size: 18px;
              color: #409EFF;
            }
            
            .result-title {
              font-weight: 500;
              color: #303133;
            }
          }
          
          .result-content {
            .trend-chart,
            .pie-chart {
              width: 100%;
              height: 200px;
              background: #F5F7FA;
              border-radius: 4px;
              display: flex;
              align-items: center;
              justify-content: center;
              color: #909399;
            }
            
            .metrics-grid {
              display: grid;
              grid-template-columns: repeat(2, 1fr);
              gap: 16px;
              
              .metric-box {
                text-align: center;
                padding: 16px;
                background: #F8F9FA;
                border-radius: 6px;
                
                .metric-number {
                  font-size: 24px;
                  font-weight: 600;
                  color: #303133;
                  margin-bottom: 4px;
                }
                
                .metric-label {
                  font-size: 12px;
                  color: #909399;
                  margin-bottom: 4px;
                }
                
                .metric-change {
                  font-size: 12px;
                  font-weight: 500;
                  
                  &.positive {
                    color: #67C23A;
                  }
                  
                  &.negative {
                    color: #F56C6C;
                  }
                }
              }
            }
          }
        }
      }
      
      .analysis-actions {
        display: flex;
        gap: 12px;
        justify-content: center;
      }
    }
  }
  
  // 配置规则样式
  .config-dashboard {
    display: flex;
    gap: 24px;
    
    .config-categories {
      width: 200px;
      flex-shrink: 0;
      
      .config-menu {
        border: 1px solid #E4E7ED;
        border-radius: 8px;
      }
    }
    
    .config-content {
      flex: 1;
      
      .config-form {
        background: #F8F9FA;
        border-radius: 8px;
        padding: 24px;
        margin-bottom: 24px;
        min-height: 400px;
      }
      
      .config-actions {
        display: flex;
        gap: 12px;
        justify-content: center;
      }
    }
  }
}

// 响应式设计
@media (max-width: 1024px) {
  .task-center {
    .task-header {
      flex-direction: column;
      gap: 16px;
      align-items: flex-start;
      
      .task-stats {
        align-self: stretch;
        justify-content: space-between;
      }
    }
    
    .analysis-dashboard {
      .analysis-controls {
        flex-direction: column;
        align-items: stretch;
        
        .date-picker,
        .source-select {
          width: 100%;
        }
      }
      
      .analysis-results {
        .result-grid {
          grid-template-columns: 1fr;
        }
      }
    }
    
    .config-dashboard {
      flex-direction: column;
      
      .config-categories {
        width: 100%;
        
        .config-menu {
          display: flex;
          overflow-x: auto;
        }
      }
    }
  }
}

@media (max-width: 768px) {
  .task-center {
    .crawler-dashboard {
      .crawler-grid {
        grid-template-columns: 1fr;
      }
    }
    
    .task-stats {
      flex-direction: column;
      gap: 16px;
    }
  }
}
</style> 