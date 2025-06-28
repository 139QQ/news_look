import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// API健康状态
let apiHealthStatus = {
  isHealthy: false,
  lastCheck: null,
  backendUrl: null
}

// 检查API健康状态
const checkApiHealth = async () => {
  try {
    // 尝试多个可能的后端地址
    const possibleUrls = [
      'http://127.0.0.1:5000',
      'http://localhost:5000',
      'http://127.0.0.1:8000',
      'http://localhost:8000'
    ]
    
    for (const baseUrl of possibleUrls) {
      try {
        const response = await axios.get(`${baseUrl}/api/health`, { 
          timeout: 3000,
          validateStatus: status => status < 500 
        })
        
        if (response.status === 200) {
          apiHealthStatus = {
            isHealthy: true,
            lastCheck: new Date(),
            backendUrl: baseUrl
          }
          
          // 更新axios实例的baseURL
          api.defaults.baseURL = `${baseUrl}/api`
          
          console.log(`✅ 后端服务连接成功: ${baseUrl}`)
          return true
        }
      } catch (error) {
        // 继续尝试下一个URL
        continue
      }
    }
    
    // 所有URL都失败
    apiHealthStatus = {
      isHealthy: false,
      lastCheck: new Date(),
      backendUrl: null
    }
    
    console.warn('⚠️ 无法连接到后端服务，请确保后端服务已启动')
    return false
    
  } catch (error) {
    console.error('API健康检查失败:', error)
    return false
  }
}

// 获取API健康状态
const getApiHealthStatus = () => apiHealthStatus

// 请求拦截器
api.interceptors.request.use(
  async config => {
    // 如果API状态未知或不健康，先进行健康检查
    if (!apiHealthStatus.isHealthy) {
      await checkApiHealth()
    }
    
    // 如果仍然不健康，但请求不是健康检查，则给出警告
    if (!apiHealthStatus.isHealthy && !config.url?.includes('/health')) {
      console.warn('⚠️ API服务状态异常，请求可能失败')
    }
    
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    const { data } = response
    
    // 处理成功响应
    if (data.success !== false) {
      return data
    }
    
    // 处理业务错误
    ElMessage.error(data.message || '请求失败')
    return Promise.reject(new Error(data.message || '请求失败'))
  },
  error => {
    // 处理HTTP错误
    let message = '网络错误'
    
    if (error.response) {
      const { status, data, config } = error.response
      
      switch (status) {
        case 400:
          message = data?.message || '请求参数错误'
          break
        case 401:
          message = '未授权访问'
          break
        case 403:
          message = '禁止访问'
          break
        case 404:
          // 区分API端点不存在和具体资源不存在
          const url = config?.url || ''
          if (apiHealthStatus.isHealthy) {
            // 后端服务正常，但请求的资源不存在
            message = data?.message || '请求的数据不存在'
          } else {
            // 后端服务异常
            message = `API服务不可用 (${apiHealthStatus.backendUrl || '未知地址'})，请检查后端服务是否启动`
          }
          break
        case 500:
          message = data?.message || '服务器内部错误'
          break
        case 502:
          message = '网关错误，后端服务可能未启动'
          break
        case 503:
          message = '服务暂时不可用'
          break
        default:
          message = data?.message || `HTTP错误: ${status}`
      }
    } else if (error.request) {
      // 请求发出但没有收到响应，更新健康状态
      apiHealthStatus.isHealthy = false
      apiHealthStatus.lastCheck = new Date()
      
      if (error.code === 'ECONNREFUSED') {
        message = '连接被拒绝，请检查后端服务是否启动'
      } else if (error.code === 'ENOTFOUND') {
        message = '无法连接到服务器，请检查网络连接'
      } else if (error.code === 'ETIMEDOUT') {
        message = '请求超时，请稍后重试'
      } else {
        message = '网络连接失败，请检查网络状态'
      }
    } else {
      // 其他错误
      message = error.message || '请求配置错误'
    }
    
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// 新闻API
export const newsApi = {
  // 获取新闻列表
  getNewsList(params = {}) {
    return api.get('/news', { params })
  },
  
  // 获取新闻详情
  getNewsDetail(id) {
    return api.get(`/news/${id}`)
  },
  
  // 获取新闻来源
  getNewsSources() {
    return api.get('/sources')
  }
}

// 增强的爬虫控制API
export const crawlerApi = {
  // 获取爬虫状态
  getCrawlerStatus() {
    return api.get('/v1/crawlers/status')
  },
  
  // 切换爬虫状态 (新API)
  toggleCrawler(id) {
    return api.post(`/v1/crawlers/${id}/toggle`)
  },
  
  // 批量切换爬虫状态 (新API)
  batchToggleCrawlers(data) {
    return api.post('/v1/crawlers/batch/toggle', data)
  },
  
  // 更新爬虫参数 (新API)
  updateCrawlerParams(id, params) {
    return api.patch(`/v1/crawlers/${id}/params`, params)
  },
  
  // 获取爬虫错误历史 (新API)
  getCrawlerErrors(params = {}) {
    return api.get('/v1/crawlers/errors', { params })
  },
  
  // 重置爬虫错误计数 (新API)
  resetCrawlerErrors(id) {
    return api.post(`/v1/crawlers/${id}/reset-errors`)
  },
  
  // 获取爬虫性能指标 (新API)
  getCrawlerMetrics(id, params = {}) {
    return api.get(`/v1/crawlers/${id}/metrics`, { params })
  },
  
  // 启动爬虫 (保持兼容)
  startCrawler(name) {
    return api.post(`/crawlers/${name}/start`)
  },
  
  // 停止爬虫 (保持兼容)
  stopCrawler(name) {
    return api.post(`/crawlers/${name}/stop`)
  },
  
  // 启动所有爬虫
  startAllCrawlers() {
    return api.post('/crawlers/start_all')
  },
  
  // 停止所有爬虫
  stopAllCrawlers() {
    return api.post('/crawlers/stop_all')
  }
}

// 系统监控API (新增)
export const systemApi = {
  // 获取系统健康状态
  getHealth(level = 'basic') {
    return api.get(`/v1/system/health?level=${level}`)
  },
  
  // 获取系统实时指标
  getMetrics() {
    return api.get('/v1/system/metrics')
  },
  
  // 获取系统历史指标
  getMetricsHistory(params = {}) {
    return api.get('/v1/system/metrics/history', { params })
  },
  
  // 获取告警规则
  getAlertRules() {
    return api.get('/v1/system/alerts/rules')
  },
  
  // 创建告警规则
  createAlertRule(rule) {
    return api.post('/v1/system/alerts/rules', rule)
  },
  
  // 更新告警规则
  updateAlertRule(id, rule) {
    return api.put(`/v1/system/alerts/rules/${id}`, rule)
  },
  
  // 删除告警规则
  deleteAlertRule(id) {
    return api.delete(`/v1/system/alerts/rules/${id}`)
  },
  
  // 获取告警历史
  getAlertHistory(params = {}) {
    return api.get('/v1/system/alerts/history', { params })
  },
  
  // 测试通知渠道
  testNotification(config) {
    return api.post('/v1/system/alerts/test', config)
  },
  
  // 获取系统信息 (保持兼容)
  getSystemInfo() {
    return api.get('/system/info')
  },
  
  // 获取系统日志
  getSystemLogs(params = {}) {
    return api.get('/system/logs', { params })
  },
  
  // 健康检查 (保持兼容)
  healthCheck() {
    return api.get('/health')
  }
}

// 数据分析API (新增)
export const analyticsApi = {
  // 获取分析概览
  getOverview(params = {}) {
    return api.get('/v1/analytics/overview', { params })
  },
  
  // 获取ECharts图表数据
  getEChartsData(params = {}) {
    return api.get('/v1/analytics/echarts/data', { params })
  },
  
  // 导出分析数据
  exportData(params) {
    return api.post('/v1/analytics/export', params, {
      responseType: 'blob' // 用于文件下载
    })
  },
  
  // 获取趋势数据
  getTrendData(params = {}) {
    return api.get('/v1/analytics/trends', { params })
  },
  
  // 获取来源分布数据
  getSourceDistribution(params = {}) {
    return api.get('/v1/analytics/sources', { params })
  },
  
  // 获取小时分布数据
  getHourlyDistribution(params = {}) {
    return api.get('/v1/analytics/hourly', { params })
  }
}

// 统计API (保持兼容并增强)
export const statsApi = {
  // 获取统计数据
  getStats() {
    return api.get('/stats')
  },
  
  // 获取来源统计
  getSourceStats() {
    return api.get('/stats/sources')
  },
  
  // 获取每日统计
  getDailyStats() {
    return api.get('/stats/daily')
  }
}

// API状态检查
export const apiStatus = {
  // 检查API状态
  checkStatus() {
    return api.get('/v1/status')
  }
}

// 导出所有API
export const dashboardApi = {
  ...analyticsApi,
  ...systemApi,
  ...crawlerApi
}

// 导出健康检查相关功能
export const healthApi = {
  checkApiHealth,
  getApiHealthStatus,
  
  // 手动检查后端服务状态
  async manualHealthCheck() {
    const isHealthy = await checkApiHealth()
    return {
      isHealthy,
      status: apiHealthStatus,
      message: isHealthy ? '后端服务连接正常' : '无法连接到后端服务'
    }
  },
  
  // 重置健康状态
  resetHealthStatus() {
    apiHealthStatus = {
      isHealthy: false,
      lastCheck: null,
      backendUrl: null
    }
  }
}

// 自动进行初始健康检查
setTimeout(() => {
  checkApiHealth()
}, 1000)

export default api 