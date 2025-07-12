<template>
  <n-card
    :class="['news-card', { 'selected': selected }]"
    hoverable
    @click="$emit('view', news.id)"
  >
    <template #header>
      <div class="news-header">
        <n-checkbox
          :checked="selected"
          @update:checked="handleSelect"
          @click.stop
        />
        <n-ellipsis style="flex: 1; margin-left: 8px">
          {{ news.title }}
        </n-ellipsis>
      </div>
    </template>
    
    <template #header-extra>
      <n-tag size="small" :type="getSourceType(news.source)">
        {{ news.source }}
      </n-tag>
    </template>
    
    <div class="news-content">
      <n-ellipsis :line-clamp="3" :tooltip="false">
        {{ news.content }}
      </n-ellipsis>
    </div>
    
    <template #footer>
      <n-space justify="space-between" align="center">
        <div class="news-meta">
          <n-space size="small">
            <n-text depth="3" style="font-size: 12px">
              {{ formatTime(news.pub_time) }}
            </n-text>
            <n-tag
              size="small"
              :type="getSentimentType(news.sentiment)"
            >
              情感: {{ news.sentiment?.toFixed(2) || '0.00' }}
            </n-tag>
          </n-space>
        </div>
        
        <n-space size="small">
          <n-button
            size="small"
            text
            @click.stop="$emit('view', news.id)"
          >
            查看详情
          </n-button>
        </n-space>
      </n-space>
    </template>
  </n-card>
</template>

<script setup>
import { computed } from 'vue'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

const props = defineProps({
  news: {
    type: Object,
    required: true
  },
  selected: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['select', 'view'])

const formatTime = (timeStr) => {
  try {
    const date = new Date(timeStr)
    return formatDistanceToNow(date, { 
      locale: zhCN, 
      addSuffix: true 
    })
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

const handleSelect = (checked) => {
  emit('select', props.news.id)
}
</script>

<style scoped>
.news-card {
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.news-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.news-card.selected {
  border-color: #18a058;
  box-shadow: 0 4px 16px rgba(24, 160, 88, 0.2);
}

.news-header {
  display: flex;
  align-items: center;
  width: 100%;
}

.news-content {
  min-height: 60px;
  line-height: 1.6;
  margin: 12px 0;
}

.news-meta {
  flex: 1;
}
</style> 