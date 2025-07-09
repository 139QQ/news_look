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

// 数据结构校验函数
function validateSchema(data, schema) {
  if (!data || typeof data !== 'object') return false
  
  for (const [key, expectedType] of Object.entries(schema)) {
    const value = data[key]
    if (expectedType === 'number' && (typeof value !== 'number' && !Number.isFinite(Number(value)))) {
      return false
    }
    if (expectedType === 'string' && typeof value !== 'string') {
      return false
    }
    if (expectedType === 'array' && !Array.isArray(value)) {
      return false
    }
  }
  return true
}

// 数据防护层 - 处理异常数据结构
function normalizeData(response, endpoint = '') {
  // 空数据兜底
  if (!response || !response.data) {
    console.warn(`[数据防护] 空响应数据，端点: ${endpoint}`)
    return {
      data: [],
      total: 0,
      _isFallback: true,
      _fallbackReason: 'empty_response'
    }
  }

  // 处理数组数据
  if (Array.isArray(response.data)) {
    if (response.data.length === 0) {
      return {
        data: [],
        total: 0,
        _isFallback: true,
        _fallbackReason: 'empty_array'
      }
    }

    // 数据结构校验和修复
    const schema = {
      id: 'number',
      title: 'string',
      view_count: 'number'
    }

    response.data.forEach((item, index) => {
      // 自动修复常见问题
      if (item.view_count !== undefined) {
        item.view_count = Number(item.view_count) || 0
      }
      if (item.pub_time && typeof item.pub_time !== 'string') {
        item.pub_time = String(item.pub_time)
      }
      if (!item.title) {
        item.title = `未知标题 #${index + 1}`
      }
    })
  }

  return response
}

// 获取缓存数据（简单的内存缓存实现）
const cache = new Map()
function getCachedData(key) {
  const cached = cache.get(key)
  if (cached && (Date.now() - cached.timestamp < 300000)) { // 5分钟缓存
    return cached.data
  }
  return null
}

function setCachedData(key, data) {
  cache.set(key, {
    data: data,
    timestamp: Date.now()
  })
}

// 增强的404处理
async function handleNotFoundError(id, endpoint) {
  console.warn(`[404处理] 资源不存在: ${endpoint}/${id}`)
  
  // 尝试从缓存获取数据
  const cachedData = getCachedData(`${endpoint}_${id}`)
  if (cachedData) {
    console.log(`[404处理] 使用缓存数据: ${endpoint}/${id}`)
    return {
      data: cachedData,
      status: 'cached',
      _isFallback: true,
      _fallbackReason: 'not_found_cached'
    }
  }

  // 返回占位数据
  const placeholderData = {
    id: id,
    title: '数据加载中...',
    content: '该内容暂时无法获取，请稍后重试',
    pub_time: new Date().toISOString(),
    status: 'placeholder'
  }

  return {
    data: placeholderData,
    status: 'placeholder',
    _isFallback: true,
    _fallbackReason: 'not_found_placeholder'
  }
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

// 自定义错误类
class DataStructureError extends Error {
  constructor(response) {
    super('数据结构异常')
    this.name = 'DataStructureError'
    this.response = response
  }
}

class DataNotFoundError extends Error {
  constructor(endpoint, id) {
    super(`数据不存在: ${endpoint}/${id}`)
    this.name = 'DataNotFoundError'
    this.endpoint = endpoint
    this.id = id
  }
}

// 全局请求拦截器
api.interceptors.request.use(
  async config => {
    // 自动附加环境标识
    config.headers['X-Env'] = import.meta.env.MODE || 'development'
    config.headers['X-Request-ID'] = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    // 如果API状态未知或不健康，先进行健康检查
    if (!apiHealthStatus.isHealthy) {
      await checkApiHealth()
    }
    
    // 如果仍然不健康，但请求不是健康检查，则给出警告
    if (!apiHealthStatus.isHealthy && !config.url?.includes('/health')) {
      console.warn('⚠️ API服务状态异常，请求可能失败')
    }
    
    console.log(`[请求] ${config.method?.toUpperCase()} ${config.url}`, {
      requestId: config.headers['X-Request-ID'],
      params: config.params
    })
    
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 全局响应拦截器
api.interceptors.response.use(
  response => {
    const { data, config } = response
    const requestId = config.headers['X-Request-ID']
    
    console.log(`[响应] ${config.method?.toUpperCase()} ${config.url}`, {
      requestId,
      status: response.status,
      dataType: Array.isArray(data?.data) ? 'array' : typeof data
    })
    
    // 结构校验
    if (data && !data.success && data.success !== undefined) {
      throw new DataStructureError(data)
    }
    
    // 数据标准化处理
    const normalizedData = normalizeData(data, config.url)
    
    // 缓存成功的数据
    if (normalizedData && normalizedData.data && !normalizedData._isFallback) {
      setCachedData(`${config.url}_${JSON.stringify(config.params || {})}`, normalizedData.data)
    }
    
    return normalizedData
  },
  async error => {
    const { response, config, request } = error
    const requestId = config?.headers?.['X-Request-ID']
    
    // 统一错误处理
    let message = '网络错误'
    let errorData = null
    
    if (response) {
      const { status, data } = response
      const url = config?.url || ''
      
      console.error(`[错误响应] ${config?.method?.toUpperCase()} ${url}`, {
        requestId,
        status,
        error: data
      })
      
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
          // 404错误的优雅处理
          if (apiHealthStatus.isHealthy) {
            // 后端服务正常，但请求的资源不存在
            message = data?.message || '请求的数据不存在'
            
            // 尝试优雅降级
            const pathMatch = url.match(/\/(\w+)\/(.+)$/)
            if (pathMatch) {
              const [, endpoint, id] = pathMatch
              try {
                errorData = await handleNotFoundError(id, endpoint)
                console.log(`[404恢复] 使用降级数据: ${endpoint}/${id}`)
                // 返回降级数据而不是抛出错误
                return errorData
              } catch (fallbackError) {
                console.error('[404恢复失败]', fallbackError)
              }
            }
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
    } else if (request) {
      // 请求发出但没有收到响应，更新健康状态
      apiHealthStatus.isHealthy = false
      apiHealthStatus.lastCheck = new Date()
      
      console.error(`[网络错误]`, {
        requestId,
        code: error.code,
        message: error.message
      })
      
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
      console.error(`[配置错误]`, {
        requestId,
        error: error.message
      })
    }
    
    // 过滤掉已处理的404错误，避免重复显示消息
    if (!(error.response?.status === 404 && errorData)) {
      ElMessage.error(message)
    }
    
    // 错误上报（这里可以集成Sentry等）
    if (window.Sentry) {
      window.Sentry.captureException(error, {
        tags: {
          requestId,
          endpoint: config?.url,
          method: config?.method
        }
      })
    }
    
    return Promise.reject(error)
  }
)

// 增强的API函数
async function fetchDataWithFallback(endpoint, params = {}) {
  try {
    const response = await api.get(endpoint, {
      params,
      // 双重验证机制
      validateStatus: status => (status >= 200 && status < 300) || status === 404
    })
    
    if (response.status === 404) {
      return {
        status: 'empty',
        fallback: getCachedData(`${endpoint}_${JSON.stringify(params)}`)
      }
    }
    
    return response
  } catch (err) {
    // 错误上报
    if (window.Sentry) {
      window.Sentry.captureException(err)
    }
    throw err
  }
}

// 新闻API - 增强版
export const newsApi = {
  // 获取新闻列表
  async getNewsList(params = {}) {
    return fetchDataWithFallback('/news', params)
  },
  
  // 获取新闻详情 - 带404优雅处理
  async getNewsDetail(id) {
    try {
      return await fetchDataWithFallback(`/news/${id}`)
    } catch (error) {
      if (error.response?.status === 404) {
        // 已在拦截器中处理，这里不需要额外处理
        throw new DataNotFoundError('news', id)
      }
      throw error
    }
  },
  
  // 获取新闻来源
  async getNewsSources() {
    return fetchDataWithFallback('/sources')
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