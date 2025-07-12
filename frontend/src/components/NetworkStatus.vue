<template>
  <div class="network-status" v-if="!isOnline">
    <el-alert
      :title="statusText"
      :type="alertType"
      :closable="false"
      show-icon
      :effect="isOnline ? 'light' : 'dark'"
    >
      <template #default>
        <div class="status-content">
          <p>{{ statusMessage }}</p>
          <div class="status-actions" v-if="!isOnline">
            <el-button size="small" @click="checkConnection" :loading="isChecking">
              重新检测
            </el-button>
            <el-button size="small" type="info" @click="showTroubleshooting">
              故障排除
            </el-button>
          </div>
        </div>
      </template>
    </el-alert>

    <!-- 故障排除对话框 -->
    <el-dialog
      v-model="troubleshootingVisible"
      title="网络故障排除"
      width="600px"
      center
    >
      <div class="troubleshooting-content">
        <h4>🔧 常见解决方案：</h4>
        <el-steps direction="vertical" :active="currentStep">
          <el-step 
            v-for="(step, index) in troubleshootingSteps" 
            :key="index"
            :title="step.title"
            :description="step.description"
            :status="step.status"
          />
        </el-steps>
        
        <div class="step-actions">
          <el-button 
            v-if="currentStep < troubleshootingSteps.length" 
            type="primary" 
            @click="nextStep"
          >
            下一步
          </el-button>
          <el-button @click="resetSteps">重新开始</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

// 响应式数据
const isOnline = ref(navigator.onLine)
const isChecking = ref(false)
const troubleshootingVisible = ref(false)
const currentStep = ref(0)
const lastCheckTime = ref(Date.now())

// 故障排除步骤
const troubleshootingSteps = reactive([
  {
    title: '检查网络连接',
    description: '确保设备已连接到WiFi或有线网络',
    status: 'wait'
  },
  {
    title: '检查路由器状态',
    description: '重启路由器，等待2-3分钟后重新连接',
    status: 'wait'
  },
  {
    title: '检查防火墙设置',
    description: '确保防火墙没有阻止应用程序访问网络',
    status: 'wait'
  },
  {
    title: '检查代理设置',
    description: '如果使用代理，请确保代理服务器正常工作',
    status: 'wait'
  },
  {
    title: '联系网络管理员',
    description: '如果问题持续存在，请联系网络管理员或技术支持',
    status: 'wait'
  }
])

// 计算属性
const alertType = computed(() => {
  return isOnline.value ? 'success' : 'error'
})

const statusText = computed(() => {
  return isOnline.value ? '网络连接正常' : '网络连接断开'
})

const statusMessage = computed(() => {
  if (isOnline.value) {
    return '当前网络连接稳定，所有功能正常可用。'
  } else {
    return '无法连接到网络，部分功能可能无法使用。请检查网络连接。'
  }
})

// 方法
const updateOnlineStatus = () => {
  const wasOnline = isOnline.value
  isOnline.value = navigator.onLine
  
  if (wasOnline && !isOnline.value) {
    ElMessage.error('网络连接已断开')
  } else if (!wasOnline && isOnline.value) {
    ElMessage.success('网络连接已恢复')
  }
  
  lastCheckTime.value = Date.now()
}

const checkConnection = async () => {
  isChecking.value = true
  
  try {
    // 尝试请求一个轻量级的API来检测网络
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 5000)
    
    const response = await fetch('/api/health', {
      method: 'GET',
      cache: 'no-cache',
      signal: controller.signal
    })
    
    clearTimeout(timeoutId)
    
    if (response.ok) {
      isOnline.value = true
      ElMessage.success('网络连接检测成功')
    } else {
      isOnline.value = false
      ElMessage.warning('服务器响应异常')
    }
  } catch (error) {
    isOnline.value = false
    if (error.name === 'AbortError') {
      ElMessage.error('网络检测超时')
    } else {
      ElMessage.error('网络检测失败')
    }
  } finally {
    isChecking.value = false
    lastCheckTime.value = Date.now()
  }
}

const showTroubleshooting = () => {
  troubleshootingVisible.value = true
  resetSteps()
}

const nextStep = () => {
  if (currentStep.value < troubleshootingSteps.length) {
    troubleshootingSteps[currentStep.value].status = 'finish'
    currentStep.value++
    
    if (currentStep.value < troubleshootingSteps.length) {
      troubleshootingSteps[currentStep.value].status = 'process'
    }
  }
}

const resetSteps = () => {
  currentStep.value = 0
  troubleshootingSteps.forEach(step => {
    step.status = 'wait'
  })
  if (troubleshootingSteps.length > 0) {
    troubleshootingSteps[0].status = 'process'
  }
}

// 网络质量检测
const checkNetworkQuality = async () => {
  try {
    const startTime = Date.now()
    await fetch('/api/health', { cache: 'no-cache' })
    const endTime = Date.now()
    const latency = endTime - startTime
    
    return {
      latency,
      quality: latency < 100 ? 'excellent' : 
               latency < 300 ? 'good' : 
               latency < 1000 ? 'fair' : 'poor'
    }
  } catch (error) {
    return { latency: -1, quality: 'offline' }
  }
}

// 事件监听器
const handleOnline = () => {
  updateOnlineStatus()
}

const handleOffline = () => {
  updateOnlineStatus()
}

// 定期检查网络状态
let statusCheckInterval

onMounted(() => {
  // 监听网络状态变化
  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)
  
  // 定期检查网络状态（每30秒）
  statusCheckInterval = setInterval(() => {
    if (Date.now() - lastCheckTime.value > 30000) {
      checkConnection()
    }
  }, 30000)
  
  // 初始检查
  checkConnection()
})

onUnmounted(() => {
  window.removeEventListener('online', handleOnline)
  window.removeEventListener('offline', handleOffline)
  
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval)
  }
})

// 暴露方法供父组件使用
defineExpose({
  checkConnection,
  isOnline: isOnline.value,
  checkNetworkQuality
})
</script>

<style lang="scss" scoped>
.network-status {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  min-width: 300px;
  max-width: 500px;
  
  .status-content {
    .status-actions {
      margin-top: 12px;
      display: flex;
      gap: 8px;
    }
  }
}

.troubleshooting-content {
  h4 {
    margin: 0 0 20px 0;
    color: #303133;
    font-size: 16px;
  }
  
  .step-actions {
    margin-top: 20px;
    text-align: center;
    
    .el-button {
      margin: 0 8px;
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .network-status {
    top: 10px;
    right: 10px;
    left: 10px;
    min-width: auto;
  }
}

// 动画效果
.network-status {
  animation: slideInRight 0.3s ease-out;
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
</style> 