// Service Worker for NewsLook Frontend
// 版本号，用于缓存更新
const CACHE_VERSION = 'v1.0.0'
const CACHE_NAME = `newslook-cache-${CACHE_VERSION}`

// 缓存策略配置
const CACHE_STRATEGIES = {
  // 静态资源：缓存优先
  STATIC: 'cache-first',
  // API数据：网络优先，失败时使用缓存
  API: 'network-first',
  // 图片：缓存优先，失败时从网络获取
  IMAGES: 'cache-first',
  // HTML：网络优先
  HTML: 'network-first'
}

// 需要缓存的静态资源
const STATIC_CACHE_URLS = [
  '/',
  '/index.html',
  '/manifest.json',
  // CSS和JS文件将在运行时动态添加
]

// API路径模式
const API_PATTERNS = [
  /^\/api\/v1\/analytics/,
  /^\/api\/v1\/system/,
  /^\/api\/v1\/crawlers/,
  /^\/api\/stats/,
  /^\/api\/news/
]

// 图片路径模式
const IMAGE_PATTERNS = [
  /\.(png|jpg|jpeg|gif|webp|svg|ico)$/i,
  /^\/images\//,
  /^\/assets\/images\//
]

// 缓存时间配置 (毫秒)
const CACHE_DURATIONS = {
  STATIC: 7 * 24 * 60 * 60 * 1000,    // 7天
  API: 5 * 60 * 1000,                  // 5分钟
  IMAGES: 30 * 24 * 60 * 60 * 1000,    // 30天
  HTML: 1 * 60 * 60 * 1000             // 1小时
}

// Service Worker安装事件
self.addEventListener('install', event => {
  console.log('Service Worker 安装中...')
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('预缓存静态资源')
        return cache.addAll(STATIC_CACHE_URLS)
      })
      .then(() => {
        // 强制激活新的Service Worker
        return self.skipWaiting()
      })
  )
})

// Service Worker激活事件
self.addEventListener('activate', event => {
  console.log('Service Worker 激活中...')
  
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        // 删除旧版本缓存
        return Promise.all(
          cacheNames
            .filter(cacheName => cacheName.startsWith('newslook-cache-') && cacheName !== CACHE_NAME)
            .map(cacheName => {
              console.log('删除旧缓存:', cacheName)
              return caches.delete(cacheName)
            })
        )
      })
      .then(() => {
        // 接管所有客户端
        return self.clients.claim()
      })
  )
})

// 网络请求拦截
self.addEventListener('fetch', event => {
  const request = event.request
  const url = new URL(request.url)
  
  // 只处理GET请求
  if (request.method !== 'GET') {
    return
  }
  
  // 确定缓存策略
  const strategy = determineStrategy(url.pathname, url.href)
  
  event.respondWith(
    handleRequest(request, strategy)
  )
})

// 确定缓存策略
function determineStrategy(pathname, href) {
  // API请求
  if (API_PATTERNS.some(pattern => pattern.test(pathname))) {
    return CACHE_STRATEGIES.API
  }
  
  // 图片资源
  if (IMAGE_PATTERNS.some(pattern => pattern.test(pathname))) {
    return CACHE_STRATEGIES.IMAGES
  }
  
  // HTML文件
  if (pathname.endsWith('.html') || pathname === '/' || !pathname.includes('.')) {
    return CACHE_STRATEGIES.HTML
  }
  
  // 静态资源（CSS、JS等）
  return CACHE_STRATEGIES.STATIC
}

// 处理请求的主要函数
async function handleRequest(request, strategy) {
  try {
    switch (strategy) {
      case CACHE_STRATEGIES.STATIC:
        return await cacheFirst(request)
      
      case CACHE_STRATEGIES.API:
        return await networkFirst(request)
      
      case CACHE_STRATEGIES.IMAGES:
        return await cacheFirst(request)
      
      case CACHE_STRATEGIES.HTML:
        return await networkFirst(request)
      
      default:
        return await networkFirst(request)
    }
  } catch (error) {
    console.error('请求处理失败:', error)
    return await handleOffline(request)
  }
}

// 缓存优先策略
async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME)
  const cachedResponse = await cache.match(request)
  
  if (cachedResponse && !isExpired(cachedResponse)) {
    return cachedResponse
  }
  
  try {
    const networkResponse = await fetch(request)
    
    if (networkResponse.ok) {
      // 添加时间戳用于过期检查
      const responseToCache = networkResponse.clone()
      addTimestamp(responseToCache)
      cache.put(request, responseToCache)
    }
    
    return networkResponse
  } catch (error) {
    // 网络失败，返回缓存（即使已过期）
    if (cachedResponse) {
      return cachedResponse
    }
    throw error
  }
}

// 网络优先策略
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request)
    
    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME)
      const responseToCache = networkResponse.clone()
      addTimestamp(responseToCache)
      cache.put(request, responseToCache)
    }
    
    return networkResponse
  } catch (error) {
    // 网络失败，尝试从缓存获取
    const cache = await caches.open(CACHE_NAME)
    const cachedResponse = await cache.match(request)
    
    if (cachedResponse) {
      return cachedResponse
    }
    
    throw error
  }
}

// 添加时间戳到响应头
function addTimestamp(response) {
  if (response.headers) {
    response.headers.set('sw-cached-at', Date.now().toString())
  }
}

// 检查缓存是否过期
function isExpired(response) {
  const cachedAt = response.headers.get('sw-cached-at')
  if (!cachedAt) return false
  
  const now = Date.now()
  const cacheTime = parseInt(cachedAt)
  const url = new URL(response.url)
  
  // 根据资源类型确定过期时间
  let maxAge = CACHE_DURATIONS.STATIC
  
  if (API_PATTERNS.some(pattern => pattern.test(url.pathname))) {
    maxAge = CACHE_DURATIONS.API
  } else if (IMAGE_PATTERNS.some(pattern => pattern.test(url.pathname))) {
    maxAge = CACHE_DURATIONS.IMAGES
  } else if (url.pathname.endsWith('.html') || url.pathname === '/') {
    maxAge = CACHE_DURATIONS.HTML
  }
  
  return (now - cacheTime) > maxAge
}

// 处理离线情况
async function handleOffline(request) {
  const url = new URL(request.url)
  
  // 如果是导航请求，返回离线页面
  if (request.mode === 'navigate') {
    return await caches.match('/') || new Response('离线状态', {
      status: 200,
      headers: { 'Content-Type': 'text/html' }
    })
  }
  
  // API请求失败，返回离线数据
  if (API_PATTERNS.some(pattern => pattern.test(url.pathname))) {
    return new Response(JSON.stringify({
      success: false,
      message: '当前处于离线状态',
      offline: true,
      data: null
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    })
  }
  
  // 其他请求返回网络错误
  return new Response('网络错误', {
    status: 503,
    statusText: 'Service Unavailable'
  })
}

// 消息处理
self.addEventListener('message', event => {
  const { type, data } = event.data
  
  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting()
      break
      
    case 'GET_CACHE_INFO':
      getCacheInfo().then(info => {
        event.ports[0].postMessage(info)
      })
      break
      
    case 'CLEAR_CACHE':
      clearCache(data?.pattern).then(result => {
        event.ports[0].postMessage(result)
      })
      break
      
    case 'FORCE_REFRESH':
      forceRefreshCache(data?.urls).then(result => {
        event.ports[0].postMessage(result)
      })
      break
  }
})

// 获取缓存信息
async function getCacheInfo() {
  const cache = await caches.open(CACHE_NAME)
  const keys = await cache.keys()
  
  const info = {
    version: CACHE_VERSION,
    cacheName: CACHE_NAME,
    totalItems: keys.length,
    size: 0, // 无法准确计算，但可以估算
    items: []
  }
  
  for (const request of keys) {
    const response = await cache.match(request)
    const cachedAt = response.headers.get('sw-cached-at')
    const size = response.headers.get('content-length') || 0
    
    info.items.push({
      url: request.url,
      method: request.method,
      cachedAt: cachedAt ? new Date(parseInt(cachedAt)).toISOString() : null,
      size: parseInt(size),
      expired: isExpired(response)
    })
    
    info.size += parseInt(size)
  }
  
  return info
}

// 清除缓存
async function clearCache(pattern) {
  const cache = await caches.open(CACHE_NAME)
  const keys = await cache.keys()
  
  let deletedCount = 0
  
  for (const request of keys) {
    if (!pattern || new RegExp(pattern).test(request.url)) {
      await cache.delete(request)
      deletedCount++
    }
  }
  
  return {
    success: true,
    deletedCount,
    message: `已清除 ${deletedCount} 个缓存项`
  }
}

// 强制刷新缓存
async function forceRefreshCache(urls = []) {
  const cache = await caches.open(CACHE_NAME)
  let refreshedCount = 0
  
  for (const url of urls) {
    try {
      const response = await fetch(url, { cache: 'no-cache' })
      if (response.ok) {
        const responseToCache = response.clone()
        addTimestamp(responseToCache)
        await cache.put(url, responseToCache)
        refreshedCount++
      }
    } catch (error) {
      console.error(`缓存刷新失败: ${url}`, error)
    }
  }
  
  return {
    success: true,
    refreshedCount,
    message: `已刷新 ${refreshedCount} 个缓存项`
  }
}

// 后台同步（如果支持）
if ('sync' in self.registration) {
  self.addEventListener('sync', event => {
    if (event.tag === 'background-sync') {
      event.waitUntil(doBackgroundSync())
    }
  })
}

// 后台同步处理
async function doBackgroundSync() {
  try {
    // 这里可以执行一些后台同步任务
    // 比如上传离线时产生的数据
    console.log('执行后台同步')
  } catch (error) {
    console.error('后台同步失败:', error)
  }
}

// 通知点击处理
self.addEventListener('notificationclick', event => {
  event.notification.close()
  
  event.waitUntil(
    clients.openWindow('/')
  )
})

console.log('Service Worker 已加载') 