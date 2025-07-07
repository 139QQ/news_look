/**
 * 前端心跳检测系统
 * 提供服务器连接状态监控和自动重连机制
 */

import { ref, computed } from 'vue'
import axios from 'axios'

// 心跳状态管理
const heartbeatState = ref({
  isConnected: false,
  lastHeartbeat: null,
  consecutiveFailures: 0,
  totalHeartbeats: 0,
  totalFailures: 0,
  connectionStartTime: null,
  currentLatency: 0,
  averageLatency: 0,
  maxLatency: 0,
  minLatency: Infinity
})

// 心跳配置
const heartbeatConfig = ref({
  interval: 5000,           // 心跳间隔(毫秒)
  timeout: 3000,           // 超时时间(毫秒)
  maxFailures: 3,          // 最大连续失败次数
  retryInterval: 10000,    // 重试间隔(毫秒)
  enabled: true,           // 是否启用心跳
  endpoints: [             // 心跳检测端点
    '/api/health',
    '/db/health'
  ]
})

// 心跳事件回调
const heartbeatCallbacks = {
  onConnected: [],
  onDisconnected: [],
  onLatencyChange: [],
  onError: []
}

let heartbeatTimer = null
let retryTimer = null

/**
 * 心跳检测类
 */
class HeartbeatMonitor {
  constructor() {
    this.isRunning = false
    this.latencyHistory = []
    this.maxLatencyHistory = 100 // 保留最近100次延迟记录
  }

  /**
   * 启动心跳检测
   */
  start() {
    if (this.isRunning) {
      console.warn('心跳检测已在运行')
      return
    }

    console.log('启动心跳检测系统')
    this.isRunning = true
    heartbeatState.value.connectionStartTime = new Date()
    this.scheduleNextHeartbeat()
  }

  /**
   * 停止心跳检测
   */
  stop() {
    console.log('停止心跳检测系统')
    this.isRunning = false
    
    if (heartbeatTimer) {
      clearTimeout(heartbeatTimer)
      heartbeatTimer = null
    }

    if (retryTimer) {
      clearTimeout(retryTimer)
      retryTimer = null
    }
  }

  /**
   * 调度下一次心跳
   */
  scheduleNextHeartbeat() {
    if (!this.isRunning || !heartbeatConfig.value.enabled) {
      return
    }

    heartbeatTimer = setTimeout(() => {
      this.performHeartbeat()
    }, heartbeatConfig.value.interval)
  }

  /**
   * 执行心跳检测
   */
  async performHeartbeat() {
    if (!this.isRunning) {
      return
    }

    const startTime = performance.now()
    
    try {
      // 选择一个端点进行心跳检测
      const endpoint = this.selectHeartbeatEndpoint()
      
      // 发送心跳请求
      const response = await axios.get(endpoint, {
        timeout: heartbeatConfig.value.timeout,
        headers: {
          'X-Heartbeat': 'true'
        }
      })

      const endTime = performance.now()
      const latency = Math.round(endTime - startTime)

      // 处理成功响应
      this.handleHeartbeatSuccess(latency, response.data)

    } catch (error) {
      const endTime = performance.now()
      const latency = Math.round(endTime - startTime)
      
      // 处理失败响应
      this.handleHeartbeatFailure(error, latency)
    }

    // 调度下一次心跳
    this.scheduleNextHeartbeat()
  }

  /**
   * 选择心跳检测端点
   */
  selectHeartbeatEndpoint() {
    const endpoints = heartbeatConfig.value.endpoints
    const index = heartbeatState.value.totalHeartbeats % endpoints.length
    return endpoints[index]
  }

  /**
   * 处理心跳成功
   */
  handleHeartbeatSuccess(latency, responseData) {
    const wasDisconnected = !heartbeatState.value.isConnected

    // 更新状态
    heartbeatState.value.isConnected = true
    heartbeatState.value.lastHeartbeat = new Date()
    heartbeatState.value.consecutiveFailures = 0
    heartbeatState.value.totalHeartbeats++
    heartbeatState.value.currentLatency = latency

    // 更新延迟统计
    this.updateLatencyStats(latency)

    // 如果之前断开连接，现在重新连接了
    if (wasDisconnected) {
      console.log('🟢 服务器连接已恢复')
      this.triggerCallbacks('onConnected', {
        latency,
        responseData,
        recoveryTime: new Date() - heartbeatState.value.connectionStartTime
      })
    }

    // 触发延迟变化回调
    this.triggerCallbacks('onLatencyChange', {
      current: latency,
      average: heartbeatState.value.averageLatency
    })

    console.debug(`💓 心跳正常 - 延迟: ${latency}ms`)
  }

  /**
   * 处理心跳失败
   */
  handleHeartbeatFailure(error, latency) {
    const wasConnected = heartbeatState.value.isConnected

    // 更新状态
    heartbeatState.value.consecutiveFailures++
    heartbeatState.value.totalFailures++

    // 判断是否应该标记为断开连接
    if (heartbeatState.value.consecutiveFailures >= heartbeatConfig.value.maxFailures) {
      heartbeatState.value.isConnected = false

      if (wasConnected) {
        console.warn('🔴 服务器连接已断开')
        this.triggerCallbacks('onDisconnected', {
          error,
          consecutiveFailures: heartbeatState.value.consecutiveFailures
        })
      }
    }

    // 触发错误回调
    this.triggerCallbacks('onError', {
      error,
      latency,
      consecutiveFailures: heartbeatState.value.consecutiveFailures
    })

    console.warn(`💔 心跳失败 - 连续失败: ${heartbeatState.value.consecutiveFailures}次`, error)
  }

  /**
   * 更新延迟统计
   */
  updateLatencyStats(latency) {
    // 添加到历史记录
    this.latencyHistory.push(latency)
    if (this.latencyHistory.length > this.maxLatencyHistory) {
      this.latencyHistory.shift()
    }

    // 计算统计数据
    const sum = this.latencyHistory.reduce((acc, val) => acc + val, 0)
    heartbeatState.value.averageLatency = Math.round(sum / this.latencyHistory.length)
    heartbeatState.value.maxLatency = Math.max(heartbeatState.value.maxLatency, latency)
    
    if (latency < heartbeatState.value.minLatency) {
      heartbeatState.value.minLatency = latency
    }
  }

  /**
   * 触发回调函数
   */
  triggerCallbacks(event, data) {
    const callbacks = heartbeatCallbacks[event] || []
    callbacks.forEach(callback => {
      try {
        callback(data)
      } catch (error) {
        console.error(`心跳回调执行失败[${event}]:`, error)
      }
    })
  }

  /**
   * 更新配置
   */
  updateConfig(newConfig) {
    Object.assign(heartbeatConfig.value, newConfig)
    console.log('心跳配置已更新:', heartbeatConfig.value)
  }

  /**
   * 获取连接质量
   */
  getConnectionQuality() {
    if (!heartbeatState.value.isConnected) {
      return 'disconnected'
    }

    const latency = heartbeatState.value.currentLatency
    if (latency < 100) return 'excellent'
    if (latency < 300) return 'good'
    if (latency < 1000) return 'fair'
    return 'poor'
  }

  /**
   * 获取连接统计
   */
  getStats() {
    const uptime = heartbeatState.value.connectionStartTime 
      ? new Date() - heartbeatState.value.connectionStartTime 
      : 0

    const successRate = heartbeatState.value.totalHeartbeats > 0 
      ? ((heartbeatState.value.totalHeartbeats - heartbeatState.value.totalFailures) / heartbeatState.value.totalHeartbeats * 100).toFixed(2)
      : 0

    return {
      ...heartbeatState.value,
      uptime: Math.floor(uptime / 1000), // 秒
      successRate: parseFloat(successRate),
      connectionQuality: this.getConnectionQuality(),
      latencyHistory: [...this.latencyHistory]
    }
  }
}

// 创建全局心跳监控实例
const heartbeatMonitor = new HeartbeatMonitor()

/**
 * 注册心跳事件回调
 */
export function onHeartbeatConnected(callback) {
  heartbeatCallbacks.onConnected.push(callback)
}

export function onHeartbeatDisconnected(callback) {
  heartbeatCallbacks.onDisconnected.push(callback)
}

export function onHeartbeatLatencyChange(callback) {
  heartbeatCallbacks.onLatencyChange.push(callback)
}

export function onHeartbeatError(callback) {
  heartbeatCallbacks.onError.push(callback)
}

/**
 * 移除心跳事件回调
 */
export function removeHeartbeatCallback(event, callback) {
  const callbacks = heartbeatCallbacks[event]
  if (callbacks) {
    const index = callbacks.indexOf(callback)
    if (index !== -1) {
      callbacks.splice(index, 1)
    }
  }
}

/**
 * 导出心跳监控接口
 */
export const useHeartbeat = () => {
  // 响应式状态
  const isConnected = computed(() => heartbeatState.value.isConnected)
  const currentLatency = computed(() => heartbeatState.value.currentLatency)
  const averageLatency = computed(() => heartbeatState.value.averageLatency)
  const connectionQuality = computed(() => heartbeatMonitor.getConnectionQuality())
  const consecutiveFailures = computed(() => heartbeatState.value.consecutiveFailures)

  // 控制方法
  const start = () => heartbeatMonitor.start()
  const stop = () => heartbeatMonitor.stop()
  const getStats = () => heartbeatMonitor.getStats()
  const updateConfig = (config) => heartbeatMonitor.updateConfig(config)

  return {
    // 状态
    isConnected,
    currentLatency,
    averageLatency,
    connectionQuality,
    consecutiveFailures,
    
    // 方法
    start,
    stop,
    getStats,
    updateConfig,
    
    // 原始状态（用于详细信息）
    state: heartbeatState,
    config: heartbeatConfig
  }
}

// 自动启动心跳检测（在生产环境）
if (import.meta.env.PROD) {
  // 延迟启动，确保应用初始化完成
  setTimeout(() => {
    heartbeatMonitor.start()
  }, 1000)
}

export default heartbeatMonitor 