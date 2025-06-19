import { createRouter, createWebHistory } from 'vue-router'

// 路由组件懒加载
const Home = () => import('../views/Home.vue')
const NewsList = () => import('../views/NewsList.vue')
const NewsDetail = () => import('../views/NewsDetail.vue')
const Stats = () => import('../views/Stats.vue')
const Trends = () => import('../views/Trends.vue')
const Crawler = () => import('../views/Crawler.vue')
const Settings = () => import('../views/Settings.vue')
const Logs = () => import('../views/Logs.vue')

const routes = [
  {
    path: '/',
    name: 'home',
    component: Home,
    meta: {
      title: '首页'
    }
  },
  {
    path: '/news',
    name: 'news',
    component: NewsList,
    meta: {
      title: '新闻列表'
    }
  },
  {
    path: '/news/:id',
    name: 'news-detail',
    component: NewsDetail,
    meta: {
      title: '新闻详情'
    }
  },
  {
    path: '/stats',
    name: 'stats',
    component: Stats,
    meta: {
      title: '统计概览'
    }
  },
  {
    path: '/trends',
    name: 'trends',
    component: Trends,
    meta: {
      title: '趋势分析'
    }
  },
  {
    path: '/crawler',
    name: 'crawler',
    component: Crawler,
    meta: {
      title: '爬虫管理'
    }
  },
  {
    path: '/settings',
    name: 'settings',
    component: Settings,
    meta: {
      title: '系统设置'
    }
  },
  {
    path: '/logs',
    name: 'logs',
    component: Logs,
    meta: {
      title: '日志监控'
    }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - NewsLook`
  }
  next()
})

export default router 