<template>
  <div class="settings-container">
    <h2>系统设置</h2>
    
    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="爬虫设置" name="crawler">
        <div class="settings-section">
          <h3>爬虫配置</h3>
          <el-form :model="crawlerSettings" label-width="120px">
            <el-form-item label="爬取间隔">
              <el-input-number 
                v-model="crawlerSettings.interval" 
                :min="1" 
                :max="3600" 
                controls-position="right">
              </el-input-number>
              <span class="form-help">秒</span>
            </el-form-item>
            
            <el-form-item label="最大并发数">
              <el-input-number 
                v-model="crawlerSettings.maxConcurrent" 
                :min="1" 
                :max="10" 
                controls-position="right">
              </el-input-number>
            </el-form-item>
            
            <el-form-item label="启用源">
              <el-checkbox-group v-model="crawlerSettings.enabledSources">
                <el-checkbox label="东方财富">东方财富</el-checkbox>
                <el-checkbox label="新浪财经">新浪财经</el-checkbox>
                <el-checkbox label="腾讯财经">腾讯财经</el-checkbox>
                <el-checkbox label="网易财经">网易财经</el-checkbox>
                <el-checkbox label="凤凰财经">凤凰财经</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveCrawlerSettings">保存设置</el-button>
              <el-button @click="resetCrawlerSettings">重置</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="数据库设置" name="database">
        <div class="settings-section">
          <h3>数据库配置</h3>
          <el-form :model="dbSettings" label-width="120px">
            <el-form-item label="数据库路径">
              <el-input v-model="dbSettings.dbPath" placeholder="数据库存储路径"></el-input>
            </el-form-item>
            
            <el-form-item label="自动清理">
              <el-switch v-model="dbSettings.autoCleanup"></el-switch>
              <span class="form-help">自动清理过期数据</span>
            </el-form-item>
            
            <el-form-item label="保留天数" v-if="dbSettings.autoCleanup">
              <el-input-number 
                v-model="dbSettings.retentionDays" 
                :min="1" 
                :max="365" 
                controls-position="right">
              </el-input-number>
              <span class="form-help">天</span>
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveDbSettings">保存设置</el-button>
              <el-button @click="resetDbSettings">重置</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="系统信息" name="system">
        <div class="settings-section">
          <h3>系统信息</h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="系统版本">{{ systemInfo.version }}</el-descriptions-item>
            <el-descriptions-item label="Python版本">{{ systemInfo.pythonVersion }}</el-descriptions-item>
            <el-descriptions-item label="运行时间">{{ systemInfo.uptime }}</el-descriptions-item>
            <el-descriptions-item label="数据库大小">{{ systemInfo.dbSize }}</el-descriptions-item>
            <el-descriptions-item label="新闻总数">{{ systemInfo.newsCount }}</el-descriptions-item>
            <el-descriptions-item label="最后更新">{{ systemInfo.lastUpdate }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
export default {
  name: 'Settings',
  data() {
    return {
      activeTab: 'crawler',
      crawlerSettings: {
        interval: 300,
        maxConcurrent: 3,
        enabledSources: ['东方财富', '新浪财经', '腾讯财经']
      },
      dbSettings: {
        dbPath: './data/db',
        autoCleanup: false,
        retentionDays: 30
      },
      systemInfo: {
        version: '1.0.0',
        pythonVersion: '3.13.0',
        uptime: '0天0小时',
        dbSize: '0 MB',
        newsCount: 0,
        lastUpdate: '未知'
      }
    }
  },
  mounted() {
    this.loadSettings()
    this.loadSystemInfo()
  },
  methods: {
    async loadSettings() {
      try {
        const response = await fetch('/api/settings')
        if (response.ok) {
          const data = await response.json()
          if (data.crawler) this.crawlerSettings = { ...this.crawlerSettings, ...data.crawler }
          if (data.database) this.dbSettings = { ...this.dbSettings, ...data.database }
        }
      } catch (error) {
        console.error('加载设置失败:', error)
      }
    },
    
    async loadSystemInfo() {
      try {
        const response = await fetch('/api/system-info')
        if (response.ok) {
          const data = await response.json()
          this.systemInfo = { ...this.systemInfo, ...data }
        }
      } catch (error) {
        console.error('加载系统信息失败:', error)
      }
    },
    
    async saveCrawlerSettings() {
      try {
        const response = await fetch('/api/settings/crawler', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.crawlerSettings)
        })
        
        if (response.ok) {
          this.$message.success('爬虫设置保存成功')
        } else {
          throw new Error('保存失败')
        }
      } catch (error) {
        console.error('保存爬虫设置失败:', error)
        this.$message.error('保存爬虫设置失败')
      }
    },
    
    async saveDbSettings() {
      try {
        const response = await fetch('/api/settings/database', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.dbSettings)
        })
        
        if (response.ok) {
          this.$message.success('数据库设置保存成功')
        } else {
          throw new Error('保存失败')
        }
      } catch (error) {
        console.error('保存数据库设置失败:', error)
        this.$message.error('保存数据库设置失败')
      }
    },
    
    resetCrawlerSettings() {
      this.crawlerSettings = {
        interval: 300,
        maxConcurrent: 3,
        enabledSources: ['东方财富', '新浪财经', '腾讯财经']
      }
    },
    
    resetDbSettings() {
      this.dbSettings = {
        dbPath: './data/db',
        autoCleanup: false,
        retentionDays: 30
      }
    }
  }
}
</script>

<style scoped>
.settings-container {
  padding: 20px;
}

.settings-section {
  padding: 20px;
}

.settings-section h3 {
  margin-bottom: 20px;
  color: #303133;
}

.form-help {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}
</style> 