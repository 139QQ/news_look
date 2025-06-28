import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/components/Layout.vue'
import ErrorPage from '@/components/ErrorPage.vue'

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
  }
]

const router = createRouter({
  history: createWebHistory('/'),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // 路由切换时的滚动行为
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// 全局路由守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - NewsLook`
  } else {
    document.title = 'NewsLook - 财经新闻爬虫系统'
  }
  
  // 页面加载进度条（如果有的话）
  if (window.nprogress) {
    window.nprogress.start()
  }
  
  next()
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
  // 可以在这里添加错误上报逻辑
})

export default router 