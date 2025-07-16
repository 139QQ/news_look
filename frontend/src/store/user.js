import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    // 用户信息
    userInfo: {
      id: null,
      username: '',
      role: 'user', // admin, analyst, user
      permissions: []
    },
    
    // 用户偏好设置
    preferences: {
      theme: 'light',
      layout: 'default',
      dashboardLayout: 'grid',
      itemsPerPage: 20,
      defaultView: 'list'
    },
    
    // 角色配置
    roleConfig: {
      admin: {
        name: '管理员',
        permissions: ['system:monitor', 'crawler:manage', 'user:manage', 'data:export'],
        features: ['dashboard', 'crawler-monitor', 'system-config', 'user-management'],
        defaultView: 'dashboard',
        layout: 'admin-layout'
      },
      analyst: {
        name: '分析师',
        permissions: ['data:read', 'data:analyze', 'data:export', 'report:create'],
        features: ['data-analysis', 'charts', 'reports', 'trends'],
        defaultView: 'analysis',
        layout: 'analyst-layout'
      },
      user: {
        name: '普通用户',
        permissions: ['news:read', 'news:search', 'news:bookmark'],
        features: ['news-list', 'search', 'bookmarks'],
        defaultView: 'news',
        layout: 'user-layout'
      }
    }
  }),
  
  getters: {
    // 获取当前用户角色配置
    currentRoleConfig: (state) => {
      return state.roleConfig[state.userInfo.role] || state.roleConfig.user
    },
    
    // 检查用户权限
    hasPermission: (state) => (permission) => {
      const roleConfig = state.roleConfig[state.userInfo.role]
      return roleConfig?.permissions.includes(permission) || false
    },
    
    // 检查用户功能访问权限
    hasFeature: (state) => (feature) => {
      const roleConfig = state.roleConfig[state.userInfo.role]
      return roleConfig?.features.includes(feature) || false
    },
    
    // 获取用户界面布局
    getUserLayout: (state) => {
      return state.roleConfig[state.userInfo.role]?.layout || 'user-layout'
    },
    
    // 获取用户默认视图
    getDefaultView: (state) => {
      return state.roleConfig[state.userInfo.role]?.defaultView || 'news'
    }
  },
  
  actions: {
    // 设置用户信息
    setUserInfo(userInfo) {
      this.userInfo = { ...this.userInfo, ...userInfo }
    },
    
    // 设置用户角色
    setUserRole(role) {
      this.userInfo.role = role
      // 根据角色设置默认偏好
      this.updatePreferencesByRole()
    },
    
    // 根据角色更新偏好设置
    updatePreferencesByRole() {
      const roleConfig = this.roleConfig[this.userInfo.role]
      if (roleConfig) {
        this.preferences.layout = roleConfig.layout
        this.preferences.defaultView = roleConfig.defaultView
        
        // 管理员偏好
        if (this.userInfo.role === 'admin') {
          this.preferences.dashboardLayout = 'grid'
          this.preferences.itemsPerPage = 50
        }
        // 分析师偏好
        else if (this.userInfo.role === 'analyst') {
          this.preferences.dashboardLayout = 'chart'
          this.preferences.itemsPerPage = 100
        }
        // 普通用户偏好
        else {
          this.preferences.dashboardLayout = 'list'
          this.preferences.itemsPerPage = 20
        }
      }
    },
    
    // 更新用户偏好
    updatePreferences(preferences) {
      this.preferences = { ...this.preferences, ...preferences }
    },
    
    // 登录
    login(userInfo) {
      this.setUserInfo(userInfo)
      this.updatePreferencesByRole()
    },
    
    // 登出
    logout() {
      this.userInfo = {
        id: null,
        username: '',
        role: 'user',
        permissions: []
      }
      this.preferences = {
        theme: 'light',
        layout: 'default',
        dashboardLayout: 'grid',
        itemsPerPage: 20,
        defaultView: 'list'
      }
    }
  }
}) 