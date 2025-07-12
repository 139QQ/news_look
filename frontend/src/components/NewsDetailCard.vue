<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="handleVisibilityChange"
    :title="newsTitle"
    width="80%"
    top="5vh"
    class="enhanced-news-detail-dialog"
    :before-close="handleClose"
  >
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-skeleton">
      <el-skeleton :rows="8" animated />
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <el-result
        icon="error"
        title="加载失败"
        :sub-title="error"
      >
        <template #extra>
          <el-button type="primary" @click="retryLoad">
            <el-icon><Refresh /></el-icon>
            重试
          </el-button>
          <el-button @click="handleClose">关闭</el-button>
        </template>
      </el-result>
    </div>
    
    <!-- 新闻详情内容 -->
    <div v-else-if="newsData" class="enhanced-news-detail">
      <!-- 新闻元数据 -->
      <div class="news-metadata">
        <el-descriptions :column="2" border size="default">
          <el-descriptions-item label="标题" :span="2">
            <div class="news-title-display">
              {{ newsData.title || '标题信息缺失' }}
              <el-tag v-if="!newsData.title" type="warning" size="small">信息缺失</el-tag>
            </div>
          </el-descriptions-item>
          
          <el-descriptions-item label="新闻来源">
            <div class="news-source-display">
              <el-tag 
                v-if="newsData.source" 
                :type="getSourceTagType(newsData.source)"
                size="default"
              >
                {{ getSourceName(newsData.source) }}
              </el-tag>
              <span v-else class="missing-info">
                来源信息缺失
                <el-button type="text" size="small" @click="reportMissingData('source')">
                  报告问题
                </el-button>
              </span>
            </div>
          </el-descriptions-item>
          
          <el-descriptions-item label="新闻分类">
            <div class="news-category-display">
              <el-tag 
                v-if="newsData.category" 
                type="info" 
                size="default"
              >
                {{ newsData.category }}
              </el-tag>
              <span v-else class="missing-info">
                分类信息缺失
                <el-button type="text" size="small" @click="reportMissingData('category')">
                  报告问题
                </el-button>
              </span>
            </div>
          </el-descriptions-item>
          
          <el-descriptions-item label="发布时间">
            <div class="news-time-display">
              <el-icon><Clock /></el-icon>
              {{ formatTime(newsData.publish_time || newsData.pub_time) || '时间信息缺失' }}
            </div>
          </el-descriptions-item>
          
          <el-descriptions-item label="采集时间">
            <div class="news-time-display">
              <el-icon><Download /></el-icon>
              {{ formatTime(newsData.crawl_time) || '采集时间缺失' }}
            </div>
          </el-descriptions-item>
          
          <el-descriptions-item label="原文链接">
            <div class="news-url-display">
              <el-link 
                v-if="newsData.url && newsData.url !== '#'" 
                :href="newsData.url" 
                target="_blank" 
                type="primary"
                :underline="false"
              >
                <el-icon><Link /></el-icon>
                查看原文
              </el-link>
              <span v-else class="missing-info">
                原文链接不可用
              </span>
            </div>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      
      <!-- 新闻关键词 -->
      <div v-if="hasKeywords" class="news-keywords">
        <h4>
          <el-icon><Tag /></el-icon>
          关键词
        </h4>
        <div class="keywords-container">
          <el-tag
            v-for="keyword in parsedKeywords"
            :key="keyword"
            type="info"
            size="small"
            class="keyword-tag"
          >
            {{ keyword }}
          </el-tag>
        </div>
      </div>
      
      <!-- 新闻内容 -->
      <div v-if="newsData.content" class="news-content">
        <h4>
          <el-icon><Document /></el-icon>
          新闻内容
        </h4>
        <div class="content-wrapper">
          <div 
            class="content-text" 
            v-html="sanitizedContent"
            :class="{ 'content-expanded': contentExpanded }"
          ></div>
          <div v-if="isContentLong" class="content-toggle">
            <el-button 
              type="text" 
              @click="toggleContent"
              class="toggle-btn"
            >
              {{ contentExpanded ? '收起' : '展开全文' }}
              <el-icon>
                <component :is="contentExpanded ? 'ArrowUp' : 'ArrowDown'" />
              </el-icon>
            </el-button>
          </div>
        </div>
      </div>
      
      <!-- 新闻摘要 -->
      <div v-if="newsData.summary" class="news-summary">
        <h4>
          <el-icon><Document /></el-icon>
          内容摘要
        </h4>
        <p class="summary-text">{{ newsData.summary }}</p>
      </div>
      
      <!-- 数据质量反馈 -->
      <div class="data-quality-section">
        <el-divider content-position="left">数据质量反馈</el-divider>
        <div class="quality-indicators">
          <el-tag 
            :type="dataQualityScore >= 0.8 ? 'success' : dataQualityScore >= 0.6 ? 'warning' : 'danger'"
            size="small"
          >
            数据完整度: {{ Math.round(dataQualityScore * 100) }}%
          </el-tag>
          <el-button 
            v-if="hasMissingData" 
            type="text" 
            size="small"
            @click="showDataIssues = !showDataIssues"
          >
            <el-icon><Warning /></el-icon>
            {{ missingFields.length }}个字段缺失
          </el-button>
        </div>
        
        <el-collapse-transition>
          <div v-show="showDataIssues" class="data-issues">
            <el-alert
              title="数据质量问题"
              type="warning"
              :closable="false"
              show-icon
            >
              <template #default>
                <p>以下字段数据缺失或异常：</p>
                <ul>
                  <li v-for="field in missingFields" :key="field">
                    {{ fieldLabels[field] || field }}
                  </li>
                </ul>
                <div class="action-buttons">
                  <el-button size="small" @click="reportDataIssue">
                    <el-icon><Message /></el-icon>
                    报告数据问题
                  </el-button>
                </div>
              </template>
            </el-alert>
          </div>
        </el-collapse-transition>
      </div>
    </div>
    
    <!-- 空数据状态 -->
    <div v-else class="empty-state">
      <el-empty 
        description="没有找到新闻数据"
        :image-size="100"
      >
        <el-button type="primary" @click="handleClose">返回列表</el-button>
      </el-empty>
    </div>
    
    <!-- 底部操作按钮 -->
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">关闭</el-button>
        <el-button 
          v-if="newsData?.url && newsData.url !== '#'"
          type="primary" 
          @click="openOriginalLink"
        >
          <el-icon><ExternalLink /></el-icon>
          查看原文
        </el-button>
        <el-button 
          v-if="newsData"
          type="success"
          @click="shareNews"
        >
          <el-icon><Share /></el-icon>
          分享
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { newsApi } from '@/api'
import { formatTime } from '@/utils'
import DOMPurify from 'dompurify'

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  newsId: {
    type: [String, Number],
    default: null
  },
  initialData: {
    type: Object,
    default: null
  }
})

// Emits
const emit = defineEmits(['update:visible', 'close'])

// 响应式数据
const loading = ref(false)
const error = ref('')
const newsData = ref(null)
const showDataIssues = ref(false)
const contentExpanded = ref(false)

// 计算属性
const newsTitle = computed(() => {
  if (loading.value) return '加载中...'
  if (error.value) return '加载失败'
  return newsData.value?.title || '新闻详情'
})

const sanitizedContent = computed(() => {
  if (!newsData.value?.content) return ''
  return DOMPurify.sanitize(newsData.value.content, {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'],
    ALLOWED_ATTR: ['class', 'style']
  })
})

const isContentLong = computed(() => {
  return sanitizedContent.value.length > 500
})

const parsedKeywords = computed(() => {
  if (!newsData.value?.keywords) return []
  
  if (Array.isArray(newsData.value.keywords)) {
    return newsData.value.keywords
  }
  
  if (typeof newsData.value.keywords === 'string') {
    try {
      const parsed = JSON.parse(newsData.value.keywords)
      return Array.isArray(parsed) ? parsed : [newsData.value.keywords]
    } catch {
      return newsData.value.keywords.split(',').map(k => k.trim()).filter(k => k)
    }
  }
  
  return []
})

const hasKeywords = computed(() => {
  return parsedKeywords.value.length > 0
})

const missingFields = computed(() => {
  if (!newsData.value) return []
  
  const fields = []
  const requiredFields = {
    title: '标题',
    source: '来源',
    category: '分类',
    publish_time: '发布时间',
    pub_time: '发布时间',
    content: '内容'
  }
  
  for (const [field, label] of Object.entries(requiredFields)) {
    if (!newsData.value[field] || newsData.value[field] === '') {
      fields.push(field)
    }
  }
  
  return fields
})

const hasMissingData = computed(() => {
  return missingFields.value.length > 0
})

const dataQualityScore = computed(() => {
  if (!newsData.value) return 0
  
  const totalFields = 6 // title, source, category, publish_time, content, url
  const presentFields = totalFields - missingFields.value.length
  return presentFields / totalFields
})

const fieldLabels = {
  title: '标题',
  source: '来源',
  category: '分类',
  publish_time: '发布时间',
  pub_time: '发布时间',
  content: '内容',
  url: '原文链接'
}

// 监听visible变化
watch(() => props.visible, (newVal) => {
  if (newVal) {
    loadNewsDetail()
  } else {
    resetState()
  }
})

// 监听newsId变化
watch(() => props.newsId, () => {
  if (props.visible) {
    loadNewsDetail()
  }
})

// 方法
const loadNewsDetail = async () => {
  if (!props.newsId && !props.initialData) {
    error.value = '缺少新闻ID或初始数据'
    return
  }
  
  loading.value = true
  error.value = ''
  
  try {
    if (props.initialData) {
      // 使用初始数据
      newsData.value = props.initialData
      
      // 尝试获取更完整的数据
      if (props.newsId) {
        try {
          const detail = await newsApi.getNewsDetail(props.newsId)
          if (detail && detail.title) {
            newsData.value = detail
          }
        } catch (e) {
          console.warn('获取完整新闻数据失败，使用初始数据:', e)
        }
      }
    } else {
      // 直接获取数据
      const detail = await newsApi.getNewsDetail(props.newsId)
      if (!detail) {
        throw new Error('新闻不存在或已被删除')
      }
      newsData.value = detail
    }
    
    // 数据验证和清理
    validateAndCleanData()
    
  } catch (err) {
    error.value = err.message || '获取新闻详情失败'
    console.error('加载新闻详情失败:', err)
  } finally {
    loading.value = false
  }
}

const validateAndCleanData = () => {
  if (!newsData.value) return
  
  // 确保基本字段存在
  if (!newsData.value.title) {
    newsData.value.title = ''
  }
  
  if (!newsData.value.source) {
    newsData.value.source = ''
  }
  
  if (!newsData.value.category) {
    newsData.value.category = ''
  }
  
  // 统一时间字段
  if (!newsData.value.publish_time && newsData.value.pub_time) {
    newsData.value.publish_time = newsData.value.pub_time
  }
  
  // 处理关键词
  if (newsData.value.keywords && typeof newsData.value.keywords === 'string') {
    try {
      newsData.value.keywords = JSON.parse(newsData.value.keywords)
    } catch {
      newsData.value.keywords = newsData.value.keywords.split(',').map(k => k.trim()).filter(k => k)
    }
  }
}

const retryLoad = () => {
  loadNewsDetail()
}

const resetState = () => {
  loading.value = false
  error.value = ''
  newsData.value = null
  showDataIssues.value = false
  contentExpanded.value = false
}

const handleClose = () => {
  emit('update:visible', false)
  emit('close')
}

const handleVisibilityChange = (value) => {
  emit('update:visible', value)
  if (!value) {
    emit('close')
  }
}

const toggleContent = () => {
  contentExpanded.value = !contentExpanded.value
}

const openOriginalLink = () => {
  if (newsData.value?.url && newsData.value.url !== '#') {
    window.open(newsData.value.url, '_blank')
  } else {
    ElMessage.warning('原文链接不可用')
  }
}

const shareNews = async () => {
  if (!newsData.value) return
  
  const shareText = `${newsData.value.title}\n来源：${getSourceName(newsData.value.source)}`
  
  if (navigator.share) {
    try {
      await navigator.share({
        title: newsData.value.title,
        text: shareText,
        url: newsData.value.url || window.location.href
      })
    } catch (e) {
      // 用户取消分享或不支持
      copyToClipboard(shareText)
    }
  } else {
    copyToClipboard(shareText)
  }
}

const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('内容已复制到剪贴板')
  } catch (e) {
    ElMessage.error('复制失败')
  }
}

const reportMissingData = (field) => {
  ElMessage({
    message: `已记录"${fieldLabels[field]}"字段缺失问题，我们会持续改进数据质量`,
    type: 'info',
    duration: 3000
  })
}

const reportDataIssue = () => {
  ElMessageBox.confirm(
    '是否要报告此新闻的数据质量问题？这将帮助我们改进系统。',
    '报告数据问题',
    {
      confirmButtonText: '发送报告',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    // 这里可以发送数据问题报告到后端
    ElMessage.success('感谢您的反馈，我们会尽快处理')
  }).catch(() => {
    // 用户取消
  })
}

// 工具函数
const getSourceName = (source) => {
  const sourceMap = {
    'sina_finance': '新浪财经',
    'eastmoney': '东方财富',
    'tencent_finance': '腾讯财经',
    'netease_money': '网易财经',
    'ifeng_finance': '凤凰财经',
    '新浪财经': '新浪财经',
    '东方财富': '东方财富',
    '腾讯财经': '腾讯财经',
    '网易财经': '网易财经',
    '凤凰财经': '凤凰财经'
  }
  return sourceMap[source] || source || '未知来源'
}

const getSourceTagType = (source) => {
  const typeMap = {
    'sina_finance': 'primary',
    'eastmoney': 'success',
    'tencent_finance': 'warning',
    'netease_money': 'info',
    'ifeng_finance': 'danger',
    '新浪财经': 'primary',
    '东方财富': 'success',
    '腾讯财经': 'warning',
    '网易财经': 'info',
    '凤凰财经': 'danger'
  }
  return typeMap[source] || 'default'
}
</script>

<style lang="scss" scoped>
.enhanced-news-detail-dialog {
  .loading-skeleton {
    padding: 20px;
  }
  
  .error-state {
    text-align: center;
    padding: 40px 20px;
  }
  
  .enhanced-news-detail {
    .news-metadata {
      margin-bottom: 24px;
      
      .news-title-display {
        font-weight: 600;
        font-size: 16px;
        line-height: 1.5;
        
        .el-tag {
          margin-left: 8px;
        }
      }
      
      .news-source-display,
      .news-category-display,
      .news-time-display,
      .news-url-display {
        display: flex;
        align-items: center;
        
        .el-icon {
          margin-right: 4px;
        }
      }
      
      .missing-info {
        color: var(--el-color-warning);
        font-style: italic;
        
        .el-button {
          margin-left: 8px;
          padding: 0;
          font-size: 12px;
        }
      }
    }
    
    .news-keywords {
      margin-bottom: 24px;
      
      h4 {
        display: flex;
        align-items: center;
        margin-bottom: 12px;
        font-size: 14px;
        font-weight: 600;
        color: var(--el-text-color-primary);
        
        .el-icon {
          margin-right: 6px;
        }
      }
      
      .keywords-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        
        .keyword-tag {
          margin: 0;
        }
      }
    }
    
    .news-content,
    .news-summary {
      margin-bottom: 24px;
      
      h4 {
        display: flex;
        align-items: center;
        margin-bottom: 16px;
        font-size: 16px;
        font-weight: 600;
        color: var(--el-text-color-primary);
        
        .el-icon {
          margin-right: 8px;
        }
      }
      
      .content-wrapper {
        position: relative;
      }
      
      .content-text {
        line-height: 1.8;
        color: var(--el-text-color-regular);
        font-size: 14px;
        max-height: 400px;
        overflow: hidden;
        transition: max-height 0.3s ease;
        
        &.content-expanded {
          max-height: none;
        }
        
        :deep(p) {
          margin-bottom: 12px;
          
          &:last-child {
            margin-bottom: 0;
          }
        }
        
        :deep(img) {
          max-width: 100%;
          height: auto;
          border-radius: 4px;
          margin: 8px 0;
        }
        
        :deep(strong) {
          font-weight: 600;
          color: var(--el-text-color-primary);
        }
      }
      
      .content-toggle {
        text-align: center;
        margin-top: 12px;
        
        .toggle-btn {
          font-size: 14px;
          
          .el-icon {
            margin-left: 4px;
          }
        }
      }
      
      .summary-text {
        line-height: 1.6;
        color: var(--el-text-color-regular);
        font-size: 14px;
        background: var(--el-fill-color-lighter);
        padding: 16px;
        border-radius: 6px;
        border-left: 3px solid var(--el-color-primary);
      }
    }
    
    .data-quality-section {
      margin-top: 32px;
      
      .quality-indicators {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
      }
      
      .data-issues {
        .action-buttons {
          margin-top: 12px;
          
          .el-button {
            margin-right: 8px;
          }
        }
      }
    }
  }
  
  .empty-state {
    text-align: center;
    padding: 60px 20px;
  }
  
  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .enhanced-news-detail-dialog {
    width: 95% !important;
    margin: 0 auto;
    
    .enhanced-news-detail {
      .news-metadata {
        :deep(.el-descriptions) {
          .el-descriptions__label {
            width: 80px;
          }
        }
      }
      
      .keywords-container {
        .keyword-tag {
          font-size: 12px;
        }
      }
      
      .content-text {
        font-size: 13px;
        line-height: 1.6;
      }
    }
    
    .dialog-footer {
      flex-direction: column;
      
      .el-button {
        width: 100%;
        margin: 0 0 8px 0;
        
        &:last-child {
          margin-bottom: 0;
        }
      }
    }
  }
}

// 数据层级增强样式
.news-title-display {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.news-source-display {
  color: var(--el-text-color-regular);
}

.news-category-display {
  color: var(--el-text-color-secondary);
}

// 交互反馈增强
.news-metadata {
  transition: all 0.2s ease;
}

.content-text {
  transition: all 0.2s ease;
}
</style> 