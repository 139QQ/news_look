/**
 * 指数退避重试机制
 * 提供智能重试、网络错误处理和优雅降级功能
 */

import { ref } from 'vue'

// 重试状态管理
const retryState = ref({
  activeRetries: new Map(),
  totalRetries: 0,
  successfulRetries: 0,
  failedRetries: 0
})

/**
 * 指数退避重试函数
 * @param {Function} fetchFunction - 要重试的异步函数
 * @param {Object} options - 重试配置选项
 * @returns {Promise} - 返回Promise结果
 */
export async function fetchWithRetry(fetchFunction, options = {}) {
  const config = {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 30000,
    backoffFactor: 2,
    jitter: true,
    retryCondition: (error) => isRetriableError(error),
    onRetry: null,
    onFinalFailure: null,
    abortSignal: null,
    timeout: 10000,
    ...options
  }

  const requestId = generateRequestId()
  let lastError = null

  // 记录重试开始
  retryState.value.activeRetries.set(requestId, {
    attempts: 0,
    startTime: Date.now(),
    function: fetchFunction.name || 'anonymous'
  })

  try {
    // 首次尝试
    const result = await executeWithTimeout(fetchFunction, config.timeout, config.abortSignal)
    
    // 成功时清理状态
    retryState.value.activeRetries.delete(requestId)
    return result

  } catch (error) {
    lastError = error
    
    // 检查是否应该重试
    if (!config.retryCondition(error)) {
      retryState.value.activeRetries.delete(requestId)
      retryState.value.failedRetries++
      throw error
    }
  }

  // 开始重试循环
  for (let attempt = 1; attempt <= config.maxRetries; attempt++) {
    try {
      // 更新重试状态
      const retryInfo = retryState.value.activeRetries.get(requestId)
      if (retryInfo) {
        retryInfo.attempts = attempt
      }

      // 计算延迟时间
      const delay = calculateDelay(attempt, config)
      
      // 触发重试回调
      if (config.onRetry) {
        config.onRetry(lastError, attempt, delay)
      }

      console.warn(`🔄 重试第 ${attempt}/${config.maxRetries} 次，延迟 ${delay}ms`, lastError)

      // 等待延迟
      await sleep(delay)

      // 检查是否被取消
      if (config.abortSignal?.aborted) {
        throw new Error('Request aborted')
      }

      // 执行重试
      const result = await executeWithTimeout(fetchFunction, config.timeout, config.abortSignal)
      
      // 成功时清理状态并记录
      retryState.value.activeRetries.delete(requestId)
      retryState.value.totalRetries++
      retryState.value.successfulRetries++
      
      console.log(`✅ 重试成功 (第 ${attempt} 次尝试)`)
      return result

    } catch (error) {
      lastError = error
      
      // 检查是否应该继续重试
      if (!config.retryCondition(error)) {
        break
      }
    }
  }

  // 所有重试都失败了
  retryState.value.activeRetries.delete(requestId)
  retryState.value.totalRetries++
  retryState.value.failedRetries++

  // 触发最终失败回调
  if (config.onFinalFailure) {
    config.onFinalFailure(lastError, config.maxRetries)
  }

  console.error(`❌ 重试失败，已达到最大重试次数 (${config.maxRetries})`, lastError)
  throw lastError
}

/**
 * 计算延迟时间（指数退避 + 抖动）
 */
function calculateDelay(attempt, config) {
  const exponentialDelay = Math.min(
    config.baseDelay * Math.pow(config.backoffFactor, attempt - 1),
    config.maxDelay
  )

  if (config.jitter) {
    // 添加 ±25% 的随机抖动
    const jitterRange = exponentialDelay * 0.25
    const jitter = (Math.random() - 0.5) * 2 * jitterRange
    return Math.max(0, Math.round(exponentialDelay + jitter))
  }

  return exponentialDelay
}

/**
 * 判断错误是否可重试
 */
function isRetriableError(error) {
  // 网络错误
  if (error.code === 'NETWORK_ERROR' || error.message.includes('Network Error')) {
    return true
  }

  // 超时错误
  if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
    return true
  }

  // HTTP状态码错误
  if (error.response) {
    const status = error.response.status
    // 5xx 服务器错误通常可以重试
    if (status >= 500 && status < 600) {
      return true
    }
    // 429 Too Many Requests 可以重试
    if (status === 429) {
      return true
    }
    // 502, 503, 504 网关错误可以重试
    if ([502, 503, 504].includes(status)) {
      return true
    }
  }

  // 其他错误通常不重试（4xx客户端错误）
  return false
}

/**
 * 带超时的执行函数
 */
async function executeWithTimeout(fn, timeout, abortSignal) {
  return new Promise(async (resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(new Error(`Request timeout after ${timeout}ms`))
    }, timeout)

    // 处理abort signal
    const abortHandler = () => {
      clearTimeout(timeoutId)
      reject(new Error('Request aborted'))
    }

    if (abortSignal) {
      if (abortSignal.aborted) {
        clearTimeout(timeoutId)
        reject(new Error('Request aborted'))
        return
      }
      abortSignal.addEventListener('abort', abortHandler)
    }

    try {
      const result = await fn()
      clearTimeout(timeoutId)
      if (abortSignal) {
        abortSignal.removeEventListener('abort', abortHandler)
      }
      resolve(result)
    } catch (error) {
      clearTimeout(timeoutId)
      if (abortSignal) {
        abortSignal.removeEventListener('abort', abortHandler)
      }
      reject(error)
    }
  })
}

/**
 * 延迟函数
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * 生成请求ID
 */
function generateRequestId() {
  return Math.random().toString(36).substring(2, 15)
}

/**
 * 创建可中断的重试控制器
 */
export class RetryController {
  constructor() {
    this.abortController = new AbortController()
    this.isAborted = false
  }

  abort() {
    this.isAborted = true
    this.abortController.abort()
  }

  get signal() {
    return this.abortController.signal
  }
}

/**
 * 针对特定错误类型的重试策略
 */
export const retryStrategies = {
  // 网络错误重试策略
  network: {
    maxRetries: 5,
    baseDelay: 1000,
    maxDelay: 10000,
    backoffFactor: 2,
    retryCondition: (error) => {
      return error.code === 'NETWORK_ERROR' || 
             error.message.includes('Network Error') ||
             error.message.includes('Failed to fetch')
    }
  },

  // 服务器错误重试策略
  server: {
    maxRetries: 3,
    baseDelay: 2000,
    maxDelay: 30000,
    backoffFactor: 2,
    retryCondition: (error) => {
      if (error.response) {
        const status = error.response.status
        return status >= 500 || status === 429
      }
      return false
    }
  },

  // 超时错误重试策略
  timeout: {
    maxRetries: 2,
    baseDelay: 1000,
    maxDelay: 5000,
    backoffFactor: 1.5,
    timeout: 15000, // 增加超时时间
    retryCondition: (error) => {
      return error.code === 'ECONNABORTED' || 
             error.message.includes('timeout')
    }
  },

  // 快速重试策略（用于轻量级操作）
  fast: {
    maxRetries: 3,
    baseDelay: 500,
    maxDelay: 2000,
    backoffFactor: 1.5,
    jitter: false
  },

  // 保守重试策略（用于重要操作）
  conservative: {
    maxRetries: 2,
    baseDelay: 5000,
    maxDelay: 30000,
    backoffFactor: 2,
    jitter: true
  }
}

/**
 * 便捷的重试方法
 */
export function retryNetworkRequest(fetchFunction, options = {}) {
  return fetchWithRetry(fetchFunction, {
    ...retryStrategies.network,
    ...options
  })
}

export function retryServerRequest(fetchFunction, options = {}) {
  return fetchWithRetry(fetchFunction, {
    ...retryStrategies.server,
    ...options
  })
}

export function retryTimeoutRequest(fetchFunction, options = {}) {
  return fetchWithRetry(fetchFunction, {
    ...retryStrategies.timeout,
    ...options
  })
}

/**
 * 批量重试请求
 */
export async function retryBatch(requests, options = {}) {
  const config = {
    concurrency: 3,
    strategy: 'network',
    failFast: false,
    ...options
  }

  const strategy = retryStrategies[config.strategy] || retryStrategies.network
  const results = []
  const errors = []

  // 分批处理请求
  for (let i = 0; i < requests.length; i += config.concurrency) {
    const batch = requests.slice(i, i + config.concurrency)
    
    const batchPromises = batch.map(async (request, index) => {
      try {
        const result = await fetchWithRetry(request, strategy)
        return { index: i + index, result, success: true }
      } catch (error) {
        const errorResult = { index: i + index, error, success: false }
        
        if (config.failFast) {
          throw errorResult
        }
        
        errors.push(errorResult)
        return errorResult
      }
    })

    const batchResults = await Promise.all(batchPromises)
    results.push(...batchResults)
  }

  return {
    results: results.filter(r => r.success),
    errors: results.filter(r => !r.success),
    totalCount: requests.length,
    successCount: results.filter(r => r.success).length,
    errorCount: results.filter(r => !r.success).length
  }
}

/**
 * 获取重试统计信息
 */
export function getRetryStats() {
  return {
    ...retryState.value,
    activeRetryCount: retryState.value.activeRetries.size,
    successRate: retryState.value.totalRetries > 0 
      ? (retryState.value.successfulRetries / retryState.value.totalRetries * 100).toFixed(2)
      : 0
  }
}

/**
 * 清除重试统计
 */
export function clearRetryStats() {
  retryState.value.totalRetries = 0
  retryState.value.successfulRetries = 0
  retryState.value.failedRetries = 0
}

/**
 * 导出重试状态（用于Vue组件）
 */
export const useRetry = () => {
  return {
    stats: retryState,
    fetchWithRetry,
    retryNetworkRequest,
    retryServerRequest,
    retryTimeoutRequest,
    retryBatch,
    getRetryStats,
    clearRetryStats,
    RetryController
  }
} 