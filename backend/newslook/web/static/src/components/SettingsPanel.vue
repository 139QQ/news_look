<template>
  <div class="settings-panel">
    <n-space vertical size="large">
      <!-- 系统设置 -->
      <div>
        <n-h3>系统设置</n-h3>
        <n-form :model="settings" label-placement="left" label-width="120px">
          <n-form-item label="自动刷新">
            <n-switch v-model:value="settings.autoRefresh" />
          </n-form-item>
          <n-form-item label="刷新间隔">
            <n-input-number
              v-model:value="settings.refreshInterval"
              :min="10"
              :max="300"
              :step="10"
              :disabled="!settings.autoRefresh"
            >
              <template #suffix>秒</template>
            </n-input-number>
          </n-form-item>
          <n-form-item label="页面大小">
            <n-select
              v-model:value="settings.pageSize"
              :options="pageSizeOptions"
            />
          </n-form-item>
        </n-form>
      </div>
      
      <!-- 显示设置 -->
      <div>
        <n-h3>显示设置</n-h3>
        <n-form :model="settings" label-placement="left" label-width="120px">
          <n-form-item label="主题">
            <n-radio-group v-model:value="settings.theme">
              <n-radio value="light">浅色</n-radio>
              <n-radio value="dark">深色</n-radio>
              <n-radio value="auto">跟随系统</n-radio>
            </n-radio-group>
          </n-form-item>
          <n-form-item label="语言">
            <n-select
              v-model:value="settings.language"
              :options="languageOptions"
            />
          </n-form-item>
          <n-form-item label="时间格式">
            <n-select
              v-model:value="settings.timeFormat"
              :options="timeFormatOptions"
            />
          </n-form-item>
        </n-form>
      </div>
      
      <!-- 爬虫设置 -->
      <div>
        <n-h3>爬虫设置</n-h3>
        <n-form :model="settings" label-placement="left" label-width="120px">
          <n-form-item label="启用来源">
            <n-checkbox-group v-model:value="settings.enabledSources">
              <n-space vertical>
                <n-checkbox value="sina">新浪财经</n-checkbox>
                <n-checkbox value="eastmoney">东方财富</n-checkbox>
                <n-checkbox value="tencent">腾讯财经</n-checkbox>
                <n-checkbox value="netease">网易财经</n-checkbox>
                <n-checkbox value="ifeng">凤凰财经</n-checkbox>
              </n-space>
            </n-checkbox-group>
          </n-form-item>
          <n-form-item label="爬取频率">
            <n-input-number
              v-model:value="settings.crawlInterval"
              :min="1"
              :max="60"
              :step="1"
            >
              <template #suffix>分钟</template>
            </n-input-number>
          </n-form-item>
        </n-form>
      </div>
      
      <!-- 数据管理 -->
      <div>
        <n-h3>数据管理</n-h3>
        <n-space vertical>
          <n-form-item label="数据保留期">
            <n-input-number
              v-model:value="settings.dataRetentionDays"
              :min="1"
              :max="365"
              :step="1"
            >
              <template #suffix>天</template>
            </n-input-number>
          </n-form-item>
          <n-space>
            <n-button @click="cleanOldData" :loading="cleaning">
              清理过期数据
            </n-button>
            <n-button @click="exportData" :loading="exporting">
              导出数据
            </n-button>
            <n-button @click="backupData" :loading="backing">
              备份数据
            </n-button>
          </n-space>
        </n-space>
      </div>
      
      <!-- 操作按钮 -->
      <div>
        <n-space>
          <n-button type="primary" @click="saveSettings" :loading="saving">
            保存设置
          </n-button>
          <n-button @click="resetSettings">
            重置设置
          </n-button>
        </n-space>
      </div>
    </n-space>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'

const message = useMessage()

const settings = ref({
  autoRefresh: true,
  refreshInterval: 30,
  pageSize: 20,
  theme: 'light',
  language: 'zh-CN',
  timeFormat: 'relative',
  enabledSources: ['sina', 'eastmoney', 'tencent', 'netease', 'ifeng'],
  crawlInterval: 30,
  dataRetentionDays: 90
})

const loading = ref({
  saving: false,
  cleaning: false,
  exporting: false,
  backing: false
})

const pageSizeOptions = [
  { label: '10条/页', value: 10 },
  { label: '20条/页', value: 20 },
  { label: '50条/页', value: 50 },
  { label: '100条/页', value: 100 }
]

const languageOptions = [
  { label: '简体中文', value: 'zh-CN' },
  { label: 'English', value: 'en-US' }
]

const timeFormatOptions = [
  { label: '相对时间（1小时前）', value: 'relative' },
  { label: '绝对时间（2024-01-01 12:00）', value: 'absolute' }
]

const saveSettings = async () => {
  loading.value.saving = true
  try {
    // 保存设置到本地存储
    localStorage.setItem('appSettings', JSON.stringify(settings.value))
    message.success('设置已保存')
  } catch (error) {
    message.error('保存设置失败')
  } finally {
    loading.value.saving = false
  }
}

const resetSettings = () => {
  settings.value = {
    autoRefresh: true,
    refreshInterval: 30,
    pageSize: 20,
    theme: 'light',
    language: 'zh-CN',
    timeFormat: 'relative',
    enabledSources: ['sina', 'eastmoney', 'tencent', 'netease', 'ifeng'],
    crawlInterval: 30,
    dataRetentionDays: 90
  }
  message.info('设置已重置')
}

const cleanOldData = async () => {
  loading.value.cleaning = true
  try {
    // 这里调用清理数据的API
    await new Promise(resolve => setTimeout(resolve, 2000))
    message.success('过期数据清理完成')
  } catch (error) {
    message.error('清理数据失败')
  } finally {
    loading.value.cleaning = false
  }
}

const exportData = async () => {
  loading.value.exporting = true
  try {
    // 这里调用导出数据的API
    await new Promise(resolve => setTimeout(resolve, 2000))
    message.success('数据导出完成')
  } catch (error) {
    message.error('导出数据失败')
  } finally {
    loading.value.exporting = false
  }
}

const backupData = async () => {
  loading.value.backing = true
  try {
    // 这里调用备份数据的API
    await new Promise(resolve => setTimeout(resolve, 2000))
    message.success('数据备份完成')
  } catch (error) {
    message.error('备份数据失败')
  } finally {
    loading.value.backing = false
  }
}

onMounted(() => {
  // 从本地存储加载设置
  const savedSettings = localStorage.getItem('appSettings')
  if (savedSettings) {
    try {
      settings.value = { ...settings.value, ...JSON.parse(savedSettings) }
    } catch (error) {
      console.error('加载设置失败:', error)
    }
  }
})
</script>

<style scoped>
.settings-panel {
  max-width: 600px;
}
</style> 