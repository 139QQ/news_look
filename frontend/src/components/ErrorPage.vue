<template>
  <div class="error-page">
    <div class="error-container">
      <div class="error-icon">
        <el-icon :size="120">
          <component :is="errorConfig.icon" />
        </el-icon>
      </div>
      
      <div class="error-content">
        <h1 class="error-code">{{ errorCode }}</h1>
        <h2 class="error-title">{{ errorConfig.title }}</h2>
        <p class="error-description">{{ errorConfig.description }}</p>
        
        <div class="error-actions">
          <el-button type="primary" @click="goHome">
            <el-icon><House /></el-icon>
            返回首页
          </el-button>
          <el-button @click="goBack" v-if="canGoBack">
            <el-icon><ArrowLeft /></el-icon>
            返回上页
          </el-button>
          <el-button @click="reload">
            <el-icon><Refresh /></el-icon>
            重新加载
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 装饰性元素 -->
    <div class="decoration">
      <div class="floating-icon" v-for="n in 6" :key="n" :style="getFloatingStyle(n)">
        <el-icon>
          <component :is="getRandomIcon()" />
        </el-icon>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  errorCode: {
    type: [String, Number],
    default: '404'
  }
})

const router = useRouter()

// 错误配置
const errorConfigs = {
  '404': {
    icon: 'DocumentDelete',
    title: '页面未找到',
    description: '抱歉，您访问的页面不存在或已被移除。'
  },
  '403': {
    icon: 'Lock',
    title: '访问被拒绝',
    description: '您没有权限访问此页面，请联系管理员。'
  },
  '500': {
    icon: 'Warning',
    title: '服务器错误',
    description: '服务器遇到了一个错误，请稍后再试。'
  },
  'network': {
    icon: 'Connection',
    title: '网络连接异常',
    description: '无法连接到服务器，请检查您的网络连接。'
  }
}

const errorConfig = computed(() => {
  return errorConfigs[props.errorCode] || errorConfigs['404']
})

const canGoBack = computed(() => {
  return window.history.length > 1
})

// 方法
const goHome = () => {
  router.push('/')
}

const goBack = () => {
  router.go(-1)
}

const reload = () => {
  window.location.reload()
}

// 装饰性浮动图标
const getRandomIcon = () => {
  const icons = ['Document', 'Lightning', 'Connection', 'Monitor', 'Setting']
  return icons[Math.floor(Math.random() * icons.length)]
}

const getFloatingStyle = (index) => {
  const positions = [
    { top: '10%', left: '10%', delay: '0s' },
    { top: '20%', right: '15%', delay: '1s' },
    { bottom: '30%', left: '8%', delay: '2s' },
    { bottom: '20%', right: '10%', delay: '3s' },
    { top: '60%', left: '20%', delay: '4s' },
    { top: '40%', right: '25%', delay: '5s' }
  ]
  
  const position = positions[index - 1]
  return {
    ...position,
    animationDelay: position.delay
  }
}

onMounted(() => {
  // 添加页面进入动画
  const container = document.querySelector('.error-container')
  if (container) {
    container.style.animation = 'fadeInUp 0.6s ease-out'
  }
})
</script>

<style lang="scss" scoped>
.error-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
  
  .error-container {
    text-align: center;
    background: rgba(255, 255, 255, 0.95);
    padding: 60px 40px;
    border-radius: 20px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    max-width: 500px;
    width: 90%;
    z-index: 10;
    position: relative;
    
    .error-icon {
      color: #409eff;
      margin-bottom: 30px;
      opacity: 0.8;
    }
    
    .error-code {
      font-size: 72px;
      font-weight: bold;
      background: linear-gradient(135deg, #667eea, #764ba2);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin: 0 0 20px 0;
      line-height: 1;
    }
    
    .error-title {
      font-size: 28px;
      color: #303133;
      margin: 0 0 15px 0;
      font-weight: 600;
    }
    
    .error-description {
      font-size: 16px;
      color: #606266;
      margin: 0 0 40px 0;
      line-height: 1.6;
    }
    
    .error-actions {
      display: flex;
      gap: 15px;
      justify-content: center;
      flex-wrap: wrap;
      
      .el-button {
        min-width: 120px;
      }
    }
  }
  
  .decoration {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    
    .floating-icon {
      position: absolute;
      color: rgba(255, 255, 255, 0.2);
      font-size: 24px;
      animation: float 6s ease-in-out infinite;
      
      @keyframes float {
        0%, 100% {
          transform: translateY(0px) rotate(0deg);
        }
        50% {
          transform: translateY(-20px) rotate(10deg);
        }
      }
    }
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// 响应式设计
@media (max-width: 768px) {
  .error-page {
    .error-container {
      padding: 40px 20px;
      
      .error-code {
        font-size: 56px;
      }
      
      .error-title {
        font-size: 24px;
      }
      
      .error-description {
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
    }
    
    .decoration .floating-icon {
      display: none;
    }
  }
}
</style> 