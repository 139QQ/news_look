<template>
  <div class="content-organizer">
    <!-- 内容组织控制面板 -->
    <div class="organizer-controls">
      <div class="controls-row">
        <!-- 分组选择 -->
        <div class="control-group">
          <label class="control-label">分组方式</label>
          <el-select v-model="groupBy" @change="handleGroupChange" placeholder="选择分组方式">
            <el-option
              v-for="group in groupOptions"
              :key="group.value"
              :label="group.label"
              :value="group.value"
              :disabled="group.disabled"
            >
              <i :class="group.icon"></i>
              {{ group.label }}
            </el-option>
          </el-select>
        </div>

        <!-- 排序选择 -->
        <div class="control-group">
          <label class="control-label">排序方式</label>
          <el-select v-model="sortBy" @change="handleSortChange" placeholder="选择排序方式">
            <el-option
              v-for="sort in sortOptions"
              :key="sort.value"
              :label="sort.label"
              :value="sort.value"
            >
              <i :class="sort.icon"></i>
              {{ sort.label }}
            </el-option>
          </el-select>
        </div>

        <!-- 过滤器 -->
        <div class="control-group">
          <label class="control-label">过滤条件</label>
          <el-select v-model="filterBy" @change="handleFilterChange" multiple placeholder="选择过滤条件">
            <el-option
              v-for="filter in filterOptions"
              :key="filter.value"
              :label="filter.label"
              :value="filter.value"
            >
              <el-tag :type="filter.type" size="small">{{ filter.label }}</el-tag>
            </el-option>
          </el-select>
        </div>

        <!-- 视图切换 -->
        <div class="control-group">
          <label class="control-label">视图模式</label>
          <el-radio-group v-model="viewMode" @change="handleViewChange">
            <el-radio-button label="grid">
              <i class="el-icon-grid"></i>
              网格
            </el-radio-button>
            <el-radio-button label="list">
              <i class="el-icon-menu"></i>
              列表
            </el-radio-button>
            <el-radio-button label="tree">
              <i class="el-icon-share"></i>
              树形
            </el-radio-button>
          </el-radio-group>
        </div>
      </div>
    </div>

    <!-- 内容展示区域 -->
    <div class="content-display">
      <!-- 网格视图 -->
      <div v-if="viewMode === 'grid'" class="grid-view">
        <div v-for="group in organizedData" :key="group.id" class="content-group">
          <div class="group-header">
            <div class="group-title">
              <i :class="group.icon"></i>
              {{ group.title }}
              <el-badge :value="group.count" type="primary" />
            </div>
            <div class="group-actions">
              <el-button size="small" text @click="collapseGroup(group.id)">
                <i :class="group.collapsed ? 'el-icon-arrow-right' : 'el-icon-arrow-down'"></i>
              </el-button>
              <el-button size="small" text @click="sortGroup(group.id)">
                <i class="el-icon-sort"></i>
              </el-button>
            </div>
          </div>
          <transition name="slide-fade">
            <div v-show="!group.collapsed" class="group-content">
              <div class="content-grid">
                <div 
                  v-for="item in group.items" 
                  :key="item.id"
                  class="content-item"
                  :class="{ 'high-priority': item.priority === 'high', 'medium-priority': item.priority === 'medium' }"
                  @click="selectItem(item)"
                >
                  <div class="item-header">
                    <div class="item-priority">
                      <el-tag :type="getPriorityType(item.priority)" size="small">
                        {{ getPriorityLabel(item.priority) }}
                      </el-tag>
                    </div>
                    <div class="item-actions">
                      <el-button size="small" text @click.stop="editItem(item)">
                        <i class="el-icon-edit"></i>
                      </el-button>
                      <el-button size="small" text @click.stop="deleteItem(item)">
                        <i class="el-icon-delete"></i>
                      </el-button>
                    </div>
                  </div>
                  <div class="item-content">
                    <h4 class="item-title">{{ item.title }}</h4>
                    <p class="item-description">{{ item.description }}</p>
                    <div class="item-meta">
                      <span class="item-date">{{ formatDate(item.date) }}</span>
                      <span class="item-status" :class="item.status">{{ item.status }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </transition>
        </div>
      </div>

      <!-- 列表视图 -->
      <div v-else-if="viewMode === 'list'" class="list-view">
        <el-table :data="flattenedData" stripe style="width: 100%">
          <el-table-column prop="priority" label="优先级" width="100" sortable>
            <template #default="scope">
              <el-tag :type="getPriorityType(scope.row.priority)" size="small">
                {{ getPriorityLabel(scope.row.priority) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="标题" sortable />
          <el-table-column prop="category" label="分类" width="120" sortable />
          <el-table-column prop="status" label="状态" width="100" sortable>
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)" size="small">
                {{ scope.row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="date" label="日期" width="180" sortable />
          <el-table-column label="操作" width="150">
            <template #default="scope">
              <el-button size="small" @click="editItem(scope.row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteItem(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 树形视图 -->
      <div v-else-if="viewMode === 'tree'" class="tree-view">
        <el-tree
          :data="treeData"
          :props="treeProps"
          show-checkbox
          node-key="id"
          :default-expand-all="false"
          :expand-on-click-node="false"
          @node-click="handleNodeClick"
        >
          <template #default="{ node, data }">
            <div class="tree-node">
              <div class="node-content">
                <i :class="data.icon"></i>
                <span class="node-title">{{ data.title }}</span>
                <el-tag v-if="data.priority" :type="getPriorityType(data.priority)" size="small">
                  {{ getPriorityLabel(data.priority) }}
                </el-tag>
                <el-badge v-if="data.count" :value="data.count" type="primary" />
              </div>
              <div class="node-actions">
                <el-button size="small" text @click.stop="editNode(data)">
                  <i class="el-icon-edit"></i>
                </el-button>
                <el-button size="small" text @click.stop="deleteNode(data)">
                  <i class="el-icon-delete"></i>
                </el-button>
              </div>
            </div>
          </template>
        </el-tree>
      </div>
    </div>

    <!-- 内容详情抽屉 -->
    <el-drawer
      v-model="detailDrawer"
      :title="selectedItem?.title || '内容详情'"
      direction="rtl"
      size="40%"
    >
      <div v-if="selectedItem" class="item-detail">
        <div class="detail-header">
          <div class="detail-priority">
            <el-tag :type="getPriorityType(selectedItem.priority)" size="large">
              {{ getPriorityLabel(selectedItem.priority) }}
            </el-tag>
          </div>
          <div class="detail-status">
            <el-tag :type="getStatusType(selectedItem.status)" size="large">
              {{ selectedItem.status }}
            </el-tag>
          </div>
        </div>
        <div class="detail-content">
          <h3>{{ selectedItem.title }}</h3>
          <p class="detail-description">{{ selectedItem.description }}</p>
          <div class="detail-meta">
            <div class="meta-item">
              <label>分类：</label>
              <span>{{ selectedItem.category }}</span>
            </div>
            <div class="meta-item">
              <label>创建时间：</label>
              <span>{{ formatDate(selectedItem.date) }}</span>
            </div>
            <div class="meta-item">
              <label>最后更新：</label>
              <span>{{ formatDate(selectedItem.updatedAt) }}</span>
            </div>
          </div>
        </div>
        <div class="detail-actions">
          <el-button type="primary" @click="editItem(selectedItem)">编辑</el-button>
          <el-button type="danger" @click="deleteItem(selectedItem)">删除</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'ContentOrganizer',
  setup() {
    // 响应式数据
    const groupBy = ref('category')
    const sortBy = ref('priority')
    const filterBy = ref([])
    const viewMode = ref('grid')
    const selectedItem = ref(null)
    const detailDrawer = ref(false)

    // 模拟数据
    const rawData = ref([
      {
        id: 1,
        title: '财经新闻爬虫状态监控',
        description: '实时监控各大财经网站的爬虫运行状态',
        category: '系统监控',
        priority: 'high',
        status: '运行中',
        date: '2024-01-15',
        updatedAt: '2024-01-15T10:30:00'
      },
      {
        id: 2,
        title: '股票价格数据分析',
        description: '对收集的股票价格数据进行趋势分析',
        category: '数据分析',
        priority: 'medium',
        status: '已完成',
        date: '2024-01-14',
        updatedAt: '2024-01-14T16:45:00'
      },
      {
        id: 3,
        title: '爬虫规则配置优化',
        description: '优化现有爬虫规则，提高数据采集效率',
        category: '配置管理',
        priority: 'low',
        status: '待处理',
        date: '2024-01-13',
        updatedAt: '2024-01-13T09:15:00'
      },
      {
        id: 4,
        title: '用户权限管理',
        description: '管理不同用户的系统访问权限',
        category: '用户管理',
        priority: 'medium',
        status: '进行中',
        date: '2024-01-12',
        updatedAt: '2024-01-12T14:20:00'
      },
      {
        id: 5,
        title: '数据备份策略',
        description: '制定定期数据备份和恢复策略',
        category: '系统监控',
        priority: 'high',
        status: '待处理',
        date: '2024-01-11',
        updatedAt: '2024-01-11T11:00:00'
      }
    ])

    // 配置选项
    const groupOptions = [
      { value: 'category', label: '按分类分组', icon: 'el-icon-folder' },
      { value: 'priority', label: '按优先级分组', icon: 'el-icon-star-on' },
      { value: 'status', label: '按状态分组', icon: 'el-icon-circle-check' },
      { value: 'date', label: '按日期分组', icon: 'el-icon-calendar' }
    ]

    const sortOptions = [
      { value: 'priority', label: '按优先级排序', icon: 'el-icon-sort' },
      { value: 'date', label: '按日期排序', icon: 'el-icon-time' },
      { value: 'title', label: '按标题排序', icon: 'el-icon-sort-up' },
      { value: 'status', label: '按状态排序', icon: 'el-icon-circle-check' }
    ]

    const filterOptions = [
      { value: 'high', label: '高优先级', type: 'danger' },
      { value: 'medium', label: '中优先级', type: 'warning' },
      { value: 'low', label: '低优先级', type: 'info' },
      { value: 'running', label: '运行中', type: 'success' },
      { value: 'pending', label: '待处理', type: 'warning' },
      { value: 'completed', label: '已完成', type: 'success' }
    ]

    // 计算属性
    const organizedData = computed(() => {
      let filtered = rawData.value
      
      // 应用过滤器
      if (filterBy.value.length > 0) {
        filtered = filtered.filter(item => 
          filterBy.value.includes(item.priority) || 
          filterBy.value.includes(item.status.toLowerCase())
        )
      }

      // 按分组方式分组
      const groups = {}
      filtered.forEach(item => {
        const key = item[groupBy.value]
        if (!groups[key]) {
          groups[key] = {
            id: key,
            title: key,
            icon: getGroupIcon(key),
            items: [],
            count: 0,
            collapsed: false
          }
        }
        groups[key].items.push(item)
        groups[key].count++
      })

      // 对每个分组内的项目排序
      Object.values(groups).forEach(group => {
        group.items.sort((a, b) => {
          if (sortBy.value === 'priority') {
            const priorityOrder = { high: 3, medium: 2, low: 1 }
            return priorityOrder[b.priority] - priorityOrder[a.priority]
          } else if (sortBy.value === 'date') {
            return new Date(b.date) - new Date(a.date)
          } else {
            return a[sortBy.value].localeCompare(b[sortBy.value])
          }
        })
      })

      return Object.values(groups)
    })

    const flattenedData = computed(() => {
      let filtered = rawData.value
      
      if (filterBy.value.length > 0) {
        filtered = filtered.filter(item => 
          filterBy.value.includes(item.priority) || 
          filterBy.value.includes(item.status.toLowerCase())
        )
      }

      return filtered.sort((a, b) => {
        if (sortBy.value === 'priority') {
          const priorityOrder = { high: 3, medium: 2, low: 1 }
          return priorityOrder[b.priority] - priorityOrder[a.priority]
        } else if (sortBy.value === 'date') {
          return new Date(b.date) - new Date(a.date)
        } else {
          return a[sortBy.value].localeCompare(b[sortBy.value])
        }
      })
    })

    const treeData = computed(() => {
      const tree = []
      const categoryMap = {}

      rawData.value.forEach(item => {
        if (!categoryMap[item.category]) {
          categoryMap[item.category] = {
            id: item.category,
            title: item.category,
            icon: getGroupIcon(item.category),
            children: [],
            count: 0
          }
        }
        
        categoryMap[item.category].children.push({
          id: item.id,
          title: item.title,
          icon: 'el-icon-document',
          priority: item.priority,
          status: item.status,
          isLeaf: true
        })
        categoryMap[item.category].count++
      })

      return Object.values(categoryMap)
    })

    const treeProps = {
      children: 'children',
      label: 'title'
    }

    // 方法
    const handleGroupChange = (value) => {
      ElMessage.success(`分组方式已切换为：${getGroupLabel(value)}`)
    }

    const handleSortChange = (value) => {
      ElMessage.success(`排序方式已切换为：${getSortLabel(value)}`)
    }

    const handleFilterChange = (value) => {
      ElMessage.success(`过滤条件已更新，共选中${value.length}个条件`)
    }

    const handleViewChange = (value) => {
      ElMessage.success(`视图模式已切换为：${getViewLabel(value)}`)
    }

    const collapseGroup = (groupId) => {
      const group = organizedData.value.find(g => g.id === groupId)
      if (group) {
        group.collapsed = !group.collapsed
      }
    }

    const sortGroup = (groupId) => {
      ElMessage.info(`对分组 "${groupId}" 进行排序`)
    }

    const selectItem = (item) => {
      selectedItem.value = item
      detailDrawer.value = true
    }

    const editItem = (item) => {
      ElMessage.info(`编辑项目：${item.title}`)
    }

    const deleteItem = (item) => {
      ElMessageBox.confirm(
        `确定要删除 "${item.title}" 吗？`,
        '删除确认',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(() => {
        const index = rawData.value.findIndex(d => d.id === item.id)
        if (index > -1) {
          rawData.value.splice(index, 1)
          ElMessage.success('删除成功')
        }
      }).catch(() => {
        ElMessage.info('已取消删除')
      })
    }

    const handleNodeClick = (data) => {
      if (data.isLeaf) {
        const item = rawData.value.find(item => item.id === data.id)
        if (item) {
          selectItem(item)
        }
      }
    }

    const editNode = (data) => {
      ElMessage.info(`编辑节点：${data.title}`)
    }

    const deleteNode = (data) => {
      ElMessage.info(`删除节点：${data.title}`)
    }

    // 辅助函数
    const getPriorityType = (priority) => {
      const types = { high: 'danger', medium: 'warning', low: 'info' }
      return types[priority] || 'info'
    }

    const getPriorityLabel = (priority) => {
      const labels = { high: '高优先级', medium: '中优先级', low: '低优先级' }
      return labels[priority] || priority
    }

    const getStatusType = (status) => {
      const types = { 
        '运行中': 'success', 
        '已完成': 'success', 
        '待处理': 'warning', 
        '进行中': 'primary' 
      }
      return types[status] || 'info'
    }

    const getGroupIcon = (group) => {
      const icons = {
        '系统监控': 'el-icon-monitor',
        '数据分析': 'el-icon-pie-chart',
        '配置管理': 'el-icon-setting',
        '用户管理': 'el-icon-user',
        'category': 'el-icon-folder',
        'priority': 'el-icon-star-on',
        'status': 'el-icon-circle-check',
        'date': 'el-icon-calendar'
      }
      return icons[group] || 'el-icon-document'
    }

    const getGroupLabel = (value) => {
      const option = groupOptions.find(opt => opt.value === value)
      return option ? option.label : value
    }

    const getSortLabel = (value) => {
      const option = sortOptions.find(opt => opt.value === value)
      return option ? option.label : value
    }

    const getViewLabel = (value) => {
      const labels = { grid: '网格视图', list: '列表视图', tree: '树形视图' }
      return labels[value] || value
    }

    const formatDate = (date) => {
      return new Date(date).toLocaleDateString('zh-CN')
    }

    onMounted(() => {
      ElMessage.success('内容组织器已加载完成')
    })

    return {
      groupBy,
      sortBy,
      filterBy,
      viewMode,
      selectedItem,
      detailDrawer,
      groupOptions,
      sortOptions,
      filterOptions,
      organizedData,
      flattenedData,
      treeData,
      treeProps,
      handleGroupChange,
      handleSortChange,
      handleFilterChange,
      handleViewChange,
      collapseGroup,
      sortGroup,
      selectItem,
      editItem,
      deleteItem,
      handleNodeClick,
      editNode,
      deleteNode,
      getPriorityType,
      getPriorityLabel,
      getStatusType,
      formatDate
    }
  }
}
</script>

<style scoped>
.content-organizer {
  min-height: 100vh;
  background: #f5f7fa;
}

.organizer-controls {
  background: white;
  padding: 24px;
  border-radius: 8px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.controls-row {
  display: flex;
  gap: 24px;
  align-items: end;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.control-label {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
}

.content-display {
  min-height: 400px;
}

/* 网格视图样式 */
.grid-view {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.content-group {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.group-title i {
  color: #409eff;
}

.group-actions {
  display: flex;
  gap: 8px;
}

.group-content {
  padding: 24px;
}

.content-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.content-item {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.content-item:hover {
  background: #e3f2fd;
  border-color: #409eff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.content-item.high-priority {
  border-left: 4px solid #f56c6c;
}

.content-item.medium-priority {
  border-left: 4px solid #e6a23c;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.item-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.content-item:hover .item-actions {
  opacity: 1;
}

.item-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.item-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.item-description {
  font-size: 14px;
  color: #606266;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.item-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #909399;
}

.item-status {
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.item-status.运行中 {
  background: #f0f9ff;
  color: #67c23a;
}

.item-status.已完成 {
  background: #f0f9ff;
  color: #67c23a;
}

.item-status.待处理 {
  background: #fef0e6;
  color: #e6a23c;
}

.item-status.进行中 {
  background: #e6f7ff;
  color: #409eff;
}

/* 列表视图样式 */
.list-view {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* 树形视图样式 */
.tree-view {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 24px;
}

.tree-node {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 8px 0;
}

.node-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-title {
  font-weight: 500;
  color: #303133;
}

.node-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.tree-node:hover .node-actions {
  opacity: 1;
}

/* 详情抽屉样式 */
.item-detail {
  padding: 24px;
}

.detail-header {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.detail-content h3 {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 16px 0;
}

.detail-description {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  margin: 0 0 24px 0;
}

.detail-meta {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.meta-item label {
  font-weight: 500;
  color: #909399;
  min-width: 80px;
}

.detail-actions {
  display: flex;
  gap: 12px;
}

/* 动画效果 */
.slide-fade-enter-active {
  transition: all 0.3s ease;
}

.slide-fade-leave-active {
  transition: all 0.3s ease;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-10px);
  opacity: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .controls-row {
    flex-direction: column;
    gap: 16px;
  }
  
  .content-grid {
    grid-template-columns: 1fr;
  }
  
  .organizer-controls {
    padding: 16px;
  }
}
</style> 