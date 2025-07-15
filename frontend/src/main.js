import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

import App from './App.vue'
import router from './router'

// 导入统一的样式系统 - 确保正确的加载顺序
import './styles/index.scss'

// 导入监控工具
import { Monitoring } from './utils/monitoring.js'

const app = createApp(App)

// 全局错误处理
app.config.errorHandler = (err, vm, info) => {
  console.error('Vue全局错误:', err, info)
  Monitoring.captureError(err, { componentInfo: info })
}

// 注册 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, {
  locale: zhCn,
  // 配置默认尺寸和层级
  size: 'default',
  zIndex: 3000,
})

// 挂载应用
app.mount('#app') 

// 将监控对象挂载到全局，方便调试和使用
window.Monitoring = Monitoring

// 启用路由监控
if (router) {
  window.router = router
}

// 应用启动完成后的初始化
app.config.globalProperties.$ELEMENT = {
  size: 'default',
  zIndex: 3000
}

console.log('🎨 NewsLook UI 系统已启动')
console.log('✅ Element Plus 样式系统已加载')
console.log('🎯 统一全局样式和主题已应用') 