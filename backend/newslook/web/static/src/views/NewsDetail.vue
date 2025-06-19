<template>
  <div class="news-detail-container">
    <n-spin :show="loading">
      <div v-if="news">
        <!-- 返回按钮 -->
        <div style="margin-bottom: 16px">
          <n-button @click="$router.back()" quaternary>
            <template #icon>
              <n-icon><ArrowBackOutline /></n-icon>
            </template>
            返回
          </n-button>
        </div>
        
        <!-- 新闻内容 -->
        <n-card>
          <template #header>
            <n-h1 style="margin: 0">{{ news.title }}</n-h1>
          </template>
          
          <template #header-extra>
            <n-space>
              <n-button size="small" @click="shareNews">分享</n-button>
              <n-button size="small" @click="exportNews">导出</n-button>
            </n-space>
          </template>
          
          <!-- 新闻元信息 -->
          <div class="news-meta">
            <n-space size="large">
              <div>
                <n-text depth="3">来源：</n-text>
                <n-tag :type="getSourceType(news.source)">{{ news.source }}</n-tag>
              </div>
              <div>
                <n-text depth="3">作者：</n-text>
                <n-text>{{ news.author || '未知' }}</n-text>
              </div>
              <div>
                <n-text depth="3">发布时间：</n-text>
                <n-text>{{ formatTime(news.pub_time) }}</n-text>
              </div>
              <div>
                <n-text depth="3">情感值：</n-text>
                <n-tag :type="getSentimentType(news.sentiment)">
                  {{ news.sentiment?.toFixed(2) || '0.00' }}
                </n-tag>
              </div>
            </n-space>
          </div>
          
          <!-- 关键词 -->
          <div v-if="news.keywords" class="news-keywords">
            <n-text depth="3">关键词：</n-text>
            <n-space size="small" style="margin-top: 8px">
              <n-tag
                v-for="keyword in news.keywords.split(',')"
                :key="keyword"
                size="small"
                type="default"
              >
                {{ keyword.trim() }}
              </n-tag>
            </n-space>
          </div>
          
          <!-- 新闻内容 -->
          <div class="news-content">
            <n-text>{{ news.content }}</n-text>
          </div>
          
          <!-- 原文链接 -->
          <div v-if="news.url" class="news-url">
            <n-button tag="a" :href="news.url" target="_blank" text type="primary">
              查看原文
              <template #icon>
                <n-icon><OpenOutline /></n-icon>
              </template>
            </n-button>
          </div>
        </n-card>
      </div>
      
      <n-result
        v-else-if="!loading"
        status="404"
        title="新闻不存在"
        description="抱歉，您查找的新闻不存在或已被删除"
      >
        <template #footer>
          <n-button @click="$router.push('/news')">返回新闻列表</n-button>
        </template>
      </n-result>
    </n-spin>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  ArrowBackOutline,
  OpenOutline
} from '@vicons/ionicons5'
import { newsApi } from '../api'

const route = useRoute()
const message = useMessage()

const news = ref(null)
const loading = ref(false)

const formatTime = (timeStr) => {
  try {
    return new Date(timeStr).toLocaleString('zh-CN')
  } catch {
    return timeStr
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

const loadNewsDetail = async () => {
  loading.value = true
  try {
    const id = route.params.id
    const response = await newsApi.getNewsDetail(id)
    news.value = response.news
  } catch (error) {
    message.error('加载新闻详情失败')
  } finally {
    loading.value = false
  }
}

const shareNews = () => {
  if (navigator.share) {
    navigator.share({
      title: news.value.title,
      url: window.location.href
    })
  } else {
    navigator.clipboard.writeText(window.location.href)
    message.success('链接已复制到剪贴板')
  }
}

const exportNews = () => {
  // 实现导出功能
  message.info('导出功能开发中')
}

onMounted(() => {
  loadNewsDetail()
})
</script>

<style scoped>
.news-detail-container {
  max-width: 800px;
  margin: 0 auto;
}

.news-meta {
  padding: 16px 0;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 16px;
}

.news-keywords {
  margin: 16px 0;
  padding: 16px 0;
  border-bottom: 1px solid #f0f0f0;
}

.news-content {
  font-size: 16px;
  line-height: 1.8;
  margin: 24px 0;
  white-space: pre-wrap;
}

.news-url {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}
</style> 