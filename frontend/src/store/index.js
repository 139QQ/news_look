import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { statsApi, crawlerApi, systemApi } from '@/api'

// 主应用状态
export const useAppStore = defineStore('app', () => {
  // 状态
  const loading = ref(false)
  const sidebarCollapsed = ref(false)
  const isDark = ref(false)
  
  // 方法
  const setLoading = (value) => {
    loading.value = value
  }
  
  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }
  
  const toggleTheme = () => {
    isDark.value = !isDark.value
    document.documentElement.classList.toggle('dark', isDark.value)
  }
  
  return {
    loading,
    sidebarCollapsed,
    isDark,
    setLoading,
    toggleSidebar,
    toggleTheme
  }
})

// 统计数据状态
export const useStatsStore = defineStore('stats', () => {
  const stats = ref({
    total: 0,
    today_news: 0,
    active_sources: 0,
    crawl_success_rate: 0
  })
  
  const sourceStats = ref({})
  const dailyStats = ref([])
  
  // 获取统计数据
  const fetchStats = async () => {
    try {
      const data = await statsApi.getStats()
      if (data && typeof data === 'object') {
        stats.value = {
          total: data.total_news || 0,
          today_news: data.today_news || 0,
          active_sources: data.active_sources || 0,
          crawl_success_rate: data.crawl_success_rate || 0
        }
      }
    } catch (error) {
      console.error('获取统计数据失败:', error)
    }
  }
  
  // 获取来源统计
  const fetchSourceStats = async () => {
    try {
      const data = await statsApi.getSourceStats()
      if (data && data.sources) {
        sourceStats.value = data.sources
      }
    } catch (error) {
      console.error('获取来源统计失败:', error)
    }
  }
  
  // 获取每日统计
  const fetchDailyStats = async () => {
    try {
      const data = await statsApi.getDailyStats()
      if (data && Array.isArray(data.daily_stats)) {
        dailyStats.value = data.daily_stats
      }
    } catch (error) {
      console.error('获取每日统计失败:', error)
    }
  }
  
  return {
    stats,
    sourceStats,
    dailyStats,
    fetchStats,
    fetchSourceStats,
    fetchDailyStats
  }
})

// 爬虫状态
export const useCrawlerStore = defineStore('crawler', () => {
  const crawlers = ref([])
  const isLoading = ref(false)
  
  // 获取爬虫状态
  const fetchCrawlerStatus = async () => {
    isLoading.value = true
    try {
      const data = await crawlerApi.getCrawlerStatus()
      if (data && data.data && Array.isArray(data.data.crawlers)) {
        crawlers.value = data.data.crawlers
      } else {
        // 默认爬虫列表
        crawlers.value = [
          { name: 'sina', display_name: '新浪财经', status: 'stopped', success_rate: 95 },
          { name: 'eastmoney', display_name: '东方财富', status: 'stopped', success_rate: 88 },
          { name: 'tencent', display_name: '腾讯财经', status: 'stopped', success_rate: 92 },
          { name: 'netease', display_name: '网易财经', status: 'stopped', success_rate: 90 },
          { name: 'ifeng', display_name: '凤凰财经', status: 'stopped', success_rate: 78 }
        ]
      }
    } catch (error) {
      console.error('获取爬虫状态失败:', error)
    } finally {
      isLoading.value = false
    }
  }
  
  // 启动爬虫
  const startCrawler = async (name) => {
    try {
      await crawlerApi.startCrawler(name)
      await fetchCrawlerStatus()
      return true
    } catch (error) {
      console.error(`启动爬虫 ${name} 失败:`, error)
      return false
    }
  }
  
  // 停止爬虫
  const stopCrawler = async (name) => {
    try {
      await crawlerApi.stopCrawler(name)
      await fetchCrawlerStatus()
      return true
    } catch (error) {
      console.error(`停止爬虫 ${name} 失败:`, error)
      return false
    }
  }
  
  // 计算属性
  const activeCrawlers = computed(() => 
    crawlers.value.filter(c => c.status === 'running').length
  )
  
  const totalCrawlers = computed(() => crawlers.value.length)
  
  const averageSuccessRate = computed(() => {
    if (crawlers.value.length === 0) return 0
    const total = crawlers.value.reduce((sum, c) => sum + (c.success_rate || 0), 0)
    return Math.round(total / crawlers.value.length)
  })
  
  return {
    crawlers,
    isLoading,
    activeCrawlers,
    totalCrawlers,
    averageSuccessRate,
    fetchCrawlerStatus,
    startCrawler,
    stopCrawler
  }
}) 