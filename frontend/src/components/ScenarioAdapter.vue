<template>
  <div class="scenario-adapter" :class="scenarioClasses">
    <div class="scenario-header">
      <div class="scenario-info">
        <el-icon class="scenario-icon">
          <component :is="currentScenario.icon" />
        </el-icon>
        <div class="scenario-details">
          <h3 class="scenario-title">{{ currentScenario.title }}</h3>
          <p class="scenario-description">{{ currentScenario.description }}</p>
        </div>
      </div>
      
      <div class="scenario-controls">
        <el-dropdown @command="handleScenarioChange" class="scenario-selector">
          <el-button type="primary" size="small">
            <el-icon><monitor /></el-icon>
            {{ currentScenario.title }}
            <el-icon class="arrow-icon"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item 
                v-for="(scenario, key) in scenarios" 
                :key="key"
                :command="key"
                :disabled="key === currentScenarioKey"
              >
                <el-icon class="menu-icon">
                  <component :is="scenario.icon" />
                </el-icon>
                {{ scenario.title }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        
        <el-button 
          size="small" 
          @click="toggleFullscreen"
          :type="isFullscreen ? 'danger' : 'info'"
        >
          <el-icon>
            <component :is="isFullscreen ? 'close' : 'full-screen'" />
          </el-icon>
          {{ isFullscreen ? '退出全屏' : '全屏模式' }}
        </el-button>
      </div>
    </div>
    
    <div class="scenario-content">
      <!-- 办公室场景 -->
      <div v-if="currentScenarioKey === 'office'" class="office-layout">
        <div class="office-sidebar">
          <div class="sidebar-section">
            <h4 class="section-title">快速导航</h4>
            <el-menu 
              :default-active="activeOfficeMenu"
              class="office-menu"
              @select="handleOfficeMenuSelect"
            >
              <el-menu-item index="dashboard">
                <el-icon><data-board /></el-icon>
                <span>数据仪表盘</span>
              </el-menu-item>
              <el-menu-item index="monitor">
                <el-icon><monitor /></el-icon>
                <span>系统监控</span>
              </el-menu-item>
              <el-menu-item index="analysis">
                <el-icon><trend-charts /></el-icon>
                <span>数据分析</span>
              </el-menu-item>
              <el-menu-item index="reports">
                <el-icon><document /></el-icon>
                <span>报告管理</span>
              </el-menu-item>
            </el-menu>
          </div>
          
          <div class="sidebar-section">
            <h4 class="section-title">快捷操作</h4>
            <div class="quick-actions">
              <el-button 
                v-for="action in officeQuickActions"
                :key="action.key"
                :type="action.type"
                size="small"
                @click="handleQuickAction(action)"
                class="quick-action-btn"
              >
                <el-icon>
                  <component :is="action.icon" />
                </el-icon>
                {{ action.label }}
              </el-button>
            </div>
          </div>
        </div>
        
        <div class="office-main">
          <div class="office-workspace">
            <div class="workspace-grid">
              <div class="workspace-panel primary-panel">
                <div class="panel-header">
                  <h4 class="panel-title">主工作区</h4>
                  <el-button-group size="small">
                    <el-button @click="togglePanelView('grid')">
                      <el-icon><grid /></el-icon>
                    </el-button>
                    <el-button @click="togglePanelView('list')">
                      <el-icon><list /></el-icon>
                    </el-button>
                  </el-button-group>
                </div>
                <div class="panel-content">
                  <slot name="main-content">
                    <div class="placeholder-content">
                      <el-icon class="placeholder-icon"><data-board /></el-icon>
                      <p>主工作区内容区域</p>
                    </div>
                  </slot>
                </div>
              </div>
              
              <div class="workspace-panel secondary-panel">
                <div class="panel-header">
                  <h4 class="panel-title">辅助面板</h4>
                  <el-button size="small" @click="togglePanelCollapse">
                    <el-icon><expand /></el-icon>
                  </el-button>
                </div>
                <div class="panel-content">
                  <slot name="secondary-content">
                    <div class="info-cards">
                      <div class="info-card">
                        <div class="card-icon">
                          <el-icon><trend-charts /></el-icon>
                        </div>
                        <div class="card-info">
                          <div class="card-title">实时数据</div>
                          <div class="card-value">1,247</div>
                        </div>
                      </div>
                      <div class="info-card">
                        <div class="card-icon">
                          <el-icon><monitor /></el-icon>
                        </div>
                        <div class="card-info">
                          <div class="card-title">系统状态</div>
                          <div class="card-value">正常</div>
                        </div>
                      </div>
                    </div>
                  </slot>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 移动端场景 -->
      <div v-else-if="currentScenarioKey === 'mobile'" class="mobile-layout">
        <div class="mobile-header">
          <div class="header-left">
            <el-button 
              type="text" 
              size="large"
              @click="toggleMobileMenu"
              class="menu-toggle"
            >
              <el-icon><menu /></el-icon>
            </el-button>
            <h3 class="mobile-title">NewsLook</h3>
          </div>
          <div class="header-right">
            <el-button type="text" size="large" @click="showMobileSearch">
              <el-icon><search /></el-icon>
            </el-button>
            <el-button type="text" size="large" @click="showMobileNotifications">
              <el-icon><bell /></el-icon>
            </el-button>
          </div>
        </div>
        
        <div class="mobile-content">
          <div class="mobile-tabs">
            <el-tabs 
              v-model="activeMobileTab"
              type="border-card"
              @tab-change="handleMobileTabChange"
            >
              <el-tab-pane label="首页" name="home">
                <div class="mobile-feed">
                  <slot name="mobile-feed">
                    <div class="feed-item" v-for="i in 5" :key="i">
                      <div class="feed-content">
                        <h4 class="feed-title">新闻标题 {{ i }}</h4>
                        <p class="feed-summary">这是新闻摘要内容...</p>
                        <div class="feed-meta">
                          <span class="feed-source">腾讯财经</span>
                          <span class="feed-time">2小时前</span>
                        </div>
                      </div>
                    </div>
                  </slot>
                </div>
              </el-tab-pane>
              
              <el-tab-pane label="监控" name="monitor">
                <div class="mobile-monitor">
                  <slot name="mobile-monitor">
                    <div class="monitor-cards">
                      <div class="monitor-card">
                        <div class="card-header">
                          <el-icon><monitor /></el-icon>
                          <span>系统状态</span>
                        </div>
                        <div class="card-value success">运行正常</div>
                      </div>
                      <div class="monitor-card">
                        <div class="card-header">
                          <el-icon><data-analysis /></el-icon>
                          <span>数据采集</span>
                        </div>
                        <div class="card-value">1,247条</div>
                      </div>
                    </div>
                  </slot>
                </div>
              </el-tab-pane>
              
              <el-tab-pane label="设置" name="settings">
                <div class="mobile-settings">
                  <slot name="mobile-settings">
                    <div class="settings-list">
                      <div class="setting-item">
                        <span class="setting-label">主题设置</span>
                        <el-switch v-model="darkMode" />
                      </div>
                      <div class="setting-item">
                        <span class="setting-label">消息通知</span>
                        <el-switch v-model="notifications" />
                      </div>
                    </div>
                  </slot>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </div>
        
        <div class="mobile-bottom-nav">
          <div 
            v-for="nav in mobileNavItems"
            :key="nav.key"
            :class="['nav-item', { active: activeMobileTab === nav.key }]"
            @click="activeMobileTab = nav.key"
          >
            <el-icon class="nav-icon">
              <component :is="nav.icon" />
            </el-icon>
            <span class="nav-label">{{ nav.label }}</span>
          </div>
        </div>
      </div>
      
      <!-- 多屏协作场景 -->
      <div v-else-if="currentScenarioKey === 'multiscreen'" class="multiscreen-layout">
        <div class="multiscreen-header">
          <div class="screen-indicator">
            <div class="screen-info">
              <el-icon class="screen-icon"><monitor /></el-icon>
              <span class="screen-label">主屏幕</span>
            </div>
            <div class="screen-controls">
              <el-button-group size="small">
                <el-button 
                  v-for="screen in connectedScreens"
                  :key="screen.id"
                  :type="screen.active ? 'primary' : 'default'"
                  @click="toggleScreen(screen.id)"
                >
                  <el-icon><monitor /></el-icon>
                  {{ screen.name }}
                </el-button>
              </el-button-group>
            </div>
          </div>
          
          <div class="collaboration-tools">
            <el-button size="small" @click="shareScreen">
              <el-icon><share /></el-icon>
              共享屏幕
            </el-button>
            <el-button size="small" @click="syncData">
              <el-icon><refresh /></el-icon>
              同步数据
            </el-button>
            <el-button size="small" @click="inviteCollab">
              <el-icon><user-filled /></el-icon>
              邀请协作
            </el-button>
          </div>
        </div>
        
        <div class="multiscreen-content">
          <div class="screen-layout">
            <div class="screen-section main-screen">
              <div class="screen-header">
                <h4 class="screen-title">主显示屏</h4>
                <el-tag size="small" type="success">活跃</el-tag>
              </div>
              <div class="screen-content">
                <slot name="main-screen">
                  <div class="screen-dashboard">
                    <div class="dashboard-grid">
                      <div class="dashboard-item">
                        <h5>数据概览</h5>
                        <div class="chart-placeholder">
                          <el-icon><trend-charts /></el-icon>
                          <p>图表显示区域</p>
                        </div>
                      </div>
                      <div class="dashboard-item">
                        <h5>系统状态</h5>
                        <div class="status-indicators">
                          <div class="indicator success">
                            <span class="indicator-dot"></span>
                            <span>爬虫运行</span>
                          </div>
                          <div class="indicator warning">
                            <span class="indicator-dot"></span>
                            <span>数据同步</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </slot>
              </div>
            </div>
            
            <div class="screen-section secondary-screen">
              <div class="screen-header">
                <h4 class="screen-title">辅助屏幕</h4>
                <el-tag size="small" type="info">待激活</el-tag>
              </div>
              <div class="screen-content">
                <slot name="secondary-screen">
                  <div class="screen-preview">
                    <el-icon class="preview-icon"><monitor /></el-icon>
                    <p>点击激活辅助屏幕</p>
                    <el-button type="primary" @click="activateSecondaryScreen">
                      激活屏幕
                    </el-button>
                  </div>
                </slot>
              </div>
            </div>
          </div>
          
          <div class="collaboration-panel">
            <div class="panel-header">
              <h4 class="panel-title">协作面板</h4>
              <el-button size="small" @click="toggleCollabPanel">
                <el-icon><expand /></el-icon>
              </el-button>
            </div>
            <div class="panel-content">
              <div class="online-users">
                <h5>在线用户</h5>
                <div class="user-list">
                  <div 
                    v-for="user in onlineUsers"
                    :key="user.id"
                    class="user-item"
                  >
                    <el-avatar :size="24" :src="user.avatar" />
                    <span class="user-name">{{ user.name }}</span>
                    <el-tag :type="user.status === 'active' ? 'success' : 'info'" size="small">
                      {{ user.status === 'active' ? '活跃' : '离线' }}
                    </el-tag>
                  </div>
                </div>
              </div>
              
              <div class="recent-activities">
                <h5>最近活动</h5>
                <div class="activity-list">
                  <div 
                    v-for="activity in recentActivities"
                    :key="activity.id"
                    class="activity-item"
                  >
                    <el-icon class="activity-icon">
                      <component :is="activity.icon" />
                    </el-icon>
                    <div class="activity-content">
                      <p class="activity-text">{{ activity.text }}</p>
                      <span class="activity-time">{{ activity.time }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { 
  Monitor, 
  Mobile, 
  Connection,
  ArrowDown,
  Close,
  FullScreen,
  DataBoard,
  TrendCharts,
  Document,
  Grid,
  List,
  Expand,
  Menu,
  Search,
  Bell,
  Share,
  Refresh,
  UserFilled
} from '@element-plus/icons-vue'

export default {
  name: 'ScenarioAdapter',
  components: {
    Monitor,
    Mobile,
    Connection,
    ArrowDown,
    Close,
    FullScreen,
    DataBoard,
    TrendCharts,
    Document,
    Grid,
    List,
    Expand,
    Menu,
    Search,
    Bell,
    Share,
    Refresh,
    UserFilled
  },
  
  setup() {
    const currentScenarioKey = ref('office')
    const isFullscreen = ref(false)
    const activeOfficeMenu = ref('dashboard')
    const activeMobileTab = ref('home')
    const darkMode = ref(false)
    const notifications = ref(true)
    
    // 场景配置
    const scenarios = {
      office: {
        title: '办公室',
        description: '多窗口、大屏幕、高效协作',
        icon: 'Monitor',
        breakpoint: 'xl',
        features: ['多窗口', '键盘快捷键', '拖拽操作', '多任务处理']
      },
      mobile: {
        title: '移动端',
        description: '触控优化、单手操作、简化界面',
        icon: 'Mobile',
        breakpoint: 'xs',
        features: ['触控手势', '单手操作', '离线访问', '推送通知']
      },
      multiscreen: {
        title: '多屏协作',
        description: '多屏显示、团队协作、实时同步',
        icon: 'Connection',
        breakpoint: 'xxl',
        features: ['多屏联动', '实时协作', '数据同步', '屏幕共享']
      }
    }
    
    const currentScenario = computed(() => scenarios[currentScenarioKey.value])
    
    const scenarioClasses = computed(() => [
      `scenario-${currentScenarioKey.value}`,
      { 'fullscreen': isFullscreen.value }
    ])
    
    // 办公室场景数据
    const officeQuickActions = ref([
      { key: 'export', label: '导出数据', icon: 'Download', type: 'primary' },
      { key: 'refresh', label: '刷新', icon: 'Refresh', type: 'info' },
      { key: 'settings', label: '设置', icon: 'Setting', type: 'default' }
    ])
    
    // 移动端场景数据
    const mobileNavItems = ref([
      { key: 'home', label: '首页', icon: 'House' },
      { key: 'monitor', label: '监控', icon: 'Monitor' },
      { key: 'settings', label: '设置', icon: 'Setting' }
    ])
    
    // 多屏协作场景数据
    const connectedScreens = ref([
      { id: 1, name: '主屏', active: true },
      { id: 2, name: '副屏', active: false },
      { id: 3, name: '投影', active: false }
    ])
    
    const onlineUsers = ref([
      { id: 1, name: '张三', avatar: '', status: 'active' },
      { id: 2, name: '李四', avatar: '', status: 'active' },
      { id: 3, name: '王五', avatar: '', status: 'offline' }
    ])
    
    const recentActivities = ref([
      { id: 1, text: '张三更新了数据分析报告', time: '2分钟前', icon: 'Document' },
      { id: 2, text: '李四启动了爬虫任务', time: '5分钟前', icon: 'Monitor' },
      { id: 3, text: '王五导出了数据', time: '10分钟前', icon: 'Download' }
    ])
    
    // 方法
    const handleScenarioChange = (scenarioKey) => {
      currentScenarioKey.value = scenarioKey
      // 根据场景调整界面
      adjustLayoutForScenario(scenarioKey)
    }
    
    const adjustLayoutForScenario = (scenarioKey) => {
      // 根据场景调整布局
      const body = document.body
      body.classList.remove('office-mode', 'mobile-mode', 'multiscreen-mode')
      body.classList.add(`${scenarioKey}-mode`)
    }
    
    const toggleFullscreen = () => {
      if (!isFullscreen.value) {
        document.documentElement.requestFullscreen()
      } else {
        document.exitFullscreen()
      }
    }
    
    const handleFullscreenChange = () => {
      isFullscreen.value = !!document.fullscreenElement
    }
    
    const handleOfficeMenuSelect = (key) => {
      activeOfficeMenu.value = key
    }
    
    const handleQuickAction = (action) => {
      console.log('执行快捷操作:', action)
    }
    
    const togglePanelView = (view) => {
      console.log('切换面板视图:', view)
    }
    
    const togglePanelCollapse = () => {
      console.log('切换面板折叠状态')
    }
    
    const handleMobileTabChange = (tab) => {
      activeMobileTab.value = tab
    }
    
    const toggleMobileMenu = () => {
      console.log('切换移动端菜单')
    }
    
    const showMobileSearch = () => {
      console.log('显示移动端搜索')
    }
    
    const showMobileNotifications = () => {
      console.log('显示移动端通知')
    }
    
    const toggleScreen = (screenId) => {
      const screen = connectedScreens.value.find(s => s.id === screenId)
      if (screen) {
        screen.active = !screen.active
      }
    }
    
    const shareScreen = () => {
      console.log('共享屏幕')
    }
    
    const syncData = () => {
      console.log('同步数据')
    }
    
    const inviteCollab = () => {
      console.log('邀请协作')
    }
    
    const activateSecondaryScreen = () => {
      console.log('激活辅助屏幕')
    }
    
    const toggleCollabPanel = () => {
      console.log('切换协作面板')
    }
    
    // 生命周期
    onMounted(() => {
      document.addEventListener('fullscreenchange', handleFullscreenChange)
      // 根据屏幕尺寸自动选择场景
      autoSelectScenario()
    })
    
    onUnmounted(() => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
    })
    
    const autoSelectScenario = () => {
      const width = window.innerWidth
      if (width <= 768) {
        currentScenarioKey.value = 'mobile'
      } else if (width >= 1920) {
        currentScenarioKey.value = 'multiscreen'
      } else {
        currentScenarioKey.value = 'office'
      }
      adjustLayoutForScenario(currentScenarioKey.value)
    }
    
    return {
      currentScenarioKey,
      currentScenario,
      scenarioClasses,
      scenarios,
      isFullscreen,
      activeOfficeMenu,
      activeMobileTab,
      darkMode,
      notifications,
      officeQuickActions,
      mobileNavItems,
      connectedScreens,
      onlineUsers,
      recentActivities,
      handleScenarioChange,
      toggleFullscreen,
      handleOfficeMenuSelect,
      handleQuickAction,
      togglePanelView,
      togglePanelCollapse,
      handleMobileTabChange,
      toggleMobileMenu,
      showMobileSearch,
      showMobileNotifications,
      toggleScreen,
      shareScreen,
      syncData,
      inviteCollab,
      activateSecondaryScreen,
      toggleCollabPanel
    }
  }
}
</script>

<style lang="scss" scoped>
.scenario-adapter {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #F5F7FA;
  
  &.fullscreen {
    position: fixed;
    top: 0;
    left: 0;
    z-index: 9999;
  }
  
  .scenario-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    background: white;
    border-bottom: 1px solid #E4E7ED;
    
    .scenario-info {
      display: flex;
      align-items: center;
      gap: 12px;
      
      .scenario-icon {
        font-size: 24px;
        color: #409EFF;
      }
      
      .scenario-details {
        .scenario-title {
          font-size: 18px;
          font-weight: 600;
          color: #303133;
          margin: 0 0 4px 0;
        }
        
        .scenario-description {
          font-size: 12px;
          color: #909399;
          margin: 0;
        }
      }
    }
    
    .scenario-controls {
      display: flex;
      gap: 12px;
      align-items: center;
      
      .scenario-selector {
        .arrow-icon {
          margin-left: 4px;
          font-size: 12px;
        }
        
        .menu-icon {
          margin-right: 8px;
        }
      }
    }
  }
  
  .scenario-content {
    flex: 1;
    overflow: hidden;
  }
}

// 办公室场景样式
.office-layout {
  display: flex;
  height: 100%;
  
  .office-sidebar {
    width: 280px;
    background: white;
    border-right: 1px solid #E4E7ED;
    display: flex;
    flex-direction: column;
    
    .sidebar-section {
      padding: 16px;
      border-bottom: 1px solid #F0F2F5;
      
      .section-title {
        font-size: 14px;
        font-weight: 600;
        color: #303133;
        margin: 0 0 12px 0;
      }
      
      .office-menu {
        border: none;
        
        .el-menu-item {
          border-radius: 6px;
          margin: 2px 0;
          
          &.is-active {
            background: rgba(64, 158, 255, 0.1);
            color: #409EFF;
          }
        }
      }
      
      .quick-actions {
        display: flex;
        flex-direction: column;
        gap: 8px;
        
        .quick-action-btn {
          justify-content: flex-start;
          padding: 8px 12px;
        }
      }
    }
  }
  
  .office-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    
    .office-workspace {
      flex: 1;
      padding: 24px;
      
      .workspace-grid {
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 24px;
        height: 100%;
        
        .workspace-panel {
          background: white;
          border-radius: 8px;
          border: 1px solid #E4E7ED;
          display: flex;
          flex-direction: column;
          
          .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            border-bottom: 1px solid #E4E7ED;
            
            .panel-title {
              font-size: 16px;
              font-weight: 600;
              color: #303133;
              margin: 0;
            }
          }
          
          .panel-content {
            flex: 1;
            padding: 20px;
            
            .placeholder-content {
              display: flex;
              flex-direction: column;
              align-items: center;
              justify-content: center;
              height: 100%;
              color: #909399;
              
              .placeholder-icon {
                font-size: 48px;
                margin-bottom: 16px;
              }
            }
            
            .info-cards {
              display: flex;
              flex-direction: column;
              gap: 16px;
              
              .info-card {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 16px;
                background: #F8F9FA;
                border-radius: 6px;
                
                .card-icon {
                  font-size: 20px;
                  color: #409EFF;
                }
                
                .card-info {
                  flex: 1;
                  
                  .card-title {
                    font-size: 12px;
                    color: #909399;
                    margin-bottom: 4px;
                  }
                  
                  .card-value {
                    font-size: 16px;
                    font-weight: 600;
                    color: #303133;
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}

// 移动端场景样式
.mobile-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  
  .mobile-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: white;
    border-bottom: 1px solid #E4E7ED;
    
    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;
      
      .menu-toggle {
        font-size: 20px;
      }
      
      .mobile-title {
        font-size: 18px;
        font-weight: 600;
        color: #303133;
        margin: 0;
      }
    }
    
    .header-right {
      display: flex;
      gap: 8px;
      
      .el-button {
        font-size: 18px;
      }
    }
  }
  
  .mobile-content {
    flex: 1;
    overflow: hidden;
    
    .mobile-tabs {
      height: 100%;
      
      .mobile-feed {
        padding: 16px;
        
        .feed-item {
          background: white;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 12px;
          border: 1px solid #E4E7ED;
          
          .feed-content {
            .feed-title {
              font-size: 16px;
              font-weight: 600;
              color: #303133;
              margin: 0 0 8px 0;
            }
            
            .feed-summary {
              font-size: 14px;
              color: #606266;
              margin: 0 0 12px 0;
            }
            
            .feed-meta {
              display: flex;
              justify-content: space-between;
              font-size: 12px;
              color: #909399;
            }
          }
        }
      }
      
      .mobile-monitor {
        padding: 16px;
        
        .monitor-cards {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 12px;
          
          .monitor-card {
            background: white;
            border-radius: 8px;
            padding: 16px;
            border: 1px solid #E4E7ED;
            text-align: center;
            
            .card-header {
              display: flex;
              align-items: center;
              justify-content: center;
              gap: 8px;
              margin-bottom: 12px;
              color: #409EFF;
              font-size: 14px;
            }
            
            .card-value {
              font-size: 18px;
              font-weight: 600;
              color: #303133;
              
              &.success {
                color: #67C23A;
              }
            }
          }
        }
      }
      
      .mobile-settings {
        padding: 16px;
        
        .settings-list {
          background: white;
          border-radius: 8px;
          border: 1px solid #E4E7ED;
          
          .setting-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px;
            border-bottom: 1px solid #F0F2F5;
            
            &:last-child {
              border-bottom: none;
            }
            
            .setting-label {
              font-size: 14px;
              color: #303133;
            }
          }
        }
      }
    }
  }
  
  .mobile-bottom-nav {
    display: flex;
    background: white;
    border-top: 1px solid #E4E7ED;
    
    .nav-item {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 8px 12px;
      cursor: pointer;
      transition: all 0.3s;
      
      &.active {
        color: #409EFF;
      }
      
      .nav-icon {
        font-size: 20px;
        margin-bottom: 4px;
      }
      
      .nav-label {
        font-size: 12px;
      }
    }
  }
}

// 多屏协作场景样式
.multiscreen-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  
  .multiscreen-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    background: white;
    border-bottom: 1px solid #E4E7ED;
    
    .screen-indicator {
      display: flex;
      align-items: center;
      gap: 16px;
      
      .screen-info {
        display: flex;
        align-items: center;
        gap: 8px;
        
        .screen-icon {
          font-size: 18px;
          color: #409EFF;
        }
        
        .screen-label {
          font-size: 14px;
          font-weight: 500;
          color: #303133;
        }
      }
    }
    
    .collaboration-tools {
      display: flex;
      gap: 12px;
    }
  }
  
  .multiscreen-content {
    flex: 1;
    display: flex;
    gap: 24px;
    padding: 24px;
    
    .screen-layout {
      flex: 1;
      display: grid;
      grid-template-rows: 1fr 1fr;
      gap: 24px;
      
      .screen-section {
        background: white;
        border-radius: 8px;
        border: 1px solid #E4E7ED;
        display: flex;
        flex-direction: column;
        
        .screen-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 20px;
          border-bottom: 1px solid #E4E7ED;
          
          .screen-title {
            font-size: 16px;
            font-weight: 600;
            color: #303133;
            margin: 0;
          }
        }
        
        .screen-content {
          flex: 1;
          padding: 20px;
          
          .screen-dashboard {
            .dashboard-grid {
              display: grid;
              grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
              gap: 16px;
              
              .dashboard-item {
                background: #F8F9FA;
                border-radius: 6px;
                padding: 16px;
                
                h5 {
                  margin: 0 0 12px 0;
                  font-size: 14px;
                  color: #303133;
                }
                
                .chart-placeholder {
                  display: flex;
                  flex-direction: column;
                  align-items: center;
                  justify-content: center;
                  height: 100px;
                  color: #909399;
                  
                  .el-icon {
                    font-size: 24px;
                    margin-bottom: 8px;
                  }
                }
                
                .status-indicators {
                  display: flex;
                  flex-direction: column;
                  gap: 8px;
                  
                  .indicator {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 12px;
                    
                    .indicator-dot {
                      width: 8px;
                      height: 8px;
                      border-radius: 50%;
                      background: #909399;
                    }
                    
                    &.success .indicator-dot {
                      background: #67C23A;
                    }
                    
                    &.warning .indicator-dot {
                      background: #E6A23C;
                    }
                  }
                }
              }
            }
          }
          
          .screen-preview {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #909399;
            
            .preview-icon {
              font-size: 48px;
              margin-bottom: 16px;
            }
            
            p {
              margin: 0 0 16px 0;
              font-size: 14px;
            }
          }
        }
      }
    }
    
    .collaboration-panel {
      width: 320px;
      background: white;
      border-radius: 8px;
      border: 1px solid #E4E7ED;
      display: flex;
      flex-direction: column;
      
      .panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 20px;
        border-bottom: 1px solid #E4E7ED;
        
        .panel-title {
          font-size: 16px;
          font-weight: 600;
          color: #303133;
          margin: 0;
        }
      }
      
      .panel-content {
        flex: 1;
        padding: 20px;
        
        .online-users,
        .recent-activities {
          margin-bottom: 24px;
          
          &:last-child {
            margin-bottom: 0;
          }
          
          h5 {
            font-size: 14px;
            font-weight: 600;
            color: #303133;
            margin: 0 0 12px 0;
          }
          
          .user-list,
          .activity-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
            
            .user-item,
            .activity-item {
              display: flex;
              align-items: center;
              gap: 8px;
              padding: 8px;
              background: #F8F9FA;
              border-radius: 6px;
              
              .user-name {
                flex: 1;
                font-size: 12px;
                color: #303133;
              }
              
              .activity-icon {
                font-size: 16px;
                color: #409EFF;
              }
              
              .activity-content {
                flex: 1;
                
                .activity-text {
                  font-size: 12px;
                  color: #303133;
                  margin: 0 0 4px 0;
                }
                
                .activity-time {
                  font-size: 11px;
                  color: #909399;
                }
              }
            }
          }
        }
      }
    }
  }
}

// 响应式适配
@media (max-width: 1024px) {
  .office-layout {
    .office-sidebar {
      width: 240px;
    }
    
    .office-workspace {
      .workspace-grid {
        grid-template-columns: 1fr;
        
        .secondary-panel {
          order: -1;
        }
      }
    }
  }
  
  .multiscreen-layout {
    .multiscreen-content {
      flex-direction: column;
      
      .collaboration-panel {
        width: 100%;
        height: 200px;
        
        .panel-content {
          .online-users,
          .recent-activities {
            display: inline-block;
            width: 48%;
            vertical-align: top;
            margin-right: 4%;
          }
        }
      }
    }
  }
}

@media (max-width: 768px) {
  .scenario-adapter {
    .scenario-header {
      flex-direction: column;
      gap: 16px;
      align-items: flex-start;
      
      .scenario-controls {
        align-self: stretch;
        justify-content: space-between;
      }
    }
  }
  
  .office-layout {
    flex-direction: column;
    
    .office-sidebar {
      width: 100%;
      height: 200px;
      overflow-y: auto;
      
      .sidebar-section {
        .quick-actions {
          flex-direction: row;
          flex-wrap: wrap;
          
          .quick-action-btn {
            flex: 1;
            min-width: 100px;
          }
        }
      }
    }
  }
  
  .multiscreen-layout {
    .multiscreen-content {
      .screen-layout {
        grid-template-rows: 1fr;
        
        .secondary-screen {
          display: none;
        }
      }
    }
  }
}
</style> 