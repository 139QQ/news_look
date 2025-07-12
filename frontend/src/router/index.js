import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/components/Layout.vue'
import ErrorPage from '@/components/ErrorPage.vue'

// 检查运行环境
const isDev = import.meta.env.DEV
const baseUrl = isDev ? '/' : '/static/'

const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/views/Home.vue')
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue')
  },
  {
    path: '/news',
    name: 'News',
    component: () => import('@/views/News.vue')
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue')
  },
  {
    path: '/crawler-manager',
    name: 'CrawlerManager',
    component: () => import('@/views/CrawlerManager.vue'),
    meta: { title: '爬虫管理', icon: 'Lightning' }
  },
  {
    path: '/news-list',
    name: 'NewsList',
    component: () => import('@/views/NewsList.vue'),
    meta: { title: '新闻列表', icon: 'Document' }
  },
  {
    path: '/data-monitor',
    name: 'DataMonitor',
    component: () => import('@/views/DataMonitor.vue'),
    meta: { title: '数据监控', icon: 'Monitor' }
  },
  {
    path: '/config-manage',
    name: 'ConfigManage',
    component: () => import('@/views/ConfigManage.vue'),
    meta: { title: '配置管理', icon: 'Setting' }
  },
  {
    path: '/system-log',
    name: 'SystemLog',
    component: () => import('@/views/SystemLog.vue'),
    meta: { title: '系统日志', icon: 'List' }
  },
  {
    path: '/error-diagnostics',
    name: 'ErrorDiagnostics',
    component: () => import('@/views/ErrorDiagnostics.vue'),
    meta: { title: '错误诊断', icon: 'Tools' }
  },
  {
    path: '/test',
    name: 'Test',
    component: () => import('@/views/TestPage.vue'),
    meta: { title: '系统测试', icon: 'Files' }
  },
  {
    path: '/css-debugger',
    name: 'CSSDebugger',
    component: () => import('@/views/CSSDebugger.vue'),
    meta: { title: 'CSS调试', icon: 'Operation' }
  },
  {
    path: '/visibility-test',
    name: 'VisibilityTest',
    component: () => import('@/views/VisibilityTest.vue'),
    meta: { title: '可见性测试', icon: 'View' }
  },
  // 404错误处理路由
  {
    path: '/404',
    name: 'NotFound',
    component: ErrorPage,
    meta: { title: '页面未找到' }
  },
  // 捕获所有未匹配的路由
  {
    path: '/:pathMatch(.*)*',
    redirect: '/404'
  }
]

const router = createRouter({
  history: createWebHistory(baseUrl),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // 路由切换时的滚动行为
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0, behavior: 'smooth' }
    }
  }
})

// 全局路由守卫
router.beforeEach((to, from, next) => {
  try {
    // 检查路由是否存在
    if (to.matched.length === 0 && to.path !== '/404') {
      console.warn(`路由不存在: ${to.path}`)
      next('/404')
      return
    }
    
  // 设置页面标题
    if (to.meta && to.meta.title) {
    document.title = `${to.meta.title} - NewsLook`
  } else {
    document.title = 'NewsLook - 财经新闻爬虫系统'
  }
  
  // 页面加载进度条（如果有的话）
  if (window.nprogress) {
    window.nprogress.start()
  }
    
    // 记录路由访问（可选）
    if (window.trackPageView) {
      window.trackPageView(to.path, to.name)
    }
  
  next()
  } catch (error) {
    console.error('路由守卫错误:', error)
    next('/404')
  }
})

router.afterEach(() => {
  // 结束加载进度条
  if (window.nprogress) {
    window.nprogress.done()
  }
})

// 路由错误处理
router.onError((error) => {
  console.error('路由错误:', error)
  
  // 组件加载失败处理
  if (error.message && error.message.includes('Loading chunk')) {
    console.warn('组件加载失败，可能是网络问题或组件不存在')
    // 重新加载页面
    if (confirm('页面加载失败，是否重新加载？')) {
      window.location.reload()
    }
  }
  
  // 错误上报（可选）
  if (window.reportError) {
    window.reportError({
      type: 'router_error',
      message: error.message,
      stack: error.stack,
      url: window.location.href
    })
  }
})

// 路由健康检查函数
export const checkRouterHealth = () => {
  const health = {
    status: 'ok',
    issues: [],
    routes: routes.length,
    hasHistory: !!router.options.history,
    baseUrl: router.options.history.base
  }
  
  // 检查是否有重复的路由名称
  const names = new Set()
  const duplicateNames = []
  
  routes.forEach(route => {
    if (route.name) {
      if (names.has(route.name)) {
        duplicateNames.push(route.name)
      } else {
        names.add(route.name)
      }
    }
  })
  
  if (duplicateNames.length > 0) {
    health.status = 'warning'
    health.issues.push(`重复的路由名称: ${duplicateNames.join(', ')}`)
  }
  
  // 检查是否有重复的路径
  const paths = new Set()
  const duplicatePaths = []
  
  routes.forEach(route => {
    if (route.path && route.path !== '/:pathMatch(.*)*') {
      if (paths.has(route.path)) {
        duplicatePaths.push(route.path)
      } else {
        paths.add(route.path)
      }
    }
  })
  
  if (duplicatePaths.length > 0) {
    health.status = 'warning'
    health.issues.push(`重复的路由路径: ${duplicatePaths.join(', ')}`)
  }
  
  // 检查是否有404处理
  const has404 = routes.some(route => route.path === '/404' || route.path === '/:pathMatch(.*)*')
  if (!has404) {
    health.status = 'warning'
    health.issues.push('缺少404错误处理路由')
  }
  
  console.log('路由健康检查:', health)
  return health
}

export default router 