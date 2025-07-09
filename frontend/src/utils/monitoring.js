/**
 * NewsLook 前端监控工具集成
 * 支持错误监控、性能监控、用户行为追踪
 */

import { ElMessage, ElNotification } from 'element-plus'

// 监控配置
const MONITORING_CONFIG = {
  // 是否启用监控
  enabled: import.meta.env.MODE === 'production',
  // 调试模式
  debug: import.meta.env.MODE === 'development',
  // 采样率
  sampleRate: import.meta.env.MODE === 'production' ? 0.1 : 1.0,
  // 批量上报间隔
  flushInterval: 10000,
  // 最大队列大小
  maxQueueSize: 100
}

// 事件队列
const eventQueue = []
let flushTimer = null

// 性能指标收集器
class PerformanceMonitor {
  constructor() {
    this.metrics = new Map()
    this.observers = new Map()
    this.init()
  }

  init() {
    if (MONITORING_CONFIG.enabled) {
      this.initWebVitals()
      this.initNavigationTiming()
      this.initResourceTiming()
    }
  }

  // Web Vitals 监控
  initWebVitals() {
    // LCP (Largest Contentful Paint)
    if ('PerformanceObserver' in window) {
      const lcpObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries()
        const lastEntry = entries[entries.length - 1]
        this.recordMetric('LCP', lastEntry.startTime, {
          element: lastEntry.element?.tagName,
          url: lastEntry.url
        })
      })
      
      try {
        lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] })
        this.observers.set('lcp', lcpObserver)
      } catch (e) {
        console.warn('[监控] LCP观察器不支持:', e)
      }

      // FID (First Input Delay)
      const fidObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries()
        entries.forEach(entry => {
          this.recordMetric('FID', entry.processingStart - entry.startTime, {
            eventType: entry.name
          })
        })
      })
      
      try {
        fidObserver.observe({ entryTypes: ['first-input'] })
        this.observers.set('fid', fidObserver)
      } catch (e) {
        console.warn('[监控] FID观察器不支持:', e)
      }

      // CLS (Cumulative Layout Shift)
      let clsScore = 0
      const clsObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries()
        entries.forEach(entry => {
          if (!entry.hadRecentInput) {
            clsScore += entry.value
          }
        })
        this.recordMetric('CLS', clsScore)
      })
      
      try {
        clsObserver.observe({ entryTypes: ['layout-shift'] })
        this.observers.set('cls', clsObserver)
      } catch (e) {
        console.warn('[监控] CLS观察器不支持:', e)
      }
    }
  }

  // 导航时间监控
  initNavigationTiming() {
    window.addEventListener('load', () => {
      setTimeout(() => {
        const navigation = performance.getEntriesByType('navigation')[0]
        if (navigation) {
          this.recordMetric('page_load_time', navigation.loadEventEnd - navigation.fetchStart)
          this.recordMetric('dom_content_loaded', navigation.domContentLoadedEventEnd - navigation.fetchStart)
          this.recordMetric('first_paint', navigation.responseEnd - navigation.fetchStart)
        }
      }, 0)
    })
  }

  // 资源加载时间监控
  initResourceTiming() {
    if ('PerformanceObserver' in window) {
      const resourceObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries()
        entries.forEach(entry => {
          // 只记录关键资源
          if (entry.name.includes('.js') || entry.name.includes('.css') || entry.name.includes('/api/')) {
            this.recordMetric('resource_load_time', entry.duration, {
              resource: entry.name,
              type: entry.initiatorType
            })
          }
        })
      })
      
      try {
        resourceObserver.observe({ entryTypes: ['resource'] })
        this.observers.set('resource', resourceObserver)
      } catch (e) {
        console.warn('[监控] 资源观察器不支持:', e)
      }
    }
  }

  // 记录性能指标
  recordMetric(name, value, metadata = {}) {
    const metric = {
      name,
      value,
      timestamp: Date.now(),
      url: window.location.href,
      metadata
    }

    this.metrics.set(`${name}_${Date.now()}`, metric)
    
    if (MONITORING_CONFIG.debug) {
      console.log(`[性能监控] ${name}:`, value, metadata)
    }

    // 添加到事件队列
    queueEvent('performance', metric)

    // 检查阈值
    this.checkThresholds(name, value)
  }

  // 检查性能阈值
  checkThresholds(name, value) {
    const thresholds = {
      page_load_time: { warning: 3000, critical: 8000 },
      api_response_time: { warning: 1000, critical: 5000 },
      LCP: { warning: 2500, critical: 4000 },
      FID: { warning: 100, critical: 300 },
      CLS: { warning: 0.1, critical: 0.25 }
    }

    const threshold = thresholds[name]
    if (!threshold) return

    if (value > threshold.critical) {
      this.reportPerformanceIssue(name, value, 'critical')
    } else if (value > threshold.warning) {
      this.reportPerformanceIssue(name, value, 'warning')
    }
  }

  // 报告性能问题
  reportPerformanceIssue(metric, value, severity) {
    const message = `性能${severity === 'critical' ? '严重' : '警告'}: ${metric} = ${value}ms`
    
    if (severity === 'critical') {
      ElNotification.error({
        title: '性能警告',
        message,
        duration: 5000
      })
    } else if (MONITORING_CONFIG.debug) {
      ElMessage.warning(message)
    }

    // 记录性能问题事件
    queueEvent('performance_issue', {
      metric,
      value,
      severity,
      timestamp: Date.now(),
      url: window.location.href
    })
  }

  // 获取所有指标
  getAllMetrics() {
    return Object.fromEntries(this.metrics)
  }

  // 清理观察器
  cleanup() {
    this.observers.forEach(observer => observer.disconnect())
    this.observers.clear()
    this.metrics.clear()
  }
}

// 错误监控器
class ErrorMonitor {
  constructor() {
    this.errors = new Map()
    this.init()
  }

  init() {
    // 全局错误捕获
    window.addEventListener('error', this.handleError.bind(this))
    window.addEventListener('unhandledrejection', this.handleRejection.bind(this))
    
    // Vue错误处理
    if (window.Vue) {
      window.Vue.config.errorHandler = this.handleVueError.bind(this)
    }
  }

  // 处理JavaScript错误
  handleError(event) {
    const error = {
      type: 'javascript_error',
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      stack: event.error?.stack,
      timestamp: Date.now(),
      url: window.location.href,
      userAgent: navigator.userAgent
    }

    this.recordError(error)
  }

  // 处理Promise rejection
  handleRejection(event) {
    const error = {
      type: 'unhandled_rejection',
      message: event.reason?.message || String(event.reason),
      stack: event.reason?.stack,
      timestamp: Date.now(),
      url: window.location.href,
      userAgent: navigator.userAgent
    }

    this.recordError(error)
    event.preventDefault() // 阻止控制台错误输出
  }

  // 处理Vue错误
  handleVueError(err, vm, info) {
    const error = {
      type: 'vue_error',
      message: err.message,
      stack: err.stack,
      componentInfo: info,
      timestamp: Date.now(),
      url: window.location.href,
      userAgent: navigator.userAgent
    }

    this.recordError(error)
  }

  // 记录错误
  recordError(error) {
    // 过滤重复错误
    const errorKey = `${error.type}_${error.message}_${error.filename}_${error.lineno}`
    if (this.errors.has(errorKey)) {
      const existingError = this.errors.get(errorKey)
      existingError.count++
      existingError.lastOccurred = error.timestamp
      return
    }

    error.count = 1
    error.firstOccurred = error.timestamp
    error.lastOccurred = error.timestamp
    this.errors.set(errorKey, error)

    if (MONITORING_CONFIG.debug) {
      console.error('[错误监控]', error)
    }

    // 添加到事件队列
    queueEvent('error', error)

    // 显示用户友好的错误信息
    this.showUserFriendlyError(error)
  }

  // 显示用户友好的错误信息
  showUserFriendlyError(error) {
    // 过滤掉不需要显示给用户的错误
    const ignoredErrors = [
      'Script error',
      'ResizeObserver loop limit exceeded',
      'Non-Error promise rejection captured'
    ]

    if (ignoredErrors.some(ignored => error.message.includes(ignored))) {
      return
    }

    // 网络错误
    if (error.message.includes('NetworkError') || error.message.includes('fetch')) {
      ElMessage.error('网络连接异常，请检查网络状态')
      return
    }

    // API错误
    if (error.message.includes('API') || error.message.includes('axios')) {
      ElMessage.error('数据加载失败，请稍后重试')
      return
    }

    // 严重错误提示
    if (error.type === 'javascript_error') {
      ElNotification.error({
        title: '系统错误',
        message: '页面遇到了一些问题，我们已经记录并将尽快修复',
        duration: 8000
      })
    }
  }

  // 手动记录错误
  captureError(error, context = {}) {
    const errorInfo = {
      type: 'manual_error',
      message: error.message || String(error),
      stack: error.stack,
      context,
      timestamp: Date.now(),
      url: window.location.href,
      userAgent: navigator.userAgent
    }

    this.recordError(errorInfo)
  }

  // 获取所有错误
  getAllErrors() {
    return Object.fromEntries(this.errors)
  }

  // 清理错误记录
  cleanup() {
    this.errors.clear()
  }
}

// 用户行为监控器
class BehaviorMonitor {
  constructor() {
    this.actions = []
    this.session = {
      id: this.generateSessionId(),
      startTime: Date.now(),
      pageViews: 0,
      interactions: 0
    }
    this.init()
  }

  init() {
    // 页面访问记录
    this.recordPageView()
    
    // 点击事件监控
    document.addEventListener('click', this.handleClick.bind(this))
    
    // 表单交互监控
    document.addEventListener('input', this.handleInput.bind(this))
    
    // 路由变化监控（Vue Router）
    if (window.router) {
      window.router.afterEach(this.handleRouteChange.bind(this))
    }
  }

  // 生成会话ID
  generateSessionId() {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  // 记录页面访问
  recordPageView() {
    this.session.pageViews++
    const action = {
      type: 'page_view',
      url: window.location.href,
      title: document.title,
      timestamp: Date.now(),
      sessionId: this.session.id
    }

    this.recordAction(action)
  }

  // 处理点击事件
  handleClick(event) {
    // 只记录有意义的点击
    const target = event.target
    if (!target.closest('button, a, .el-button, .clickable')) {
      return
    }

    this.session.interactions++
    const action = {
      type: 'click',
      element: target.tagName,
      className: target.className,
      text: target.textContent?.slice(0, 50),
      timestamp: Date.now(),
      sessionId: this.session.id
    }

    this.recordAction(action)
  }

  // 处理输入事件
  handleInput(event) {
    const target = event.target
    const action = {
      type: 'input',
      element: target.tagName,
      inputType: target.type,
      name: target.name,
      timestamp: Date.now(),
      sessionId: this.session.id
    }

    this.recordAction(action)
  }

  // 处理路由变化
  handleRouteChange(to, from) {
    const action = {
      type: 'route_change',
      from: from.path,
      to: to.path,
      timestamp: Date.now(),
      sessionId: this.session.id
    }

    this.recordAction(action)
    this.recordPageView() // 新页面访问
  }

  // 记录用户行为
  recordAction(action) {
    this.actions.push(action)
    
    // 限制行为记录数量
    if (this.actions.length > 1000) {
      this.actions.shift()
    }

    if (MONITORING_CONFIG.debug) {
      console.log('[行为监控]', action)
    }

    // 采样后添加到事件队列
    if (Math.random() < 0.05) { // 5%采样率
      queueEvent('behavior', action)
    }
  }

  // 获取会话信息
  getSessionInfo() {
    return {
      ...this.session,
      duration: Date.now() - this.session.startTime,
      actionsCount: this.actions.length
    }
  }

  // 获取最近的行为
  getRecentActions(limit = 50) {
    return this.actions.slice(-limit)
  }
}

// 事件队列管理
function queueEvent(type, data) {
  if (!MONITORING_CONFIG.enabled) return

  const event = {
    type,
    data,
    timestamp: Date.now(),
    sessionId: behaviorMonitor.session.id
  }

  eventQueue.push(event)

  // 限制队列大小
  if (eventQueue.length > MONITORING_CONFIG.maxQueueSize) {
    eventQueue.shift()
  }

  // 批量上报
  scheduleFlush()
}

// 调度事件上报
function scheduleFlush() {
  if (flushTimer) return

  flushTimer = setTimeout(() => {
    flushEvents()
    flushTimer = null
  }, MONITORING_CONFIG.flushInterval)
}

// 上报事件
async function flushEvents() {
  if (eventQueue.length === 0) return

  const events = eventQueue.splice(0, 50) // 每次最多上报50个事件
  
  try {
    // 发送到后端
    await fetch('/api/monitoring/events', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        events,
        environment: import.meta.env.MODE,
        userAgent: navigator.userAgent,
        timestamp: Date.now()
      })
    })

    if (MONITORING_CONFIG.debug) {
      console.log(`[监控] 上报 ${events.length} 个事件`)
    }
  } catch (error) {
    console.error('[监控] 事件上报失败:', error)
    // 失败的事件重新放回队列
    eventQueue.unshift(...events)
  }
}

// Sentry集成（如果可用）
function initSentry() {
  if (window.Sentry && MONITORING_CONFIG.enabled) {
    window.Sentry.init({
      dsn: import.meta.env.VITE_SENTRY_DSN,
      environment: import.meta.env.MODE,
      sampleRate: MONITORING_CONFIG.sampleRate,
      beforeSend(event) {
        // 过滤敏感数据
        if (event.request?.headers) {
          delete event.request.headers['Authorization']
          delete event.request.headers['Cookie']
        }
        return event
      }
    })

    // 设置用户上下文
    window.Sentry.setContext('session', behaviorMonitor.getSessionInfo())
  }
}

// 初始化监控系统
const performanceMonitor = new PerformanceMonitor()
const errorMonitor = new ErrorMonitor()
const behaviorMonitor = new BehaviorMonitor()

// 在页面加载完成后初始化Sentry
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSentry)
} else {
  initSentry()
}

// 导出监控工具
export {
  performanceMonitor,
  errorMonitor,
  behaviorMonitor,
  queueEvent,
  flushEvents
}

// 全局监控对象
export const Monitoring = {
  // 手动记录错误
  captureError: errorMonitor.captureError.bind(errorMonitor),
  
  // 记录性能指标
  recordMetric: performanceMonitor.recordMetric.bind(performanceMonitor),
  
  // 记录用户行为
  recordAction: behaviorMonitor.recordAction.bind(behaviorMonitor),
  
  // 获取监控数据
  getMetrics: performanceMonitor.getAllMetrics.bind(performanceMonitor),
  getErrors: errorMonitor.getAllErrors.bind(errorMonitor),
  getSession: behaviorMonitor.getSessionInfo.bind(behaviorMonitor),
  
  // 清理监控器
  cleanup() {
    performanceMonitor.cleanup()
    errorMonitor.cleanup()
    if (flushTimer) {
      clearTimeout(flushTimer)
    }
    flushEvents() // 最后一次上报
  }
}

// 页面卸载时清理并上报最后的数据
window.addEventListener('beforeunload', () => {
  Monitoring.cleanup()
}) 