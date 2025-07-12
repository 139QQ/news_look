<template>
  <div class="virtual-scroll-table" ref="tableContainer">
    <!-- 表头 -->
    <div class="table-header" :style="{ width: totalWidth + 'px' }">
      <div 
        v-for="column in columns" 
        :key="column.key"
        class="header-cell"
        :style="{ width: column.width + 'px', minWidth: column.minWidth + 'px' }"
        @click="handleSort(column)"
      >
        <span class="header-text">{{ column.title }}</span>
        <el-icon v-if="column.sortable" class="sort-icon" :class="getSortClass(column.key)">
          <Sort />
        </el-icon>
        
        <!-- 字段筛选器 -->
        <el-popover 
          v-if="column.filterable"
          :width="200"
          trigger="click"
          placement="bottom"
        >
          <template #reference>
            <el-icon class="filter-icon" :class="{ active: filters[column.key] }">
              <Filter />
            </el-icon>
          </template>
          <div class="filter-content">
            <el-input
              v-model="filterValues[column.key]"
              :placeholder="`筛选${column.title}`"
              size="small"
              @input="handleFilter(column.key)"
              clearable
            />
            <div class="filter-actions">
              <el-button size="small" @click="clearFilter(column.key)">清除</el-button>
              <el-button size="small" type="primary" @click="applyFilter(column.key)">确定</el-button>
            </div>
          </div>
        </el-popover>
      </div>
    </div>

    <!-- 虚拟滚动容器 -->
    <div 
      class="table-body" 
      ref="scrollContainer"
      :style="{ height: height + 'px' }"
      @scroll="handleScroll"
    >
      <!-- 占位div，用于撑开滚动条 -->
      <div :style="{ height: totalHeight + 'px', position: 'relative' }">
        <!-- 可见行区域 -->
        <div 
          class="visible-rows"
          :style="{ 
            transform: `translateY(${offsetY}px)`,
            width: totalWidth + 'px'
          }"
        >
          <div 
            v-for="(row, index) in visibleData" 
            :key="getRowKey(row, startIndex + index)"
            class="table-row"
            :class="{ 
              'row-selected': selectedRows.includes(getRowKey(row, startIndex + index)),
              'row-hover': hoverIndex === startIndex + index 
            }"
            @click="handleRowClick(row, startIndex + index)"
            @mouseenter="hoverIndex = startIndex + index"
            @mouseleave="hoverIndex = -1"
          >
            <!-- 选择框 -->
            <div 
              v-if="selectable" 
              class="selection-cell"
              :style="{ width: selectionWidth + 'px' }"
            >
              <el-checkbox 
                :model-value="selectedRows.includes(getRowKey(row, startIndex + index))"
                @change="handleRowSelect(row, startIndex + index)"
              />
            </div>

            <!-- 数据单元格 -->
            <div 
              v-for="column in columns" 
              :key="column.key"
              class="table-cell"
              :style="{ width: column.width + 'px', minWidth: column.minWidth + 'px' }"
            >
              <!-- 自定义渲染 -->
              <template v-if="column.render">
                <component 
                  :is="column.render" 
                  :row="row" 
                  :column="column" 
                  :index="startIndex + index"
                />
              </template>
              
              <!-- 默认渲染 -->
              <template v-else>
                <span 
                  class="cell-content"
                  :class="{ 'cell-ellipsis': column.ellipsis }"
                  :title="column.ellipsis ? getCellValue(row, column.key) : ''"
                >
                  {{ formatCellValue(getCellValue(row, column.key), column) }}
                </span>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 表格底部信息 -->
    <div class="table-footer">
      <div class="footer-info">
        <span>共 {{ filteredDataCount }} 条记录</span>
        <span v-if="selectedRows.length > 0">，已选择 {{ selectedRows.length }} 条</span>
      </div>
      
      <!-- 批量操作 -->
      <div v-if="selectedRows.length > 0" class="batch-actions">
        <el-button-group size="small">
          <el-button @click="clearSelection">清除选择</el-button>
          <el-button @click="selectAll">全选</el-button>
          <el-button @click="invertSelection">反选</el-button>
        </el-button-group>
        <slot name="batch-actions" :selected-rows="selectedRows" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Sort, Filter } from '@element-plus/icons-vue'

// Props定义
const props = defineProps({
  // 数据源
  data: {
    type: Array,
    default: () => []
  },
  
  // 列配置
  columns: {
    type: Array,
    required: true
  },
  
  // 表格高度
  height: {
    type: Number,
    default: 400
  },
  
  // 行高
  rowHeight: {
    type: Number,
    default: 48
  },
  
  // 缓冲区行数
  bufferSize: {
    type: Number,
    default: 10
  },
  
  // 是否可选择
  selectable: {
    type: Boolean,
    default: false
  },
  
  // 选择列宽度
  selectionWidth: {
    type: Number,
    default: 50
  },
  
  // 行键值字段
  rowKey: {
    type: String,
    default: 'id'
  },
  
  // 是否显示加载状态
  loading: {
    type: Boolean,
    default: false
  }
})

// Emits定义
const emit = defineEmits([
  'row-click',
  'selection-change',
  'sort-change',
  'filter-change'
])

// 响应式数据
const tableContainer = ref(null)
const scrollContainer = ref(null)
const scrollTop = ref(0)
const hoverIndex = ref(-1)

// 排序状态
const sortState = reactive({
  key: '',
  order: '' // 'asc' | 'desc' | ''
})

// 筛选状态
const filters = reactive({})
const filterValues = reactive({})

// 选择状态
const selectedRows = ref([])

// 计算属性
const totalWidth = computed(() => {
  let width = props.selectable ? props.selectionWidth : 0
  return width + props.columns.reduce((sum, col) => sum + (col.width || 120), 0)
})

const filteredData = computed(() => {
  let result = [...props.data]
  
  // 应用筛选
  Object.keys(filters).forEach(key => {
    if (filters[key]) {
      const filterValue = filters[key].toLowerCase()
      result = result.filter(row => {
        const cellValue = getCellValue(row, key)
        return String(cellValue).toLowerCase().includes(filterValue)
      })
    }
  })
  
  // 应用排序
  if (sortState.key && sortState.order) {
    result.sort((a, b) => {
      const aVal = getCellValue(a, sortState.key)
      const bVal = getCellValue(b, sortState.key)
      
      let comparison = 0
      if (aVal < bVal) comparison = -1
      if (aVal > bVal) comparison = 1
      
      return sortState.order === 'desc' ? -comparison : comparison
    })
  }
  
  return result
})

const filteredDataCount = computed(() => filteredData.value.length)

const totalHeight = computed(() => filteredData.value.length * props.rowHeight)

const visibleCount = computed(() => Math.ceil(props.height / props.rowHeight) + props.bufferSize * 2)

const startIndex = computed(() => {
  const index = Math.floor(scrollTop.value / props.rowHeight) - props.bufferSize
  return Math.max(0, index)
})

const endIndex = computed(() => {
  const index = startIndex.value + visibleCount.value
  return Math.min(filteredData.value.length, index)
})

const visibleData = computed(() => {
  return filteredData.value.slice(startIndex.value, endIndex.value)
})

const offsetY = computed(() => startIndex.value * props.rowHeight)

// 方法
const handleScroll = (event) => {
  scrollTop.value = event.target.scrollTop
}

const handleSort = (column) => {
  if (!column.sortable) return
  
  if (sortState.key === column.key) {
    // 切换排序顺序: asc -> desc -> ''
    if (sortState.order === 'asc') {
      sortState.order = 'desc'
    } else if (sortState.order === 'desc') {
      sortState.key = ''
      sortState.order = ''
    } else {
      sortState.order = 'asc'
    }
  } else {
    sortState.key = column.key
    sortState.order = 'asc'
  }
  
  emit('sort-change', { key: sortState.key, order: sortState.order })
}

const getSortClass = (key) => {
  if (sortState.key !== key) return ''
  return `sort-${sortState.order}`
}

const handleFilter = (key) => {
  // 实时筛选（防抖处理在父组件中实现）
  filters[key] = filterValues[key]
  emit('filter-change', { key, value: filters[key] })
}

const applyFilter = (key) => {
  filters[key] = filterValues[key]
  emit('filter-change', { key, value: filters[key] })
}

const clearFilter = (key) => {
  filterValues[key] = ''
  filters[key] = ''
  emit('filter-change', { key, value: '' })
}

const handleRowClick = (row, index) => {
  emit('row-click', { row, index })
}

const handleRowSelect = (row, index) => {
  const key = getRowKey(row, index)
  const selectedIndex = selectedRows.value.indexOf(key)
  
  if (selectedIndex > -1) {
    selectedRows.value.splice(selectedIndex, 1)
  } else {
    selectedRows.value.push(key)
  }
  
  emit('selection-change', selectedRows.value)
}

const clearSelection = () => {
  selectedRows.value = []
  emit('selection-change', [])
}

const selectAll = () => {
  selectedRows.value = filteredData.value.map((row, index) => getRowKey(row, index))
  emit('selection-change', selectedRows.value)
}

const invertSelection = () => {
  const allKeys = filteredData.value.map((row, index) => getRowKey(row, index))
  selectedRows.value = allKeys.filter(key => !selectedRows.value.includes(key))
  emit('selection-change', selectedRows.value)
}

const getRowKey = (row, index) => {
  return row[props.rowKey] || index
}

const getCellValue = (row, key) => {
  return key.split('.').reduce((obj, k) => obj?.[k], row) || ''
}

const formatCellValue = (value, column) => {
  if (column.formatter && typeof column.formatter === 'function') {
    return column.formatter(value)
  }
  return value
}

// 生命周期
onMounted(() => {
  // 初始化时滚动到顶部
  nextTick(() => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = 0
    }
  })
})

// 监听数据变化，重置滚动位置
watch(() => props.data, () => {
  scrollTop.value = 0
  if (scrollContainer.value) {
    scrollContainer.value.scrollTop = 0
  }
})
</script>

<style scoped>
.virtual-scroll-table {
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  overflow: hidden;
  background: var(--el-bg-color);
}

.table-header {
  display: flex;
  background: var(--el-bg-color-page);
  border-bottom: 1px solid var(--el-border-color);
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-cell {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-right: 1px solid var(--el-border-color);
  cursor: pointer;
  user-select: none;
  position: relative;
}

.header-cell:last-child {
  border-right: none;
}

.header-cell:hover {
  background: var(--el-fill-color-light);
}

.header-text {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sort-icon {
  margin-left: 8px;
  opacity: 0.6;
  transition: all 0.3s;
}

.sort-icon.sort-asc {
  opacity: 1;
  color: var(--el-color-primary);
  transform: rotate(0deg);
}

.sort-icon.sort-desc {
  opacity: 1;
  color: var(--el-color-primary);
  transform: rotate(180deg);
}

.filter-icon {
  margin-left: 8px;
  opacity: 0.6;
  cursor: pointer;
  transition: all 0.3s;
}

.filter-icon:hover,
.filter-icon.active {
  opacity: 1;
  color: var(--el-color-primary);
}

.filter-content {
  padding: 8px 0;
}

.filter-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.table-body {
  overflow: auto;
  position: relative;
}

.visible-rows {
  position: absolute;
  top: 0;
  left: 0;
}

.table-row {
  display: flex;
  border-bottom: 1px solid var(--el-border-color-lighter);
  transition: background-color 0.2s;
  min-height: 48px;
}

.table-row:hover,
.table-row.row-hover {
  background: var(--el-fill-color-light);
}

.table-row.row-selected {
  background: var(--el-color-primary-light-9);
}

.selection-cell,
.table-cell {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  border-right: 1px solid var(--el-border-color-lighter);
  min-height: 48px;
}

.table-cell:last-child {
  border-right: none;
}

.cell-content {
  width: 100%;
}

.cell-ellipsis {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--el-bg-color-page);
  border-top: 1px solid var(--el-border-color);
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.footer-info {
  display: flex;
  gap: 8px;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-cell,
  .selection-cell,
  .table-cell {
    padding: 8px 12px;
  }
  
  .table-footer {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }
  
  .batch-actions {
    justify-content: space-between;
  }
}

/* 滚动条样式 */
.table-body::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.table-body::-webkit-scrollbar-track {
  background: var(--el-fill-color-lighter);
  border-radius: 4px;
}

.table-body::-webkit-scrollbar-thumb {
  background: var(--el-fill-color-dark);
  border-radius: 4px;
}

.table-body::-webkit-scrollbar-thumb:hover {
  background: var(--el-fill-color-darker);
}
</style> 