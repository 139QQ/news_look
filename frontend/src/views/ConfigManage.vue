<template>
  <div class="config-manage">
    <el-card>
      <template #header>
        <span>系统配置管理</span>
      </template>
      
      <el-tabs v-model="activeTab">
        <el-tab-pane label="爬虫配置" name="crawler">
          <el-form :model="crawlerConfig" label-width="120px">
            <el-form-item label="抓取间隔">
              <el-input-number v-model="crawlerConfig.interval" :min="1" :max="3600" />
              <span class="ml-10">秒</span>
            </el-form-item>
            <el-form-item label="超时时间">
              <el-input-number v-model="crawlerConfig.timeout" :min="5" :max="300" />
              <span class="ml-10">秒</span>
            </el-form-item>
            <el-form-item label="重试次数">
              <el-input-number v-model="crawlerConfig.retryCount" :min="0" :max="10" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveCrawlerConfig">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="数据库配置" name="database">
          <el-form :model="dbConfig" label-width="120px">
            <el-form-item label="数据库类型">
              <el-select v-model="dbConfig.type">
                <el-option label="SQLite" value="sqlite" />
                <el-option label="MySQL" value="mysql" />
                <el-option label="PostgreSQL" value="postgresql" />
              </el-select>
            </el-form-item>
            <el-form-item label="数据库路径">
              <el-input v-model="dbConfig.path" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveDbConfig">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="系统设置" name="system">
          <el-form :model="systemConfig" label-width="120px">
            <el-form-item label="日志级别">
              <el-select v-model="systemConfig.logLevel">
                <el-option label="DEBUG" value="debug" />
                <el-option label="INFO" value="info" />
                <el-option label="WARNING" value="warning" />
                <el-option label="ERROR" value="error" />
              </el-select>
            </el-form-item>
            <el-form-item label="日志保留天数">
              <el-input-number v-model="systemConfig.logRetentionDays" :min="1" :max="365" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveSystemConfig">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'

const activeTab = ref('crawler')

const crawlerConfig = reactive({
  interval: 60,
  timeout: 30,
  retryCount: 3
})

const dbConfig = reactive({
  type: 'sqlite',
  path: './data/db'
})

const systemConfig = reactive({
  logLevel: 'info',
  logRetentionDays: 30
})

const saveCrawlerConfig = () => {
  ElMessage.success('爬虫配置保存成功')
}

const saveDbConfig = () => {
  ElMessage.success('数据库配置保存成功')
}

const saveSystemConfig = () => {
  ElMessage.success('系统配置保存成功')
}
</script>

<style scoped lang="scss">
.config-manage {
  .ml-10 {
    margin-left: 10px;
  }
}
</style> 