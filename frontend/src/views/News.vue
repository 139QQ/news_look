<template>
  <div class="news-container">
    <div class="news-header">
      <h2>财经新闻</h2>
      <div class="news-filters">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-select v-model="selectedSource" placeholder="选择新闻源" @change="handleSourceChange" clearable>
              <el-option label="全部来源" value=""></el-option>
              <el-option 
                v-for="source in sources" 
                :key="source" 
                :label="source" 
                :value="source">
              </el-option>
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-select v-model="selectedCategory" placeholder="选择分类" @change="handleCategoryChange" clearable>
              <el-option label="全部分类" value=""></el-option>
              <el-option 
                v-for="category in categories" 
                :key="category" 
                :label="category" 
                :value="category">
              </el-option>
            </el-select>
          </el-col>
          <el-col :span="8">
            <el-input 
              v-model="searchKeyword" 
              placeholder="搜索新闻标题..." 
              @keyup.enter="handleSearch"
              clearable>
              <template #append>
                <el-button @click="handleSearch" icon="Search"></el-button>
              </template>
            </el-input>
          </el-col>
          <el-col :span="4">
            <el-button @click="refreshNews" type="primary" icon="Refresh">刷新</el-button>
          </el-col>
        </el-row>
      </div>
    </div>

    <div class="news-content">
      <el-loading v-loading="loading" element-loading-text="加载中...">
        <div v-if="newsList.length === 0 && !loading" class="empty-state">
          <el-empty description="暂无新闻数据"></el-empty>
        </div>
        
        <div v-else class="news-list">
          <el-card 
            v-for="news in newsList" 
            :key="news.id" 
            class="news-item"
            shadow="hover">
            <div class="news-item-header">
              <h3 class="news-title" @click="viewNewsDetail(news)">{{ news.title }}</h3>
              <div class="news-meta">
                <el-tag size="small" type="info">{{ news.source || '未知来源' }}</el-tag>
                <span class="news-time">{{ formatTime(news.pub_time) }}</span>
              </div>
            </div>
            
            <div class="news-content-preview">
              <p v-if="news.content">{{ getContentPreview(news.content) }}</p>
            </div>
            
            <div class="news-item-footer">
              <div class="news-keywords" v-if="news.keywords">
                <el-tag 
                  v-for="keyword in getKeywords(news.keywords)" 
                  :key="keyword" 
                  size="small" 
                  class="keyword-tag">
                  {{ keyword }}
                </el-tag>
              </div>
              <div class="news-actions">
                <el-button size="small" @click="viewNewsDetail(news)" type="primary" link>查看详情</el-button>
                <el-button size="small" @click="openOriginal(news.url)" type="info" link>原文链接</el-button>
              </div>
            </div>
          </el-card>
        </div>

        <div class="pagination-container" v-if="totalCount > 0">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="totalCount"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange">
          </el-pagination>
        </div>
      </el-loading>
    </div>

    <!-- 新闻详情对话框 -->
    <el-dialog 
      v-model="detailDialogVisible" 
      :title="selectedNews?.title" 
      width="80%" 
      top="5vh">
      <div v-if="selectedNews" class="news-detail">
        <div class="detail-meta">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="来源">{{ selectedNews.source || '未知来源' }}</el-descriptions-item>
            <el-descriptions-item label="发布时间">{{ formatTime(selectedNews.pub_time) }}</el-descriptions-item>
            <el-descriptions-item label="作者" v-if="selectedNews.author">{{ selectedNews.author }}</el-descriptions-item>
            <el-descriptions-item label="分类" v-if="selectedNews.category">{{ selectedNews.category }}</el-descriptions-item>
          </el-descriptions>
        </div>
        
        <div class="detail-content" v-if="selectedNews.content">
          <h4>新闻内容</h4>
          <div class="content-text">{{ selectedNews.content }}</div>
        </div>
        
        <div class="detail-keywords" v-if="selectedNews.keywords">
          <h4>关键词</h4>
          <el-tag 
            v-for="keyword in getKeywords(selectedNews.keywords)" 
            :key="keyword" 
            class="keyword-tag">
            {{ keyword }}
          </el-tag>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="openOriginal(selectedNews?.url)">查看原文</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
export default {
  name: 'News',
  data() {
    return {
      newsList: [],
      sources: [],
      categories: [],
      selectedSource: '',
      selectedCategory: '',
      searchKeyword: '',
      currentPage: 1,
      pageSize: 20,
      totalCount: 0,
      loading: false,
      detailDialogVisible: false,
      selectedNews: null
    }
  },
  mounted() {
    this.loadInitialData()
  },
  methods: {
    async loadInitialData() {
      await Promise.all([
        this.loadSources(),
        this.loadCategories(),
        this.loadNews()
      ])
    },
    
    async loadSources() {
      try {
        const response = await fetch('/api/sources')
        if (response.ok) {
          const data = await response.json()
          this.sources = data.sources || []
        }
      } catch (error) {
        console.error('加载新闻源失败:', error)
        this.$message.error('加载新闻源失败')
      }
    },
    
    async loadCategories() {
      try {
        const response = await fetch('/api/categories')
        if (response.ok) {
          const data = await response.json()
          this.categories = data.categories || []
        }
      } catch (error) {
        console.error('加载分类失败:', error)
        this.$message.error('加载分类失败')
      }
    },
    
    async loadNews() {
      this.loading = true
      try {
        const params = new URLSearchParams({
          page: this.currentPage,
          per_page: this.pageSize
        })
        
        if (this.selectedSource) params.append('source', this.selectedSource)
        if (this.selectedCategory) params.append('category', this.selectedCategory)
        if (this.searchKeyword) params.append('keyword', this.searchKeyword)
        
        const response = await fetch(`/api/news?${params}`)
        if (response.ok) {
          const data = await response.json()
          this.newsList = data.news || []
          this.totalCount = data.total || 0
        } else {
          throw new Error('请求失败')
        }
      } catch (error) {
        console.error('加载新闻失败:', error)
        this.$message.error('加载新闻失败')
        this.newsList = []
        this.totalCount = 0
      } finally {
        this.loading = false
      }
    },
    
    handleSourceChange() {
      this.currentPage = 1
      this.loadNews()
    },
    
    handleCategoryChange() {
      this.currentPage = 1
      this.loadNews()
    },
    
    handleSearch() {
      this.currentPage = 1
      this.loadNews()
    },
    
    refreshNews() {
      this.loadNews()
    },
    
    handleSizeChange(newSize) {
      this.pageSize = newSize
      this.currentPage = 1
      this.loadNews()
    },
    
    handleCurrentChange(newPage) {
      this.currentPage = newPage
      this.loadNews()
    },
    
    viewNewsDetail(news) {
      this.selectedNews = news
      this.detailDialogVisible = true
    },
    
    openOriginal(url) {
      if (url) {
        window.open(url, '_blank')
      } else {
        this.$message.warning('原文链接不可用')
      }
    },
    
    formatTime(timeStr) {
      if (!timeStr) return '未知时间'
      try {
        const date = new Date(timeStr)
        return date.toLocaleString('zh-CN')
      } catch {
        return timeStr
      }
    },
    
    getContentPreview(content) {
      if (!content) return ''
      return content.length > 200 ? content.substring(0, 200) + '...' : content
    },
    
    getKeywords(keywords) {
      if (!keywords) return []
      if (typeof keywords === 'string') {
        return keywords.split(',').map(k => k.trim()).filter(k => k)
      }
      return Array.isArray(keywords) ? keywords : []
    }
  }
}
</script>

<style scoped>
.news-container {
  padding: 20px;
}

.news-header {
  margin-bottom: 20px;
}

.news-header h2 {
  margin-bottom: 15px;
  color: #303133;
}

.news-filters {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 6px;
}

.news-content {
  min-height: 400px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.news-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.news-item {
  transition: all 0.3s ease;
}

.news-item:hover {
  transform: translateY(-2px);
}

.news-item-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.news-title {
  flex: 1;
  margin: 0;
  margin-right: 15px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  cursor: pointer;
  line-height: 1.4;
}

.news-title:hover {
  color: #409EFF;
}

.news-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 5px;
  white-space: nowrap;
}

.news-time {
  font-size: 12px;
  color: #909399;
}

.news-content-preview {
  margin: 10px 0;
}

.news-content-preview p {
  margin: 0;
  color: #606266;
  line-height: 1.5;
}

.news-item-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 15px;
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}

.news-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  flex: 1;
}

.keyword-tag {
  margin: 0;
}

.news-actions {
  display: flex;
  gap: 10px;
}

.pagination-container {
  margin-top: 30px;
  text-align: center;
}

.news-detail .detail-meta {
  margin-bottom: 20px;
}

.news-detail .detail-content {
  margin-bottom: 20px;
}

.news-detail .detail-content h4 {
  margin-bottom: 10px;
  color: #303133;
}

.news-detail .content-text {
  line-height: 1.6;
  color: #606266;
  background: #f5f7fa;
  padding: 15px;
  border-radius: 6px;
  max-height: 400px;
  overflow-y: auto;
}

.news-detail .detail-keywords h4 {
  margin-bottom: 10px;
  color: #303133;
}

.news-detail .detail-keywords .keyword-tag {
  margin-right: 8px;
  margin-bottom: 5px;
}
</style> 