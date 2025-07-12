/**
 * WebSocket 连接管理器
 * 用于实时状态更新和服务器推送
 */
class WebSocketManager {
  constructor() {
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectInterval = 3000
    this.listeners = new Map()
    this.isConnecting = false
    this.heartbeatTimer = null
    this.messageQueue = []
  }

  /**
   * 连接WebSocket
   * @param {string} url WebSocket地址
   */
  connect(url = 'ws://localhost:5000/ws') {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return
    }

    this.isConnecting = true

    try {
      this.ws = new WebSocket(url)
      
      this.ws.onopen = this.handleOpen.bind(this)
      this.ws.onmessage = this.handleMessage.bind(this)
      this.ws.onclose = this.handleClose.bind(this)
      this.ws.onerror = this.handleError.bind(this)

    } catch (error) {
      console.error('WebSocket连接失败:', error)
      this.isConnecting = false
      this.scheduleReconnect()
    }
  }

  /**
   * 连接成功处理
   */
  handleOpen() {
    console.log('✅ WebSocket连接已建立')
    this.isConnecting = false
    this.reconnectAttempts = 0
    
    // 启动心跳检测
    this.startHeartbeat()
    
    // 发送队列中的消息
    this.processMessageQueue()
    
    // 触发连接事件
    this.emit('connected')
  }

  /**
   * 消息处理
   */
  handleMessage(event) {
    try {
      const data = JSON.parse(event.data)
      
      // 处理心跳响应
      if (data.type === 'pong') {
        return
      }
      
      // 触发对应的监听器
      this.emit(data.type, data.payload)
      
    } catch (error) {
      console.error('WebSocket消息解析失败:', error)
    }
  }

  /**
   * 连接关闭处理
   */
  handleClose(event) {
    console.log('WebSocket连接已关闭:', event.code, event.reason)
    this.isConnecting = false
    this.stopHeartbeat()
    
    // 触发断开连接事件
    this.emit('disconnected', { code: event.code, reason: event.reason })
    
    // 自动重连
    if (event.code !== 1000) { // 非正常关闭
      this.scheduleReconnect()
    }
  }

  /**
   * 错误处理
   */
  handleError(error) {
    console.error('WebSocket错误:', error)
    this.isConnecting = false
    this.emit('error', error)
  }

  /**
   * 启动心跳检测
   */
  startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000) // 30秒心跳
  }

  /**
   * 停止心跳检测
   */
  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 安排重连
   */
  scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('WebSocket重连次数已达上限，停止重连')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1)
    
    console.log(`WebSocket将在${delay}ms后尝试第${this.reconnectAttempts}次重连`)
    
    setTimeout(() => {
      this.connect()
    }, delay)
  }

  /**
   * 处理消息队列
   */
  processMessageQueue() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift()
      this.send(message)
    }
  }

  /**
   * 发送消息
   * @param {Object} message 消息对象
   */
  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      // 添加到队列等待连接恢复
      this.messageQueue.push(message)
    }
  }

  /**
   * 添加事件监听器
   * @param {string} event 事件名称
   * @param {Function} callback 回调函数
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)
  }

  /**
   * 移除事件监听器
   * @param {string} event 事件名称
   * @param {Function} callback 回调函数
   */
  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event)
      const index = callbacks.indexOf(callback)
      if (index !== -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  /**
   * 触发事件
   * @param {string} event 事件名称
   * @param {*} data 事件数据
   */
  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`WebSocket事件监听器错误 (${event}):`, error)
        }
      })
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.stopHeartbeat()
    if (this.ws) {
      this.ws.close(1000, '主动断开连接')
      this.ws = null
    }
  }

  /**
   * 获取连接状态
   */
  getStatus() {
    if (!this.ws) return 'disconnected'
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'connected'
      case WebSocket.CLOSING:
        return 'closing'
      case WebSocket.CLOSED:
        return 'disconnected'
      default:
        return 'unknown'
    }
  }
}

// 创建全局实例
const wsManager = new WebSocketManager()

export default wsManager 