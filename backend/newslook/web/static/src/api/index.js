import axios from 'axios'

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 可以在这里添加token等认证信息
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('API请求错误:', error)
    return Promise.reject(error)
  }
)

// API接口
export const newsApi = {
  // 获取新闻列表
  getNewsList(params = {}) {
    return api.get('/news', { params })
  },
  
  // 获取新闻详情
  getNewsDetail(id) {
    return api.get(`/news/${id}`)
  },
  
  // 搜索新闻
  searchNews(query, params = {}) {
    return api.get('/news/search', { 
      params: { q: query, ...params } 
    })
  },
  
  // 获取统计数据
  getStats() {
    return api.get('/stats')
  },
  
  // 获取趋势数据
  getTrends(params = {}) {
    return api.get('/trends', { params })
  }
}

export const crawlerApi = {
  // 获取爬虫状态
  getStatus() {
    return api.get('/crawler/status')
  },
  
  // 启动爬虫
  start(sources = []) {
    return api.post('/crawler/start', { sources })
  },
  
  // 停止爬虫
  stop(sources = []) {
    return api.post('/crawler/stop', { sources })
  },
  
  // 获取爬虫配置
  getConfig() {
    return api.get('/crawler/config')
  },
  
  // 更新爬虫配置
  updateConfig(config) {
    return api.put('/crawler/config', config)
  }
}

export const systemApi = {
  // 获取系统信息
  getInfo() {
    return api.get('/system/info')
  },
  
  // 获取日志
  getLogs(params = {}) {
    return api.get('/system/logs', { params })
  },
  
  // 清理数据
  cleanData(params = {}) {
    return api.post('/system/clean', params)
  },
  
  // 导出数据
  exportData(format = 'excel') {
    return api.get(`/system/export/${format}`, {
      responseType: 'blob'
    })
  }
}

export default api 