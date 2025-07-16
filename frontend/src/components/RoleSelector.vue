<template>
  <div class="role-selector">
    <el-dropdown 
      trigger="click" 
      @command="handleRoleChange"
      class="role-dropdown"
    >
      <el-button type="primary" class="role-button">
        <el-icon class="role-icon">
          <component :is="currentRoleIcon" />
        </el-icon>
        {{ currentRoleConfig.name }}
        <el-icon class="arrow-icon">
          <arrow-down />
        </el-icon>
      </el-button>
      
      <template #dropdown>
        <el-dropdown-menu class="role-menu">
          <el-dropdown-item 
            v-for="(config, role) in roleConfigs" 
            :key="role"
            :command="role"
            :class="{ active: currentRole === role }"
            class="role-item"
          >
            <div class="role-item-content">
              <el-icon class="role-item-icon">
                <component :is="getRoleIcon(role)" />
              </el-icon>
              <div class="role-item-info">
                <div class="role-item-name">{{ config.name }}</div>
                <div class="role-item-desc">{{ config.description }}</div>
              </div>
              <el-tag 
                v-if="currentRole === role" 
                size="small" 
                type="success"
                class="current-tag"
              >
                当前
              </el-tag>
            </div>
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
    
    <!-- 角色说明卡片 -->
    <el-card 
      v-if="showRoleInfo" 
      class="role-info-card"
      shadow="hover"
    >
      <template #header>
        <div class="card-header">
          <el-icon class="header-icon">
            <component :is="currentRoleIcon" />
          </el-icon>
          <span class="header-title">{{ currentRoleConfig.name }}</span>
          <el-button 
            type="text" 
            size="small" 
            @click="showRoleInfo = false"
            class="close-btn"
          >
            <el-icon><close /></el-icon>
          </el-button>
        </div>
      </template>
      
      <div class="role-info-content">
        <div class="info-section">
          <h4>主要功能</h4>
          <ul class="feature-list">
            <li 
              v-for="feature in currentRoleConfig.features" 
              :key="feature"
              class="feature-item"
            >
              <el-icon class="feature-icon">
                <check />
              </el-icon>
              {{ getFeatureName(feature) }}
            </li>
          </ul>
        </div>
        
        <div class="info-section">
          <h4>权限范围</h4>
          <el-tag 
            v-for="permission in currentRoleConfig.permissions" 
            :key="permission"
            size="small"
            class="permission-tag"
          >
            {{ getPermissionName(permission) }}
          </el-tag>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { useUserStore } from '@/store/user'
import { 
  ArrowDown, 
  Close, 
  Check, 
  User, 
  Setting, 
  DataAnalysis 
} from '@element-plus/icons-vue'

export default {
  name: 'RoleSelector',
  components: {
    ArrowDown,
    Close,
    Check,
    User,
    Setting,
    DataAnalysis
  },
  
  setup() {
    const userStore = useUserStore()
    const showRoleInfo = ref(false)
    
    // 角色配置
    const roleConfigs = {
      admin: {
        name: '管理员',
        description: '系统管理和监控',
        icon: 'Setting',
        permissions: ['system:monitor', 'crawler:manage', 'user:manage', 'data:export'],
        features: ['dashboard', 'crawler-monitor', 'system-config', 'user-management']
      },
      analyst: {
        name: '分析师',
        description: '数据分析和报告',
        icon: 'DataAnalysis',
        permissions: ['data:read', 'data:analyze', 'data:export', 'report:create'],
        features: ['data-analysis', 'charts', 'reports', 'trends']
      },
      user: {
        name: '普通用户',
        description: '新闻浏览和搜索',
        icon: 'User',
        permissions: ['news:read', 'news:search', 'news:bookmark'],
        features: ['news-list', 'search', 'bookmarks']
      }
    }
    
    // 计算属性
    const currentRole = computed(() => userStore.userInfo.role)
    const currentRoleConfig = computed(() => roleConfigs[currentRole.value])
    const currentRoleIcon = computed(() => getRoleIcon(currentRole.value))
    
    // 方法
    const handleRoleChange = (role) => {
      userStore.setUserRole(role)
      showRoleInfo.value = true
      
      // 3秒后自动隐藏角色信息
      setTimeout(() => {
        showRoleInfo.value = false
      }, 3000)
    }
    
    const getRoleIcon = (role) => {
      const iconMap = {
        admin: 'Setting',
        analyst: 'DataAnalysis',
        user: 'User'
      }
      return iconMap[role] || 'User'
    }
    
    const getFeatureName = (feature) => {
      const featureMap = {
        'dashboard': '仪表盘',
        'crawler-monitor': '爬虫监控',
        'system-config': '系统配置',
        'user-management': '用户管理',
        'data-analysis': '数据分析',
        'charts': '图表展示',
        'reports': '报告生成',
        'trends': '趋势分析',
        'news-list': '新闻列表',
        'search': '搜索功能',
        'bookmarks': '收藏功能'
      }
      return featureMap[feature] || feature
    }
    
    const getPermissionName = (permission) => {
      const permissionMap = {
        'system:monitor': '系统监控',
        'crawler:manage': '爬虫管理',
        'user:manage': '用户管理',
        'data:export': '数据导出',
        'data:read': '数据读取',
        'data:analyze': '数据分析',
        'report:create': '报告创建',
        'news:read': '新闻阅读',
        'news:search': '新闻搜索',
        'news:bookmark': '新闻收藏'
      }
      return permissionMap[permission] || permission
    }
    
    return {
      showRoleInfo,
      roleConfigs,
      currentRole,
      currentRoleConfig,
      currentRoleIcon,
      handleRoleChange,
      getRoleIcon,
      getFeatureName,
      getPermissionName
    }
  }
}
</script>

<style lang="scss" scoped>
.role-selector {
  position: relative;
  
  .role-dropdown {
    .role-button {
      padding: 8px 16px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 500;
      
      .role-icon {
        font-size: 16px;
      }
      
      .arrow-icon {
        margin-left: 4px;
        font-size: 12px;
        transition: transform 0.3s;
      }
      
      &:hover .arrow-icon {
        transform: rotate(180deg);
      }
    }
  }
  
  .role-menu {
    min-width: 280px;
    padding: 8px;
    
    .role-item {
      margin: 4px 0;
      border-radius: 6px;
      padding: 0;
      
      &.active {
        background: rgba(64, 158, 255, 0.1);
        color: #409EFF;
      }
      
      .role-item-content {
        display: flex;
        align-items: center;
        padding: 12px;
        gap: 12px;
        
        .role-item-icon {
          font-size: 20px;
          color: #409EFF;
        }
        
        .role-item-info {
          flex: 1;
          
          .role-item-name {
            font-size: 14px;
            font-weight: 500;
            color: #303133;
          }
          
          .role-item-desc {
            font-size: 12px;
            color: #909399;
            margin-top: 2px;
          }
        }
        
        .current-tag {
          font-size: 10px;
        }
      }
    }
  }
  
  .role-info-card {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    margin-top: 8px;
    z-index: 1000;
    border: 1px solid #E4E7ED;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    
    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .header-icon {
        font-size: 18px;
        color: #409EFF;
      }
      
      .header-title {
        flex: 1;
        font-weight: 500;
        color: #303133;
      }
      
      .close-btn {
        padding: 4px;
        color: #909399;
        
        &:hover {
          color: #409EFF;
        }
      }
    }
    
    .role-info-content {
      .info-section {
        margin-bottom: 16px;
        
        &:last-child {
          margin-bottom: 0;
        }
        
        h4 {
          font-size: 13px;
          color: #606266;
          margin: 0 0 8px 0;
          font-weight: 500;
        }
        
        .feature-list {
          list-style: none;
          padding: 0;
          margin: 0;
          
          .feature-item {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 0;
            font-size: 12px;
            color: #606266;
            
            .feature-icon {
              font-size: 12px;
              color: #67C23A;
            }
          }
        }
        
        .permission-tag {
          margin: 2px 4px 2px 0;
          font-size: 11px;
        }
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .role-selector {
    .role-info-card {
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 90%;
      max-width: 400px;
    }
  }
}
</style> 