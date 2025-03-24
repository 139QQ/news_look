# 项目结构

## 1. 目录结构

```
finance_news_crawler/
├── app/                      # 应用核心目录
│   ├── __init__.py           # 应用初始化
│   ├── config/               # 配置模块
│   │   ├── __init__.py
│   │   ├── default.py        # 默认配置
│   │   ├── development.py    # 开发环境配置
│   │   ├── production.py     # 生产环境配置
│   │   └── testing.py        # 测试环境配置
│   ├── models/               # 数据模型
│   │   ├── __init__.py
│   │   └── news.py           # 新闻数据模型
│   ├── crawlers/             # 爬虫模块
│   │   ├── __init__.py
│   │   ├── base.py           # 爬虫基类
│   │   ├── eastmoney.py      # 东方财富爬虫
│   │   ├── eastmoney_simple.py # 简化版东方财富爬虫
│   │   ├── sina.py           # 新浪财经爬虫
│   │   ├── tencent.py        # 腾讯财经爬虫
│   │   ├── netease.py        # 网易财经爬虫
│   │   └── ifeng.py          # 凤凰财经爬虫
│   ├── cli/                  # 命令行接口
│   │   ├── __init__.py
│   │   ├── crawler_commands.py  # 爬虫命令行接口
│   │   ├── web_commands.py      # Web应用命令行接口
│   │   └── scheduler_commands.py  # 调度器命令行接口
│   ├── db/                   # 数据库模块
│   │   ├── __init__.py
│   │   ├── sqlite_manager.py # SQLite管理器
│   │   └── migrations/       # 数据库迁移
│   │       ├── __init__.py
│   │       └── versions/     # 迁移版本
│   ├── utils/                # 工具模块
│   │   ├── __init__.py
│   │   ├── database.py       # 数据库操作
│   │   ├── logger.py         # 日志工具
│   │   ├── text_cleaner.py   # 文本清洗
│   │   ├── sentiment_analyzer.py # 情感分析
│   │   └── profiler.py       # 性能分析
│   ├── web/                  # Web应用
│   │   ├── __init__.py
│   │   ├── routes.py         # 路由定义
│   │   ├── forms.py          # 表单定义
│   │   ├── static/           # 静态资源
│   │   │   ├── css/
│   │   │   ├── js/
│   │   │   └── img/
│   │   └── templates/        # 模板文件
│   └── tasks/                # 任务模块
│       ├── __init__.py
│       └── scheduler.py      # 任务调度器
├── data/                     # 数据文件目录
│   ├── output/               # 输出数据
│   ├── sentiment_dict/       # 情感词典
│   └── finance_news.db       # 数据库文件
├── db/                       # 数据库备份目录
├── logs/                     # 日志文件目录
│   ├── eastmoney/            # 东方财富爬虫日志
│   ├── eastmoney_simple/     # 简化版东方财富爬虫日志
│   ├── sina/                 # 新浪财经爬虫日志
│   ├── tencent/              # 腾讯财经爬虫日志
│   ├── netease/              # 网易财经爬虫日志
│   └── ifeng/                # 凤凰财经爬虫日志
├── backup/                   # 备份文件目录
├── tests/                    # 测试目录
│   ├── __init__.py
│   ├── conftest.py           # 测试配置
│   ├── crawlers/             # 爬虫测试
│   │   ├── __init__.py
│   │   ├── test_eastmoney.py
│   │   └── test_sina.py
│   ├── db/                   # 数据库测试
│   │   ├── __init__.py
│   │   └── test_sqlite.py
│   └── utils/                # 工具测试
│       ├── __init__.py
│       └── test_sentiment.py
├── scripts/                  # 脚本目录
│   ├── clean_logs.ps1        # 日志清理脚本
│   ├── reorganize_logs.ps1   # 日志整理脚本
│   ├── backup_db.py          # 数据库备份脚本
│   ├── log_analyzer.py       # 日志分析脚本
│   └── deploy.sh             # 部署脚本
├── requirements/             # 依赖管理
│   ├── base.txt              # 基础依赖
│   ├── dev.txt               # 开发依赖
│   ├── test.txt              # 测试依赖
│   └── prod.txt              # 生产环境依赖
├── docs/                     # 文档目录
│   ├── architecture/         # 架构文档
│   │   └── structure.md      # 项目结构
│   ├── development/          # 开发文档
│   │   ├── coding_style.md   # 编码规范
│   │   └── contribution.md   # 贡献指南
│   ├── user/                 # 用户文档
│   │   ├── installation.md   # 安装指南
│   │   └── usage.md          # 使用手册
│   └── api/                  # API文档
│       └── crawler_api.md    # 爬虫API
├── .github/                  # GitHub配置
│   └── workflows/            # GitHub Actions工作流
│       ├── test.yml          # 测试工作流
│       └── lint.yml          # 代码检查工作流
├── run.py                    # 主入口点
├── run_crawler.py            # 爬虫运行脚本
├── run_scheduler.py          # 调度器运行脚本
├── requirements.txt          # 依赖列表（将被拆分）
├── .env.example              # 环境变量示例
├── .pylintrc                 # Pylint配置
├── pyproject.toml            # Python项目配置
├── Dockerfile                # Docker配置
├── docker-compose.yml        # Docker Compose配置
├── .editorconfig             # 编辑器配置
├── .gitignore                # Git忽略配置
└── README.md                 # 项目说明
```

## 2. 入口点说明

项目有三个主要入口点：

1. **run.py**：主入口点，用于启动Web应用
   ```bash
   python run.py
   ```

2. **run_crawler.py**：爬虫统一入口
   ```bash
   # 运行所有爬虫
   python run_crawler.py
   
   # 运行特定爬虫
   python run_crawler.py -s 东方财富 -d 1
   ```

3. **run_scheduler.py**：调度器入口，用于定时任务
   ```bash
   python run_scheduler.py
   ```

## 3. 模块依赖关系

- **app/crawlers**：依赖于 **app/db** 和 **app/utils**
- **app/web**：依赖于 **app/models** 和 **app/utils**
- **app/tasks**：依赖于 **app/crawlers**
- **app/cli**：依赖于 **app/crawlers**、**app/web** 和 **app/tasks**
- **run*.py**：依赖于 **app/cli** 