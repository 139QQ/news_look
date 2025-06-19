<template>
  <div class="error-boundary">
    <div v-if="hasError" class="error-display">
      <div class="error-container">
        <div class="error-icon">
          <el-icon size="80" color="#F56C6C">
            <WarningFilled />
          </el-icon>
        </div>
        
        <div class="error-content">
          <h2 class="error-title">
            {{ errorInfo.type === 'network' ? '网络连接异常' : '应用程序错误' }}
          </h2>
          
          <p class="error-message">{{ errorInfo.message }}</p>
          
          <div class="error-details" v-if="showDetails">
            <h4>错误详情：</h4>
            <div class="error-stack">
              <pre>{{ errorInfo.stack }}</pre>
            </div>
            
            <div class="error-meta">
              <p><strong>发生时间：</strong>{{ errorInfo.timestamp }}</p>
              <p><strong>页面路径：</strong>{{ errorInfo.path }}</p>
              <p><strong>用户代理：</strong>{{ errorInfo.userAgent }}</p>
            </div>
          </div>
          
          <div class="error-actions">
            <el-button type="primary" @click="reload">
              <el-icon><Refresh /></el-icon>
              重新加载
            </el-button>
            <el-button @click="goHome">
              <el-icon><House /></el-icon>
              返回首页
            </el-button>
            <el-button type="info" @click="toggleDetails">
              <el-icon><View /></el-icon>
              {{ showDetails ? '隐藏' : '显示' }}详情
            </el-button>
            <el-button type="success" @click="reportError">
              <el-icon><Position /></el-icon>
              上报错误
            </el-button>
          </div>
        </div>
      </div>
    </div>
    
    <div v-else>
      <slot />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, provide } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()

// 响应式数据
const hasError = ref(false)
const showDetails = ref(false)
const errorInfo = reactive({
  type: '',
  message: '',
  stack: '',
  timestamp: '',
  path: '',
  userAgent: ''
})

// 错误处理函数
const handleError = (error, errorType = 'javascript') => {
  hasError.value = true
  
  errorInfo.type = errorType
  errorInfo.message = error.message || '未知错误'
  errorInfo.stack = error.stack || 'No stack trace available'
  errorInfo.timestamp = new Date().toLocaleString('zh-CN')
  errorInfo.path = window.location.pathname
  errorInfo.userAgent = navigator.userAgent
  
  console.error('Error caught by ErrorBoundary:', error)
}

// 网络错误处理
const handleNetworkError = (error) => {
  handleError({
    message: '网络请求失败，请检查网络连接或稍后重试',
    stack: error.toString()
  }, 'network')
}

// Promise 拒绝处理
const handlePromiseRejection = (event) => {
  const error = event.reason
  handleError({
    message: error.message || '异步操作失败',
    stack: error.stack || event.reason.toString()
  }, 'promise')
}

// 资源加载错误处理
const handleResourceError = (event) => {
  const target = event.target
  const errorMsg = `资源加载失败: ${target.src || target.href || '未知资源'}`
  
  handleError({
    message: errorMsg,
    stack: `Resource: ${target.tagName} - ${target.src || target.href}`
  }, 'resource')
}

// 方法
const reload = () => {
  window.location.reload()
}

const goHome = () => {
  hasError.value = false
  router.push('/')
}

const toggleDetails = () => {
  showDetails.value = !showDetails.value
}

const reportError = async () => {
  try {
    // 这里可以发送错误报告到服务器
    const errorReport = {
      ...errorInfo,
      url: window.location.href,
      timestamp: Date.now()
    }
    
    // 模拟发送错误报告
    console.log('Error report:', errorReport)
    
    // 实际项目中可以发送到错误收集服务
    // await fetch('/api/error-report', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify(errorReport)
    // })
    
    ElMessage.success('错误报告已发送')
  } catch (error) {
    ElMessage.error('错误报告发送失败')
  }
}

// 重置错误状态
const resetError = () => {
  hasError.value = false
  showDetails.value = false
  Object.keys(errorInfo).forEach(key => {
    errorInfo[key] = ''
  })
}

// 提供错误处理方法给子组件
provide('errorHandler', {
  handleError,
  handleNetworkError,
  resetError
})

// 事件监听器
let errorHandler, rejectionHandler, resourceErrorHandler

onMounted(() => {
  // 监听全局JavaScript错误
  errorHandler = (event) => {
    handleError(event.error || {
      message: event.message,
      stack: `${event.filename}:${event.lineno}:${event.colno}`
    })
  }
  
  // 监听未处理的Promise拒绝
  rejectionHandler = handlePromiseRejection
  
  // 监听资源加载错误
  resourceErrorHandler = handleResourceError
  
  window.addEventListener('error', errorHandler)
  window.addEventListener('unhandledrejection', rejectionHandler)
  window.addEventListener('error', resourceErrorHandler, true)
})

onUnmounted(() => {
  if (errorHandler) {
    window.removeEventListener('error', errorHandler)
  }
  if (rejectionHandler) {
    window.removeEventListener('unhandledrejection', rejectionHandler)
  }
  if (resourceErrorHandler) {
    window.removeEventListener('error', resourceErrorHandler, true)
  }
})

// 导出方法供外部使用
defineExpose({
  handleError,
  handleNetworkError,
  resetError
})
</script>

<style lang="scss" scoped>
.error-boundary {
  width: 100%;
  height: 100%;
}

.error-display {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 50%, #fecfef 100%);
  padding: 20px;
  
  .error-container {
    background: rgba(255, 255, 255, 0.95);
    border-radius: 20px;
    padding: 40px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
    backdrop-filter: blur(10px);
    max-width: 700px;
    width: 100%;
    text-align: center;
    
    .error-icon {
      margin-bottom: 20px;
    }
    
    .error-content {
      .error-title {
        font-size: 28px;
        color: #303133;
        margin: 0 0 15px 0;
        font-weight: 600;
      }
      
      .error-message {
        font-size: 16px;
        color: #606266;
        margin: 0 0 30px 0;
        line-height: 1.6;
      }
      
      .error-details {
        text-align: left;
        background: #f8f9fa;
        border-radius: 8px;
        padding: 20px;
        margin: 20px 0 30px 0;
        
        h4 {
          margin: 0 0 15px 0;
          color: #303133;
          font-size: 16px;
        }
        
        .error-stack {
          background: #2c3e50;
          color: #ecf0f1;
          padding: 15px;
          border-radius: 6px;
          margin: 10px 0;
          overflow-x: auto;
          font-family: 'Courier New', monospace;
          font-size: 12px;
          line-height: 1.4;
          
          pre {
            margin: 0;
            white-space: pre-wrap;
            word-break: break-all;
          }
        }
        
        .error-meta {
          margin-top: 15px;
          
          p {
            margin: 5px 0;
            font-size: 14px;
            color: #666;
            
            strong {
              color: #303133;
            }
          }
        }
      }
      
      .error-actions {
        display: flex;
        gap: 12px;
        justify-content: center;
        flex-wrap: wrap;
        
        .el-button {
          min-width: 120px;
        }
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .error-display {
    padding: 15px;
    
    .error-container {
      padding: 30px 20px;
      
      .error-title {
        font-size: 24px;
      }
      
      .error-message {
        font-size: 14px;
      }
      
      .error-actions {
        flex-direction: column;
        align-items: center;
        
        .el-button {
          width: 100%;
          max-width: 200px;
        }
      }
      
      .error-details {
        .error-stack {
          font-size: 11px;
        }
        
        .error-meta p {
          font-size: 13px;
        }
      }
    }
  }
}

// 暗色主题适配
@media (prefers-color-scheme: dark) {
  .error-display {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    
    .error-container {
      background: rgba(30, 30, 30, 0.95);
      color: #ecf0f1;
      
      .error-title {
        color: #ecf0f1;
      }
      
      .error-message {
        color: #bdc3c7;
      }
      
      .error-details {
        background: #34495e;
        
        h4 {
          color: #ecf0f1;
        }
        
        .error-meta p {
          color: #95a5a6;
          
          strong {
            color: #ecf0f1;
          }
        }
      }
    }
  }
}
</style> 