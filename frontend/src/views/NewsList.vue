<template>
  <div class="news-list">
    <!-- 搜索和筛选区域 -->
    <el-card class="search-card">
      <el-form :model="searchForm" :inline="true" class="search-form">
        <el-form-item label="关键词">
          <el-input
            v-model="searchForm.keyword"
            placeholder="请输入关键词搜索"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        
        <el-form-item label="新闻来源">
          <el-select
            v-model="searchForm.source"
            placeholder="选择新闻来源"
            clearable
            style="width: 150px"
          >
            <el-option
              v-for="source in newsSources"
              :key="source.value"
              :label="source.label"
              :value="source.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="searchForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 240px"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 新闻列表 -->
    <el-card class="news-card">
      <template #header>
        <div class="card-header">
          <span>新闻列表 (共 {{ pagination.total }} 条)</span>
          <div class="header-actions">
            <el-button type="text" @click="refreshNewsList">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <el-table 
        :data="newsList" 
        v-loading="loading"
        @row-click="handleRowClick"
        class="news-table"
      >
        <el-table-column type="index" label="#" width="60" />
        
        <el-table-column prop="title" label="标题" min-width="300">
          <template #default="{ row }">
            <div class="news-title" @click="showNewsDetail(row)">
              <el-link type="primary" :underline="false">
                {{ row.title }}
              </el-link>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="source" label="来源" width="120">
          <template #default="{ row }">
            <el-tag :type="getSourceTagType(row.source)" size="small">
              {{ getSourceName(row.source) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="category" label="分类" width="100">
          <template #default="{ row }">
            <el-tag type="info" size="small" v-if="row.category">
              {{ row.category }}
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="publish_time" label="发布时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.publish_time) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="crawl_time" label="采集时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.crawl_time) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="showNewsDetail(row)">
              查看
            </el-button>
            <el-button 
              type="text" 
              size="small" 
              @click="openOriginalLink(row.url)"
              v-if="row.url"
            >
              原文
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 新闻详情弹窗 - 使用增强的详情卡片 -->
    <NewsDetailCard
      v-model:visible="detailDialogVisible"
      :news-id="currentNewsId"
      :initial-data="currentNews"
      @close="handleDetailClose"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { newsApi } from '@/api'
import { formatTime } from '@/utils'
import NewsDetailCard from '@/components/NewsDetailCard.vue'

// 响应式数据
const loading = ref(false)
const newsList = ref([])
const newsSources = ref([
  { label: '新浪财经', value: 'sina_finance' },
  { label: '东方财富', value: 'eastmoney' },
  { label: '腾讯财经', value: 'tencent_finance' },
  { label: '网易财经', value: 'netease_money' },
  { label: '凤凰财经', value: 'ifeng_finance' }
])

// 搜索表单
const searchForm = reactive({
  keyword: '',
  source: '',
  dateRange: []
})

// 分页数据
const pagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0
})

// 新闻详情弹窗
const detailDialogVisible = ref(false)
const currentNews = ref(null)
const currentNewsId = ref(null)

// 生命周期
onMounted(() => {
  loadNewsList()
  loadNewsSources()
})

// 加载新闻列表
const loadNewsList = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      per_page: pagination.pageSize,
      keyword: searchForm.keyword || undefined,
      source: searchForm.source || undefined,
      start_date: searchForm.dateRange?.[0] || undefined,
      end_date: searchForm.dateRange?.[1] || undefined
    }
    
    const response = await newsApi.getNewsList(params)
    
    if (response && response.data) {
      newsList.value = response.data
      pagination.total = response.total || 0
    } else {
      // 使用模拟数据
      const mockData = generateMockNews()
      newsList.value = mockData.slice(
        (pagination.currentPage - 1) * pagination.pageSize,
        pagination.currentPage * pagination.pageSize
      )
      pagination.total = mockData.length
    }
  } catch (error) {
    console.error('加载新闻列表失败:', error)
    // 使用模拟数据作为后备
    const mockData = generateMockNews()
    newsList.value = mockData.slice(
      (pagination.currentPage - 1) * pagination.pageSize,
      pagination.currentPage * pagination.pageSize
    )
    pagination.total = mockData.length
  } finally {
    loading.value = false
  }
}

// 加载新闻来源
const loadNewsSources = async () => {
  try {
    const sources = await newsApi.getNewsSources()
    if (Array.isArray(sources)) {
      newsSources.value = sources.map(source => ({
        label: getSourceName(source),
        value: source
      }))
    }
  } catch (error) {
    console.error('加载新闻来源失败:', error)
  }
}

// 生成模拟新闻数据
const generateMockNews = () => {
  const sources = ['sina_finance', 'eastmoney', 'tencent_finance', 'netease_money', 'ifeng_finance']
  const categories = ['股市', '基金', '债券', '外汇', '期货', '理财', '保险']
  const mockNews = []
  
  for (let i = 1; i <= 100; i++) {
    const publishTime = new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000)
    const crawlTime = new Date(publishTime.getTime() + Math.random() * 60 * 60 * 1000)
    
    mockNews.push({
      id: i,
      title: `财经新闻标题 ${i} - ${categories[Math.floor(Math.random() * categories.length)]}市场动态分析`,
      content: `这是新闻 ${i} 的详细内容。包含了详细的市场分析和专业观点，为投资者提供有价值的参考信息。内容涵盖了市场趋势、政策解读、投资建议等多个方面。`,
      summary: `新闻 ${i} 的内容摘要，简要概括了主要观点和核心信息。`,
      source: sources[Math.floor(Math.random() * sources.length)],
      category: categories[Math.floor(Math.random() * categories.length)],
      url: `https://example.com/news/${i}`,
      publish_time: publishTime.toISOString(),
      crawl_time: crawlTime.toISOString()
    })
  }
  
  return mockNews
}

// 搜索处理
const handleSearch = () => {
  pagination.currentPage = 1
  loadNewsList()
}

// 重置搜索
const handleReset = () => {
  searchForm.keyword = ''
  searchForm.source = ''
  searchForm.dateRange = []
  pagination.currentPage = 1
  loadNewsList()
}

// 刷新列表
const refreshNewsList = () => {
  loadNewsList()
}

// 分页处理
const handleSizeChange = (size) => {
  pagination.pageSize = size
  pagination.currentPage = 1
  loadNewsList()
}

const handleCurrentChange = (page) => {
  pagination.currentPage = page
  loadNewsList()
}

// 行点击处理
const handleRowClick = (row) => {
  showNewsDetail(row)
}

// 显示新闻详情
const showNewsDetail = async (news) => {
  console.log('显示新闻详情:', news)
  
  // 设置新闻ID和初始数据
  currentNewsId.value = news.id
  currentNews.value = news
  
  // 显示详情弹窗
  detailDialogVisible.value = true
}

// 处理详情卡片关闭事件
const handleDetailClose = () => {
  detailDialogVisible.value = false
  currentNewsId.value = null
  currentNews.value = null
}

// 打开原文链接
const openOriginalLink = (url) => {
  if (url) {
    window.open(url, '_blank')
  } else {
    ElMessage.warning('原文链接不可用')
  }
}

// 工具函数
const getSourceName = (source) => {
  const sourceMap = {
    'sina_finance': '新浪财经',
    'eastmoney': '东方财富',
    'tencent_finance': '腾讯财经',
    'netease_money': '网易财经',
    'ifeng_finance': '凤凰财经'
  }
  return sourceMap[source] || source
}

const getSourceTagType = (source) => {
  const typeMap = {
    'sina_finance': 'primary',
    'eastmoney': 'success',
    'tencent_finance': 'warning',
    'netease_money': 'info',
    'ifeng_finance': 'danger'
  }
  return typeMap[source] || 'default'
}
</script>

<style lang="scss" scoped>
.news-list {
  padding: 20px;
  
  .search-card {
    margin-bottom: 20px;
    
    .search-form {
      .el-form-item {
        margin-bottom: 0;
      }
    }
  }
  
  .news-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .news-table {
      .news-title {
        cursor: pointer;
        
        .el-link {
          font-weight: 500;
          
          &:hover {
            text-decoration: underline;
          }
        }
      }
    }
    
    .pagination-wrapper {
      display: flex;
      justify-content: center;
      margin-top: 20px;
    }
  }
  
  .text-muted {
    color: var(--el-text-color-placeholder);
  }
}

.news-detail-dialog {
  .news-detail {
    .news-meta {
      margin-bottom: 20px;
    }
    
    .news-content,
    .news-summary {
      margin-top: 20px;
      
      h4 {
        margin-bottom: 10px;
        color: var(--el-text-color-primary);
        font-size: 16px;
        font-weight: 600;
      }
      
      .content-text {
        line-height: 1.6;
        color: var(--el-text-color-regular);
        
        :deep(p) {
          margin-bottom: 10px;
        }
        
        :deep(img) {
          max-width: 100%;
          height: auto;
        }
      }
      
      p {
        line-height: 1.6;
        color: var(--el-text-color-regular);
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .news-list {
    padding: 10px;
    
    .search-form {
      .el-form-item {
        display: block;
        margin-bottom: 10px;
        
        .el-input,
        .el-select,
        .el-date-picker {
          width: 100% !important;
        }
      }
    }
    
    .news-table {
      :deep(.el-table__body-wrapper) {
        overflow-x: auto;
      }
    }
  }
  
  .news-detail-dialog {
    width: 95% !important;
    margin: 0 auto;
  }
}
</style> 