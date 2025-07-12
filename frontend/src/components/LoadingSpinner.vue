<template>
  <div class="loading-spinner" :class="{ 'full-screen': fullscreen }">
    <div class="spinner-container">
      <div class="spinner" :style="spinnerStyle">
        <div class="spinner-inner">
          <div class="spinner-circle" v-for="n in 8" :key="n" :style="getCircleStyle(n)"></div>
        </div>
      </div>
      
      <div class="loading-text" v-if="text">
        {{ text }}
      </div>
      
      <div class="loading-progress" v-if="showProgress">
        <el-progress 
          :percentage="progress" 
          :stroke-width="4"
          :show-text="false"
          color="#409eff"
        />
        <span class="progress-text">{{ progress }}%</span>
      </div>
    </div>
    
    <div class="loading-backdrop" v-if="fullscreen"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  // 是否全屏显示
  fullscreen: {
    type: Boolean,
    default: false
  },
  // 加载文本
  text: {
    type: String,
    default: ''
  },
  // 大小
  size: {
    type: String,
    default: 'medium', // small, medium, large
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  },
  // 颜色
  color: {
    type: String,
    default: '#409eff'
  },
  // 是否显示进度
  showProgress: {
    type: Boolean,
    default: false
  },
  // 进度值
  progress: {
    type: Number,
    default: 0,
    validator: (value) => value >= 0 && value <= 100
  }
})

// 计算旋转器样式
const spinnerStyle = computed(() => {
  const sizes = {
    small: '32px',
    medium: '48px',
    large: '64px'
  }
  
  return {
    width: sizes[props.size],
    height: sizes[props.size]
  }
})

// 获取圆圈样式
const getCircleStyle = (index) => {
  const delay = (index - 1) * 0.1
  return {
    backgroundColor: props.color,
    animationDelay: `${delay}s`
  }
}
</script>

<style lang="scss" scoped>
.loading-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  
  &.full-screen {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 9999;
    
    .loading-backdrop {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(255, 255, 255, 0.8);
      backdrop-filter: blur(4px);
    }
  }
  
  .spinner-container {
    position: relative;
    z-index: 10;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
  }
  
  .spinner {
    position: relative;
    
    .spinner-inner {
      position: relative;
      width: 100%;
      height: 100%;
      animation: rotate 2s linear infinite;
    }
    
    .spinner-circle {
      position: absolute;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      animation: scale 1.6s ease-in-out infinite;
      
      &:nth-child(1) { top: 0; left: 50%; transform: translateX(-50%); }
      &:nth-child(2) { top: 25%; right: 0; transform: translateY(-50%); }
      &:nth-child(3) { bottom: 0; right: 25%; transform: translateX(50%); }
      &:nth-child(4) { bottom: 25%; left: 0; transform: translateY(50%); }
      &:nth-child(5) { bottom: 0; left: 50%; transform: translateX(-50%); }
      &:nth-child(6) { bottom: 25%; left: 0; transform: translateY(50%); }
      &:nth-child(7) { top: 0; left: 25%; transform: translateX(-50%); }
      &:nth-child(8) { top: 25%; left: 0; transform: translateY(-50%); }
    }
  }
  
  .loading-text {
    font-size: 14px;
    color: #606266;
    font-weight: 500;
    text-align: center;
  }
  
  .loading-progress {
    width: 200px;
    text-align: center;
    
    .progress-text {
      display: block;
      margin-top: 8px;
      font-size: 12px;
      color: #909399;
    }
  }
}

@keyframes rotate {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

@keyframes scale {
  0%, 100% {
    transform: scale(0.5);
    opacity: 0.5;
  }
  50% {
    transform: scale(1);
    opacity: 1;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .loading-spinner {
    .loading-progress {
      width: 150px;
    }
    
    .loading-text {
      font-size: 12px;
    }
  }
}
</style> 