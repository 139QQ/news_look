# NewsLook 前端界面

<div align="center">

![NewsLook Logo](./public/favicon.svg)

**现代化的财经新闻爬虫系统前端界面**

[![Vue.js](https://img.shields.io/badge/Vue.js-3.4-4FC08D?style=flat-square&logo=vue.js)](https://vuejs.org/)
[![Element Plus](https://img.shields.io/badge/Element%20Plus-2.4-409EFF?style=flat-square&logo=element)](https://element-plus.org/)
[![Vite](https://img.shields.io/badge/Vite-5.0-646CFF?style=flat-square&logo=vite)](https://vitejs.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6?style=flat-square&logo=typescript)](https://www.typescriptlang.org/)

</div>

## ✨ 特性

- 🚀 **现代技术栈**: Vue 3 + Element Plus + Vite
- 📱 **响应式设计**: 完美适配桌面端和移动端
- 🎨 **现代化UI**: 基于Element Plus的美观界面
- 📊 **数据可视化**: 集成ECharts图表库
- ⚡ **高性能**: Vite构建工具，开发体验极佳
- 🔧 **类型安全**: 完整的TypeScript支持
- 🌙 **主题切换**: 支持明暗主题切换
- 📦 **按需加载**: 组件和路由懒加载
- 🛡️ **错误处理**: 完善的错误边界和提示

## 🏗️ 项目结构

```
frontend/
├── public/                 # 静态资源
│   ├── favicon.svg        # 网站图标
│   └── index.html         # HTML模板
├── src/
│   ├── api/               # API接口
│   ├── assets/            # 静态资源
│   ├── components/        # 通用组件
│   │   ├── Layout.vue     # 布局组件
│   │   ├── ErrorPage.vue  # 错误页面
│   │   └── LoadingSpinner.vue # 加载组件
│   ├── router/            # 路由配置
│   ├── store/             # 状态管理
│   ├── styles/            # 样式文件
│   ├── utils/             # 工具函数
│   ├── views/             # 页面组件
│   │   ├── Dashboard.vue      # 数据概览
│   │   ├── CrawlerManager.vue # 爬虫管理
│   │   ├── NewsList.vue       # 新闻列表
│   │   ├── DataMonitor.vue    # 数据监控
│   │   ├── ConfigManage.vue   # 配置管理
│   │   └── SystemLog.vue      # 系统日志
│   ├── App.vue            # 根组件
│   └── main.js            # 入口文件
├── scripts/               # 构建脚本
│   ├── start.js          # 开发启动脚本
│   └── build.js          # 生产构建脚本
├── package.json          # 项目配置
├── vite.config.js        # Vite配置
└── README.md             # 项目文档
```

## 🚀 快速开始

### 环境要求

- Node.js >= 16.0.0
- npm >= 8.0.0

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
# 使用Vite开发服务器
npm run dev

# 或使用自定义启动脚本（包含环境检查）
npm run start
```

开发服务器将在 http://localhost:3000 启动

### 生产构建

```bash
# 标准构建
npm run build

# 带分析的构建脚本
npm run build:prod

# 构建分析
npm run build:analyze
```

### 预览生产版本

```bash
npm run preview
# 或
npm run serve
```

## 📱 功能模块

### 🏠 数据概览 (Dashboard)
- 实时统计数据展示
- 新闻来源分布图表
- 每日新闻趋势图
- 爬虫状态监控
- 快速操作面板

### ⚡ 爬虫管理 (CrawlerManager)
- 爬虫状态监控
- 批量启动/停止操作
- 实时成功率统计
- 爬虫配置管理
- 错误信息显示

### 📰 新闻列表 (NewsList)
- 新闻搜索和筛选
- 分页浏览
- 新闻详情查看
- 原文链接跳转
- 响应式表格

### 📊 数据监控 (DataMonitor)
- 实时性能指标
- 爬取速度图表
- 状态分布统计
- 自动刷新机制
- 详细状态表格

### ⚙️ 配置管理 (ConfigManage)
- 爬虫参数配置
- 数据库设置
- 系统参数调整
- 配置导入导出

### 📋 系统日志 (SystemLog)
- 日志级别筛选
- 关键词搜索
- 分页浏览
- 日志清理
- 实时日志流

## 🎨 主题和样式

### 主题切换
系统支持明暗主题切换，用户可以在顶部导航栏切换主题。

### 响应式设计
- **桌面端**: 完整功能和布局
- **平板**: 自适应布局调整
- **手机**: 移动端优化界面

### 自定义样式
样式文件位于 `src/styles/` 目录：
- `variables.scss`: 全局变量
- `index.scss`: 基础样式
- 组件级样式使用scoped CSS

## 🔧 配置说明

### 环境变量
在项目根目录创建 `.env` 文件：

```env
# 开发环境
VITE_API_BASE_URL=http://localhost:5000/api
VITE_APP_TITLE=NewsLook 开发版

# 生产环境
VITE_API_BASE_URL=/api
VITE_APP_TITLE=NewsLook 财经新闻系统
```

### API代理配置
开发环境API代理在 `vite.config.js` 中配置：

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:5000',
      changeOrigin: true,
      secure: false
    }
  }
}
```

## 🛠️ 开发指南

### 代码规范
- 使用 ESLint 进行代码检查
- 使用 Prettier 进行代码格式化
- 组件名使用 PascalCase
- 文件名使用 kebab-case

### 组件开发
新组件请放在 `src/components/` 目录，并遵循以下结构：

```vue
<template>
  <!-- 模板 -->
</template>

<script setup>
// 使用 Composition API
</script>

<style lang="scss" scoped>
// 样式
</style>
```

### 状态管理
使用 Pinia 进行状态管理，Store 文件位于 `src/store/`：

```javascript
// 使用 Composition API 风格
export const useExampleStore = defineStore('example', () => {
  const state = ref()
  const getters = computed(() => {})
  const actions = () => {}
  
  return { state, getters, actions }
})
```

## 🔍 测试

```bash
# 类型检查
npm run type-check

# 代码格式化
npm run format

# 代码检查
npm run lint
```

## 📦 构建优化

### 生产构建优化
- 自动代码分割
- Tree Shaking
- 资源压缩
- 懒加载路由
- 组件按需导入

### 包大小分析
使用构建分析查看包大小：

```bash
npm run build:analyze
```

分析报告将生成在 `dist/bundle-analysis.html`

## 🚀 部署

### 静态部署
构建完成后，将 `dist/` 目录部署到静态服务器即可。

### Nginx 配置示例
```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /path/to/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://backend-server:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目基于 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 问题反馈

如果遇到问题，请通过以下方式反馈：

- 📧 Email: support@newslook.com
- 🐛 Issues: [GitHub Issues](https://github.com/newsLook/newsLook-frontend/issues)
- 💬 讨论: [GitHub Discussions](https://github.com/newsLook/newsLook-frontend/discussions)

## 🙏 致谢

感谢以下开源项目：

- [Vue.js](https://vuejs.org/) - 渐进式JavaScript框架
- [Element Plus](https://element-plus.org/) - Vue 3 组件库
- [Vite](https://vitejs.dev/) - 下一代前端构建工具
- [ECharts](https://echarts.apache.org/) - 数据可视化图表库
- [Pinia](https://pinia.vuejs.org/) - Vue.js 状态管理库

---

<div align="center">
  Made with ❤️ by NewsLook Team
</div> 