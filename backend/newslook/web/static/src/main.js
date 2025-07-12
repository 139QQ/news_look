import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { store } from './store'

// Naive UI
import naive from 'naive-ui'

// 通用字体
import 'vfonts/Lato.css'
// 等宽字体
import 'vfonts/FiraCode.css'

const app = createApp(App)

app.use(naive)
app.use(router)
app.use(store)

app.mount('#app') 