<template>
  <div class="test-page">
    <div class="test-container">
      <h1>🧪 系统测试页面</h1>
      <p>这是一个测试页面，用于验证基本功能是否正常</p>
      
      <!-- 基础组件测试 -->
      <div class="test-section">
        <h2>📋 基础组件测试</h2>
        
        <!-- 按钮测试 -->
        <div class="test-group">
          <h3>按钮组件</h3>
          <el-button type="primary">主要按钮</el-button>
          <el-button type="success">成功按钮</el-button>
          <el-button type="warning">警告按钮</el-button>
          <el-button type="danger">危险按钮</el-button>
        </div>
        
        <!-- 卡片测试 -->
        <div class="test-group">
          <h3>卡片组件</h3>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-card class="test-card">
                <template #header>
                  <span>测试卡片 1</span>
                </template>
                <div>这是卡片内容</div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="test-card">
                <template #header>
                  <span>测试卡片 2</span>
                </template>
                <div>这是卡片内容</div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="test-card">
                <template #header>
                  <span>测试卡片 3</span>
                </template>
                <div>这是卡片内容</div>
              </el-card>
            </el-col>
          </el-row>
        </div>
        
        <!-- 图标测试 -->
        <div class="test-group">
          <h3>图标组件</h3>
          <div class="icon-grid">
            <div class="icon-item">
              <el-icon size="24" color="#409EFF"><Edit /></el-icon>
              <span>Edit</span>
            </div>
            <div class="icon-item">
              <el-icon size="24" color="#67C23A"><Check /></el-icon>
              <span>Check</span>
            </div>
            <div class="icon-item">
              <el-icon size="24" color="#E6A23C"><Warning /></el-icon>
              <span>Warning</span>
            </div>
            <div class="icon-item">
              <el-icon size="24" color="#F56C6C"><Close /></el-icon>
              <span>Close</span>
            </div>
          </div>
        </div>
        
        <!-- API 测试 -->
        <div class="test-group">
          <h3>API 连接测试</h3>
          <div class="api-test">
            <el-button type="primary" @click="testHealthAPI" :loading="apiTesting">
              测试健康检查 API
            </el-button>
            <el-button type="success" @click="testStatsAPI" :loading="apiTesting">
              测试统计 API
            </el-button>
            <el-button type="info" @click="testCrawlerAPI" :loading="apiTesting">
              测试爬虫 API
            </el-button>
          </div>
          
          <div class="api-results" v-if="apiResults.length > 0">
            <h4>测试结果：</h4>
            <ul>
              <li 
                v-for="(result, index) in apiResults" 
                :key="index"
                :class="result.success ? 'success' : 'error'"
              >
                {{ result.message }}
              </li>
            </ul>
          </div>
        </div>
        
        <!-- 表格测试 -->
        <div class="test-group">
          <h3>表格组件</h3>
          <el-table :data="tableData" style="width: 100%">
            <el-table-column prop="name" label="名称" width="180" />
            <el-table-column prop="status" label="状态" width="180">
              <template #default="{ row }">
                <el-tag :type="getTagType(row.status)">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="value" label="数值" />
          </el-table>
        </div>
      </div>
      
      <!-- 导航测试 -->
      <div class="test-section">
        <h2>🧭 路由导航测试</h2>
        <div class="nav-test">
          <el-button @click="$router.push('/dashboard')">
            跳转到 Dashboard
          </el-button>
          <el-button @click="$router.push('/error-diagnostics')">
            跳转到错误诊断
          </el-button>
          <el-button @click="$router.push('/news-list')">
            跳转到新闻列表
          </el-button>
          <el-button @click="$router.push('/crawler-manager')">
            跳转到爬虫管理
          </el-button>
        </div>
      </div>
      
      <!-- 系统信息 -->
      <div class="test-section">
        <h2>ℹ️ 系统信息</h2>
        <div class="system-info">
          <p><strong>时间：</strong>{{ currentTime }}</p>
          <p><strong>用户代理：</strong>{{ userAgent }}</p>
          <p><strong>当前路径：</strong>{{ currentPath }}</p>
          <p><strong>Vue 版本：</strong>{{ vueVersion }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Edit, Check, Warning, Close } from '@element-plus/icons-vue'

const route = useRoute()

// 响应式数据
const currentTime = ref('')
const apiTesting = ref(false)
const apiResults = ref([])
const tableData = ref([
  { name: '测试项目 1', status: 'success', value: 100 },
  { name: '测试项目 2', status: 'warning', value: 85 },
  { name: '测试项目 3', status: 'error', value: 42 },
  { name: '测试项目 4', status: 'info', value: 78 }
])

// 计算属性
const userAgent = navigator.userAgent
const currentPath = route.path
const vueVersion = '3.4.0' // 这里应该从 package.json 获取，但为了简化直接写死

// 定时器
let timeTimer = null

// 方法
const updateTime = () => {
  currentTime.value = new Date().toLocaleString('zh-CN')
}

const getTagType = (status) => {
  switch (status) {
    case 'success': return 'success'
    case 'warning': return 'warning'
    case 'error': return 'danger'
    case 'info': return 'info'
    default: return ''
  }
}

// API 测试方法
const testHealthAPI = async () => {
  apiTesting.value = true
  try {
    const response = await fetch('/api/health')
    if (response.ok) {
      const data = await response.json()
      apiResults.value.push({
        success: true,
        message: `✅ 健康检查 API 成功: ${data.status || 'healthy'}`
      })
      ElMessage.success('健康检查 API 测试成功')
    } else {
      throw new Error(`HTTP ${response.status}`)
    }
  } catch (error) {
    apiResults.value.push({
      success: false,
      message: `❌ 健康检查 API 失败: ${error.message}`
    })
    ElMessage.error('健康检查 API 测试失败')
  } finally {
    apiTesting.value = false
  }
}

const testStatsAPI = async () => {
  apiTesting.value = true
  try {
    const response = await fetch('/api/stats')
    if (response.ok) {
      const data = await response.json()
      apiResults.value.push({
        success: true,
        message: `✅ 统计 API 成功: 总新闻 ${data.total_news || 0} 条`
      })
      ElMessage.success('统计 API 测试成功')
    } else {
      throw new Error(`HTTP ${response.status}`)
    }
  } catch (error) {
    apiResults.value.push({
      success: false,
      message: `❌ 统计 API 失败: ${error.message}`
    })
    ElMessage.error('统计 API 测试失败')
  } finally {
    apiTesting.value = false
  }
}

const testCrawlerAPI = async () => {
  apiTesting.value = true
  try {
    const response = await fetch('/api/crawler/status')
    if (response.ok) {
      const data = await response.json()
      const count = data.data ? data.data.length : 0
      apiResults.value.push({
        success: true,
        message: `✅ 爬虫 API 成功: 找到 ${count} 个爬虫`
      })
      ElMessage.success('爬虫 API 测试成功')
    } else {
      throw new Error(`HTTP ${response.status}`)
    }
  } catch (error) {
    apiResults.value.push({
      success: false,
      message: `❌ 爬虫 API 失败: ${error.message}`
    })
    ElMessage.error('爬虫 API 测试失败')
  } finally {
    apiTesting.value = false
  }
}

// 生命周期
onMounted(() => {
  console.log('测试页面已挂载')
  updateTime()
  timeTimer = setInterval(updateTime, 1000)
  
  // 显示挂载成功消息
  ElMessage.success('测试页面加载成功！')
})

onUnmounted(() => {
  if (timeTimer) {
    clearInterval(timeTimer)
  }
})
</script>

<style lang="scss" scoped>
.test-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  
  .test-container {
    background: #fff;
    border-radius: 8px;
    padding: 30px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    
    h1 {
      text-align: center;
      color: #303133;
      margin-bottom: 10px;
    }
    
    > p {
      text-align: center;
      color: #606266;
      margin-bottom: 40px;
    }
  }
  
  .test-section {
    margin-bottom: 40px;
    
    h2 {
      color: #409EFF;
      border-bottom: 2px solid #409EFF;
      padding-bottom: 10px;
      margin-bottom: 30px;
    }
  }
  
  .test-group {
    margin-bottom: 30px;
    
    h3 {
      color: #606266;
      margin-bottom: 15px;
    }
  }
  
  .test-card {
    margin-bottom: 20px;
  }
  
  .icon-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
    gap: 20px;
    margin-top: 15px;
    
    .icon-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      padding: 15px;
      border: 1px solid #e4e7ed;
      border-radius: 6px;
      transition: all 0.3s;
      
      &:hover {
        border-color: #409EFF;
        background: #f0f9ff;
      }
      
      span {
        font-size: 12px;
        color: #606266;
      }
    }
  }
  
  .api-test {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 20px;
  }
  
  .api-results {
    background: #f5f7fa;
    padding: 15px;
    border-radius: 6px;
    
    h4 {
      margin: 0 0 10px 0;
      color: #303133;
    }
    
    ul {
      margin: 0;
      padding-left: 20px;
      
      li {
        margin-bottom: 5px;
        
        &.success {
          color: #67C23A;
        }
        
        &.error {
          color: #F56C6C;
        }
      }
    }
  }
  
  .nav-test {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }
  
  .system-info {
    background: #f5f7fa;
    padding: 20px;
    border-radius: 6px;
    
    p {
      margin: 8px 0;
      color: #606266;
      
      strong {
        color: #303133;
        min-width: 100px;
        display: inline-block;
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .test-page {
    padding: 10px;
    
    .test-container {
      padding: 20px;
    }
    
    .icon-grid {
      grid-template-columns: repeat(2, 1fr);
    }
    
    .api-test,
    .nav-test {
      flex-direction: column;
      
      .el-button {
        width: 100%;
      }
    }
  }
}
</style> 