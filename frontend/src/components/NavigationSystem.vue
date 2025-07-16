<template>
  <div class="navigation-system">
    <!-- 侧边栏导航 -->
    <div class="sidebar-navigation" :class="{ 'collapsed': isCollapsed }">
      <div class="sidebar-header">
        <div class="logo-section">
          <el-icon class="logo-icon">
            <data-board />
          </el-icon>
          <h2 v-if="!isCollapsed" class="logo-title">NewsLook</h2>
        </div>
        <el-button 
          type="text" 
          @click="toggleSidebar"
          class="collapse-btn"
          :class="{ 'collapsed': isCollapsed }"
        >
          <el-icon>
            <expand v-if="isCollapsed" />
            <fold v-else />
          </el-icon>
        </el-button>
      </div>
      
      <div class="sidebar-content">
        <el-scrollbar class="sidebar-scrollbar">
          <!-- 主导航菜单 -->
          <el-menu
            :default-active="activeMenuKey"
            :collapse="isCollapsed"
            :collapse-transition="false"
            :unique-opened="true"
            class="sidebar-menu"
            @select="handleMenuSelect"
          >
            <template v-for="menuItem in navigationMenus" :key="menuItem.key">
              <!-- 单级菜单 -->
              <el-menu-item 
                v-if="!menuItem.children"
                :index="menuItem.key"
                :disabled="menuItem.disabled"
              >
                <el-icon class="menu-icon">
                  <component :is="menuItem.icon" />
                </el-icon>
                <template #title>
                  <span class="menu-title">{{ menuItem.title }}</span>
                  <el-badge 
                    v-if="menuItem.badge" 
                    :value="menuItem.badge"
                    :type="menuItem.badgeType || 'primary'"
                    class="menu-badge"
                  />
                </template>
              </el-menu-item>
              
              <!-- 多级菜单 -->
              <el-sub-menu 
                v-else
                :index="menuItem.key"
                :disabled="menuItem.disabled"
              >
                <template #title>
                  <el-icon class="menu-icon">
                    <component :is="menuItem.icon" />
                  </el-icon>
                  <span class="menu-title">{{ menuItem.title }}</span>
                  <el-badge 
                    v-if="menuItem.badge" 
                    :value="menuItem.badge"
                    :type="menuItem.badgeType || 'primary'"
                    class="menu-badge"
                  />
                </template>
                
                <template v-for="subItem in menuItem.children" :key="subItem.key">
                  <!-- 二级菜单 -->
                  <el-menu-item 
                    v-if="!subItem.children"
                    :index="subItem.key"
                    :disabled="subItem.disabled"
                  >
                    <el-icon class="submenu-icon">
                      <component :is="subItem.icon" />
                    </el-icon>
                    <template #title>
                      <span class="submenu-title">{{ subItem.title }}</span>
                      <el-badge 
                        v-if="subItem.badge" 
                        :value="subItem.badge"
                        :type="subItem.badgeType || 'primary'"
                        class="submenu-badge"
                      />
                    </template>
                  </el-menu-item>
                  
                  <!-- 三级菜单 -->
                  <el-sub-menu 
                    v-else
                    :index="subItem.key"
                    :disabled="subItem.disabled"
                  >
                    <template #title>
                      <el-icon class="submenu-icon">
                        <component :is="subItem.icon" />
                      </el-icon>
                      <span class="submenu-title">{{ subItem.title }}</span>
                    </template>
                    
                    <el-menu-item 
                      v-for="thirdItem in subItem.children"
                      :key="thirdItem.key"
                      :index="thirdItem.key"
                      :disabled="thirdItem.disabled"
                    >
                      <el-icon class="third-menu-icon">
                        <component :is="thirdItem.icon" />
                      </el-icon>
                      <template #title>
                        <span class="third-menu-title">{{ thirdItem.title }}</span>
                      </template>
                    </el-menu-item>
                  </el-sub-menu>
                </template>
              </el-sub-menu>
            </template>
          </el-menu>
        </el-scrollbar>
        
        <!-- 侧边栏底部快捷操作 -->
        <div class="sidebar-footer">
          <div class="quick-actions">
            <el-tooltip 
              v-for="action in quickActions"
              :key="action.key"
              :content="action.tooltip"
              placement="right"
              :disabled="!isCollapsed"
            >
              <el-button 
                :type="action.type"
                :size="isCollapsed ? 'large' : 'small'"
                @click="handleQuickAction(action)"
                class="quick-action-btn"
                :class="{ 'collapsed': isCollapsed }"
              >
                <el-icon>
                  <component :is="action.icon" />
                </el-icon>
                <span v-if="!isCollapsed" class="action-text">{{ action.text }}</span>
              </el-button>
            </el-tooltip>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 主内容区域 -->
    <div class="main-content-area">
      <!-- 面包屑导航 -->
      <div class="breadcrumb-navigation">
        <div class="breadcrumb-wrapper">
          <el-breadcrumb separator="/" class="breadcrumb-trail">
            <el-breadcrumb-item 
              v-for="(crumb, index) in breadcrumbTrail"
              :key="index"
              :to="crumb.path"
              :class="{ 'active': index === breadcrumbTrail.length - 1 }"
            >
              <el-icon v-if="crumb.icon" class="breadcrumb-icon">
                <component :is="crumb.icon" />
              </el-icon>
              <span class="breadcrumb-text">{{ crumb.title }}</span>
            </el-breadcrumb-item>
          </el-breadcrumb>
          
          <!-- 面包屑操作区 -->
          <div class="breadcrumb-actions">
            <el-button-group size="small">
              <el-button 
                @click="goBack"
                :disabled="!canGoBack"
                type="info"
              >
                <el-icon><arrow-left /></el-icon>
                返回
              </el-button>
              <el-button 
                @click="goForward"
                :disabled="!canGoForward"
                type="info"
              >
                前进
                <el-icon><arrow-right /></el-icon>
              </el-button>
            </el-button-group>
            
            <el-dropdown @command="handleBreadcrumbAction" trigger="click">
              <el-button size="small" type="primary">
                <el-icon><more /></el-icon>
                更多操作
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="refresh">
                    <el-icon><refresh /></el-icon>
                    刷新页面
                  </el-dropdown-item>
                  <el-dropdown-item command="bookmark">
                    <el-icon><star /></el-icon>
                    添加书签
                  </el-dropdown-item>
                  <el-dropdown-item command="share">
                    <el-icon><share /></el-icon>
                    分享页面
                  </el-dropdown-item>
                  <el-dropdown-item command="fullscreen">
                    <el-icon><full-screen /></el-icon>
                    全屏显示
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
        
        <!-- 页面标题和描述 -->
        <div class="page-header">
          <div class="page-title-section">
            <h1 class="page-title">{{ currentPageTitle }}</h1>
            <p v-if="currentPageDescription" class="page-description">
              {{ currentPageDescription }}
            </p>
          </div>
          
          <div class="page-meta">
            <div class="meta-item">
              <el-icon class="meta-icon"><clock /></el-icon>
              <span class="meta-text">最后更新：{{ lastUpdateTime }}</span>
            </div>
            <div class="meta-item">
              <el-icon class="meta-icon"><user /></el-icon>
              <span class="meta-text">当前用户：{{ currentUser }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 页面内容插槽 -->
      <div class="page-content">
        <slot name="content">
          <div class="content-placeholder">
            <el-icon class="placeholder-icon"><document /></el-icon>
            <h3>页面内容区域</h3>
            <p>这里是页面的主要内容区域</p>
          </div>
        </slot>
      </div>
    </div>
    
    <!-- 导航历史面板 -->
    <el-drawer
      v-model="showNavigationHistory"
      title="导航历史"
      direction="rtl"
      size="300px"
      class="navigation-history-drawer"
    >
      <div class="history-content">
        <div class="history-search">
          <el-input
            v-model="historySearchText"
            placeholder="搜索导航历史"
            :prefix-icon="Search"
            size="small"
          />
        </div>
        
        <div class="history-list">
          <div class="history-section">
            <h4 class="section-title">最近访问</h4>
            <div 
              v-for="item in recentHistory"
              :key="item.key"
              class="history-item"
              @click="navigateToHistory(item)"
            >
              <el-icon class="history-icon">
                <component :is="item.icon" />
              </el-icon>
              <div class="history-info">
                <div class="history-title">{{ item.title }}</div>
                <div class="history-time">{{ item.visitTime }}</div>
              </div>
            </div>
          </div>
          
          <div class="history-section">
            <h4 class="section-title">常用页面</h4>
            <div 
              v-for="item in frequentPages"
              :key="item.key"
              class="history-item"
              @click="navigateToHistory(item)"
            >
              <el-icon class="history-icon">
                <component :is="item.icon" />
              </el-icon>
              <div class="history-info">
                <div class="history-title">{{ item.title }}</div>
                <div class="history-count">访问 {{ item.visitCount }} 次</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import {
  DataBoard,
  Expand,
  Fold,
  Monitor,
  TrendCharts,
  Document,
  Setting,
  User,
  Bell,
  Search,
  ArrowLeft,
  ArrowRight,
  More,
  Refresh,
  Star,
  Share,
  FullScreen,
  Clock,
  House,
  DataAnalysis,
  Files,
  Operation
} from '@element-plus/icons-vue'

export default {
  name: 'NavigationSystem',
  components: {
    DataBoard,
    Expand,
    Fold,
    Monitor,
    TrendCharts,
    Document,
    Setting,
    User,
    Bell,
    Search,
    ArrowLeft,
    ArrowRight,
    More,
    Refresh,
    Star,
    Share,
    FullScreen,
    Clock,
    House,
    DataAnalysis,
    Files,
    Operation
  },
  
  setup() {
    const route = useRoute()
    const router = useRouter()
    const userStore = useUserStore()
    
    const isCollapsed = ref(false)
    const activeMenuKey = ref('dashboard')
    const showNavigationHistory = ref(false)
    const historySearchText = ref('')
    const navigationHistory = ref([])
    const currentPageTitle = ref('数据仪表盘')
    const currentPageDescription = ref('实时监控系统状态和数据概览')
    const lastUpdateTime = ref('2024-01-15 14:30:25')
    const currentUser = ref('系统管理员')
    
    // 导航菜单配置
    const navigationMenus = ref([
      {
        key: 'dashboard',
        title: '仪表盘',
        icon: 'House',
        path: '/dashboard'
      },
      {
        key: 'monitor',
        title: '监控中心',
        icon: 'Monitor',
        path: '/monitor',
        children: [
          {
            key: 'crawler-status',
            title: '爬虫状态',
            icon: 'Monitor',
            path: '/monitor/crawler-status'
          },
          {
            key: 'system-health',
            title: '系统健康',
            icon: 'TrendCharts',
            path: '/monitor/system-health'
          },
          {
            key: 'real-time-logs',
            title: '实时日志',
            icon: 'Document',
            path: '/monitor/real-time-logs'
          }
        ]
      },
      {
        key: 'data-analysis',
        title: '数据分析',
        icon: 'DataAnalysis',
        path: '/data-analysis',
        children: [
          {
            key: 'news-trends',
            title: '新闻趋势',
            icon: 'TrendCharts',
            path: '/data-analysis/news-trends'
          },
          {
            key: 'keyword-analysis',
            title: '关键词分析',
            icon: 'Search',
            path: '/data-analysis/keyword-analysis'
          },
          {
            key: 'sentiment-analysis',
            title: '情感分析',
            icon: 'DataAnalysis',
            path: '/data-analysis/sentiment-analysis',
            children: [
              {
                key: 'positive-sentiment',
                title: '积极情感',
                icon: 'Star',
                path: '/data-analysis/sentiment-analysis/positive'
              },
              {
                key: 'negative-sentiment',
                title: '消极情感',
                icon: 'Warning',
                path: '/data-analysis/sentiment-analysis/negative'
              }
            ]
          }
        ]
      },
      {
        key: 'content-management',
        title: '内容管理',
        icon: 'Files',
        path: '/content-management',
        children: [
          {
            key: 'news-list',
            title: '新闻列表',
            icon: 'Document',
            path: '/content-management/news-list'
          },
          {
            key: 'category-management',
            title: '分类管理',
            icon: 'Operation',
            path: '/content-management/category-management'
          },
          {
            key: 'content-review',
            title: '内容审核',
            icon: 'View',
            path: '/content-management/content-review',
            badge: 5,
            badgeType: 'warning'
          }
        ]
      },
      {
        key: 'system-settings',
        title: '系统设置',
        icon: 'Setting',
        path: '/system-settings',
        children: [
          {
            key: 'crawler-config',
            title: '爬虫配置',
            icon: 'Setting',
            path: '/system-settings/crawler-config'
          },
          {
            key: 'user-management',
            title: '用户管理',
            icon: 'User',
            path: '/system-settings/user-management'
          },
          {
            key: 'notification-settings',
            title: '通知设置',
            icon: 'Bell',
            path: '/system-settings/notification-settings'
          }
        ]
      }
    ])
    
    // 快捷操作
    const quickActions = ref([
      {
        key: 'refresh',
        text: '刷新',
        tooltip: '刷新当前页面',
        icon: 'Refresh',
        type: 'primary'
      },
      {
        key: 'search',
        text: '搜索',
        tooltip: '全局搜索',
        icon: 'Search',
        type: 'info'
      },
      {
        key: 'notifications',
        text: '通知',
        tooltip: '查看通知',
        icon: 'Bell',
        type: 'warning'
      },
      {
        key: 'settings',
        text: '设置',
        tooltip: '系统设置',
        icon: 'Setting',
        type: 'default'
      }
    ])
    
    // 面包屑导航
    const breadcrumbTrail = ref([
      { title: '首页', path: '/', icon: 'House' },
      { title: '监控中心', path: '/monitor', icon: 'Monitor' },
      { title: '爬虫状态', path: '/monitor/crawler-status', icon: 'Monitor' }
    ])
    
    // 导航历史
    const recentHistory = ref([
      {
        key: 'dashboard',
        title: '数据仪表盘',
        icon: 'House',
        path: '/dashboard',
        visitTime: '2分钟前'
      },
      {
        key: 'news-trends',
        title: '新闻趋势',
        icon: 'TrendCharts',
        path: '/data-analysis/news-trends',
        visitTime: '5分钟前'
      },
      {
        key: 'crawler-status',
        title: '爬虫状态',
        icon: 'Monitor',
        path: '/monitor/crawler-status',
        visitTime: '10分钟前'
      }
    ])
    
    const frequentPages = ref([
      {
        key: 'dashboard',
        title: '数据仪表盘',
        icon: 'House',
        path: '/dashboard',
        visitCount: 25
      },
      {
        key: 'news-list',
        title: '新闻列表',
        icon: 'Document',
        path: '/content-management/news-list',
        visitCount: 18
      },
      {
        key: 'system-health',
        title: '系统健康',
        icon: 'TrendCharts',
        path: '/monitor/system-health',
        visitCount: 12
      }
    ])
    
    // 计算属性
    const canGoBack = computed(() => navigationHistory.value.length > 1)
    const canGoForward = computed(() => false) // 简化实现
    
    // 方法
    const toggleSidebar = () => {
      isCollapsed.value = !isCollapsed.value
    }
    
    const handleMenuSelect = (key) => {
      activeMenuKey.value = key
      // 更新面包屑
      updateBreadcrumb(key)
      // 记录导航历史
      recordNavigationHistory(key)
    }
    
    const updateBreadcrumb = (menuKey) => {
      // 根据菜单key更新面包屑
      const menuItem = findMenuItemByKey(menuKey, navigationMenus.value)
      if (menuItem) {
        const trail = buildBreadcrumbTrail(menuItem)
        breadcrumbTrail.value = trail
        currentPageTitle.value = menuItem.title
        currentPageDescription.value = menuItem.description || `${menuItem.title}页面`
      }
    }
    
    const findMenuItemByKey = (key, menus) => {
      for (const menu of menus) {
        if (menu.key === key) {
          return menu
        }
        if (menu.children) {
          const found = findMenuItemByKey(key, menu.children)
          if (found) return found
        }
      }
      return null
    }
    
    const buildBreadcrumbTrail = (menuItem) => {
      const trail = [{ title: '首页', path: '/', icon: 'House' }]
      
      // 简化实现，实际应该根据菜单层级构建
      if (menuItem.path !== '/') {
        trail.push({
          title: menuItem.title,
          path: menuItem.path,
          icon: menuItem.icon
        })
      }
      
      return trail
    }
    
    const recordNavigationHistory = (menuKey) => {
      const menuItem = findMenuItemByKey(menuKey, navigationMenus.value)
      if (menuItem) {
        const historyItem = {
          key: menuKey,
          title: menuItem.title,
          path: menuItem.path,
          icon: menuItem.icon,
          timestamp: Date.now()
        }
        
        // 添加到历史记录
        navigationHistory.value.unshift(historyItem)
        
        // 保持历史记录不超过50条
        if (navigationHistory.value.length > 50) {
          navigationHistory.value = navigationHistory.value.slice(0, 50)
        }
      }
    }
    
    const handleQuickAction = (action) => {
      switch (action.key) {
        case 'refresh':
          location.reload()
          break
        case 'search':
          // 显示搜索面板
          console.log('显示搜索面板')
          break
        case 'notifications':
          // 显示通知面板
          console.log('显示通知面板')
          break
        case 'settings':
          // 跳转到设置页面
          handleMenuSelect('system-settings')
          break
      }
    }
    
    const goBack = () => {
      if (canGoBack.value) {
        const previousPage = navigationHistory.value[1]
        if (previousPage) {
          handleMenuSelect(previousPage.key)
          navigationHistory.value = navigationHistory.value.slice(1)
        }
      }
    }
    
    const goForward = () => {
      // 简化实现
      console.log('前进')
    }
    
    const handleBreadcrumbAction = (command) => {
      switch (command) {
        case 'refresh':
          location.reload()
          break
        case 'bookmark':
          console.log('添加书签')
          break
        case 'share':
          console.log('分享页面')
          break
        case 'fullscreen':
          document.documentElement.requestFullscreen()
          break
      }
    }
    
    const navigateToHistory = (historyItem) => {
      handleMenuSelect(historyItem.key)
      showNavigationHistory.value = false
    }
    
    // 生命周期
    onMounted(() => {
      // 初始化当前页面
      handleMenuSelect('dashboard')
    })
    
    return {
      isCollapsed,
      activeMenuKey,
      showNavigationHistory,
      historySearchText,
      navigationMenus,
      quickActions,
      breadcrumbTrail,
      recentHistory,
      frequentPages,
      currentPageTitle,
      currentPageDescription,
      lastUpdateTime,
      currentUser,
      canGoBack,
      canGoForward,
      toggleSidebar,
      handleMenuSelect,
      handleQuickAction,
      goBack,
      goForward,
      handleBreadcrumbAction,
      navigateToHistory
    }
  }
}
</script>

<style lang="scss" scoped>
.navigation-system {
  display: flex;
  height: 100vh;
  
  // 侧边栏导航样式
  .sidebar-navigation {
    width: 260px;
    background: #304156;
    color: white;
    transition: width 0.3s ease;
    display: flex;
    flex-direction: column;
    
    &.collapsed {
      width: 64px;
    }
    
    .sidebar-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 20px;
      border-bottom: 1px solid #3a4b5c;
      
      .logo-section {
        display: flex;
        align-items: center;
        gap: 12px;
        
        .logo-icon {
          font-size: 32px;
          color: #409EFF;
        }
        
        .logo-title {
          font-size: 20px;
          font-weight: 600;
          margin: 0;
          color: white;
        }
      }
      
      .collapse-btn {
        color: #C0C4CC;
        font-size: 16px;
        
        &:hover {
          color: white;
        }
        
        &.collapsed {
          transform: rotate(180deg);
        }
      }
    }
    
    .sidebar-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      
      .sidebar-scrollbar {
        flex: 1;
        
        .sidebar-menu {
          border: none;
          background: transparent;
          
          :deep(.el-menu-item) {
            color: #C0C4CC;
            border-radius: 6px;
            margin: 4px 12px;
            
            &:hover {
              background: #3a4b5c;
              color: white;
            }
            
            &.is-active {
              background: #409EFF;
              color: white;
            }
            
            .menu-icon,
            .submenu-icon,
            .third-menu-icon {
              font-size: 18px;
            }
            
            .menu-badge,
            .submenu-badge {
              margin-left: 8px;
            }
          }
          
          :deep(.el-sub-menu__title) {
            color: #C0C4CC;
            border-radius: 6px;
            margin: 4px 12px;
            
            &:hover {
              background: #3a4b5c;
              color: white;
            }
          }
          
          :deep(.el-sub-menu.is-active .el-sub-menu__title) {
            color: #409EFF;
          }
        }
      }
      
      .sidebar-footer {
        padding: 16px;
        border-top: 1px solid #3a4b5c;
        
        .quick-actions {
          display: flex;
          flex-direction: column;
          gap: 8px;
          
          .quick-action-btn {
            justify-content: flex-start;
            color: #C0C4CC;
            border: 1px solid #3a4b5c;
            background: transparent;
            
            &:hover {
              color: white;
              background: #3a4b5c;
            }
            
            &.collapsed {
              justify-content: center;
              
              .action-text {
                display: none;
              }
            }
            
            .action-text {
              margin-left: 8px;
            }
          }
        }
      }
    }
  }
  
  // 主内容区域样式
  .main-content-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: #F5F7FA;
    
    .breadcrumb-navigation {
      background: white;
      border-bottom: 1px solid #E4E7ED;
      padding: 16px 24px;
      
      .breadcrumb-wrapper {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        
        .breadcrumb-trail {
          flex: 1;
          
          :deep(.el-breadcrumb__item) {
            .el-breadcrumb__inner {
              display: flex;
              align-items: center;
              gap: 4px;
              color: #606266;
              
              &:hover {
                color: #409EFF;
              }
            }
            
            &.active .el-breadcrumb__inner {
              color: #409EFF;
              font-weight: 500;
            }
          }
          
          .breadcrumb-icon {
            font-size: 14px;
          }
        }
        
        .breadcrumb-actions {
          display: flex;
          gap: 12px;
          align-items: center;
        }
      }
      
      .page-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        
        .page-title-section {
          .page-title {
            font-size: 24px;
            font-weight: 600;
            color: #303133;
            margin: 0 0 8px 0;
          }
          
          .page-description {
            font-size: 14px;
            color: #606266;
            margin: 0;
          }
        }
        
        .page-meta {
          display: flex;
          gap: 16px;
          
          .meta-item {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 12px;
            color: #909399;
            
            .meta-icon {
              font-size: 14px;
            }
          }
        }
      }
    }
    
    .page-content {
      flex: 1;
      padding: 24px;
      overflow-y: auto;
      
      .content-placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        color: #909399;
        
        .placeholder-icon {
          font-size: 64px;
          margin-bottom: 16px;
        }
        
        h3 {
          margin: 0 0 8px 0;
          font-size: 18px;
        }
        
        p {
          margin: 0;
          font-size: 14px;
        }
      }
    }
  }
}

// 导航历史抽屉样式
.navigation-history-drawer {
  .history-content {
    .history-search {
      margin-bottom: 20px;
    }
    
    .history-list {
      .history-section {
        margin-bottom: 24px;
        
        .section-title {
          font-size: 14px;
          font-weight: 600;
          color: #303133;
          margin: 0 0 12px 0;
          padding-bottom: 8px;
          border-bottom: 1px solid #E4E7ED;
        }
        
        .history-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px;
          border-radius: 6px;
          cursor: pointer;
          transition: background-color 0.3s;
          
          &:hover {
            background: #F5F7FA;
          }
          
          .history-icon {
            font-size: 16px;
            color: #409EFF;
          }
          
          .history-info {
            flex: 1;
            
            .history-title {
              font-size: 14px;
              color: #303133;
              margin-bottom: 4px;
            }
            
            .history-time,
            .history-count {
              font-size: 12px;
              color: #909399;
            }
          }
        }
      }
    }
  }
}

// 响应式设计
@media (max-width: 1024px) {
  .navigation-system {
    .sidebar-navigation {
      width: 240px;
      
      &.collapsed {
        width: 60px;
      }
    }
    
    .main-content-area {
      .breadcrumb-navigation {
        padding: 12px 16px;
        
        .breadcrumb-wrapper {
          flex-direction: column;
          gap: 12px;
          align-items: flex-start;
        }
        
        .page-header {
          flex-direction: column;
          gap: 12px;
          align-items: flex-start;
          
          .page-meta {
            flex-direction: column;
            gap: 8px;
          }
        }
      }
      
      .page-content {
        padding: 16px;
      }
    }
  }
}

@media (max-width: 768px) {
  .navigation-system {
    .sidebar-navigation {
      position: fixed;
      top: 0;
      left: 0;
      height: 100vh;
      z-index: 1000;
      transform: translateX(-100%);
      transition: transform 0.3s ease;
      
      &.show {
        transform: translateX(0);
      }
    }
    
    .main-content-area {
      width: 100%;
      
      .breadcrumb-navigation {
        .breadcrumb-wrapper {
          .breadcrumb-actions {
            flex-direction: column;
            gap: 8px;
          }
        }
      }
    }
  }
}
</style> 