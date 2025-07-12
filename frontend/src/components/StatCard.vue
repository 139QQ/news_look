<template>
  <el-card 
    class="stat-card hoverable fade-in" 
    :class="[type, { 'has-trend': trend !== null }]"
    :style="animationStyle"
  >
    <div class="stat-content">
      <div class="stat-icon" :class="`stat-icon--${type}`">
        <el-icon :size="iconSize">
          <component :is="icon" />
        </el-icon>
      </div>
      <div class="stat-info">
        <div class="stat-value">{{ formattedValue }}</div>
        <div class="stat-label">{{ label }}</div>
      </div>
    </div>
    
    <div v-if="trend !== null" class="stat-trend">
      <el-icon :class="trend > 0 ? 'trend-up' : 'trend-down'">
        <ArrowUp v-if="trend > 0" />
        <ArrowDown v-else />
      </el-icon>
      <span>{{ Math.abs(trend) }}%</span>
    </div>
    
    <!-- 进度条（可选） -->
    <div v-if="showProgress" class="stat-progress">
      <el-progress 
        :percentage="progressValue" 
        :stroke-width="4"
        :show-text="false"
        :color="progressColor"
      />
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowUp, ArrowDown } from '@element-plus/icons-vue'

// Props定义
const props = defineProps({
  // 卡片基本信息
  label: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    required: true
  },
  icon: {
    type: [String, Object],
    required: true
  },
  type: {
    type: String,
    default: 'primary',
    validator: (value) => ['primary', 'success', 'warning', 'info', 'danger'].includes(value)
  },
  
  // 趋势数据
  trend: {
    type: Number,
    default: null
  },
  
  // 动画设置
  animationDelay: {
    type: Number,
    default: 0
  },
  
  // 图标大小
  iconSize: {
    type: Number,
    default: 32
  },
  
  // 进度条相关
  showProgress: {
    type: Boolean,
    default: false
  },
  progressValue: {
    type: Number,
    default: 0
  },
  
  // 点击事件
  clickable: {
    type: Boolean,
    default: false
  }
})

// Emits定义
const emit = defineEmits(['click'])

// 计算属性
const formattedValue = computed(() => {
  const { value } = props
  
  // 如果是字符串且包含特殊标识，直接返回
  if (typeof value === 'string' && (value.includes('加载中') || value.includes('暂无数据'))) {
    return value
  }
  
  // 数字格式化
  const num = parseInt(value)
  if (isNaN(num)) return value
  
  // 大数字缩写
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  
  return num.toLocaleString()
})

const animationStyle = computed(() => ({
  animationDelay: `${props.animationDelay}ms`
}))

const progressColor = computed(() => {
  const colorMap = {
    primary: '#409EFF',
    success: '#67C23A',
    warning: '#E6A23C',
    info: '#909399',
    danger: '#F56C6C'
  }
  return colorMap[props.type] || colorMap.primary
})

// 事件处理
const handleClick = () => {
  if (props.clickable) {
    emit('click')
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.stat-card {
  height: 140px;
  border: none;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  
  // 卡片类型边框
  &.primary::before { 
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: $primary-color;
    z-index: 1;
  }
  
  &.success::before { 
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: $success-color;
    z-index: 1;
  }
  
  &.warning::before { 
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: $warning-color;
    z-index: 1;
  }
  
  &.info::before { 
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: $info-color;
    z-index: 1;
  }
  
  &.danger::before { 
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: $danger-color;
    z-index: 1;
  }
  
  // 卡片内容区域
  :deep(.el-card__body) {
    padding: $spacing-lg;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  
  .stat-content {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    flex: 1;
    
    .stat-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 70px;
      height: 70px;
      border-radius: 50%;
      transition: $transition-base;
      flex-shrink: 0;
      
      &--primary {
        background: rgba($primary-color, 0.1);
        color: $primary-color;
      }
      
      &--success {
        background: rgba($success-color, 0.1);
        color: $success-color;
      }
      
      &--warning {
        background: rgba($warning-color, 0.1);
        color: $warning-color;
      }
      
      &--info {
        background: rgba($info-color, 0.1);
        color: $info-color;
      }
      
      &--danger {
        background: rgba($danger-color, 0.1);
        color: $danger-color;
      }
    }
    
    .stat-info {
      flex: 1;
      min-width: 0; // 防止文本溢出
      
      .stat-value {
        font-size: 28px;
        font-weight: $font-weight-title;
        color: $text-color-primary;
        margin-bottom: 4px;
        line-height: 1.2;
        word-break: break-all;
      }
      
      .stat-label {
        font-size: $font-size-auxiliary;
        color: $text-color-secondary;
        line-height: 1.4;
      }
    }
  }
  
  .stat-trend {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 4px;
    font-size: $font-size-auxiliary;
    margin-top: $spacing-xs;
    
    .trend-up { 
      color: $success-color; 
    }
    
    .trend-down { 
      color: $danger-color; 
    }
  }
  
  .stat-progress {
    margin-top: $spacing-sm;
  }
  
  // 悬停效果增强
  &:hover {
    .stat-icon {
      transform: scale(1.1);
    }
    
    .stat-value {
      color: $primary-color;
    }
  }
  
  // 响应式调整
  @media (max-width: $breakpoint-md) {
    height: 120px;
    
    .stat-content {
      .stat-icon {
        width: 60px;
        height: 60px;
      }
      
      .stat-info .stat-value {
        font-size: 24px;
      }
    }
  }
  
  @media (max-width: $breakpoint-sm) {
    height: auto;
    min-height: 140px;
    
    .stat-content {
      flex-direction: column;
      text-align: center;
      gap: $spacing-sm;
      
      .stat-icon {
        margin-bottom: $spacing-xs;
      }
    }
  }
}

// 动画定义
.fade-in {
  animation: fadeInUp 0.6s ease-out forwards;
  opacity: 0;
  transform: translateY(20px);
}

@keyframes fadeInUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// 加载状态
.loading {
  .stat-value {
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: loading 1.5s infinite;
    border-radius: 4px;
    color: transparent;
  }
}

@keyframes loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style> 