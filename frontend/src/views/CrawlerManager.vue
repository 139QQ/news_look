<template>
  <div class="crawler-manager">
    <el-card class="mb-20">
      <template #header>
        <div class="flex-between">
          <span>爬虫管理</span>
          <div>
            <el-button 
              type="success" 
              :loading="isStartingAll"
              @click="startAllCrawlers"
            >
              <el-icon><CaretRight /></el-icon>
              启动全部
            </el-button>
            <el-button 
              type="danger" 
              :loading="isStoppingAll"
              @click="stopAllCrawlers"
            >
              <el-icon><VideoPause /></el-icon>
              停止全部
            </el-button>
            <el-button 
              type="primary" 
              @click="refreshStatus"
              :loading="crawlerStore.isLoading"
            >
              <el-icon><Refresh /></el-icon>
              刷新状态
            </el-button>
          </div>
        </div>
      </template>
      
      <el-table 
        :data="crawlerStore.crawlers" 
        style="width: 100%"
        :loading="crawlerStore.isLoading"
        v-loading="crawlerStore.isLoading"
      >
        <el-table-column prop="display_name" label="爬虫名称" width="150">
          <template #default="{ row }">
            <div class="flex">
              <el-icon class="mr-10">
                <component :is="getSourceIcon(row.name)" />
              </el-icon>
              {{ row.display_name }}
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag 
              :type="getStatusType(row.status)"
              size="small"
            >
              <el-icon class="mr-5">
                <component :is="getStatusIcon(row.status)" />
              </el-icon>
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="success_rate" label="成功率" width="100">
          <template #default="{ row }">
            <el-progress 
              :percentage="row.success_rate" 
              :status="getProgressStatus(row.success_rate)"
              :stroke-width="8"
            />
          </template>
        </el-table-column>
        
        <el-table-column prop="last_run" label="最后运行时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.last_run) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                v-if="row.status !== 'running'"
                type="success" 
                size="small"
                :loading="loadingStates[row.name]?.starting"
                @click="startCrawler(row.name)"
              >
                <el-icon><CaretRight /></el-icon>
                启动
              </el-button>
              
              <el-button 
                v-if="row.status === 'running'"
                type="danger" 
                size="small"
                :loading="loadingStates[row.name]?.stopping"
                @click="stopCrawler(row.name)"
              >
                <el-icon><VideoPause /></el-icon>
                停止
              </el-button>
              
              <el-button 
                type="primary" 
                size="small"
                @click="showConfig(row)"
              >
                <el-icon><Setting /></el-icon>
                配置
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 爬虫统计 -->
    <el-row :gutter="20">
      <el-col :xs="24" :sm="8" :md="8" :lg="8">
        <el-card class="stat-card">
          <el-statistic 
            title="总爬虫数" 
            :value="crawlerStore.totalCrawlers"
          >
            <template #suffix>
              <el-icon><Lightning /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="8" :md="8" :lg="8">
        <el-card class="stat-card">
          <el-statistic 
            title="运行中" 
            :value="crawlerStore.activeCrawlers"
            value-style="color: #67c23a"
          >
            <template #suffix>
              <el-icon><CaretRight /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="8" :md="8" :lg="8">
        <el-card class="stat-card">
          <el-statistic 
            title="平均成功率" 
            :value="crawlerStore.averageSuccessRate"
            suffix="%"
            :value-style="getSuccessRateStyle(crawlerStore.averageSuccessRate)"
          >
            <template #suffix>
              <span>%</span>
              <el-icon><TrendCharts /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>

    <!-- 爬虫配置对话框 -->
    <el-dialog 
      v-model="configDialogVisible" 
      title="爬虫配置"
      width="600px"
    >
      <el-form :model="configForm" label-width="120px">
        <el-form-item label="爬虫名称">
          <el-input v-model="configForm.name" disabled />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="configForm.display_name" />
        </el-form-item>
        <el-form-item label="抓取间隔">
          <el-input-number 
            v-model="configForm.interval" 
            :min="1" 
            :max="3600"
            suffix="秒"
          />
        </el-form-item>
        <el-form-item label="超时时间">
          <el-input-number 
            v-model="configForm.timeout" 
            :min="5" 
            :max="300"
            suffix="秒"
          />
        </el-form-item>
        <el-form-item label="重试次数">
          <el-input-number 
            v-model="configForm.retry_count" 
            :min="0" 
            :max="10"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveConfig">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useCrawlerStore } from '@/store'
import { crawlerApi } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

// Store
const crawlerStore = useCrawlerStore()

// 加载状态
const isStartingAll = ref(false)
const isStoppingAll = ref(false)
const loadingStates = ref({})

// 配置对话框
const configDialogVisible = ref(false)
const configForm = reactive({
  name: '',
  display_name: '',
  interval: 60,
  timeout: 30,
  retry_count: 3
})

// 状态类型映射
const getStatusType = (status) => {
  const typeMap = {
    'running': 'success',
    'stopped': 'info', 
    'error': 'danger'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    'running': '运行中',
    'stopped': '已停止',
    'error': '错误'
  }
  return textMap[status] || '未知'
}

const getStatusIcon = (status) => {
  const iconMap = {
    'running': 'CaretRight',
    'stopped': 'VideoPause',
    'error': 'Warning'
  }
  return iconMap[status] || 'QuestionFilled'
}

const getSourceIcon = (name) => {
  const iconMap = {
    'sina': 'Notebook',
    'eastmoney': 'TrendCharts', 
    'tencent': 'ChatDotRound',
    'netease': 'Headset',
    'ifeng': 'Promotion'
  }
  return iconMap[name] || 'Document'
}

// 获取进度条状态
const getProgressStatus = (rate) => {
  if (rate >= 90) return 'success'
  if (rate >= 70) return ''
  if (rate >= 50) return 'warning'
  return 'exception'
}

// 获取成功率样式
const getSuccessRateStyle = (rate) => {
  if (rate >= 90) return { color: '#67c23a' }
  if (rate >= 70) return { color: '#409eff' }
  if (rate >= 50) return { color: '#e6a23c' }
  return { color: '#f56c6c' }
}

// 时间格式化
const formatTime = (time) => {
  if (!time) return '-'
  return dayjs(time).format('MM-DD HH:mm')
}

// 启动单个爬虫
const startCrawler = async (name) => {
  if (!loadingStates.value[name]) {
    loadingStates.value[name] = {}
  }
  loadingStates.value[name].starting = true
  
  try {
    const success = await crawlerStore.startCrawler(name)
    if (success) {
      ElMessage.success(`爬虫 ${name} 启动成功`)
    }
  } catch (error) {
    ElMessage.error(`爬虫 ${name} 启动失败`)
  } finally {
    loadingStates.value[name].starting = false
  }
}

// 停止单个爬虫
const stopCrawler = async (name) => {
  if (!loadingStates.value[name]) {
    loadingStates.value[name] = {}
  }
  loadingStates.value[name].stopping = true
  
  try {
    const success = await crawlerStore.stopCrawler(name)
    if (success) {
      ElMessage.success(`爬虫 ${name} 停止成功`)
    }
  } catch (error) {
    ElMessage.error(`爬虫 ${name} 停止失败`)
  } finally {
    loadingStates.value[name].stopping = false
  }
}

// 启动所有爬虫
const startAllCrawlers = async () => {
  try {
    await ElMessageBox.confirm('确定要启动所有爬虫吗？', '确认操作', {
      type: 'warning'
    })
    
    isStartingAll.value = true
    await crawlerApi.startAllCrawlers()
    await crawlerStore.fetchCrawlerStatus()
    ElMessage.success('所有爬虫启动成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('启动失败')
    }
  } finally {
    isStartingAll.value = false
  }
}

// 停止所有爬虫
const stopAllCrawlers = async () => {
  try {
    await ElMessageBox.confirm('确定要停止所有爬虫吗？', '确认操作', {
      type: 'warning'
    })
    
    isStoppingAll.value = true
    await crawlerApi.stopAllCrawlers()
    await crawlerStore.fetchCrawlerStatus()
    ElMessage.success('所有爬虫停止成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('停止失败')
    }
  } finally {
    isStoppingAll.value = false
  }
}

// 刷新状态
const refreshStatus = () => {
  crawlerStore.fetchCrawlerStatus()
}

// 显示配置
const showConfig = (crawler) => {
  Object.assign(configForm, {
    name: crawler.name,
    display_name: crawler.display_name,
    interval: 60,
    timeout: 30,
    retry_count: 3
  })
  configDialogVisible.value = true
}

// 保存配置
const saveConfig = () => {
  ElMessage.success('配置保存成功')
  configDialogVisible.value = false
}
</script>

<style scoped lang="scss">
.crawler-manager {
  .stat-card {
    margin-bottom: 20px;
  }
  
  .flex {
    display: flex;
    align-items: center;
  }
  
  .mr-5 {
    margin-right: 5px;
  }
  
  .mr-10 {
    margin-right: 10px;
  }
}
</style> 