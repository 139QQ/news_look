import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'

/**
 * 全局消息提示管理器
 * 提供统一的用户反馈接口
 */
class MessageManager {
  constructor() {
    this.loadingInstance = null
    this.loadingCount = 0
  }

  /**
   * 成功消息
   * @param {string} message 消息内容
   * @param {Object} options 配置选项
   */
  success(message, options = {}) {
    return ElMessage.success({
      message,
      duration: 3000,
      showClose: true,
      ...options
    })
  }

  /**
   * 错误消息
   * @param {string} message 消息内容
   * @param {Object} options 配置选项
   */
  error(message, options = {}) {
    return ElMessage.error({
      message,
      duration: 5000,
      showClose: true,
      ...options
    })
  }

  /**
   * 警告消息
   * @param {string} message 消息内容
   * @param {Object} options 配置选项
   */
  warning(message, options = {}) {
    return ElMessage.warning({
      message,
      duration: 4000,
      showClose: true,
      ...options
    })
  }

  /**
   * 信息消息
   * @param {string} message 消息内容
   * @param {Object} options 配置选项
   */
  info(message, options = {}) {
    return ElMessage.info({
      message,
      duration: 3000,
      showClose: true,
      ...options
    })
  }

  /**
   * 操作成功通知
   * @param {string} title 标题
   * @param {string} message 消息内容
   * @param {Object} options 配置选项
   */
  notifySuccess(title, message = '', options = {}) {
    return ElNotification.success({
      title,
      message,
      duration: 4000,
      position: 'top-right',
      ...options
    })
  }

  /**
   * 操作失败通知
   * @param {string} title 标题
   * @param {string} message 消息内容
   * @param {Object} options 配置选项
   */
  notifyError(title, message = '', options = {}) {
    return ElNotification.error({
      title,
      message,
      duration: 6000,
      position: 'top-right',
      ...options
    })
  }

  /**
   * 操作警告通知
   * @param {string} title 标题
   * @param {string} message 消息内容
   * @param {Object} options 配置选项
   */
  notifyWarning(title, message = '', options = {}) {
    return ElNotification.warning({
      title,
      message,
      duration: 5000,
      position: 'top-right',
      ...options
    })
  }

  /**
   * 信息通知
   * @param {string} title 标题
   * @param {string} message 消息内容
   * @param {Object} options 配置选项
   */
  notifyInfo(title, message = '', options = {}) {
    return ElNotification.info({
      title,
      message,
      duration: 4000,
      position: 'top-right',
      ...options
    })
  }

  /**
   * 确认对话框
   * @param {string} title 标题
   * @param {string} content 内容
   * @param {Object} options 配置选项
   */
  async confirm(title, content = '', options = {}) {
    try {
      await ElMessageBox.confirm(content, title, {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: false,
        ...options
      })
      return true
    } catch {
      return false
    }
  }

  /**
   * 删除确认对话框
   * @param {string} itemName 删除项名称
   * @param {Object} options 配置选项
   */
  async confirmDelete(itemName = '该项', options = {}) {
    return this.confirm(
      '删除确认',
      `确定要删除${itemName}吗？此操作不可撤销。`,
      {
        confirmButtonText: '删除',
        confirmButtonClass: 'el-button--danger',
        type: 'warning',
        ...options
      }
    )
  }

  /**
   * 操作确认对话框（带倒计时）
   * @param {string} title 标题
   * @param {string} content 内容
   * @param {string} action 操作名称
   * @param {number} countdown 倒计时秒数
   */
  async confirmWithCountdown(title, content, action = '执行', countdown = 5) {
    let timer = null
    let currentCountdown = countdown

    try {
      const result = await ElMessageBox.confirm(content, title, {
        confirmButtonText: `${action} (${currentCountdown})`,
        cancelButtonText: '取消',
        type: 'warning',
        beforeClose: (action, instance, done) => {
          if (timer) {
            clearInterval(timer)
          }
          done()
        }
      })

      // 启动倒计时
      timer = setInterval(() => {
        currentCountdown--
        if (currentCountdown > 0) {
          document.querySelector('.el-message-box__btns .el-button--primary span').textContent = 
            `${action} (${currentCountdown})`
        } else {
          clearInterval(timer)
          document.querySelector('.el-message-box__btns .el-button--primary span').textContent = action
          document.querySelector('.el-message-box__btns .el-button--primary').disabled = false
        }
      }, 1000)

      // 初始禁用确认按钮
      setTimeout(() => {
        const confirmBtn = document.querySelector('.el-message-box__btns .el-button--primary')
        if (confirmBtn) {
          confirmBtn.disabled = true
        }
      }, 100)

      return true
    } catch {
      if (timer) {
        clearInterval(timer)
      }
      return false
    }
  }

  /**
   * 显示全局加载状态
   * @param {string} text 加载文本
   */
  showLoading(text = '加载中...') {
    this.loadingCount++
    
    if (!this.loadingInstance && this.loadingCount === 1) {
      this.loadingInstance = ElLoading.service({
        lock: true,
        text,
        background: 'rgba(0, 0, 0, 0.7)',
        spinner: 'el-icon-loading'
      })
    }
  }

  /**
   * 隐藏全局加载状态
   */
  hideLoading() {
    this.loadingCount = Math.max(0, this.loadingCount - 1)
    
    if (this.loadingInstance && this.loadingCount === 0) {
      this.loadingInstance.close()
      this.loadingInstance = null
    }
  }

  /**
   * 操作反馈包装器
   * 自动处理加载状态和结果提示
   * @param {Function} asyncFn 异步操作函数
   * @param {Object} options 配置选项
   */
  async withFeedback(asyncFn, options = {}) {
    const {
      loadingText = '操作中...',
      successTitle = '操作成功',
      successMessage = '',
      errorTitle = '操作失败',
      showLoading = true,
      showSuccess = true,
      showError = true
    } = options

    try {
      if (showLoading) {
        this.showLoading(loadingText)
      }

      const result = await asyncFn()

      if (showSuccess) {
        if (successMessage) {
          this.notifySuccess(successTitle, successMessage)
        } else {
          this.success(successTitle)
        }
      }

      return result
    } catch (error) {
      console.error('操作失败:', error)
      
      if (showError) {
        const errorMessage = this.getErrorMessage(error)
        this.notifyError(errorTitle, errorMessage)
      }
      
      throw error
    } finally {
      if (showLoading) {
        this.hideLoading()
      }
    }
  }

  /**
   * 提取错误信息
   * @param {Error|Object} error 错误对象
   * @returns {string} 错误信息
   */
  getErrorMessage(error) {
    if (typeof error === 'string') {
      return error
    }
    
    if (error?.response?.data?.message) {
      return error.response.data.message
    }
    
    if (error?.message) {
      return error.message
    }
    
    if (error?.response?.status) {
      const statusMessages = {
        400: '请求参数错误',
        401: '未授权访问',
        403: '权限不足',
        404: '资源不存在',
        500: '服务器内部错误',
        502: '网关错误',
        503: '服务不可用'
      }
      return statusMessages[error.response.status] || `HTTP错误 ${error.response.status}`
    }
    
    return '操作失败，请稍后重试'
  }

  /**
   * 批量操作反馈
   * @param {Array} operations 操作数组
   * @param {Object} options 配置选项
   */
  async batchFeedback(operations, options = {}) {
    const {
      loadingText = '批量操作中...',
      successTitle = '批量操作完成',
      errorTitle = '批量操作部分失败'
    } = options

    this.showLoading(loadingText)
    
    const results = {
      success: [],
      failed: []
    }

    try {
      for (let i = 0; i < operations.length; i++) {
        const operation = operations[i]
        try {
          const result = await operation()
          results.success.push({ index: i, result })
        } catch (error) {
          results.failed.push({ index: i, error })
        }
      }

      if (results.failed.length === 0) {
        this.notifySuccess(successTitle, `成功处理 ${results.success.length} 项`)
      } else if (results.success.length === 0) {
        this.notifyError('批量操作失败', `${results.failed.length} 项操作失败`)
      } else {
        this.notifyWarning(
          errorTitle, 
          `成功：${results.success.length} 项，失败：${results.failed.length} 项`
        )
      }

      return results
    } finally {
      this.hideLoading()
    }
  }
}

// 创建全局实例
const message = new MessageManager()

export default message 