// 🔄 全局加载状态管理工具
// =========================

import { ElLoading } from 'element-plus'

// 加载实例存储
let loadingInstance = null
let loadingCount = 0

/**
 * 显示全局加载状态
 * @param {Object} options - 加载配置选项
 * @param {String} options.text - 加载提示文本
 * @param {String} options.background - 背景色
 * @param {String} options.customClass - 自定义类名
 */
export function showLoading(options = {}) {
  loadingCount++
  
  if (loadingInstance) {
    return loadingInstance
  }
  
  const defaultOptions = {
    lock: true,
    text: '加载中...',
    background: 'rgba(0, 0, 0, 0.05)',
    customClass: 'custom-loading'
  }
  
  const finalOptions = { ...defaultOptions, ...options }
  
  loadingInstance = ElLoading.service(finalOptions)
  
  return loadingInstance
}

/**
 * 隐藏全局加载状态
 */
export function hideLoading() {
  if (loadingCount > 0) {
    loadingCount--
  }
  
  if (loadingCount === 0 && loadingInstance) {
    loadingInstance.close()
    loadingInstance = null
  }
}

/**
 * 强制隐藏加载状态
 */
export function forceHideLoading() {
  loadingCount = 0
  if (loadingInstance) {
    loadingInstance.close()
    loadingInstance = null
  }
}

/**
 * 显示页面加载状态
 */
export function showPageLoading() {
  return showLoading({
    text: '页面加载中...',
    background: 'rgba(255, 255, 255, 0.9)',
    customClass: 'page-loading'
  })
}

/**
 * 显示数据加载状态
 */
export function showDataLoading() {
  return showLoading({
    text: '数据加载中...',
    background: 'rgba(0, 0, 0, 0.1)',
    customClass: 'data-loading'
  })
}

/**
 * 显示提交加载状态
 */
export function showSubmitLoading() {
  return showLoading({
    text: '提交中...',
    background: 'rgba(64, 158, 255, 0.1)',
    customClass: 'submit-loading'
  })
}

/**
 * 显示删除加载状态
 */
export function showDeleteLoading() {
  return showLoading({
    text: '删除中...',
    background: 'rgba(245, 108, 108, 0.1)',
    customClass: 'delete-loading'
  })
}

/**
 * 异步函数加载包装器
 * @param {Function} asyncFn - 异步函数
 * @param {Object} loadingOptions - 加载配置选项
 * @returns {Function} 包装后的异步函数
 */
export function withLoading(asyncFn, loadingOptions = {}) {
  return async function(...args) {
    showLoading(loadingOptions)
    try {
      const result = await asyncFn.apply(this, args)
      return result
    } finally {
      hideLoading()
    }
  }
}

/**
 * Promise 加载包装器
 * @param {Promise} promise - Promise 对象
 * @param {Object} loadingOptions - 加载配置选项
 * @returns {Promise} 包装后的 Promise
 */
export function withPromiseLoading(promise, loadingOptions = {}) {
  showLoading(loadingOptions)
  
  return promise.finally(() => {
    hideLoading()
  })
}

/**
 * 区域加载状态
 * @param {String|Element} target - 目标元素选择器或元素
 * @param {Object} options - 加载配置选项
 * @returns {Object} 加载实例
 */
export function showRegionLoading(target, options = {}) {
  const defaultOptions = {
    target,
    text: '加载中...',
    background: 'rgba(255, 255, 255, 0.8)',
    customClass: 'region-loading'
  }
  
  const finalOptions = { ...defaultOptions, ...options }
  
  return ElLoading.service(finalOptions)
}

/**
 * 表格加载状态
 * @param {String|Element} target - 表格元素选择器或元素
 * @returns {Object} 加载实例
 */
export function showTableLoading(target) {
  return showRegionLoading(target, {
    text: '数据加载中...',
    background: 'rgba(255, 255, 255, 0.9)',
    customClass: 'table-loading'
  })
}

/**
 * 卡片加载状态
 * @param {String|Element} target - 卡片元素选择器或元素
 * @returns {Object} 加载实例
 */
export function showCardLoading(target) {
  return showRegionLoading(target, {
    text: '加载中...',
    background: 'rgba(245, 247, 250, 0.9)',
    customClass: 'card-loading'
  })
}

/**
 * 按钮加载状态管理
 */
export class ButtonLoadingManager {
  constructor() {
    this.loadingButtons = new Map()
  }
  
  /**
   * 设置按钮加载状态
   * @param {String} buttonId - 按钮ID
   * @param {Boolean} loading - 是否加载中
   */
  setButtonLoading(buttonId, loading = true) {
    this.loadingButtons.set(buttonId, loading)
  }
  
  /**
   * 获取按钮加载状态
   * @param {String} buttonId - 按钮ID
   * @returns {Boolean} 是否加载中
   */
  getButtonLoading(buttonId) {
    return this.loadingButtons.get(buttonId) || false
  }
  
  /**
   * 清除按钮加载状态
   * @param {String} buttonId - 按钮ID
   */
  clearButtonLoading(buttonId) {
    this.loadingButtons.delete(buttonId)
  }
  
  /**
   * 清除所有按钮加载状态
   */
  clearAllLoading() {
    this.loadingButtons.clear()
  }
}

// 导出按钮加载管理器实例
export const buttonLoadingManager = new ButtonLoadingManager()

/**
 * 获取当前加载状态
 * @returns {Object} 当前加载状态信息
 */
export function getLoadingState() {
  return {
    isLoading: loadingInstance !== null,
    loadingCount,
    instance: loadingInstance
  }
}

// 默认导出
export default {
  showLoading,
  hideLoading,
  forceHideLoading,
  showPageLoading,
  showDataLoading,
  showSubmitLoading,
  showDeleteLoading,
  withLoading,
  withPromiseLoading,
  showRegionLoading,
  showTableLoading,
  showCardLoading,
  buttonLoadingManager,
  getLoadingState
} 