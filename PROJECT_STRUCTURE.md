# NewsLook 项目结构概览
更新时间: 2025-06-02 17:37:25

## 🏗️ 项目结构

```
NewsLook/
├── 📁 frontend/               # 前端应用 (Vue.js + Vite)
│   ├── 📁 src/
│   │   ├── 📁 assets/         # 静态资源 (整合后)
│   │   ├── 📁 components/     # Vue组件
│   │   ├── 📁 views/          # 页面视图
│   │   ├── 📁 store/          # Pinia状态管理
│   │   ├── 📁 utils/          # 前端工具函数
│   │   └── 📄 main.js         # 入口文件
│   ├── 📁 public/             # 公共资源
│   ├── 📁 dist/               # 构建输出
│   ├── 📄 package.json        # 前端依赖
│   ├── 📄 vite.config.js      # 构建配置
│   └── 📄 index.html          # HTML模板
│
├── 📁 backend/                # 后端应用 (Python + Flask)
│   ├── 📁 app/                # 主应用模块
│   │   ├── 📁 web/            # Web界面
│   │   ├── 📁 api/            # API接口
│   │   ├── 📁 crawlers/       # 爬虫模块
│   │   └── 📁 utils/          # 工具函数
│   ├── 📁 newslook/           # 核心业务逻辑
│   │   ├── 📁 crawlers/       # 核心爬虫
│   │   ├── 📁 utils/          # 核心工具
│   │   └── 📁 web/            # Web路由
│   ├── 📁 api/                # 外部API
│   ├── 📁 utils/              # 通用工具
│   ├── 📁 config/             # 配置文件
│   ├── 📄 main.py             # 主启动文件
│   └── 📄 run.py              # 运行脚本
│
├── 📁 data/                   # 数据目录
│   ├── 📁 databases/          # 数据库文件
│   ├── 📁 logs/               # 日志文件
│   ├── 📁 test_data/          # 测试数据
│   └── 📁 cache/              # 缓存文件
│
├── 📁 scripts/                # 脚本工具
│   ├── 📁 backup/             # 备份脚本
│   ├── 📄 start.bat           # Windows启动
│   ├── 📄 start.sh            # Linux/Mac启动
│   └── 📄 *.py                # 各种工具脚本
│
├── 📁 tests/                  # 测试文件
│   ├── 📁 unit/               # 单元测试
│   ├── 📁 integration/        # 集成测试
│   └── 📁 fixtures/           # 测试数据
│
├── 📁 examples/               # 示例代码
│   ├── 📁 crawlers/           # 爬虫示例
│   └── 📁 configs/            # 配置示例
│
├── 📁 docs/                   # 项目文档
│   ├── 📄 README.md           # 项目说明
│   ├── 📄 CHANGELOG.md        # 更新日志
│   └── 📄 *.md                # 其他文档
│
├── 📁 backup/                 # 备份文件
│   ├── 📁 legacy_files/       # 旧版文件
│   ├── 📁 duplicate_files/    # 重复文件
│   └── 📁 old_web_v*/         # 旧版Web
│
├── 📄 requirements.txt        # Python依赖
├── 📄 .gitignore             # Git忽略文件
├── 📄 .editorconfig          # 编辑器配置
└── 📄 PROJECT_STRUCTURE.md   # 本文件
```

## 🚀 快速启动

### 后端启动
```bash
# 安装依赖
pip install -r requirements.txt

# 启动后端服务
python main.py
# 或者
cd backend && python main.py
```

### 前端开发
```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 使用启动脚本
```bash
# Windows
scripts/start.bat

# Linux/Mac  
scripts/start.sh
```

## 📝 重要说明

1. **文件整理**: 所有重复和分散的文件已经整理到合适的目录
2. **备份保护**: 原始文件已备份到 `backup/` 目录
3. **导入路径**: Python导入路径已自动更新
4. **配置文件**: 前端构建配置已更新路径映射
5. **启动方式**: 支持多种启动方式，建议使用脚本启动

## 🔧 开发指南

- **前端开发**: 在 `frontend/` 目录下进行Vue.js开发
- **后端开发**: 在 `backend/` 目录下进行Python开发  
- **新增爬虫**: 在 `backend/app/crawlers/` 或 `backend/newslook/crawlers/` 添加
- **配置管理**: 配置文件统一在 `backend/config/` 目录
- **测试**: 测试文件在 `tests/` 目录，按模块组织

## ⚠️ 注意事项

- 确保两个服务器端口不冲突 (前端:3000, 后端:5000)
- 数据库文件在 `data/databases/` 目录
- 日志文件在 `data/logs/` 目录
- 测试前请备份重要数据
