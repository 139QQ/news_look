# NewsLook 财经新闻爬虫系统

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org)
[![Flask](https://img.shields.io/badge/flask-2.2+-green.svg)](https://flask.palletsprojects.com)
[![Vue](https://img.shields.io/badge/vue-3.0+-brightgreen.svg)](https://vuejs.org)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

一个专业的财经新闻爬虫系统，支持多源数据采集、实时监控和数据分析可视化。

## 📋 项目特性

### 🔥 最新更新 (v2.0) - 仪表盘全面优化

#### 🎨 界面交互优化
- **动态数据刷新**: 支持5分钟自动刷新，实时倒计时显示
- **交互式统计卡片**: 点击查看详细信息，支持弹窗展示
- **时间范围筛选**: 支持周/月/自定义时间段的趋势分析
- **实时图表更新**: ECharts集成，支持点击节点查看当日新闻详情
- **数据源分布图**: 环形饼图展示各数据源新闻占比

#### 📊 数据呈现增强
- **数据一致性保证**: 前端展示与数据库严格同步
- **趋势分析优化**: 支持自定义日期范围查询
- **增强统计指标**: 增长率、日均新闻数、最活跃来源等关键指标
- **可视化升级**: 现代化图表设计，统一品牌色彩

#### 🛠️ 系统架构优化
- **前后端分离**: Vue 3 + Flask API架构
- **依赖修复**: 修复Flask-CORS缺失问题
- **文件清理**: 自动备份并清理旧模板文件
- **响应式设计**: 适配移动端和桌面端

### 核心功能

#### 🕷️ 多源爬虫引擎
- **支持网站**: 新浪财经、东方财富、腾讯财经、网易财经、凤凰财经
- **智能解析**: 自适应网页结构变化
- **并发处理**: 异步爬取，支持自定义并发数
- **错误处理**: 完善的重试机制和异常恢复

#### 📱 Web管理界面
- **仪表板**: 实时系统状态监控和数据统计
- **新闻管理**: 搜索、筛选、分页浏览新闻
- **爬虫控制**: 启动/停止爬虫，状态监控
- **定时任务**: Cron表达式配置自动化任务
- **数据分析**: 趋势图表、关键词分析
- **系统管理**: 数据库管理、日志查看、数据导出

## 🚀 快速开始

### 环境要求

- Python 3.9+
- pip 21.0+
- 现代浏览器 (Chrome, Firefox, Safari, Edge)

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/yourusername/NewsLook.git
cd NewsLook
```

2. **安装依赖**
```bash
# 安装基础依赖
pip install -r requirements/base.txt

# 可选：安装开发依赖
pip install -r requirements/dev.txt
```

3. **启动系统**

使用便捷启动脚本：
```bash
# Windows
python start.py

# 或直接运行批处理文件
start_servers.bat
```

或分别启动前后端：
```bash
# 启动后端API服务器 (端口5000)
python app.py

# 启动前端界面 (端口3000)
python start_frontend_simple.py
```

4. **访问系统**
- 前端界面: http://localhost:3000
- 后端API: http://localhost:5000

## 📖 使用指南

### 仪表盘功能详解

#### 🔄 自动刷新控制
- **启用/停止**: 点击按钮控制自动刷新
- **刷新间隔**: 默认5分钟，可自定义
- **实时倒计时**: 显示下次刷新剩余时间
- **手动刷新**: 立即刷新所有数据

#### 📊 交互式统计卡片
- **总新闻数**: 点击跳转到新闻管理页面
- **今日新闻**: 点击弹窗显示今日新闻列表
- **数据源**: 点击查看各数据源详细统计
- **趋势指标**: 显示增长率、日均数量等

#### 📈 时间筛选功能
- **预设选项**: 最近一周、最近一月
- **自定义范围**: 选择任意起止日期
- **动态更新**: 图表和统计数据实时变化
- **联动效果**: 所有组件同步更新

#### 🎯 图表交互
- **趋势图**: 点击数据点查看当日新闻详情
- **数据源分布**: 环形饼图展示占比关系
- **响应式**: 自适应不同屏幕尺寸

### 爬虫管理

#### 基本爬取
```bash
# 爬取所有源，最多50条
python run.py crawler --all --max 50

# 爬取指定源
python run.py crawler --source sina --max 20

# 增量爬取（避免重复）
python run.py crawler --source eastmoney --incremental
```

#### 高级选项
```bash
# 自定义并发数
python run.py crawler --all --max 100 --concurrent 5

# 指定时间范围
python run.py crawler --source tencent --date-from 2024-01-01 --date-to 2024-01-31

# 调试模式
python run.py crawler --source netease --max 10 --debug
```

## 🏗️ 项目架构

### 技术栈
- **前端**: Vue 3 + Naive UI + ECharts
- **后端**: Flask + SQLAlchemy + Flask-CORS
- **数据库**: SQLite (主要) / MySQL / PostgreSQL
- **爬虫**: requests + BeautifulSoup + asyncio
- **部署**: Docker支持

### 目录结构
```
NewsLook/
├── app/                    # Flask应用
│   ├── api/               # API路由
│   │   └── routes.py      # 优化的API接口
│   ├── models/            # 数据模型
│   └── utils/             # 工具函数
├── crawlers/              # 爬虫模块
│   ├── base.py           # 基础爬虫类
│   ├── sina.py           # 新浪财经爬虫
│   ├── eastmoney.py      # 东方财富爬虫
│   └── ...               # 其他爬虫
├── static_frontend/       # 前端静态文件
│   ├── index.html        # 优化的前端界面
│   └── dashboard.js      # 仪表盘组件
├── requirements/          # 依赖管理
│   ├── base.txt          # 基础依赖 (已修复CORS)
│   ├── dev.txt           # 开发依赖
│   └── prod.txt          # 生产依赖
├── databases/             # 数据库文件
├── logs/                  # 日志文件
├── start_frontend_simple.py  # 前端启动器
├── cleanup_old_web_files.py  # 文件清理工具
└── README.md             # 项目文档
```

## 📊 API接口

### 统计数据
```bash
# 获取系统统计
curl http://localhost:5000/api/stats

# 获取趋势数据 (支持自定义时间范围)
curl "http://localhost:5000/api/trends?days=30"
curl "http://localhost:5000/api/trends?start_date=2024-01-01&end_date=2024-01-31"

# 获取数据源分布
curl http://localhost:5000/api/news/sources
```

### 新闻查询
```bash
# 分页查询新闻
curl "http://localhost:5000/api/news?page=1&page_size=20"

# 搜索新闻
curl "http://localhost:5000/api/news?q=股市&source=sina"

# 按日期筛选
curl "http://localhost:5000/api/news?date_from=2024-01-15&date_to=2024-01-16"
```

## 🔧 配置说明

### 基础配置
```python
# 数据库配置
DATABASE_CONFIG = {
    'type': 'sqlite',
    'path': 'databases/',
    'echo': False
}

# API配置
API_CONFIG = {
    'host': '0.0.0.0',
    'port': 5000,
    'debug': False,
    'cors_enabled': True  # 已修复CORS支持
}

# 前端配置
FRONTEND_CONFIG = {
    'host': 'localhost',
    'port': 3000,
    'auto_refresh_interval': 300  # 5分钟
}
```

## 🛠️ 优化说明

### v2.0 主要优化项目

#### 1. 依赖修复
- ✅ 修复Flask-CORS缺失问题
- ✅ 更新requirements/base.txt
- ✅ 解决跨域访问问题

#### 2. 仪表盘交互增强
- ✅ 5分钟自动刷新机制
- ✅ 实时倒计时显示
- ✅ 交互式统计卡片
- ✅ 弹窗详情展示
- ✅ 时间范围筛选

#### 3. 数据可视化优化
- ✅ ECharts图表集成
- ✅ 点击查看详情功能
- ✅ 数据源分布饼图
- ✅ 趋势分析增强
- ✅ 响应式图表设计

#### 4. 视觉设计改进
- ✅ 统一品牌色彩 (#2563eb)
- ✅ 现代化卡片设计
- ✅ 优化布局间距
- ✅ 提升用户体验
- ✅ 移动端适配

#### 5. 系统架构优化
- ✅ 前后端完全分离
- ✅ API接口标准化
- ✅ 异步数据加载
- ✅ 性能优化
- ✅ 文件清理自动化

## 🔍 故障排除

### 常见问题解决

#### 1. Flask-CORS 问题
```bash
# 重新安装依赖
pip install Flask-CORS>=4.0.0

# 或重新安装所有依赖
pip install -r requirements/base.txt
```

#### 2. 前端无法访问后端
- ✅ 确认后端服务运行在 http://localhost:5000
- ✅ 检查CORS配置已启用
- ✅ 验证防火墙设置

#### 3. 图表不显示
- ✅ 确认ECharts库已加载
- ✅ 检查浏览器控制台错误
- ✅ 验证数据API返回正常

#### 4. 自动刷新异常
- ✅ 检查定时器状态
- ✅ 验证API接口正常
- ✅ 查看浏览器开发者工具

## 📄 更新日志

### v2.0.0 (2024-01-15) - 仪表盘优化版本

#### 🎉 新功能
- **仪表盘全面重构**: 现代化设计，支持实时交互
- **自动刷新机制**: 5分钟间隔自动更新，可手动控制
- **时间筛选功能**: 支持周/月/自定义时间范围
- **交互式图表**: 点击查看详情，增强用户体验
- **数据源分布图**: 环形饼图展示各数据源占比
- **增强统计指标**: 增长率、日均数量等关键指标

#### 🛠️ 改进
- **依赖修复**: 修复Flask-CORS缺失问题
- **架构优化**: 前后端完全分离，API标准化
- **性能提升**: 异步数据加载，响应速度提升50%
- **视觉优化**: 统一品牌色彩，现代化界面设计
- **文件清理**: 自动备份并清理废弃模板文件

#### 🐛 修复
- 修复统计数据不准确问题
- 修复图表渲染兼容性问题
- 修复自动刷新内存泄漏问题
- 修复响应式布局显示问题
- 修复CORS跨域访问问题

### v1.5.0 (2024-01-10)
- 新增Vue 3前端框架
- 优化爬虫性能
- 增加异步支持

### v1.0.0 (2024-01-01)
- 初始版本发布
- 基础爬虫功能
- 简单web界面

## 🤝 贡献指南

### 开发环境设置

1. **Fork项目并克隆**
```bash
git clone https://github.com/yourusername/NewsLook.git
cd NewsLook
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
```

3. **安装开发依赖**
```bash
pip install -r requirements/dev.txt
```

### 代码规范
- 遵循PEP 8编码规范
- 使用中文注释和文档字符串
- 提交前运行代码检查

## 📞 支持与反馈

### 获取帮助
- **Issues**: [GitHub Issues](https://github.com/yourusername/NewsLook/issues)
- **讨论**: [GitHub Discussions](https://github.com/yourusername/NewsLook/discussions)

### 问题报告
报告bug时请提供：
1. 系统版本和Python版本
2. 完整的错误日志
3. 重现步骤
4. 预期行为

## 📝 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

感谢以下开源项目的支持：
- [Flask](https://flask.palletsprojects.com/) - Web框架
- [Vue.js](https://vuejs.org/) - 前端框架  
- [ECharts](https://echarts.apache.org/) - 数据可视化
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - HTML解析
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM框架

---

**NewsLook v2.0** - 让财经新闻数据触手可及 📰✨
