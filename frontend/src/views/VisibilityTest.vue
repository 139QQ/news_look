<template>
  <div class="visibility-test">
    <!-- 基础可见性测试 -->
    <div class="test-section">
      <h1 style="color: red; font-size: 24px; background: yellow; padding: 10px;">
        🔥 如果你能看到这个红色文字，说明页面基础渲染正常
      </h1>
    </div>

    <!-- 元素定位测试 -->
    <div class="test-section" style="margin: 20px 0; padding: 20px; border: 3px solid blue; background: lightblue;">
      <h2>📍 元素定位测试</h2>
      <p>这是一个蓝色边框的测试区域</p>
      
      <!-- 绝对定位测试 -->
      <div style="position: relative; height: 100px; background: lightgray; margin: 10px 0;">
        <div style="position: absolute; top: 10px; left: 10px; background: red; color: white; padding: 5px;">
          绝对定位元素 (top: 10px, left: 10px)
        </div>
        <div style="position: absolute; top: 10px; right: 10px; background: green; color: white; padding: 5px;">
          绝对定位元素 (top: 10px, right: 10px)
        </div>
      </div>
    </div>

    <!-- CSS 样式测试 -->
    <div class="test-section" style="margin: 20px 0;">
      <h2>🎨 CSS 样式测试</h2>
      
      <!-- 透明度测试 -->
      <div style="margin: 10px 0;">
        <div style="opacity: 1; background: green; color: white; padding: 10px; margin: 5px 0;">
          透明度 opacity: 1 (应该可见)
        </div>
        <div style="opacity: 0.5; background: orange; color: white; padding: 10px; margin: 5px 0;">
          透明度 opacity: 0.5 (半透明)
        </div>
        <div style="opacity: 0.1; background: red; color: white; padding: 10px; margin: 5px 0;">
          透明度 opacity: 0.1 (几乎不可见)
        </div>
      </div>
      
      <!-- 显示属性测试 -->
      <div style="margin: 10px 0;">
        <div style="display: block; background: purple; color: white; padding: 10px; margin: 5px 0;">
          display: block (应该可见)
        </div>
        <div style="display: inline-block; background: teal; color: white; padding: 10px; margin: 5px 0;">
          display: inline-block (应该可见)
        </div>
        <div style="visibility: visible; background: navy; color: white; padding: 10px; margin: 5px 0;">
          visibility: visible (应该可见)
        </div>
      </div>
    </div>

    <!-- Z-index 层级测试 -->
    <div class="test-section" style="margin: 20px 0;">
      <h2>📚 Z-index 层级测试</h2>
      <div style="position: relative; height: 150px; background: lightgray;">
        <div style="position: absolute; top: 20px; left: 20px; width: 100px; height: 80px; background: red; z-index: 1; display: flex; align-items: center; justify-content: center; color: white;">
          Z-index: 1
        </div>
        <div style="position: absolute; top: 40px; left: 40px; width: 100px; height: 80px; background: blue; z-index: 2; display: flex; align-items: center; justify-content: center; color: white;">
          Z-index: 2
        </div>
        <div style="position: absolute; top: 60px; left: 60px; width: 100px; height: 80px; background: green; z-index: 3; display: flex; align-items: center; justify-content: center; color: white;">
          Z-index: 3
        </div>
      </div>
    </div>

    <!-- Element Plus 组件测试 -->
    <div class="test-section" style="margin: 20px 0;">
      <h2>🧩 Element Plus 组件测试</h2>
      <el-alert title="如果你能看到这个警告框，说明 Element Plus 正常工作" type="success" show-icon />
      
      <div style="margin: 10px 0;">
        <el-button type="primary">主要按钮</el-button>
        <el-button type="success">成功按钮</el-button>
        <el-button type="warning">警告按钮</el-button>
        <el-button type="danger">危险按钮</el-button>
      </div>
      
      <el-card style="margin: 10px 0;">
        <template #header>
          <span>卡片标题</span>
        </template>
        <p>这是一个 Element Plus 卡片组件的内容区域</p>
      </el-card>
    </div>

    <!-- 响应式测试 -->
    <div class="test-section" style="margin: 20px 0;">
      <h2>📱 响应式测试</h2>
      <div class="responsive-test">
        <div class="desktop-only">桌面端显示 (min-width: 768px)</div>
        <div class="mobile-only">移动端显示 (max-width: 767px)</div>
      </div>
    </div>

    <!-- JavaScript 交互测试 -->
    <div class="test-section" style="margin: 20px 0;">
      <h2>⚡ JavaScript 交互测试</h2>
      <el-button @click="testClick" type="primary">点击测试 (计数: {{ clickCount }})</el-button>
      <p>当前时间: {{ currentTime }}</p>
    </div>

    <!-- 控制台输出测试 -->
    <div class="test-section" style="margin: 20px 0;">
      <h2>🖥️ 控制台测试</h2>
      <el-button @click="logToConsole" type="info">输出测试信息到控制台</el-button>
      <p style="color: #666; font-size: 14px;">
        点击按钮后，请打开浏览器开发者工具的 Console 面板查看输出
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

// 响应式数据
const clickCount = ref(0)
const currentTime = ref('')
let timeTimer = null

// 点击测试
const testClick = () => {
  clickCount.value++
  console.log('🖱️ 按钮被点击，当前计数:', clickCount.value)
}

// 控制台输出测试
const logToConsole = () => {
  console.log('🔍 === 可见性测试调试信息 ===')
  console.log('✅ JavaScript 正常执行')
  console.log('📊 当前页面信息:', {
    url: window.location.href,
    title: document.title,
    viewport: `${window.innerWidth}x${window.innerHeight}`,
    userAgent: navigator.userAgent
  })
  console.log('🎨 Element Plus 组件状态:', {
    elementPlusLoaded: !!window.ElementPlus,
    vueVersion: '3.x'
  })
  console.log('🔍 DOM 元素检查:')
  
  // 检查主要容器
  const testContainer = document.querySelector('.visibility-test')
  if (testContainer) {
    console.log('✅ 测试容器找到:', {
      width: testContainer.offsetWidth,
      height: testContainer.offsetHeight,
      display: getComputedStyle(testContainer).display,
      visibility: getComputedStyle(testContainer).visibility,
      opacity: getComputedStyle(testContainer).opacity
    })
  } else {
    console.error('❌ 测试容器未找到')
  }
  
  console.log('🔍 === 调试信息结束 ===')
}

// 更新时间
const updateTime = () => {
  currentTime.value = new Date().toLocaleString()
}

// 生命周期
onMounted(() => {
  console.log('🚀 可见性测试页面已挂载')
  updateTime()
  timeTimer = setInterval(updateTime, 1000)
  
  // 自动输出调试信息
  setTimeout(() => {
    logToConsole()
  }, 1000)
})

onUnmounted(() => {
  if (timeTimer) {
    clearInterval(timeTimer)
  }
})
</script>

<style scoped>
.visibility-test {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.test-section {
  margin-bottom: 30px;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: #fafafa;
}

.test-section h2 {
  margin-bottom: 15px;
  color: #333;
}

.responsive-test {
  display: flex;
  gap: 20px;
}

.desktop-only {
  background: #e7f3ff;
  padding: 10px;
  border: 2px solid #409eff;
  border-radius: 4px;
}

.mobile-only {
  background: #fff2e7;
  padding: 10px;
  border: 2px solid #e6a23c;
  border-radius: 4px;
  display: none;
}

@media (max-width: 767px) {
  .desktop-only {
    display: none;
  }
  
  .mobile-only {
    display: block;
  }
  
  .responsive-test {
    flex-direction: column;
  }
}

/* 强制可见样式，避免被其他样式覆盖 */
.visibility-test * {
  box-sizing: border-box;
}
</style> 