<template>
  <div class="css-debugger">
    <div class="debug-header">
      <h1>🔧 CSS 调试工具</h1>
      <p>帮助检测和修复页面显示问题</p>
    </div>

    <!-- 快速检测 -->
    <el-card class="debug-section">
      <template #header>
        <span>🚀 快速检测</span>
      </template>
      
      <div class="quick-actions">
        <el-button type="primary" @click="highlightAllElements">
          高亮所有元素
        </el-button>
        <el-button type="success" @click="showElementInfo">
          显示元素信息
        </el-button>
        <el-button type="warning" @click="detectHiddenElements">
          检测隐藏元素
        </el-button>
        <el-button type="danger" @click="resetStyles">
          重置调试样式
        </el-button>
      </div>
    </el-card>

    <!-- CSS属性检测 -->
    <el-card class="debug-section">
      <template #header>
        <span>🔍 CSS 属性检测</span>
      </template>
      
      <el-row :gutter="20">
        <el-col :span="12">
          <h3>常见隐藏属性检测</h3>
          <div class="detection-results">
            <div v-for="result in detectionResults" :key="result.property">
              <el-tag 
                :type="result.issues > 0 ? 'danger' : 'success'" 
                size="small"
              >
                {{ result.property }}: {{ result.issues }} 个问题
              </el-tag>
              <div v-if="result.issues > 0" class="issue-details">
                <el-text size="small">{{ result.details }}</el-text>
              </div>
            </div>
          </div>
        </el-col>
        
        <el-col :span="12">
          <h3>元素层级信息</h3>
          <div class="z-index-info">
            <div v-for="layer in zIndexLayers" :key="layer.element">
              <div class="layer-item">
                <strong>{{ layer.element }}</strong>: z-index {{ layer.zIndex }}
                <el-tag :type="layer.type" size="small">{{ layer.status }}</el-tag>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 实时样式修改 -->
    <el-card class="debug-section">
      <template #header>
        <span>⚡ 实时样式修改</span>
      </template>
      
      <el-row :gutter="20">
        <el-col :span="8">
          <h4>目标选择器</h4>
          <el-input v-model="targetSelector" placeholder="输入CSS选择器，如 .dashboard">
            <template #prepend>选择器</template>
          </el-input>
        </el-col>
        
        <el-col :span="8">
          <h4>CSS属性</h4>
          <el-select v-model="cssProperty" placeholder="选择CSS属性">
            <el-option label="display" value="display" />
            <el-option label="visibility" value="visibility" />
            <el-option label="opacity" value="opacity" />
            <el-option label="z-index" value="z-index" />
            <el-option label="position" value="position" />
            <el-option label="overflow" value="overflow" />
            <el-option label="transform" value="transform" />
          </el-select>
        </el-col>
        
        <el-col :span="8">
          <h4>属性值</h4>
          <el-input v-model="cssValue" placeholder="输入CSS值">
            <template #append>
              <el-button @click="applyCSSRule">应用</el-button>
            </template>
          </el-input>
        </el-col>
      </el-row>
      
      <div class="applied-rules" v-if="appliedRules.length > 0">
        <h4>已应用的规则</h4>
        <div v-for="(rule, index) in appliedRules" :key="index" class="rule-item">
          <code>{{ rule.selector }} { {{ rule.property }}: {{ rule.value }}; }</code>
          <el-button size="small" type="danger" @click="removeRule(index)">移除</el-button>
        </div>
      </div>
    </el-card>

    <!-- 布局检测 -->
    <el-card class="debug-section">
      <template #header>
        <span>📐 布局检测</span>
      </template>
      
      <div class="layout-info">
        <h4>视窗信息</h4>
        <p>窗口大小: {{ viewportInfo.width }}px × {{ viewportInfo.height }}px</p>
        <p>滚动位置: x={{ viewportInfo.scrollX }}px, y={{ viewportInfo.scrollY }}px</p>
        
        <h4>元素溢出检测</h4>
        <el-button @click="detectOverflow">检测溢出元素</el-button>
        <div v-if="overflowElements.length > 0" class="overflow-results">
          <div v-for="element in overflowElements" :key="element.selector">
            <el-alert
              :title="`${element.selector} 存在溢出`"
              :description="`宽度: ${element.width}px, 容器: ${element.containerWidth}px`"
              type="warning"
              show-icon
            />
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

// 响应式数据
const targetSelector = ref('.dashboard')
const cssProperty = ref('display')
const cssValue = ref('block')
const appliedRules = ref([])

const detectionResults = ref([
  { property: 'display: none', issues: 0, details: '' },
  { property: 'visibility: hidden', issues: 0, details: '' },
  { property: 'opacity: 0', issues: 0, details: '' },
  { property: 'z-index conflicts', issues: 0, details: '' },
  { property: 'overflow: hidden', issues: 0, details: '' }
])

const zIndexLayers = ref([])
const overflowElements = ref([])

const viewportInfo = reactive({
  width: window.innerWidth,
  height: window.innerHeight,
  scrollX: window.scrollX,
  scrollY: window.scrollY
})

// 高亮所有元素
const highlightAllElements = () => {
  const style = document.createElement('style')
  style.id = 'debug-highlight'
  style.textContent = `
    * {
      outline: 1px solid red !important;
      outline-offset: -1px !important;
    }
    *:hover {
      outline: 2px solid blue !important;
      background-color: rgba(0, 0, 255, 0.1) !important;
    }
  `
  
  // 移除之前的样式
  const existing = document.getElementById('debug-highlight')
  if (existing) existing.remove()
  
  document.head.appendChild(style)
  ElMessage.success('已高亮所有元素，悬停查看详情')
}

// 显示元素信息
const showElementInfo = () => {
  let isActive = false
  
  const clickHandler = (e) => {
    e.preventDefault()
    e.stopPropagation()
    
    const element = e.target
    const rect = element.getBoundingClientRect()
    const computedStyle = window.getComputedStyle(element)
    
    const info = `
元素: ${element.tagName.toLowerCase()}${element.className ? '.' + element.className.split(' ').join('.') : ''}
位置: x=${Math.round(rect.x)}, y=${Math.round(rect.y)}
大小: ${Math.round(rect.width)} × ${Math.round(rect.height)}
display: ${computedStyle.display}
visibility: ${computedStyle.visibility}
opacity: ${computedStyle.opacity}
z-index: ${computedStyle.zIndex}
position: ${computedStyle.position}
overflow: ${computedStyle.overflow}
    `.trim()
    
    ElMessage({
      message: info,
      type: 'info',
      duration: 0,
      showClose: true
    })
    
    // 移除事件监听器
    document.removeEventListener('click', clickHandler, true)
    isActive = false
  }
  
  if (!isActive) {
    document.addEventListener('click', clickHandler, true)
    isActive = true
    ElMessage.info('点击任意元素查看详细信息')
  }
}

// 检测隐藏元素
const detectHiddenElements = () => {
  const allElements = document.querySelectorAll('*')
  const results = {
    'display: none': { count: 0, elements: [] },
    'visibility: hidden': { count: 0, elements: [] },
    'opacity: 0': { count: 0, elements: [] },
    'overflow: hidden': { count: 0, elements: [] }
  }
  
  allElements.forEach(element => {
    const style = window.getComputedStyle(element)
    
    if (style.display === 'none') {
      results['display: none'].count++
      results['display: none'].elements.push(element)
    }
    
    if (style.visibility === 'hidden') {
      results['visibility: hidden'].count++
      results['visibility: hidden'].elements.push(element)
    }
    
    if (style.opacity === '0') {
      results['opacity: 0'].count++
      results['opacity: 0'].elements.push(element)
    }
    
    if (style.overflow === 'hidden' && element.scrollHeight > element.clientHeight) {
      results['overflow: hidden'].count++
      results['overflow: hidden'].elements.push(element)
    }
  })
  
  // 更新检测结果
  detectionResults.value = [
    {
      property: 'display: none',
      issues: results['display: none'].count,
      details: results['display: none'].count > 0 ? `${results['display: none'].count} 个元素被隐藏` : ''
    },
    {
      property: 'visibility: hidden',
      issues: results['visibility: hidden'].count,
      details: results['visibility: hidden'].count > 0 ? `${results['visibility: hidden'].count} 个元素不可见` : ''
    },
    {
      property: 'opacity: 0',
      issues: results['opacity: 0'].count,
      details: results['opacity: 0'].count > 0 ? `${results['opacity: 0'].count} 个透明元素` : ''
    },
    {
      property: 'overflow: hidden',
      issues: results['overflow: hidden'].count,
      details: results['overflow: hidden'].count > 0 ? `${results['overflow: hidden'].count} 个溢出被隐藏` : ''
    }
  ]
  
  ElMessage.success('隐藏元素检测完成')
}

// 检测z-index层级
const detectZIndexLayers = () => {
  const elements = document.querySelectorAll('*')
  const layers = []
  
  elements.forEach(element => {
    const style = window.getComputedStyle(element)
    const zIndex = style.zIndex
    
    if (zIndex !== 'auto' && zIndex !== '0') {
      layers.push({
        element: element.tagName.toLowerCase() + (element.className ? '.' + element.className.split(' ')[0] : ''),
        zIndex: parseInt(zIndex),
        status: parseInt(zIndex) > 1000 ? '高' : parseInt(zIndex) > 100 ? '中' : '低',
        type: parseInt(zIndex) > 1000 ? 'danger' : parseInt(zIndex) > 100 ? 'warning' : 'info'
      })
    }
  })
  
  zIndexLayers.value = layers.sort((a, b) => b.zIndex - a.zIndex)
}

// 应用CSS规则
const applyCSSRule = () => {
  if (!targetSelector.value || !cssProperty.value || !cssValue.value) {
    ElMessage.error('请填写完整的CSS规则')
    return
  }
  
  try {
    const elements = document.querySelectorAll(targetSelector.value)
    if (elements.length === 0) {
      ElMessage.warning('未找到匹配的元素')
      return
    }
    
    elements.forEach(element => {
      element.style[cssProperty.value] = cssValue.value
    })
    
    appliedRules.value.push({
      selector: targetSelector.value,
      property: cssProperty.value,
      value: cssValue.value
    })
    
    ElMessage.success(`已应用规则到 ${elements.length} 个元素`)
  } catch (error) {
    ElMessage.error('CSS规则应用失败: ' + error.message)
  }
}

// 移除CSS规则
const removeRule = (index) => {
  appliedRules.value.splice(index, 1)
}

// 检测溢出元素
const detectOverflow = () => {
  const elements = document.querySelectorAll('*')
  const overflow = []
  
  elements.forEach(element => {
    const rect = element.getBoundingClientRect()
    const parent = element.parentElement
    
    if (parent) {
      const parentRect = parent.getBoundingClientRect()
      
      if (rect.width > parentRect.width || rect.height > parentRect.height) {
        overflow.push({
          selector: element.tagName.toLowerCase() + (element.className ? '.' + element.className.split(' ')[0] : ''),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          containerWidth: Math.round(parentRect.width),
          containerHeight: Math.round(parentRect.height)
        })
      }
    }
  })
  
  overflowElements.value = overflow
  ElMessage.info(`检测到 ${overflow.length} 个溢出元素`)
}

// 重置调试样式
const resetStyles = () => {
  // 移除调试样式
  const debugStyle = document.getElementById('debug-highlight')
  if (debugStyle) debugStyle.remove()
  
  // 重置应用的样式
  appliedRules.value.forEach(rule => {
    const elements = document.querySelectorAll(rule.selector)
    elements.forEach(element => {
      element.style[rule.property] = ''
    })
  })
  
  appliedRules.value = []
  ElMessage.success('已重置所有调试样式')
}

// 更新视窗信息
const updateViewportInfo = () => {
  viewportInfo.width = window.innerWidth
  viewportInfo.height = window.innerHeight
  viewportInfo.scrollX = window.scrollX
  viewportInfo.scrollY = window.scrollY
}

// 生命周期
onMounted(() => {
  detectZIndexLayers()
  window.addEventListener('resize', updateViewportInfo)
  window.addEventListener('scroll', updateViewportInfo)
})

onUnmounted(() => {
  resetStyles()
  window.removeEventListener('resize', updateViewportInfo)
  window.removeEventListener('scroll', updateViewportInfo)
})
</script>

<style lang="scss" scoped>
.css-debugger {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
  
  .debug-header {
    text-align: center;
    margin-bottom: 30px;
    
    h1 {
      color: #303133;
      margin-bottom: 8px;
    }
    
    p {
      color: #606266;
      margin: 0;
    }
  }
  
  .debug-section {
    margin-bottom: 30px;
  }
  
  .quick-actions {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
  }
  
  .detection-results {
    .el-tag {
      margin: 4px 8px 4px 0;
    }
    
    .issue-details {
      margin: 4px 0 8px 0;
      padding: 8px;
      background: #f5f7fa;
      border-radius: 4px;
      font-size: 12px;
    }
  }
  
  .z-index-info {
    .layer-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px;
      margin: 4px 0;
      background: #f5f7fa;
      border-radius: 4px;
    }
  }
  
  .applied-rules {
    margin-top: 20px;
    
    .rule-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px;
      margin: 4px 0;
      background: #f0f9ff;
      border: 1px solid #e1f5fe;
      border-radius: 4px;
      
      code {
        font-family: 'Courier New', monospace;
        color: #2563eb;
      }
    }
  }
  
  .layout-info {
    h4 {
      color: #303133;
      margin: 16px 0 8px 0;
    }
    
    p {
      margin: 4px 0;
      color: #606266;
    }
  }
  
  .overflow-results {
    margin-top: 16px;
    
    .el-alert {
      margin-bottom: 8px;
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .css-debugger {
    padding: 10px;
    
    .quick-actions {
      flex-direction: column;
      
      .el-button {
        width: 100%;
      }
    }
  }
}
</style> 