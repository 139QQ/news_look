import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

// 操作历史栈
class ActionHistory {
  constructor(maxSize = 50) {
    this.undoStack = []
    this.redoStack = []
    this.maxSize = maxSize
  }

  // 添加新操作
  push(action) {
    // 清空重做栈
    this.redoStack = []
    
    // 添加到撤销栈
    this.undoStack.push(action)
    
    // 限制栈大小
    if (this.undoStack.length > this.maxSize) {
      this.undoStack.shift()
    }
  }

  // 撤销操作
  undo() {
    if (this.undoStack.length === 0) {
      return null
    }

    const action = this.undoStack.pop()
    this.redoStack.push(action)
    return action
  }

  // 重做操作
  redo() {
    if (this.redoStack.length === 0) {
      return null
    }

    const action = this.redoStack.pop()
    this.undoStack.push(action)
    return action
  }

  // 清空历史
  clear() {
    this.undoStack = []
    this.redoStack = []
  }

  // 获取状态
  get canUndo() {
    return this.undoStack.length > 0
  }

  get canRedo() {
    return this.redoStack.length > 0
  }

  get undoCount() {
    return this.undoStack.length
  }

  get redoCount() {
    return this.redoStack.length
  }
}

// 快捷键配置
const defaultShortcuts = {
  // 系统快捷键
  'ctrl+z': 'undo',
  'ctrl+y': 'redo',
  'ctrl+shift+z': 'redo',
  'ctrl+r': 'refresh',
  'f5': 'refresh',
  'ctrl+s': 'save',
  'ctrl+f': 'search',
  'esc': 'escape',
  
  // 导航快捷键
  'ctrl+1': 'goToTab1',
  'ctrl+2': 'goToTab2',
  'ctrl+3': 'goToTab3',
  'ctrl+4': 'goToTab4',
  'ctrl+5': 'goToTab5',
  
  // 功能快捷键
  'ctrl+shift+d': 'toggleDarkMode',
  'ctrl+shift+f': 'toggleFullscreen',
  'ctrl+shift+r': 'hardRefresh',
  'ctrl+shift+c': 'clearCache',
  
  // 表格快捷键
  'ctrl+a': 'selectAll',
  'delete': 'deleteSelected',
  'ctrl+d': 'duplicateSelected',
  'ctrl+e': 'exportData',
  
  // 爬虫控制快捷键
  'ctrl+shift+s': 'startAllCrawlers',
  'ctrl+shift+p': 'stopAllCrawlers',
  'ctrl+shift+t': 'toggleAllCrawlers',
  
  // 数据快捷键
  'ctrl+shift+e': 'exportAllData',
  'ctrl+shift+i': 'importData',
  'ctrl+shift+b': 'backup'
}

// 快捷键处理器
export function useKeyboardShortcuts(customShortcuts = {}, options = {}) {
  const shortcuts = { ...defaultShortcuts, ...customShortcuts }
  const actionHistory = new ActionHistory(options.maxHistorySize || 50)
  const isEnabled = ref(true)
  const listeners = ref(new Map())

  // 注册快捷键监听器
  const registerShortcut = (key, callback) => {
    if (typeof callback === 'string') {
      // 如果是字符串，则查找预定义的回调
      const predefinedCallback = listeners.value.get(callback)
      if (predefinedCallback) {
        listeners.value.set(key, predefinedCallback)
      }
    } else if (typeof callback === 'function') {
      listeners.value.set(key, callback)
    }
  }

  // 注册预定义的处理器
  const registerHandler = (name, callback) => {
    listeners.value.set(name, callback)
  }

  // 键盘事件处理
  const handleKeyDown = (event) => {
    if (!isEnabled.value) return

    // 构建快捷键字符串
    let keyString = ''
    if (event.ctrlKey) keyString += 'ctrl+'
    if (event.shiftKey) keyString += 'shift+'
    if (event.altKey) keyString += 'alt+'
    if (event.metaKey) keyString += 'cmd+'

    // 特殊键处理
    const specialKeys = {
      'Escape': 'esc',
      'F5': 'f5',
      'Delete': 'delete',
      'Backspace': 'backspace',
      'Enter': 'enter',
      'Tab': 'tab',
      'Space': 'space',
      'ArrowUp': 'up',
      'ArrowDown': 'down',
      'ArrowLeft': 'left',
      'ArrowRight': 'right'
    }

    const key = specialKeys[event.key] || event.key.toLowerCase()
    keyString += key

    // 查找并执行回调
    const shortcutAction = shortcuts[keyString]
    if (shortcutAction) {
      const callback = listeners.value.get(shortcutAction) || listeners.value.get(keyString)
      if (callback) {
        event.preventDefault()
        event.stopPropagation()
        
        try {
          callback(event)
          // 显示快捷键提示
          if (options.showTooltips) {
            ElMessage({
              message: `快捷键: ${keyString.toUpperCase()}`,
              type: 'info',
              duration: 1000,
              showClose: false
            })
          }
        } catch (error) {
          console.error('快捷键执行错误:', error)
          ElMessage.error('操作执行失败')
        }
      }
    }
  }

  // 添加操作到历史
  const addAction = (action) => {
    actionHistory.push(action)
  }

  // 撤销操作
  const undo = () => {
    const action = actionHistory.undo()
    if (action && action.undo && typeof action.undo === 'function') {
      try {
        action.undo()
        ElMessage.success('撤销成功')
        return true
      } catch (error) {
        console.error('撤销操作失败:', error)
        ElMessage.error('撤销失败')
        return false
      }
    } else {
      ElMessage.warning('没有可撤销的操作')
      return false
    }
  }

  // 重做操作
  const redo = () => {
    const action = actionHistory.redo()
    if (action && action.redo && typeof action.redo === 'function') {
      try {
        action.redo()
        ElMessage.success('重做成功')
        return true
      } catch (error) {
        console.error('重做操作失败:', error)
        ElMessage.error('重做失败')
        return false
      }
    } else {
      ElMessage.warning('没有可重做的操作')
      return false
    }
  }

  // 清空历史
  const clearHistory = () => {
    actionHistory.clear()
    ElMessage.info('操作历史已清空')
  }

  // 获取历史状态
  const getHistoryState = () => {
    return {
      canUndo: actionHistory.canUndo,
      canRedo: actionHistory.canRedo,
      undoCount: actionHistory.undoCount,
      redoCount: actionHistory.redoCount
    }
  }

  // 启用/禁用快捷键
  const setEnabled = (enabled) => {
    isEnabled.value = enabled
  }

  // 获取所有快捷键
  const getAllShortcuts = () => {
    return Object.entries(shortcuts).map(([key, action]) => ({
      key: key.toUpperCase(),
      action,
      description: getShortcutDescription(action)
    }))
  }

  // 获取快捷键描述
  const getShortcutDescription = (action) => {
    const descriptions = {
      'undo': '撤销',
      'redo': '重做',
      'refresh': '刷新',
      'save': '保存',
      'search': '搜索',
      'escape': '取消/关闭',
      'goToTab1': '切换到第1个标签',
      'goToTab2': '切换到第2个标签',
      'goToTab3': '切换到第3个标签',
      'goToTab4': '切换到第4个标签',
      'goToTab5': '切换到第5个标签',
      'toggleDarkMode': '切换暗色模式',
      'toggleFullscreen': '切换全屏',
      'hardRefresh': '强制刷新',
      'clearCache': '清除缓存',
      'selectAll': '全选',
      'deleteSelected': '删除选中项',
      'duplicateSelected': '复制选中项',
      'exportData': '导出数据',
      'startAllCrawlers': '启动所有爬虫',
      'stopAllCrawlers': '停止所有爬虫',
      'toggleAllCrawlers': '切换所有爬虫状态',
      'exportAllData': '导出所有数据',
      'importData': '导入数据',
      'backup': '备份数据'
    }
    return descriptions[action] || action
  }

  // 注册默认处理器
  const registerDefaultHandlers = () => {
    // 撤销/重做
    registerHandler('undo', undo)
    registerHandler('redo', redo)
    
    // 刷新
    registerHandler('refresh', () => {
      window.location.reload()
    })
    
    // 硬刷新
    registerHandler('hardRefresh', () => {
      window.location.reload(true)
    })
    
    // 阻止默认保存
    registerHandler('save', (event) => {
      event.preventDefault()
      ElMessage.info('请使用界面中的保存按钮')
    })
    
    // 搜索
    registerHandler('search', () => {
      const searchInput = document.querySelector('input[type="search"], .search-input input')
      if (searchInput) {
        searchInput.focus()
      }
    })
    
    // ESC键处理
    registerHandler('escape', () => {
      // 关闭所有打开的对话框
      const dialogs = document.querySelectorAll('.el-dialog__wrapper')
      dialogs.forEach(dialog => {
        const closeBtn = dialog.querySelector('.el-dialog__headerbtn')
        if (closeBtn) closeBtn.click()
      })
      
      // 清除选择
      const selection = window.getSelection()
      if (selection) {
        selection.removeAllRanges()
      }
    })
  }

  // 生命周期钩子
  onMounted(() => {
    registerDefaultHandlers()
    document.addEventListener('keydown', handleKeyDown)
  })

  onUnmounted(() => {
    document.removeEventListener('keydown', handleKeyDown)
  })

  return {
    // 状态
    isEnabled,
    
    // 方法
    registerShortcut,
    registerHandler,
    addAction,
    undo,
    redo,
    clearHistory,
    getHistoryState,
    setEnabled,
    getAllShortcuts,
    
    // 历史状态
    canUndo: () => actionHistory.canUndo,
    canRedo: () => actionHistory.canRedo,
    undoCount: () => actionHistory.undoCount,
    redoCount: () => actionHistory.redoCount
  }
}

// 创建标准操作对象的辅助函数
export function createAction(name, redoFn, undoFn, data = {}) {
  return {
    name,
    timestamp: Date.now(),
    data,
    redo: redoFn,
    undo: undoFn
  }
}

// 批量操作辅助函数
export function createBatchAction(name, actions) {
  return {
    name,
    timestamp: Date.now(),
    actions,
    redo: () => {
      actions.forEach(action => {
        if (action.redo) action.redo()
      })
    },
    undo: () => {
      // 逆序执行撤销
      actions.reverse().forEach(action => {
        if (action.undo) action.undo()
      })
    }
  }
}

export default useKeyboardShortcuts 