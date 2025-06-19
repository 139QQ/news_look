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

// 请求拦截器
api.interceptors.request.use(
  config => {
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
      switch (error.response.status) {
        case 400:
          message = '请求参数错误'
          break
        case 401:
          message = '未授权访问'
          break
        case 403:
          message = '禁止访问'
          break
        case 404:
          message = '资源不存在'
          break
        case 500:
          message = '服务器错误'
          break
        default:
          message = `错误代码: ${error.response.status}`
      }
    } else if (error.request) {
      message = '网络连接失败'
    }
    
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// API方法
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

export const crawlerApi = {
  // 获取爬虫状态
  getCrawlerStatus() {
    return api.get('/crawler/status')
  },
  
  // 启动爬虫
  startCrawler(name) {
    return api.post(`/crawlers/${name}/start`)
  },
  
  // 停止爬虫
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

export const systemApi = {
  // 获取系统信息
  getSystemInfo() {
    return api.get('/system/info')
  },
  
  // 获取系统日志
  getSystemLogs(params = {}) {
    return api.get('/system/logs', { params })
  },
  
  // 健康检查
  healthCheck() {
    return api.get('/health')
  }
}

export default api 