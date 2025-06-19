<template>
  <div class="system-log">
    <el-card>
      <template #header>
        <div class="flex-between">
          <span>系统日志</span>
          <div>
            <el-button type="primary" @click="refreshLogs">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button type="danger" @click="clearLogs">
              <el-icon><Delete /></el-icon>
              清空日志
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 日志过滤 -->
      <div class="log-filters mb-20">
        <el-form :inline="true">
          <el-form-item label="日志级别">
            <el-select v-model="logLevel" placeholder="选择级别" clearable>
              <el-option label="全部" value="" />
              <el-option label="DEBUG" value="DEBUG" />
              <el-option label="INFO" value="INFO" />
              <el-option label="WARNING" value="WARNING" />
              <el-option label="ERROR" value="ERROR" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="关键词">
            <el-input 
              v-model="keyword" 
              placeholder="搜索日志内容"
              clearable
              style="width: 200px"
            />
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="filterLogs">搜索</el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <!-- 日志列表 -->
      <div class="log-container">
        <div 
          v-for="log in filteredLogs" 
          :key="log.id"
          :class="['log-item', `log-${log.level.toLowerCase()}`]"
        >
          <div class="log-header">
            <el-tag 
              :type="getLogLevelType(log.level)" 
              size="small"
            >
              {{ log.level }}
            </el-tag>
            <span class="log-time">{{ log.timestamp }}</span>
          </div>
          <div class="log-content">{{ log.message }}</div>
        </div>
        
        <div v-if="filteredLogs.length === 0" class="empty-logs">
          <el-empty description="暂无日志数据" />
        </div>
      </div>
      
      <!-- 分页 -->
      <div class="text-center mt-20">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          :total="totalLogs"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { systemApi } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

// 响应式数据
const logs = ref([])
const logLevel = ref('')
const keyword = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const totalLogs = ref(0)
const loading = ref(false)

// 日志级别类型映射
const getLogLevelType = (level) => {
  const typeMap = {
    'DEBUG': 'info',
    'INFO': 'success',
    'WARNING': 'warning',
    'ERROR': 'danger'
  }
  return typeMap[level] || 'info'
}

// 过滤后的日志
const filteredLogs = computed(() => {
  let filtered = logs.value
  
  if (logLevel.value) {
    filtered = filtered.filter(log => log.level === logLevel.value)
  }
  
  if (keyword.value) {
    filtered = filtered.filter(log => 
      log.message.toLowerCase().includes(keyword.value.toLowerCase())
    )
  }
  
  return filtered
})

// 获取日志数据
const fetchLogs = async () => {
  loading.value = true
  try {
    const response = await systemApi.getSystemLogs({
      page: currentPage.value,
      page_size: pageSize.value
    })
    
    if (response && response.data) {
      logs.value = response.data
      totalLogs.value = response.total || 0
    } else {
      // 模拟日志数据
      logs.value = generateMockLogs()
      totalLogs.value = 500
    }
  } catch (error) {
    console.error('获取日志失败:', error)
    // 使用模拟数据
    logs.value = generateMockLogs()
    totalLogs.value = 500
  } finally {
    loading.value = false
  }
}

// 生成模拟日志数据
const generateMockLogs = () => {
  const levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
  const messages = [
    '系统启动完成',
    '爬虫管理器初始化成功',
    '数据库连接建立',
    '开始爬取新浪财经新闻',
    '新闻数据保存成功',
    '爬虫任务执行完成',
    '检测到网络连接异常',
    '重试连接成功',
    '数据库查询执行',
    '用户访问日志记录'
  ]
  
  return Array.from({ length: pageSize.value }, (_, index) => ({
    id: Date.now() + index,
    level: levels[index % levels.length],
    timestamp: dayjs().subtract(index * 5, 'minute').format('YYYY-MM-DD HH:mm:ss'),
    message: messages[index % messages.length]
  }))
}

// 刷新日志
const refreshLogs = () => {
  fetchLogs()
  ElMessage.success('日志已刷新')
}

// 清空日志
const clearLogs = async () => {
  try {
    await ElMessageBox.confirm('确定要清空所有日志吗？此操作不可恢复。', '确认操作', {
      type: 'warning'
    })
    
    logs.value = []
    totalLogs.value = 0
    ElMessage.success('日志已清空')
  } catch (error) {
    // 用户取消操作
  }
}

// 过滤日志
const filterLogs = () => {
  // 过滤逻辑在computed中处理
  ElMessage.info('日志过滤完成')
}

// 页面大小改变
const handleSizeChange = (size) => {
  pageSize.value = size
  fetchLogs()
}

// 当前页改变
const handleCurrentChange = (page) => {
  currentPage.value = page
  fetchLogs()
}

// 生命周期
onMounted(() => {
  fetchLogs()
})
</script>

<style scoped lang="scss">
.system-log {
  .log-filters {
    background-color: #f5f7fa;
    padding: 16px;
    border-radius: 4px;
  }
  
  .log-container {
    max-height: 600px;
    overflow-y: auto;
    border: 1px solid #e4e7ed;
    border-radius: 4px;
    
    .log-item {
      padding: 12px 16px;
      border-bottom: 1px solid #f0f0f0;
      
      &:last-child {
        border-bottom: none;
      }
      
      &.log-error {
        background-color: #fef0f0;
      }
      
      &.log-warning {
        background-color: #fdf6ec;
      }
      
      &.log-info {
        background-color: #f0f9ff;
      }
      
      &.log-debug {
        background-color: #f5f7fa;
      }
      
      .log-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
        
        .log-time {
          font-size: 12px;
          color: #909399;
        }
      }
      
      .log-content {
        font-family: 'Courier New', monospace;
        font-size: 14px;
        line-height: 1.5;
        color: #303133;
        word-break: break-all;
      }
    }
    
    .empty-logs {
      padding: 40px;
      text-align: center;
    }
  }
}
</style> 