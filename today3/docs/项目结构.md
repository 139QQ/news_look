# 财经新闻爬虫系统 - 项目结构

## 目录结构

```
finance_news_crawler/
├── app/                      # 应用核心目录
│   ├── __init__.py           # 应用初始化
│   ├── config.py             # 配置文件
│   ├── models/               # 数据模型
│   │   ├── __init__.py
│   │   └── news.py           # 新闻数据模型
│   ├── crawlers/             # 爬虫模块
│   │   ├── __init__.py
│   │   ├── base.py           # 爬虫基类
│   │   ├── eastmoney.py      # 东方财富爬虫
│   │   ├── sina.py           # 新浪财经爬虫
│   │   ├── tencent.py        # 腾讯财经爬虫
│   │   └── netease.py        # 网易财经爬虫
│   ├── utils/                # 工具模块
│   │   ├── __init__.py
│   │   ├── database.py       # 数据库操作
│   │   ├── db_manager.py     # 数据库管理
│   │   ├── text_cleaner.py   # 文本清洗
│   │   ├── sentiment.py      # 情感分析
│   │   └── logger.py         # 日志工具
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
├── db/                       # 数据库文件目录
├── logs/                     # 日志文件目录
├── data/                     # 数据文件目录
├── backup/                   # 备份文件目录
├── tests/                    # 测试目录
│   ├── __init__.py
│   ├── test_crawlers.py
│   ├── test_database.py
│   └── test_utils.py
├── docs/                     # 文档目录
│   ├── 项目文档.md
│   └── 项目结构.md
├── run.py                    # Web应用入口
├── run_crawler.py            # 爬虫运行入口
├── run_scheduler.py          # 调度器运行入口
├── start.bat                 # Windows启动脚本
├── start.sh                  # Linux/Mac启动脚本
├── .editorconfig             # 编辑器配置
├── .gitignore                # Git忽略文件
├── requirements.txt          # 依赖列表
└── README.md                 # 项目说明
```

## 模块说明

### 1. 应用核心模块 (app/)

- **app/__init__.py**: 应用初始化，设置必要的目录和导入配置
- **app/config.py**: 系统配置，包括数据库、日志、爬虫、Web应用等配置

#### 1.1 数据模型模块 (app/models/)

- **app/models/news.py**: 定义新闻和反馈数据模型，包括数据转换和序列化方法

#### 1.2 爬虫模块 (app/crawlers/)

- **app/crawlers/base.py**: 爬虫基类，定义通用方法和接口
- **app/crawlers/eastmoney.py**: 东方财富爬虫实现
- **app/crawlers/sina.py**: 新浪财经爬虫实现
- **app/crawlers/tencent.py**: 腾讯财经爬虫实现
- **app/crawlers/netease.py**: 网易财经爬虫实现

#### 1.3 工具模块 (app/utils/)

- **app/utils/database.py**: 数据库操作，包括新闻和反馈的CRUD操作
- **app/utils/db_manager.py**: 数据库管理工具，包括合并、备份、恢复、导出、导入等功能
- **app/utils/text_cleaner.py**: 文本清洗工具，处理编码问题和格式化文本
- **app/utils/sentiment.py**: 情感分析工具，分析新闻情感倾向
- **app/utils/logger.py**: 日志工具，统一日志格式和输出

#### 1.4 Web应用模块 (app/web/)

- **app/web/__init__.py**: Web应用初始化，创建Flask应用
- **app/web/routes.py**: 路由定义，处理HTTP请求
- **app/web/forms.py**: 表单定义，处理用户输入
- **app/web/static/**: 静态资源，包括CSS、JS和图片
- **app/web/templates/**: 模板文件，使用Jinja2模板引擎

#### 1.5 任务模块 (app/tasks/)

- **app/tasks/scheduler.py**: 任务调度器，管理定时任务

### 2. 数据存储目录

- **db/**: 存储数据库文件，包括主数据库和来源专用数据库
- **logs/**: 存储日志文件，按模块和日期分类
- **data/**: 存储数据文件，包括导出的数据和报告
- **backup/**: 存储备份文件，包括数据库备份

### 3. 测试目录 (tests/)

- **tests/test_crawlers.py**: 爬虫模块测试
- **tests/test_database.py**: 数据库模块测试
- **tests/test_utils.py**: 工具模块测试

### 4. 文档目录 (docs/)

- **docs/项目文档.md**: 项目详细文档
- **docs/项目结构.md**: 项目结构说明

### 5. 入口文件

- **run.py**: Web应用入口，启动Flask应用
- **run_crawler.py**: 爬虫运行入口，支持命令行参数
- **run_scheduler.py**: 调度器运行入口，支持守护进程模式

### 6. 其他文件

- **start.bat**: Windows启动脚本
- **start.sh**: Linux/Mac启动脚本
- **.editorconfig**: 编辑器配置，统一代码风格
- **.gitignore**: Git忽略文件，排除不需要版本控制的文件
- **requirements.txt**: 依赖列表，列出所有Python包依赖
- **README.md**: 项目说明，包括安装和使用方法 