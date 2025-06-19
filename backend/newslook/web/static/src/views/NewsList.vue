<template>
  <div class="news-list-container">
    <!-- 页面标题和搜索 -->
    <div class="page-header">
      <div class="title-section">
        <n-h1>新闻列表</n-h1>
        <n-text depth="3">浏览和管理财经新闻数据</n-text>
      </div>
      
      <div class="search-section">
        <n-input-group>
          <n-input
            v-model:value="searchQuery"
            placeholder="搜索新闻标题、内容或关键词..."
            clearable
            @keyup.enter="handleSearch"
            style="width: 300px"
          >
            <template #prefix>
              <n-icon><SearchOutline /></n-icon>
            </template>
          </n-input>
          <n-button type="primary" @click="handleSearch" :loading="loading">
            搜索
          </n-button>
        </n-input-group>
      </div>
    </div>
    
    <!-- 筛选器 -->
    <n-card style="margin-bottom: 16px">
      <n-space align="center">
        <!-- 来源筛选 -->
        <div>
          <n-text>来源：</n-text>
          <n-select
            v-model:value="filters.source"
            placeholder="选择新闻来源"
            clearable
            style="width: 150px; margin-left: 8px"
            :options="sourceOptions"
          />
        </div>
        
        <!-- 日期筛选 -->
        <div>
          <n-text>时间：</n-text>
          <n-date-picker
            v-model:value="filters.dateRange"
            type="daterange"
            clearable
            style="margin-left: 8px"
            @update:value="handleDateChange"
          />
        </div>
        
        <!-- 情感筛选 -->
        <div>
          <n-text>情感：</n-text>
          <n-select
            v-model:value="filters.sentiment"
            placeholder="选择情感倾向"
            clearable
            style="width: 120px; margin-left: 8px"
            :options="sentimentOptions"
          />
        </div>
        
        <!-- 排序 -->
        <div>
          <n-text>排序：</n-text>
          <n-select
            v-model:value="sortBy"
            style="width: 150px; margin-left: 8px"
            :options="sortOptions"
            @update:value="handleSortChange"
          />
        </div>
        
        <!-- 操作按钮 -->
        <n-space>
          <n-button @click="resetFilters" secondary>
            重置
          </n-button>
          <n-button @click="refreshNews" :loading="loading">
            <template #icon>
              <n-icon><RefreshOutline /></n-icon>
            </template>
            刷新
          </n-button>
        </n-space>
      </n-space>
    </n-card>
    
    <!-- 新闻列表 -->
    <n-card>
      <template #header>
        <n-space justify="space-between">
          <span>共找到 {{ totalCount }} 条新闻</span>
          <n-space>
            <!-- 视图切换 -->
            <n-button-group>
              <n-button
                :type="viewMode === 'list' ? 'primary' : 'default'"
                @click="viewMode = 'list'"
              >
                <template #icon>
                  <n-icon><ListOutline /></n-icon>
                </template>
              </n-button>
              <n-button
                :type="viewMode === 'card' ? 'primary' : 'default'"
                @click="viewMode = 'card'"
              >
                <template #icon>
                  <n-icon><GridOutline /></n-icon>
                </template>
              </n-button>
            </n-button-group>
            
            <!-- 批量操作 -->
            <n-dropdown :options="batchOptions" @select="handleBatchAction">
              <n-button secondary :disabled="selectedRows.length === 0">
                批量操作 ({{ selectedRows.length }})
                <template #icon>
                  <n-icon><ChevronDownOutline /></n-icon>
                </template>
              </n-button>
            </n-dropdown>
          </n-space>
        </n-space>
      </template>
      
      <!-- 列表视图 -->
      <div v-if="viewMode === 'list'">
        <n-data-table
          v-model:checked-row-keys="selectedRows"
          :columns="columns"
          :data="newsList"
          :loading="loading"
          :pagination="paginationProps"
          :row-key="row => row.id"
          size="medium"
          striped
          @update:page="handlePageChange"
          @update:page-size="handlePageSizeChange"
        />
      </div>
      
      <!-- 卡片视图 -->
      <div v-else>
        <n-grid :cols="3" :x-gap="16" :y-gap="16" v-if="newsList.length > 0">
          <n-grid-item v-for="news in newsList" :key="news.id">
            <NewsCard
              :news="news"
              :selected="selectedRows.includes(news.id)"
              @select="toggleSelection"
              @view="viewNewsDetail"
            />
          </n-grid-item>
        </n-grid>
        
        <n-empty v-else description="暂无新闻数据" />
        
        <!-- 卡片视图分页 -->
        <n-pagination
          v-if="newsList.length > 0"
          v-model:page="currentPage"
          v-model:page-size="pageSize"
          :item-count="totalCount"
          :page-sizes="pageSizes"
          show-size-picker
          show-quick-jumper
          style="margin-top: 24px; justify-content: center"
          @update:page="handlePageChange"
          @update:page-size="handlePageSizeChange"
        />
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, h } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  SearchOutline,
  RefreshOutline,
  ListOutline,
  GridOutline,
  ChevronDownOutline,
  EyeOutline,
  DownloadOutline,
  TrashOutline
} from '@vicons/ionicons5'
import { newsApi } from '../api'
import NewsCard from '../components/NewsCard.vue'

const router = useRouter()
const message = useMessage()

// 响应式数据
const searchQuery = ref('')
const loading = ref(false)
const viewMode = ref('list')
const selectedRows = ref([])
const newsList = ref([])
const totalCount = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const filters = ref({
  source: null,
  dateRange: null,
  sentiment: null
})

const sortBy = ref('pub_time_desc')

// 配置选项
const sourceOptions = [
  { label: '新浪财经', value: 'sina' },
  { label: '东方财富', value: 'eastmoney' },
  { label: '腾讯财经', value: 'tencent' },
  { label: '网易财经', value: 'netease' },
  { label: '凤凰财经', value: 'ifeng' }
]

const sentimentOptions = [
  { label: '积极', value: 'positive' },
  { label: '中性', value: 'neutral' },
  { label: '消极', value: 'negative' }
]

const sortOptions = [
  { label: '发布时间（最新）', value: 'pub_time_desc' },
  { label: '发布时间（最早）', value: 'pub_time_asc' },
  { label: '相关度', value: 'relevance' },
  { label: '情感值（高到低）', value: 'sentiment_desc' },
  { label: '情感值（低到高）', value: 'sentiment_asc' }
]

const pageSizes = [10, 20, 50, 100]

// 批量操作选项
const batchOptions = [
  {
    label: '导出选中',
    key: 'export',
    icon: () => h(DownloadOutline)
  },
  {
    label: '删除选中',
    key: 'delete',
    icon: () => h(TrashOutline)
  }
]

// 表格列定义
const columns = [
  {
    type: 'selection'
  },
  {
    title: '标题',
    key: 'title',
    width: 300,
    ellipsis: {
      tooltip: true
    },
    render: (row) => h(
      'a',
      {
        style: 'color: #18a058; cursor: pointer; text-decoration: none',
        onClick: () => viewNewsDetail(row.id)
      },
      row.title
    )
  },
  {
    title: '来源',
    key: 'source',
    width: 100,
    render: (row) => h(
      'n-tag',
      { size: 'small', type: getSourceType(row.source) },
      row.source
    )
  },
  {
    title: '发布时间',
    key: 'pub_time',
    width: 180,
    render: (row) => formatDateTime(row.pub_time)
  },
  {
    title: '情感值',
    key: 'sentiment',
    width: 100,
    render: (row) => h(
      'n-tag',
      { 
        size: 'small', 
        type: getSentimentType(row.sentiment) 
      },
      row.sentiment?.toFixed(2) || '0.00'
    )
  },
  {
    title: '关键词',
    key: 'keywords',
    width: 200,
    ellipsis: {
      tooltip: true
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render: (row) => h(
      'n-space',
      { size: 'small' },
      [
        h(
          'n-button',
          {
            size: 'small',
            onClick: () => viewNewsDetail(row.id)
          },
          { icon: () => h(EyeOutline), default: () => '查看' }
        )
      ]
    )
  }
]

// 计算属性
const paginationProps = computed(() => ({
  page: currentPage.value,
  pageSize: pageSize.value,
  itemCount: totalCount.value,
  pageSizes: pageSizes,
  showSizePicker: true,
  showQuickJumper: true
}))

// 方法
const formatDateTime = (dateStr) => {
  try {
    return new Date(dateStr).toLocaleString('zh-CN')
  } catch {
    return dateStr
  }
}

const getSourceType = (source) => {
  const sourceTypes = {
    'sina': 'info',
    'eastmoney': 'success',
    'tencent': 'warning',
    'netease': 'error',
    'ifeng': 'default'
  }
  return sourceTypes[source] || 'default'
}

const getSentimentType = (sentiment) => {
  if (sentiment > 0.2) return 'success'
  if (sentiment < -0.2) return 'error'
  return 'default'
}

const viewNewsDetail = (id) => {
  router.push(`/news/${id}`)
}

const toggleSelection = (id) => {
  const index = selectedRows.value.indexOf(id)
  if (index > -1) {
    selectedRows.value.splice(index, 1)
  } else {
    selectedRows.value.push(id)
  }
}

const loadNews = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      limit: pageSize.value,
      q: searchQuery.value
    }
    
    // 添加筛选条件
    if (filters.value.source) {
      params.source = filters.value.source
    }
    
    if (filters.value.dateRange) {
      params.start_date = new Date(filters.value.dateRange[0]).toISOString().split('T')[0]
      params.end_date = new Date(filters.value.dateRange[1]).toISOString().split('T')[0]
    }
    
    if (filters.value.sentiment) {
      params.sentiment = filters.value.sentiment
    }
    
    // 添加排序
    const [sortField, sortOrder] = sortBy.value.split('_')
    params.sort = sortField
    params.order = sortOrder
    
    const response = await newsApi.getNewsList(params)
    newsList.value = response.news || []
    totalCount.value = response.total || 0
    
  } catch (error) {
    message.error('加载新闻列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadNews()
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadNews()
}

const handlePageSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  loadNews()
}

const handleDateChange = () => {
  currentPage.value = 1
  loadNews()
}

const handleSortChange = () => {
  currentPage.value = 1
  loadNews()
}

const resetFilters = () => {
  searchQuery.value = ''
  filters.value = {
    source: null,
    dateRange: null,
    sentiment: null
  }
  sortBy.value = 'pub_time_desc'
  currentPage.value = 1
  loadNews()
}

const refreshNews = () => {
  loadNews()
}

const handleBatchAction = (key) => {
  switch (key) {
    case 'export':
      exportSelected()
      break
    case 'delete':
      deleteSelected()
      break
  }
}

const exportSelected = async () => {
  try {
    // 这里实现导出逻辑
    message.success(`正在导出 ${selectedRows.value.length} 条新闻`)
  } catch (error) {
    message.error('导出失败')
  }
}

const deleteSelected = async () => {
  try {
    // 这里实现删除逻辑
    message.success(`已删除 ${selectedRows.value.length} 条新闻`)
    selectedRows.value = []
    loadNews()
  } catch (error) {
    message.error('删除失败')
  }
}

// 生命周期
onMounted(() => {
  loadNews()
})
</script>

<style scoped>
.news-list-container {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 24px;
}

.title-section {
  flex: 1;
}

.search-section {
  flex-shrink: 0;
}

.n-data-table :deep(.n-data-table-th) {
  background-color: #fafafa;
}

.n-data-table :deep(.n-data-table-tr:hover) {
  background-color: rgba(24, 160, 88, 0.05);
}
</style> 