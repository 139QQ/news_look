<template>
  <n-config-provider :theme="theme" :locale="zhCN" :date-locale="dateZhCN">
    <n-layout style="height: 100vh">
      <!-- 顶部导航栏 -->
      <n-layout-header style="height: 64px; padding: 0 24px" bordered>
        <div style="display: flex; align-items: center; justify-content: space-between; height: 100%">
          <!-- Logo和标题 -->
          <div style="display: flex; align-items: center">
            <n-icon size="32" color="#18a058" style="margin-right: 12px">
              <NewspaperOutline />
            </n-icon>
            <n-h2 style="margin: 0; font-weight: 600; color: #18a058">
              NewsLook
            </n-h2>
            <n-text depth="3" style="margin-left: 8px">财经新闻爬虫系统</n-text>
          </div>
          
          <!-- 导航菜单 -->
          <n-menu
            v-model:value="activeKey"
            mode="horizontal"
            :options="menuOptions"
            style="flex: 1; justify-content: center"
          />
          
          <!-- 工具栏 -->
          <div style="display: flex; align-items: center; gap: 12px">
            <!-- 刷新按钮 -->
            <n-button
              circle
              quaternary
              @click="refreshData"
              :loading="refreshing"
            >
              <template #icon>
                <n-icon><RefreshOutline /></n-icon>
              </template>
            </n-button>
            
            <!-- 主题切换 -->
            <n-button
              circle
              quaternary
              @click="toggleTheme"
            >
              <template #icon>
                <n-icon>
                  <MoonOutline v-if="!isDark" />
                  <SunnyOutline v-else />
                </n-icon>
              </template>
            </n-button>
            
            <!-- 设置 -->
            <n-button
              circle
              quaternary
              @click="showSettings = true"
            >
              <template #icon>
                <n-icon><SettingsOutline /></n-icon>
              </template>
            </n-button>
          </div>
        </div>
      </n-layout-header>
      
      <!-- 主体内容 -->
      <n-layout has-sider style="height: calc(100vh - 64px)">
        <!-- 侧边栏 -->
        <n-layout-sider
          bordered
          show-trigger="bar"
          collapse-mode="width"
          :collapsed-width="64"
          :width="240"
          :collapsed="collapsed"
          @collapse="collapsed = true"
          @expand="collapsed = false"
        >
          <n-menu
            v-model:value="activeKey"
            :collapsed="collapsed"
            :collapsed-width="64"
            :collapsed-icon-size="22"
            :options="sideMenuOptions"
            :indent="24"
            style="height: 100%"
          />
        </n-layout-sider>
        
        <!-- 内容区域 -->
        <n-layout-content style="padding: 24px">
          <router-view />
        </n-layout-content>
      </n-layout>
      
      <!-- 全局消息 -->
      <n-message-provider>
        <MessageHandler />
      </n-message-provider>
    </n-layout>
    
    <!-- 设置抽屉 -->
    <n-drawer v-model:show="showSettings" :width="400" placement="right">
      <n-drawer-content title="系统设置" closable>
        <SettingsPanel />
      </n-drawer-content>
    </n-drawer>
  </n-config-provider>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import {
  darkTheme,
  zhCN,
  dateZhCN,
  NIcon
} from 'naive-ui'
import {
  NewspaperOutline,
  HomeOutline,
  StatsChartOutline,
  SettingsOutline,
  CloudDownloadOutline,
  TerminalOutline,
  RefreshOutline,
  MoonOutline,
  SunnyOutline,
  DocumentTextOutline,
  TrendingUpOutline
} from '@vicons/ionicons5'

import MessageHandler from './components/MessageHandler.vue'
import SettingsPanel from './components/SettingsPanel.vue'

const router = useRouter()

// 主题相关
const isDark = ref(false)
const theme = computed(() => isDark.value ? darkTheme : null)

// 导航相关
const activeKey = ref('home')
const collapsed = ref(false)
const showSettings = ref(false)
const refreshing = ref(false)

// 创建图标渲染函数
const renderIcon = (icon) => () => h(NIcon, null, { default: () => h(icon) })

// 顶部菜单选项
const menuOptions = [
  {
    label: '首页',
    key: 'home',
    icon: renderIcon(HomeOutline)
  },
  {
    label: '新闻列表',
    key: 'news',
    icon: renderIcon(DocumentTextOutline)
  },
  {
    label: '数据统计',
    key: 'stats',
    icon: renderIcon(StatsChartOutline)
  },
  {
    label: '爬虫管理',
    key: 'crawler',
    icon: renderIcon(CloudDownloadOutline)
  }
]

// 侧边栏菜单选项
const sideMenuOptions = [
  {
    label: '首页',
    key: 'home',
    icon: renderIcon(HomeOutline)
  },
  {
    label: '新闻管理',
    key: 'news-section',
    icon: renderIcon(DocumentTextOutline),
    children: [
      {
        label: '新闻列表',
        key: 'news'
      },
      {
        label: '新闻详情',
        key: 'news-detail'
      }
    ]
  },
  {
    label: '数据分析',
    key: 'analytics-section',
    icon: renderIcon(TrendingUpOutline),
    children: [
      {
        label: '统计概览',
        key: 'stats'
      },
      {
        label: '趋势分析',
        key: 'trends'
      }
    ]
  },
  {
    label: '系统管理',
    key: 'system-section',
    icon: renderIcon(SettingsOutline),
    children: [
      {
        label: '爬虫管理',
        key: 'crawler'
      },
      {
        label: '系统设置',
        key: 'settings'
      },
      {
        label: '日志监控',
        key: 'logs'
      }
    ]
  }
]

// 方法
const toggleTheme = () => {
  isDark.value = !isDark.value
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}

const refreshData = async () => {
  refreshing.value = true
  try {
    // 这里可以调用刷新数据的API
    await new Promise(resolve => setTimeout(resolve, 1000))
  } finally {
    refreshing.value = false
  }
}

// 初始化
onMounted(() => {
  // 恢复主题设置
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme === 'dark') {
    isDark.value = true
  }
  
  // 设置当前路由
  activeKey.value = router.currentRoute.value.name || 'home'
})

// 监听路由变化
router.afterEach((to) => {
  activeKey.value = to.name || 'home'
})
</script>

<style>
/* 全局样式 */
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #d9d9d9;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #bfbfbf;
}

/* 暗色主题滚动条 */
.dark ::-webkit-scrollbar-thumb {
  background: #4a4a4a;
}

.dark ::-webkit-scrollbar-thumb:hover {
  background: #5a5a5a;
}
</style> 