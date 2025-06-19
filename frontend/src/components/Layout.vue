<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="sidebarWidth" class="layout-sidebar">
      <div class="logo">
        <el-icon><Lightning /></el-icon>
        <span v-show="!appStore.sidebarCollapsed" class="logo-text">NewsLook</span>
      </div>
      
      <el-menu
        :default-active="$route.path"
        class="sidebar-menu"
        :collapse="appStore.sidebarCollapsed"
        :collapse-transition="false"
        router
      >
        <el-menu-item
          v-for="route in menuRoutes"
          :key="route.path"
          :index="route.path"
        >
          <el-icon><component :is="route.meta.icon" /></el-icon>
          <template #title>{{ route.meta.title }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="layout-main">
      <!-- 顶部栏 -->
      <el-header class="layout-header">
        <div class="header-left">
          <el-button 
            type="text" 
            @click="appStore.toggleSidebar"
            class="sidebar-toggle"
          >
            <el-icon><Menu /></el-icon>
          </el-button>
          
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>NewsLook</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentPageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <el-button 
            type="text" 
            @click="appStore.toggleTheme"
            class="theme-toggle"
          >
            <el-icon>
              <Sunny v-if="appStore.isDark" />
              <Moon v-else />
            </el-icon>
          </el-button>
          
          <el-button 
            type="text" 
            @click="refreshData"
            :loading="appStore.loading"
          >
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </el-header>

      <!-- 页面内容 -->
      <el-main class="layout-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore, useStatsStore, useCrawlerStore } from '@/store'

// Store
const appStore = useAppStore()
const statsStore = useStatsStore()
const crawlerStore = useCrawlerStore()

// Route
const route = useRoute()

// 计算属性
const sidebarWidth = computed(() => 
  appStore.sidebarCollapsed ? '64px' : '200px'
)

const currentPageTitle = computed(() => 
  route.meta?.title || '首页'
)

// 菜单路由
const menuRoutes = [
  {
    path: '/dashboard',
    meta: { title: '数据概览', icon: 'Odometer' }
  },
  {
    path: '/crawler-manager',
    meta: { title: '爬虫管理', icon: 'Lightning' }
  },
  {
    path: '/news-list',
    meta: { title: '新闻列表', icon: 'Document' }
  },
  {
    path: '/data-monitor',
    meta: { title: '数据监控', icon: 'Monitor' }
  },
  {
    path: '/config-manage',
    meta: { title: '配置管理', icon: 'Setting' }
  },
  {
    path: '/system-log',
    meta: { title: '系统日志', icon: 'List' }
  },
  {
    path: '/error-diagnostics',
    meta: { title: '错误诊断', icon: 'Tools' }
  },
  {
    path: '/test',
    meta: { title: '系统测试', icon: 'Files' }
  },
  {
    path: '/css-debugger',
    meta: { title: 'CSS调试', icon: 'Operation' }
  },
  {
    path: '/visibility-test',
    meta: { title: '可见性测试', icon: 'View' }
  }
]

// 刷新数据
const refreshData = async () => {
  appStore.setLoading(true)
  try {
    await Promise.all([
      statsStore.fetchStats(),
      crawlerStore.fetchCrawlerStatus()
    ])
  } finally {
    appStore.setLoading(false)
  }
}

// 生命周期
onMounted(() => {
  refreshData()
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.layout-container {
  height: 100vh;
  width: 100%;
  overflow: hidden; /* 防止整体页面滚动 */
  position: relative; /* 确保定位上下文 */
}

.layout-sidebar {
  background-color: #001529;
  transition: width 0.3s;
  position: relative;
  z-index: $z-index-normal;
  height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
  
  .logo {
    height: $header-height;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 18px;
    font-weight: bold;
    border-bottom: 1px solid #1f1f1f;
    
    .el-icon {
      font-size: 24px;
      margin-right: 8px;
    }
    
    .logo-text {
      transition: opacity 0.3s;
    }
  }
  
  .sidebar-menu {
    border-right: none;
    background-color: #001529;
    
    :deep(.el-menu-item) {
      color: rgba(255, 255, 255, 0.65);
      
      &:hover {
        background-color: #1890ff;
        color: white;
      }
      
      &.is-active {
        background-color: #1890ff;
        color: white;
      }
    }
  }
}

.layout-header {
  background-color: white;
  border-bottom: 1px solid $border-color-light;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  position: relative;
  z-index: $z-index-normal + 1;
  height: $header-height;
  flex-shrink: 0;
  
  .header-left {
    display: flex;
    align-items: center;
    
    .sidebar-toggle {
      margin-right: 16px;
      font-size: 18px;
    }
  }
  
  .header-right {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .el-button {
      font-size: 16px;
    }
  }
}

.layout-content {
  background-color: $bg-color-page;
  height: calc(100vh - #{$header-height});
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  padding: 0; /* 移除默认padding */
}

.layout-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  position: relative;
}

// 暗色主题
.dark {
  .layout-header {
    background-color: #1a1a1a;
    border-bottom-color: #333;
    color: white;
  }
  
  .layout-content {
    background-color: #141414;
  }
}
</style> 