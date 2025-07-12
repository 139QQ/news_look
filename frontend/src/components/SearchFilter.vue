<template>
  <div class="search-filter">
    <el-card class="filter-card" shadow="hover">
      <template #header>
        <div class="filter-header">
          <span class="filter-title">
            <el-icon><Search /></el-icon>
            筛选条件
          </span>
          <div class="filter-actions">
            <el-button 
              size="small" 
              @click="resetFilters"
              :disabled="!hasActiveFilters"
            >
              重置
            </el-button>
            <el-button 
              size="small" 
              @click="toggleCollapse"
              :icon="collapsed ? 'ArrowDown' : 'ArrowUp'"
            >
              {{ collapsed ? '展开' : '收起' }}
            </el-button>
          </div>
        </div>
      </template>
      
      <el-collapse-transition>
        <div v-show="!collapsed" class="filter-content">
          <!-- 关键词搜索 -->
          <div class="filter-row">
            <el-input
              v-model="searchKeyword"
              placeholder="输入关键词搜索..."
              clearable
              :prefix-icon="Search"
              class="search-input"
              @input="handleSearchInput"
              @clear="handleSearchClear"
            >
              <template #append>
                <el-button 
                  type="primary"
                  :loading="searching"
                  @click="handleSearch"
                >
                  搜索
                </el-button>
              </template>
            </el-input>
          </div>
          
          <!-- 筛选条件行 -->
          <div class="filter-row">
            <div class="filter-group">
              <label class="filter-label">来源：</label>
              <el-select
                v-model="filters.source"
                placeholder="选择新闻来源"
                clearable
                multiple
                collapse-tags
                collapse-tags-tooltip
                class="filter-select"
                @change="handleFilterChange"
              >
                <el-option
                  v-for="source in sourceOptions"
                  :key="source.value"
                  :label="source.label"
                  :value="source.value"
                >
                  <span class="option-item">
                    <el-icon class="option-icon">
                      <component :is="source.icon" />
                    </el-icon>
                    {{ source.label }}
                  </span>
                </el-option>
              </el-select>
            </div>
            
            <div class="filter-group">
              <label class="filter-label">时间：</label>
              <el-date-picker
                v-model="filters.dateRange"
                type="datetimerange"
                range-separator="至"
                start-placeholder="开始时间"
                end-placeholder="结束时间"
                format="MM-DD HH:mm"
                value-format="YYYY-MM-DD HH:mm:ss"
                class="filter-date"
                @change="handleFilterChange"
              />
            </div>
            
            <div class="filter-group">
              <label class="filter-label">状态：</label>
              <el-select
                v-model="filters.status"
                placeholder="选择状态"
                clearable
                class="filter-select"
                @change="handleFilterChange"
              >
                <el-option label="全部" value="" />
                <el-option label="运行中" value="running" />
                <el-option label="已停止" value="stopped" />
                <el-option label="异常" value="error" />
              </el-select>
            </div>
          </div>
          
          <!-- 高级筛选 -->
          <div v-if="showAdvanced" class="filter-row advanced-row">
            <div class="filter-group">
              <label class="filter-label">排序：</label>
              <el-select
                v-model="filters.sortBy"
                placeholder="排序方式"
                class="filter-select"
                @change="handleFilterChange"
              >
                <el-option label="时间降序" value="time_desc" />
                <el-option label="时间升序" value="time_asc" />
                <el-option label="相关度" value="relevance" />
                <el-option label="成功率" value="success_rate" />
              </el-select>
            </div>
            
            <div class="filter-group">
              <label class="filter-label">数量：</label>
              <el-input-number
                v-model="filters.limit"
                :min="10"
                :max="1000"
                :step="10"
                class="filter-number"
                @change="handleFilterChange"
              />
            </div>
            
            <div class="filter-group">
              <label class="filter-label">成功率：</label>
              <el-slider
                v-model="filters.successRateRange"
                range
                :min="0"
                :max="100"
                :step="5"
                show-stops
                class="filter-slider"
                @change="handleFilterChange"
              />
            </div>
          </div>
          
          <!-- 快捷筛选 -->
          <div class="filter-row quick-filters">
            <label class="filter-label">快捷：</label>
            <div class="quick-filter-tags">
              <el-tag
                v-for="quick in quickFilters"
                :key="quick.key"
                :type="quick.active ? 'primary' : ''"
                :effect="quick.active ? 'dark' : 'plain'"
                clickable
                class="quick-tag"
                @click="toggleQuickFilter(quick)"
              >
                <el-icon class="mr-5">
                  <component :is="quick.icon" />
                </el-icon>
                {{ quick.label }}
              </el-tag>
            </div>
          </div>
          
          <!-- 结果统计 -->
          <div class="filter-result">
            <div class="result-info">
              <el-icon><DataLine /></el-icon>
              找到 <strong>{{ totalCount }}</strong> 条结果
              <span v-if="hasActiveFilters" class="active-filters">
                （已应用 {{ activeFilterCount }} 个筛选条件）
              </span>
            </div>
            
            <div class="result-actions">
              <el-button
                size="small"
                type="text"
                @click="showAdvanced = !showAdvanced"
              >
                {{ showAdvanced ? '简化筛选' : '高级筛选' }}
              </el-button>
              
              <el-button
                size="small"
                type="text"
                @click="saveCurrentFilter"
                :disabled="!hasActiveFilters"
              >
                保存筛选
              </el-button>
            </div>
          </div>
        </div>
      </el-collapse-transition>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { 
  Search, 
  ArrowDown, 
  ArrowUp, 
  DataLine,
  Clock,
  TrendCharts,
  Warning,
  Select
} from '@element-plus/icons-vue'
import { debounce } from 'lodash-es'

// Props
const props = defineProps({
  // 搜索模式：news(新闻)、crawler(爬虫)、log(日志)
  mode: {
    type: String,
    default: 'news'
  },
  // 是否显示高级筛选
  showAdvancedDefault: {
    type: Boolean,
    default: false
  },
  // 总数量
  totalCount: {
    type: Number,
    default: 0
  }
})

// Emits
const emit = defineEmits([
  'search',
  'filter-change',
  'reset'
])

// 响应式数据
const searchKeyword = ref('')
const searching = ref(false)
const collapsed = ref(false)
const showAdvanced = ref(props.showAdvancedDefault)

// 筛选条件
const filters = ref({
  source: [],
  dateRange: null,
  status: '',
  sortBy: 'time_desc',
  limit: 50,
  successRateRange: [0, 100]
})

// 快捷筛选
const quickFilters = ref([
  {
    key: 'today',
    label: '今日',
    icon: 'Clock',
    active: false,
    filter: () => {
      const today = new Date()
      const start = new Date(today.getFullYear(), today.getMonth(), today.getDate())
      const end = new Date(start.getTime() + 24 * 60 * 60 * 1000 - 1)
      return {
        dateRange: [
          start.toISOString().slice(0, 19).replace('T', ' '),
          end.toISOString().slice(0, 19).replace('T', ' ')
        ]
      }
    }
  },
  {
    key: 'running',
    label: '运行中',
    icon: 'TrendCharts',
    active: false,
    filter: () => ({ status: 'running' })
  },
  {
    key: 'high_success',
    label: '高成功率',
    icon: 'Select',
    active: false,
    filter: () => ({ successRateRange: [90, 100] })
  },
  {
    key: 'error',
    label: '有异常',
    icon: 'Warning',
    active: false,
    filter: () => ({ status: 'error' })
  }
])

// 来源选项
const sourceOptions = computed(() => {
  const baseOptions = [
    { label: '新浪财经', value: 'sina', icon: 'Notebook' },
    { label: '东方财富', value: 'eastmoney', icon: 'TrendCharts' },
    { label: '腾讯财经', value: 'tencent', icon: 'ChatDotRound' },
    { label: '网易财经', value: 'netease', icon: 'Headset' },
    { label: '凤凰财经', value: 'ifeng', icon: 'Promotion' }
  ]
  
  // 根据模式调整选项
  if (props.mode === 'crawler') {
    return baseOptions
  } else if (props.mode === 'news') {
    return baseOptions
  } else {
    return baseOptions
  }
})

// 计算属性
const hasActiveFilters = computed(() => {
  return (
    searchKeyword.value.trim() !== '' ||
    filters.value.source.length > 0 ||
    filters.value.dateRange !== null ||
    filters.value.status !== '' ||
    filters.value.sortBy !== 'time_desc' ||
    filters.value.limit !== 50 ||
    filters.value.successRateRange[0] !== 0 ||
    filters.value.successRateRange[1] !== 100
  )
})

const activeFilterCount = computed(() => {
  let count = 0
  if (searchKeyword.value.trim() !== '') count++
  if (filters.value.source.length > 0) count++
  if (filters.value.dateRange !== null) count++
  if (filters.value.status !== '') count++
  if (filters.value.sortBy !== 'time_desc') count++
  if (filters.value.limit !== 50) count++
  if (filters.value.successRateRange[0] !== 0 || filters.value.successRateRange[1] !== 100) count++
  return count
})

// 防抖搜索
const handleSearchInput = debounce((value) => {
  if (value.trim()) {
    handleSearch()
  }
}, 500)

// 搜索处理
const handleSearch = async () => {
  searching.value = true
  try {
    emit('search', {
      keyword: searchKeyword.value.trim(),
      filters: { ...filters.value }
    })
  } finally {
    searching.value = false
  }
}

// 搜索清空
const handleSearchClear = () => {
  searchKeyword.value = ''
  handleFilterChange()
}

// 筛选变化
const handleFilterChange = () => {
  emit('filter-change', {
    keyword: searchKeyword.value.trim(),
    filters: { ...filters.value }
  })
}

// 重置筛选
const resetFilters = () => {
  searchKeyword.value = ''
  filters.value = {
    source: [],
    dateRange: null,
    status: '',
    sortBy: 'time_desc',
    limit: 50,
    successRateRange: [0, 100]
  }
  
  // 重置快捷筛选
  quickFilters.value.forEach(quick => {
    quick.active = false
  })
  
  emit('reset')
}

// 切换收起/展开
const toggleCollapse = () => {
  collapsed.value = !collapsed.value
}

// 快捷筛选切换
const toggleQuickFilter = (quick) => {
  quick.active = !quick.active
  
  if (quick.active) {
    // 应用快捷筛选
    const filterResult = quick.filter()
    Object.assign(filters.value, filterResult)
    
    // 如果是今日筛选，其他时间相关的快捷筛选要取消
    if (quick.key === 'today') {
      quickFilters.value.forEach(q => {
        if (q.key !== 'today' && ['week', 'month'].includes(q.key)) {
          q.active = false
        }
      })
    }
  } else {
    // 取消快捷筛选 - 根据类型重置对应字段
    if (quick.key === 'today') {
      filters.value.dateRange = null
    } else if (quick.key === 'running' || quick.key === 'error') {
      filters.value.status = ''
    } else if (quick.key === 'high_success') {
      filters.value.successRateRange = [0, 100]
    }
  }
  
  handleFilterChange()
}

// 保存当前筛选
const saveCurrentFilter = () => {
  const filterConfig = {
    keyword: searchKeyword.value.trim(),
    filters: { ...filters.value },
    timestamp: new Date().toISOString()
  }
  
  // 这里可以保存到本地存储或发送到服务器
  localStorage.setItem('saved_filter', JSON.stringify(filterConfig))
  
  ElMessage.success('筛选条件已保存')
}

// 监听器
watch(
  () => filters.value,
  () => {
    // 同步快捷筛选状态
    quickFilters.value.forEach(quick => {
      const filterResult = quick.filter()
      const isMatch = Object.keys(filterResult).every(key => {
        const filterValue = filters.value[key]
        const quickValue = filterResult[key]
        
        if (Array.isArray(quickValue)) {
          return Array.isArray(filterValue) && 
                 quickValue.length === filterValue.length &&
                 quickValue.every((v, i) => v === filterValue[i])
        }
        
        return filterValue === quickValue
      })
      
      quick.active = isMatch
    })
  },
  { deep: true }
)

// 生命周期
onMounted(() => {
  // 尝试加载保存的筛选条件
  try {
    const saved = localStorage.getItem('saved_filter')
    if (saved) {
      const savedFilter = JSON.parse(saved)
      // 可以选择是否自动应用保存的筛选
    }
  } catch (error) {
    console.warn('加载保存的筛选条件失败:', error)
  }
})

// 暴露方法
defineExpose({
  resetFilters,
  getCurrentFilters: () => ({
    keyword: searchKeyword.value.trim(),
    filters: { ...filters.value }
  })
})
</script>

<style scoped lang="scss">
.search-filter {
  margin-bottom: 16px;
  
  .filter-card {
    border-radius: 8px;
    transition: all 0.3s ease;
    
    &:hover {
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
  }
  
  .filter-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .filter-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }
    
    .filter-actions {
      display: flex;
      gap: 8px;
    }
  }
  
  .filter-content {
    .filter-row {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 16px;
      flex-wrap: wrap;
      
      &.advanced-row {
        background: var(--el-fill-color-extra-light);
        padding: 12px;
        border-radius: 6px;
        border-left: 3px solid var(--el-color-primary);
      }
      
      &.quick-filters {
        align-items: flex-start;
        
        .quick-filter-tags {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          
          .quick-tag {
            cursor: pointer;
            transition: all 0.2s ease;
            
            &:hover {
              transform: scale(1.05);
            }
          }
        }
      }
      
      &:last-child {
        margin-bottom: 0;
      }
    }
    
    .search-input {
      flex: 1;
      min-width: 300px;
    }
    
    .filter-group {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .filter-label {
        white-space: nowrap;
        font-weight: 500;
        color: var(--el-text-color-regular);
        min-width: 50px;
      }
      
      .filter-select {
        width: 200px;
      }
      
      .filter-date {
        width: 300px;
      }
      
      .filter-number {
        width: 120px;
      }
      
      .filter-slider {
        width: 200px;
        margin: 0 12px;
      }
    }
    
    .option-item {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .option-icon {
        color: var(--el-color-primary);
      }
    }
    
    .filter-result {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 0;
      border-top: 1px solid var(--el-border-color-light);
      margin-top: 16px;
      
      .result-info {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--el-text-color-regular);
        
        .active-filters {
          color: var(--el-color-primary);
          font-size: 12px;
        }
      }
      
      .result-actions {
        display: flex;
        gap: 8px;
      }
    }
  }
  
  .mr-5 {
    margin-right: 5px;
  }
  
  // 响应式设计
  @media (max-width: 768px) {
    .filter-row {
      flex-direction: column;
      align-items: stretch !important;
      
      .filter-group {
        flex-direction: column;
        align-items: stretch;
        
        .filter-label {
          margin-bottom: 4px;
        }
        
        .filter-select,
        .filter-date,
        .filter-number {
          width: 100%;
        }
      }
    }
    
    .search-input {
      min-width: auto !important;
    }
    
    .filter-result {
      flex-direction: column;
      gap: 8px;
      align-items: stretch;
    }
  }
}
</style> 