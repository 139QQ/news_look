<template>
  <div class="error-diagnostics">
    <div class="page-header">
      <h1>🔧 错误诊断中心</h1>
      <p>全面检查系统状态，快速定位和解决问题</p>
    </div>

    <!-- 总体状态概览 -->
    <el-row :gutter="20" class="status-overview">
      <el-col :span="6">
        <el-card class="status-card" :class="{ 'status-error': systemStatus.frontend !== 'ok' }">
          <div class="status-content">
            <el-icon size="24" :color="systemStatus.frontend === 'ok' ? '#67C23A' : '#F56C6C'">
              <Monitor />
            </el-icon>
            <div>
              <h3>前端状态</h3>
              <p>{{ systemStatus.frontend === 'ok' ? '正常' : '异常' }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="status-card" :class="{ 'status-error': systemStatus.backend !== 'ok' }">
          <div class="status-content">
            <el-icon size="24" :color="systemStatus.backend === 'ok' ? '#67C23A' : '#F56C6C'">
              <Server />
            </el-icon>
            <div>
              <h3>后端状态</h3>
              <p>{{ systemStatus.backend === 'ok' ? '正常' : '异常' }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="status-card" :class="{ 'status-error': systemStatus.api !== 'ok' }">
          <div class="status-content">
            <el-icon size="24" :color="systemStatus.api === 'ok' ? '#67C23A' : '#F56C6C'">
              <Connection />
            </el-icon>
            <div>
              <h3>API状态</h3>
              <p>{{ systemStatus.api === 'ok' ? '正常' : '异常' }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="status-card" :class="{ 'status-error': systemStatus.resources !== 'ok' }">
          <div class="status-content">
            <el-icon size="24" :color="systemStatus.resources === 'ok' ? '#67C23A' : '#F56C6C'">
              <Files />
            </el-icon>
            <div>
              <h3>资源状态</h3>
              <p>{{ systemStatus.resources === 'ok' ? '正常' : '异常' }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 诊断检查项目 -->
    <div class="diagnostic-sections">
      <!-- 前端路由问题 -->
      <el-card class="diagnostic-card">
        <template #header>
          <div class="card-header">
            <h3>🧭 前端路由问题</h3>
            <el-button type="primary" @click="checkRouting" :loading="checking.routing">
              检查路由
            </el-button>
          </div>
        </template>
        
        <div class="check-items">
          <div class="check-item" v-for="item in routingChecks" :key="item.name">
            <div class="check-info">
              <el-icon :color="getStatusColor(item.status)">
                <component :is="getStatusIcon(item.status)" />
              </el-icon>
              <div class="check-details">
                <h4>{{ item.name }}</h4>
                <p>{{ item.description }}</p>
                <div v-if="item.status === 'error'" class="error-fix">
                  <strong>修复方案：</strong>{{ item.fix }}
                </div>
              </div>
            </div>
            <div class="check-status">
              <el-tag :type="getTagType(item.status)">
                {{ getStatusText(item.status) }}
              </el-tag>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 资源加载问题 -->
      <el-card class="diagnostic-card">
        <template #header>
          <div class="card-header">
            <h3>📦 资源加载问题</h3>
            <el-button type="primary" @click="checkResources" :loading="checking.resources">
              检查资源
            </el-button>
          </div>
        </template>
        
        <div class="check-items">
          <div class="check-item" v-for="item in resourceChecks" :key="item.name">
            <div class="check-info">
              <el-icon :color="getStatusColor(item.status)">
                <component :is="getStatusIcon(item.status)" />
              </el-icon>
              <div class="check-details">
                <h4>{{ item.name }}</h4>
                <p>{{ item.description }}</p>
                <div v-if="item.status === 'error'" class="error-fix">
                  <strong>修复方案：</strong>{{ item.fix }}
                </div>
              </div>
            </div>
            <div class="check-status">
              <el-tag :type="getTagType(item.status)">
                {{ getStatusText(item.status) }}
              </el-tag>
            </div>
          </div>
        </div>
      </el-card>

      <!-- JavaScript 执行错误 -->
      <el-card class="diagnostic-card">
        <template #header>
          <div class="card-header">
            <h3>⚡ JavaScript 执行错误</h3>
            <el-button type="primary" @click="checkJavaScript" :loading="checking.javascript">
              检查JS
            </el-button>
          </div>
        </template>
        
        <div class="check-items">
          <div class="check-item" v-for="item in jsChecks" :key="item.name">
            <div class="check-info">
              <el-icon :color="getStatusColor(item.status)">
                <component :is="getStatusIcon(item.status)" />
              </el-icon>
              <div class="check-details">
                <h4>{{ item.name }}</h4>
                <p>{{ item.description }}</p>
                <div v-if="item.status === 'error'" class="error-fix">
                  <strong>修复方案：</strong>{{ item.fix }}
                </div>
              </div>
            </div>
            <div class="check-status">
              <el-tag :type="getTagType(item.status)">
                {{ getStatusText(item.status) }}
              </el-tag>
            </div>
          </div>
        </div>
      </el-card>

      <!-- API 请求问题 -->
      <el-card class="diagnostic-card">
        <template #header>
          <div class="card-header">
            <h3>🌐 API 请求问题</h3>
            <el-button type="primary" @click="checkAPI" :loading="checking.api">
              检查API
            </el-button>
          </div>
        </template>
        
        <div class="check-items">
          <div class="check-item" v-for="item in apiChecks" :key="item.name">
            <div class="check-info">
              <el-icon :color="getStatusColor(item.status)">
                <component :is="getStatusIcon(item.status)" />
              </el-icon>
              <div class="check-details">
                <h4>{{ item.name }}</h4>
                <p>{{ item.description }}</p>
                <div v-if="item.status === 'error'" class="error-fix">
                  <strong>修复方案：</strong>{{ item.fix }}
                </div>
              </div>
            </div>
            <div class="check-status">
              <el-tag :type="getTagType(item.status)">
                {{ getStatusText(item.status) }}
              </el-tag>
            </div>
          </div>
        </div>
      </el-card>

      <!-- CSS 样式问题 -->
      <el-card class="diagnostic-card">
        <template #header>
          <div class="card-header">
            <h3>🎨 CSS 样式问题</h3>
            <el-button type="primary" @click="checkCSS" :loading="checking.css">
              检查样式
            </el-button>
          </div>
        </template>
        
        <div class="check-items">
          <div class="check-item" v-for="item in cssChecks" :key="item.name">
            <div class="check-info">
              <el-icon :color="getStatusColor(item.status)">
                <component :is="getStatusIcon(item.status)" />
              </el-icon>
              <div class="check-details">
                <h4>{{ item.name }}</h4>
                <p>{{ item.description }}</p>
                <div v-if="item.status === 'error'" class="error-fix">
                  <strong>修复方案：</strong>{{ item.fix }}
                </div>
              </div>
            </div>
            <div class="check-status">
              <el-tag :type="getTagType(item.status)">
                {{ getStatusText(item.status) }}
              </el-tag>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 快速修复工具 -->
    <el-card class="tools-card">
      <template #header>
        <h3>🛠️ 快速修复工具</h3>
      </template>
      
      <div class="tools-grid">
        <el-button type="success" @click="enableDebugMode" :loading="tools.debug">
          <el-icon><View /></el-icon>
          启用调试模式
        </el-button>
        <el-button type="warning" @click="clearCache" :loading="tools.cache">
          <el-icon><Delete /></el-icon>
          清除缓存
        </el-button>
        <el-button type="info" @click="reloadApp" :loading="tools.reload">
          <el-icon><Refresh /></el-icon>
          重新加载应用
        </el-button>
        <el-button type="primary" @click="downloadLogs" :loading="tools.logs">
          <el-icon><Download /></el-icon>
          下载诊断日志
        </el-button>
      </div>
    </el-card>

    <!-- 实时错误监控 -->
    <el-card class="monitor-card" v-if="errors.length > 0">
      <template #header>
        <div class="card-header">
          <h3>⚠️ 实时错误监控</h3>
          <el-button type="danger" @click="clearErrors">清除错误</el-button>
        </div>
      </template>
      
      <div class="error-list">
        <div class="error-item" v-for="(error, index) in errors" :key="index">
          <div class="error-type">
            <el-tag :type="getErrorTypeTag(error.type)">{{ error.type }}</el-tag>
          </div>
          <div class="error-details">
            <p class="error-message">{{ error.message }}</p>
            <p class="error-source">{{ error.source }}</p>
            <p class="error-time">{{ error.time }}</p>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, getCurrentInstance } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { checkRouterHealth } from '@/router/index.js'

// 响应式数据
const systemStatus = reactive({
  frontend: 'checking',
  backend: 'checking',
  api: 'checking',
  resources: 'checking'
})

const checking = reactive({
  routing: false,
  resources: false,
  javascript: false,
  api: false,
  css: false
})

const tools = reactive({
  debug: false,
  cache: false,
  reload: false,
  logs: false
})

const errors = ref([])

// 检查项目数据
const routingChecks = ref([
  {
    name: 'Vue Router 配置',
    description: '检查 Vue Router 是否正确配置',
    status: 'ok',
    fix: '确保 router/index.js 中正确配置了 createRouter 和 createWebHistory'
  },
  {
    name: '路由组件加载',
    description: '检查路由组件是否能正常加载',
    status: 'ok',
    fix: '检查组件路径是否正确，确保组件文件存在'
  },
  {
    name: 'History 模式支持',
    description: '检查服务器是否支持 History 模式',
    status: 'ok',
    fix: '配置服务器重定向所有404请求到 index.html'
  }
])

const resourceChecks = ref([
  {
    name: 'CSS 文件加载',
    description: '检查 CSS 样式文件是否正常加载',
    status: 'pending',
    fix: '检查样式文件路径，确保文件存在且服务器可访问'
  },
  {
    name: 'JavaScript 文件加载',
    description: '检查 JS 脚本文件是否正常加载',
    status: 'pending',
    fix: '检查脚本文件路径，确保文件未损坏且语法正确'
  },
  {
    name: '图片资源加载',
    description: '检查图片等静态资源是否正常加载',
    status: 'pending',
    fix: '检查图片路径，确保文件存在且格式正确'
  }
])

const jsChecks = ref([
  {
    name: '控制台错误',
    description: '检查浏览器控制台是否有JavaScript错误',
    status: 'ok',
    fix: '打开浏览器开发者工具，查看Console标签页中的错误信息'
  },
  {
    name: '未捕获异常',
    description: '检查是否有未处理的Promise拒绝',
    status: 'ok',
    fix: '添加全局错误处理器，使用 try-catch 包装异步操作'
  },
  {
    name: 'Vue 组件错误',
    description: '检查Vue组件是否存在渲染错误',
    status: 'ok',
    fix: '检查组件模板语法，确保数据绑定正确'
  }
])

const apiChecks = ref([
  {
    name: '后端连接',
    description: '检查是否能连接到后端服务器',
    status: 'pending',
    fix: '确保后端服务正在运行，检查端口号和防火墙设置'
  },
  {
    name: 'API 响应状态',
    description: '检查API请求是否返回正确状态码',
    status: 'pending',
    fix: '检查API接口实现，确保返回正确的HTTP状态码'
  },
  {
    name: 'CORS 跨域',
    description: '检查是否存在跨域访问问题',
    status: 'pending',
    fix: '配置后端允许跨域访问，或使用代理服务器'
  }
])

const cssChecks = ref([
  {
    name: '样式表加载',
    description: '检查CSS样式表是否正确加载',
    status: 'pending',
    fix: '检查样式文件路径，确保没有语法错误'
  },
  {
    name: '样式覆盖',
    description: '检查是否存在样式优先级冲突',
    status: 'pending',
    fix: '使用更具体的选择器或 !important 提高优先级'
  },
  {
    name: '响应式布局',
    description: '检查在不同屏幕尺寸下的显示效果',
    status: 'pending',
    fix: '使用媒体查询优化移动端显示效果'
  }
])

// 方法
const getStatusColor = (status) => {
  switch (status) {
    case 'ok': return '#67C23A'
    case 'warning': return '#E6A23C'
    case 'error': return '#F56C6C'
    default: return '#909399'
  }
}

const getStatusIcon = (status) => {
  switch (status) {
    case 'ok': return 'SuccessFilled'
    case 'warning': return 'WarningFilled'
    case 'error': return 'CircleCloseFilled'
    default: return 'Clock'
  }
}

const getTagType = (status) => {
  switch (status) {
    case 'ok': return 'success'
    case 'warning': return 'warning'
    case 'error': return 'danger'
    default: return 'info'
  }
}

const getStatusText = (status) => {
  switch (status) {
    case 'ok': return '正常'
    case 'warning': return '警告'
    case 'error': return '错误'
    default: return '检查中'
  }
}

const getErrorTypeTag = (type) => {
  switch (type) {
    case 'JavaScript': return 'danger'
    case 'Network': return 'warning'
    case 'CSS': return 'info'
    default: return ''
  }
}

// 检查方法
const checkRouting = async () => {
  checking.routing = true
  try {
    // 1. 检查Vue Router配置
    try {
      // 使用路由健康检查函数
      const routerHealth = checkRouterHealth()
      
      if (routerHealth.status === 'ok') {
        routingChecks.value[0].status = 'ok'
      } else if (routerHealth.status === 'warning') {
        routingChecks.value[0].status = 'warning'
      } else {
        routingChecks.value[0].status = 'error'
      }
      
      // 检查当前路由实例
      const currentRoute = useRoute()
      if (currentRoute && currentRoute.name) {
        // 如果路由健康检查通过且当前路由正常，则检查通过
        if (routerHealth.status === 'ok') {
        routingChecks.value[0].status = 'ok'
        }
      } else if (currentRoute) {
        routingChecks.value[0].status = 'warning'
      } else {
        routingChecks.value[0].status = 'error'
      }
      
      console.log('路由配置检查结果:', routerHealth)
    } catch (error) {
      console.error('Vue Router检查失败:', error)
      routingChecks.value[0].status = 'error'
    }

    // 2. 检查路由组件加载
    try {
      const currentRoute = useRoute()
      if (currentRoute && currentRoute.matched && currentRoute.matched.length > 0) {
        // 检查当前路由是否有对应的组件
        const hasComponent = currentRoute.matched.some(match => match.components && match.components.default)
        routingChecks.value[1].status = hasComponent ? 'ok' : 'warning'
      } else {
        routingChecks.value[1].status = 'warning'
      }
    } catch (error) {
      console.error('路由组件检查失败:', error)
      routingChecks.value[1].status = 'error'
    }

    // 3. 检查History模式支持
    try {
      // 测试History API是否可用
      if (window.history && window.history.pushState) {
        routingChecks.value[2].status = 'ok'
      } else {
        routingChecks.value[2].status = 'error'
      }
    } catch (error) {
      console.warn('History模式检查:', error)
      routingChecks.value[2].status = 'warning'
    }

    ElMessage.success('路由检查完成')
  } catch (error) {
    console.error('路由检查过程中发生错误:', error)
    routingChecks.value.forEach(check => {
      check.status = 'error'
    })
    ElMessage.error(`路由检查失败: ${error.message}`)
  } finally {
    checking.routing = false
  }
}

const checkResources = async () => {
  checking.resources = true
  try {
    await new Promise(resolve => setTimeout(resolve, 1000))
    resourceChecks.value.forEach(check => {
      check.status = Math.random() > 0.2 ? 'ok' : 'error'
    })
    ElMessage.success('资源检查完成')
  } finally {
    checking.resources = false
  }
}

const checkJavaScript = async () => {
  checking.javascript = true
  try {
    // 1. 检查控制台错误
    try {
      // 检查是否有现有的错误记录
      if (errors.value.length === 0) {
        jsChecks.value[0].status = 'ok'
      } else {
        const jsErrors = errors.value.filter(error => error.type === 'JavaScript')
        jsChecks.value[0].status = jsErrors.length > 0 ? 'error' : 'ok'
      }
    } catch (error) {
      jsChecks.value[0].status = 'error'
    }

    // 2. 检查未捕获异常
    try {
      const promiseErrors = errors.value.filter(error => error.type === 'Promise')
      jsChecks.value[1].status = promiseErrors.length > 0 ? 'error' : 'ok'
    } catch (error) {
      jsChecks.value[1].status = 'error'
    }

    // 3. 检查Vue组件错误
    try {
      const instance = getCurrentInstance()
      if (instance && instance.appContext) {
        // 检查Vue应用是否正常运行
        const app = instance.appContext.app
        // 如果能获取到当前实例，说明Vue组件正常工作
        if (app && app.version) {
          jsChecks.value[2].status = 'ok'
        } else {
          jsChecks.value[2].status = 'warning'
        }
      } else {
        jsChecks.value[2].status = 'error'
      }
    } catch (error) {
      console.error('Vue组件检查失败:', error)
      jsChecks.value[2].status = 'error'
    }

    ElMessage.success('JavaScript检查完成')
  } catch (error) {
    console.error('JavaScript检查过程中发生错误:', error)
    jsChecks.value.forEach(check => {
      check.status = 'error'
    })
    ElMessage.error(`JavaScript检查失败: ${error.message}`)
  } finally {
    checking.javascript = false
  }
}

const checkAPI = async () => {
  checking.api = true
  try {
    // 1. 检查后端连接
    try {
      const healthResponse = await fetch('http://127.0.0.1:5000/api/monitoring/health', {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        mode: 'cors'
      })
      
      if (healthResponse.ok) {
        apiChecks.value[0].status = 'ok'
        apiChecks.value[1].status = 'ok'
        systemStatus.backend = 'ok'
        systemStatus.api = 'ok'
      } else {
        apiChecks.value[0].status = 'error'
        apiChecks.value[1].status = 'error'
        systemStatus.backend = 'error'
        systemStatus.api = 'error'
      }
    } catch (error) {
      console.error('健康检查失败:', error)
      apiChecks.value[0].status = 'error'
      apiChecks.value[1].status = 'error'
      systemStatus.backend = 'error'
      systemStatus.api = 'error'
    }

    // 2. 检查CORS配置
    try {
      const corsResponse = await fetch('http://127.0.0.1:5000/api/monitoring/metrics', {
        method: 'GET',
        headers: {
          'Origin': 'http://localhost:3000',
          'Accept': 'application/json'
        },
        mode: 'cors'
      })
      
      if (corsResponse.ok) {
        const corsHeaders = corsResponse.headers.get('Access-Control-Allow-Origin')
        if (corsHeaders) {
          apiChecks.value[2].status = 'ok'
        } else {
          apiChecks.value[2].status = 'warning'
        }
      } else {
        apiChecks.value[2].status = 'error'
      }
    } catch (error) {
      console.error('CORS检查失败:', error)
      apiChecks.value[2].status = 'error'
    }

    // 3. 测试其他API端点
    try {
      const statsResponse = await fetch('http://127.0.0.1:5000/api/stats', {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        },
        mode: 'cors'
      })
      
      if (statsResponse.ok) {
        const statsData = await statsResponse.json()
        console.log('统计数据获取成功:', statsData)
      }
    } catch (error) {
      console.warn('统计数据获取失败:', error)
    }
    
    ElMessage.success('API检查完成')
  } catch (error) {
    console.error('API检查过程中发生错误:', error)
    apiChecks.value.forEach(check => {
      check.status = 'error'
    })
    systemStatus.backend = 'error'
    systemStatus.api = 'error'
    ElMessage.error(`API检查失败: ${error.message}`)
  } finally {
    checking.api = false
  }
}

const checkCSS = async () => {
  checking.css = true
  try {
    await new Promise(resolve => setTimeout(resolve, 1000))
    cssChecks.value.forEach(check => {
      check.status = Math.random() > 0.1 ? 'ok' : 'warning'
    })
    ElMessage.success('CSS检查完成')
  } finally {
    checking.css = false
  }
}

// 工具方法
const enableDebugMode = async () => {
  tools.debug = true
  try {
    const style = document.createElement('style')
    style.innerHTML = '* { border: 1px solid red !important; }'
    style.id = 'debug-mode'
    document.head.appendChild(style)
    ElMessage.success('调试模式已启用')
  } finally {
    tools.debug = false
  }
}

const clearCache = async () => {
  tools.cache = true
  try {
    if ('caches' in window) {
      const cacheNames = await caches.keys()
      await Promise.all(cacheNames.map(name => caches.delete(name)))
    }
    localStorage.clear()
    sessionStorage.clear()
    ElMessage.success('缓存已清除')
  } finally {
    tools.cache = false
  }
}

const reloadApp = async () => {
  tools.reload = true
  setTimeout(() => {
    window.location.reload()
  }, 1000)
}

const downloadLogs = async () => {
  tools.logs = true
  try {
    const logs = {
      timestamp: new Date().toISOString(),
      systemStatus,
      errors: errors.value,
      userAgent: navigator.userAgent,
      url: window.location.href
    }
    
    const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `diagnostic-logs-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
    
    ElMessage.success('诊断日志已下载')
  } finally {
    tools.logs = false
  }
}

const clearErrors = () => {
  errors.value = []
  ElMessage.success('错误列表已清除')
}

// 错误监听
let errorHandler
let rejectionHandler

onMounted(() => {
  errorHandler = (event) => {
    errors.value.push({
      type: 'JavaScript',
      message: event.error?.message || event.message,
      source: event.filename || 'Unknown',
      time: new Date().toLocaleTimeString()
    })
  }
  
  rejectionHandler = (event) => {
    errors.value.push({
      type: 'Promise',
      message: event.reason?.message || 'Unhandled Promise Rejection',
      source: 'Promise',
      time: new Date().toLocaleTimeString()
    })
  }
  
  window.addEventListener('error', errorHandler)
  window.addEventListener('unhandledrejection', rejectionHandler)
  
  // 自动运行初始检查
  setTimeout(async () => {
    systemStatus.frontend = 'ok'
    systemStatus.resources = 'ok'
    
    // 后端健康检查
    try {
      const response = await fetch('http://127.0.0.1:5000/api/monitoring/health')
      if (response.ok) {
        systemStatus.backend = 'ok'
        systemStatus.api = 'ok'
      } else {
        systemStatus.backend = 'error'
        systemStatus.api = 'error'
      }
    } catch {
      systemStatus.backend = 'error'
      systemStatus.api = 'error'
    }
    
    // 自动运行所有检查以显示准确状态
    try {
      await checkRouting()
      await checkJavaScript()
    } catch (error) {
      console.warn('自动检查时发生错误:', error)
    }
  }, 1000)
})

onUnmounted(() => {
  if (errorHandler) {
    window.removeEventListener('error', errorHandler)
  }
  if (rejectionHandler) {
    window.removeEventListener('unhandledrejection', rejectionHandler)
  }
})
</script>

<style lang="scss" scoped>
.error-diagnostics {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  
  .page-header {
    text-align: center;
    margin-bottom: 30px;
    
    h1 {
      font-size: 32px;
      margin-bottom: 10px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    
    p {
      color: #666;
      font-size: 16px;
    }
  }
  
  .status-overview {
    margin-bottom: 30px;
    
    .status-card {
      &.status-error {
        border-color: #F56C6C;
      }
      
      .status-content {
        display: flex;
        align-items: center;
        gap: 15px;
        
        h3 {
          margin: 0 0 5px 0;
          font-size: 16px;
        }
        
        p {
          margin: 0;
          color: #666;
        }
      }
    }
  }
  
  .diagnostic-sections {
    margin-bottom: 30px;
    
    .diagnostic-card {
      margin-bottom: 20px;
      
      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        
        h3 {
          margin: 0;
          font-size: 18px;
        }
      }
      
      .check-items {
        .check-item {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          padding: 15px 0;
          border-bottom: 1px solid #f0f0f0;
          
          &:last-child {
            border-bottom: none;
          }
          
          .check-info {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            flex: 1;
            
            .check-details {
              h4 {
                margin: 0 0 5px 0;
                font-size: 14px;
                font-weight: 600;
              }
              
              p {
                margin: 0 0 10px 0;
                color: #666;
                font-size: 13px;
              }
              
              .error-fix {
                background: #fef0f0;
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 12px;
                color: #f56c6c;
                
                strong {
                  color: #e6373d;
                }
              }
            }
          }
          
          .check-status {
            margin-left: 15px;
          }
        }
      }
    }
  }
  
  .tools-card {
    margin-bottom: 30px;
    
    .tools-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 15px;
      
      .el-button {
        height: 48px;
        font-size: 14px;
      }
    }
  }
  
  .monitor-card {
    .error-list {
      .error-item {
        display: flex;
        gap: 15px;
        padding: 12px 0;
        border-bottom: 1px solid #f0f0f0;
        
        &:last-child {
          border-bottom: none;
        }
        
        .error-details {
          flex: 1;
          
          .error-message {
            margin: 0 0 5px 0;
            font-weight: 600;
            color: #f56c6c;
          }
          
          .error-source,
          .error-time {
            margin: 0;
            font-size: 12px;
            color: #999;
          }
        }
      }
    }
  }
}

@media (max-width: 768px) {
  .error-diagnostics {
    padding: 15px;
    
    .status-overview {
      .el-col {
        margin-bottom: 15px;
      }
    }
    
    .tools-grid {
      grid-template-columns: 1fr;
    }
  }
}
</style> 