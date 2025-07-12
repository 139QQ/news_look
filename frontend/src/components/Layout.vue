<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="sidebarWidth" class="layout-sidebar">
      <div class="logo">
        <el-icon class="logo-icon"><Lightning /></el-icon>
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
          class="menu-item"
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
          
          <el-breadcrumb separator="/" class="breadcrumb">
            <el-breadcrumb-item>
              <el-icon class="breadcrumb-icon"><House /></el-icon>
              NewsLook
            </el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentPageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <!-- 搜索框 -->
          <el-input
            v-model="searchQuery"
            placeholder="搜索新闻..."
            class="search-input"
            clearable
            @input="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          
          <el-button 
            type="text" 
            @click="appStore.toggleTheme"
            class="theme-toggle header-btn"
            title="切换主题"
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
            class="refresh-btn header-btn"
            title="刷新数据"
          >
            <el-icon><Refresh /></el-icon>
          </el-button>
          
          <!-- 用户头像占位 -->
          <div class="user-avatar">
            <el-avatar :size="32" icon="User" />
          </div>
        </div>
      </el-header>

      <!-- 页面内容 -->
      <el-main class="layout-content">
        <div class="content-wrapper">
          <router-view />
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore, useStatsStore, useCrawlerStore } from '@/store'
import { 
  Lightning, Menu, House, Search, Sunny, Moon, Refresh, User,
  Odometer, Document, Monitor, Setting, List, Tools, Files, 
  Operation, View 
} from '@element-plus/icons-vue'

// Store
const appStore = useAppStore()
const statsStore = useStatsStore()
const crawlerStore = useCrawlerStore()

// Route
const route = useRoute()

// 响应式数据
const searchQuery = ref('')

// 计算属性
const sidebarWidth = computed(() => 
  appStore.sidebarCollapsed ? '64px' : '240px'
)

const currentPageTitle = computed(() => 
  route.meta?.title || '首页'
)

// 菜单路由 - 符合设计规范的图标和结构
const menuRoutes = [
  {
    path: '/home',
    meta: { title: '首页', icon: 'House' }
  },
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

// 搜索处理
const handleSearch = (value) => {
  // TODO: 实现全局搜索功能
  console.log('搜索:', value)
}

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
  overflow: hidden;
  background-color: $bg-color-page;
}

// 🎨 侧边栏样式 - 符合设计规范
.layout-sidebar {
  background-color: $bg-color-sidebar;
  transition: width 0.3s $transition-base;
  position: relative;
  z-index: $z-index-sticky;
  height: 100vh;
  overflow: hidden;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  
  // Logo区域
  .logo {
    height: $header-height;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: $font-size-large;
    font-weight: $font-weight-title;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding: 0 $spacing-md;
    position: relative;
    
    .logo-icon {
      font-size: 28px;
      color: $primary-color;
      margin-right: $spacing-sm;
      transition: $transition-base;
      
      &:hover {
        transform: rotate(10deg);
      }
    }
    
    .logo-text {
      transition: opacity 0.3s, transform 0.3s;
      letter-spacing: 1px;
    }
  }
  
  // 菜单样式
  .sidebar-menu {
    border: none;
    background: transparent;
    padding: $spacing-sm;
    height: calc(100vh - #{$header-height});
    overflow-y: auto;
    overflow-x: hidden;
    
    // 自定义滚动条
    &::-webkit-scrollbar {
      width: 4px;
    }
    
    &::-webkit-scrollbar-track {
      background: rgba(255, 255, 255, 0.1);
    }
    
    &::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.3);
      border-radius: 2px;
    }
    
    .menu-item {
      border-radius: $border-radius-medium;
      margin-bottom: $spacing-xs;
      color: rgba(255, 255, 255, 0.8);
      transition: $transition-base;
      position: relative;
      overflow: hidden;
      
      &:hover {
        background-color: $bg-color-hover;
        color: white;
        transform: translateX(4px);
      }
      
      &.is-active {
        background: linear-gradient(135deg, $primary-color, $primary-light);
        color: white;
        box-shadow: 0 2px 8px rgba($primary-color, 0.3);
        
        &::before {
          content: '';
          position: absolute;
          left: 0;
          top: 0;
          width: 3px;
          height: 100%;
          background: white;
        }
      }
      
      .el-icon {
        font-size: 18px;
        margin-right: $spacing-sm;
      }
    }
  }
}

// 🎯 主内容区域
.layout-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

// 📊 顶部导航栏 - 符合设计规范
.layout-header {
  background: $bg-color-card;
  border-bottom: 1px solid $border-color-lighter;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  z-index: $z-index-fixed;
  padding: 0 $spacing-lg;
  display: flex;
  align-items: center;
  justify-content: space-between;
  
  .header-left {
    display: flex;
    align-items: center;
    gap: $spacing-lg;
    
    .sidebar-toggle {
      padding: $spacing-sm;
      border-radius: $border-radius-medium;
      color: $text-color-secondary;
      transition: $transition-base;
      
      &:hover {
        background-color: $bg-color-hover;
        color: $primary-color;
      }
    }
    
    .breadcrumb {
      .el-breadcrumb__item {
        font-weight: $font-weight-normal;
        
        .el-breadcrumb__inner {
          color: $text-color-secondary;
          
          &.is-link:hover {
            color: $primary-color;
          }
        }
        
        &:last-child .el-breadcrumb__inner {
          color: $text-color-primary;
          font-weight: $font-weight-title;
        }
      }
      
      .breadcrumb-icon {
        margin-right: 4px;
        color: $primary-color;
      }
    }
  }
  
  .header-right {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    
    .search-input {
      width: 280px;
      
      :deep(.el-input__inner) {
        border-radius: 6px;
        background-color: $bg-color-base;
        border: 1px solid $border-color-light;
        transition: $transition-base;
        
        &:focus {
          border-color: $primary-color;
          background-color: $bg-color-card;
        }
      }
    }
    
    .header-btn {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: $text-color-secondary;
      transition: $transition-base;
      
      &:hover {
        background-color: $bg-color-hover;
        color: $primary-color;
        transform: translateY(-1px);
      }
      
      .el-icon {
        font-size: 18px;
      }
    }
    
    .user-avatar {
      margin-left: $spacing-sm;
      cursor: pointer;
      
      .el-avatar {
        transition: $transition-base;
        
        &:hover {
          transform: scale(1.1);
        }
      }
    }
  }
}

// 📄 内容区域
.layout-content {
  flex: 1;
  overflow: auto;
  background-color: $bg-color-page;
  
  .content-wrapper {
    max-width: $container-max-width;
    margin: 0 auto;
    padding: $spacing-lg;
    min-height: 100%;
  }
}

// 📱 响应式适配
@media (max-width: $breakpoint-md) {
  .layout-header {
    padding: 0 $spacing-md;
    
    .header-left {
      gap: $spacing-md;
    }
    
    .header-right {
      gap: $spacing-sm;
      
      .search-input {
        width: 200px;
      }
    }
  }
  
  .layout-content .content-wrapper {
    padding: $spacing-md;
  }
}

@media (max-width: $breakpoint-sm) {
  .layout-header {
    padding: 0 $spacing-sm;
    
    .header-right {
      .search-input {
        display: none;
      }
    }
  }
  
  .layout-content .content-wrapper {
    padding: $spacing-sm;
  }
}

// 🎭 动画效果
.layout-sidebar,
.layout-header {
  .el-icon {
    transition: $transition-base;
  }
}

// 确保菜单项在折叠时正确显示
.layout-sidebar.el-aside--collapsed {
  .logo-text {
    opacity: 0;
    transform: translateX(-10px);
  }
  
  .sidebar-menu {
    .menu-item {
      justify-content: center;
      
      .el-icon {
        margin-right: 0;
      }
    }
  }
}
</style> 