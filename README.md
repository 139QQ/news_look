# 财经新闻爬虫系统 (NewsLook)

一个用于爬取各大财经网站新闻的系统，包括东方财富、新浪财经、腾讯财经、网易财经和凤凰财经等网站。
还有很多功能需要完善

## 功能特点

- 支持多个财经网站的新闻爬取
- 统一的爬虫接口和数据格式
- 完善的错误处理和日志记录
- 灵活的配置选项
- 支持代理使用
- 支持按时间范围爬取新闻
- 自动提取新闻标题、内容、发布时间、作者等信息
- 自动提取相关股票信息
- 支持情感分析
- 每个来源使用独立数据库，支持分布式部署

## 系统架构

```
app/
  ├── crawlers/         # 爬虫模块
  │   ├── __init__.py   # 爬虫包初始化文件，提供获取爬虫实例的接口
  │   ├── base.py       # 爬虫基类，封装通用功能
  │   ├── eastmoney.py  # 东方财富爬虫
  │   ├── sina.py       # 新浪财经爬虫
  │   ├── tencent.py    # 腾讯财经爬虫
  │   ├── netease.py    # 网易财经爬虫
  │   └── ifeng.py      # 凤凰财经爬虫
  ├── web/              # Web应用模块
  │   ├── __init__.py
  │   ├── routes.py     # 路由定义
  │   └── views.py      # 视图函数
  ├── utils/            # 工具模块
  │   ├── logger.py     # 日志工具
  │   ├── text_cleaner.py # 文本清洗工具
  │   ├── proxy.py      # 代理管理
  │   ├── ad_filter.py  # 广告过滤
  │   └── sentiment.py  # 情感分析工具
  ├── db/               # 数据库模块
  │   └── database.py   # 数据库操作
  ├── models/           # 数据模型
  │   └── news.py       # 新闻数据模型
  ├── tasks/            # 定时任务
  │   └── scheduler.py  # 任务调度器
  ├── templates/        # HTML模板
  ├── static/           # 静态资源
  ├── config.py         # 全局配置
  └── __init__.py       # 应用初始化
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

系统提供了统一的命令行入口 `run.py`，支持三种运行模式：爬虫模式、调度模式和Web应用模式。

### 1. 爬虫模式

爬虫模式用于运行爬虫任务，支持多种爬虫类型。

```bash
# 基本使用
python run.py crawler --source <来源名称> --days <天数>

# 爬取腾讯财经最近3天的新闻
python run.py crawler --source 腾讯财经 --days 3

# 使用代理爬取新浪财经最近7天的新闻
python run.py crawler --source 新浪财经 --days 7 --use-proxy
```

### 2. 调度模式

调度模式用于定时执行爬虫任务，可以设置爬虫类型和时间间隔。

```bash
# 启动调度器
python run.py scheduler

# 使用特定配置启动调度器
python run.py scheduler --config config.json
```

### 3. Web应用模式

Web应用模式提供了一个Web界面，可以查看爬取的新闻和爬虫运行状态。

```bash
# 启动Web应用
python run.py web

# 指定端口启动Web应用
python run.py web --port 8080
```

## 数据库架构

系统使用两级数据库架构：

1. **主数据库**: `finance_news.db` - 用于存储聚合的新闻数据
2. **来源专用数据库**: 每个来源对应一个独立的数据库文件，如 `腾讯财经.db`、`新浪财经.db` 等

### 文件命名约定

来源专用数据库使用来源名称作为文件名，例如：
- 腾讯财经 -> `腾讯财经.db`
- 新浪财经 -> `新浪财经.db`
- 东方财富 -> `东方财富.db`
- 网易财经 -> `网易财经.db`
- 凤凰财经 -> `凤凰财经.db`

### 数据库实现细节

#### 1. 为每个爬虫设置专用数据库路径

在 `CrawlerManager` 类中，我们为每个爬虫实例设置了对应的数据库路径：

```python
# 为每个爬虫设置固定的数据库路径
self._set_db_path(ifeng_crawler, "凤凰财经")
self._set_db_path(sina_crawler, "新浪财经")
self._set_db_path(tencent_crawler, "腾讯财经")
self._set_db_path(netease_crawler, "网易财经")
self._set_db_path(eastmoney_crawler, "东方财富")
```

#### 2. 改进 NewsDatabase 类

`NewsDatabase` 类支持以下功能：

- 使用 `source_db_map` 属性，建立来源名称到数据库文件的映射
- 支持按来源名称选择对应的数据库进行查询
- 支持按来源统计新闻数量
- 支持在所有数据库中查找指定ID的新闻
- 从所有数据库中收集来源和分类数据

## 爬虫系统改进

### 存在的问题

1. **代码重复**：各爬虫间存在大量重复代码，如HTTP请求、数据清洗等通用功能
2. **错误处理不完善**：缺乏统一的异常处理机制，导致爬虫在遇到异常时容易崩溃
3. **日志系统不健全**：日志记录不完整，难以追踪问题
4. **配置分散**：配置信息散布在代码中，难以统一管理
5. **扩展性差**：添加新爬虫需要重复实现大量基础功能
6. **数据存储不统一**：数据存储逻辑与爬虫逻辑混合，不利于维护
7. **过度依赖浏览器自动化**：部分爬虫依赖Selenium等浏览器自动化工具，资源消耗大且稳定性差

### 改进方案

1. **基类抽象**：创建`BaseCrawler`基类，封装通用功能
2. **统一接口**：所有爬虫实现统一接口，便于调用和管理
3. **完善错误处理**：添加全面的异常捕获和处理机制
4. **增强日志系统**：实现详细的日志记录，包括调试、信息、警告和错误级别
5. **配置集中化**：将配置信息集中管理，便于修改和维护
6. **模块化设计**：将爬虫、数据处理、存储等功能模块化，降低耦合
7. **增强可扩展性**：便于添加新的爬虫源
8. **减少浏览器依赖**：尽可能使用轻量级请求库代替浏览器自动化

## 项目优化建议

### 文件组织整理

1. **测试文件移动**：将`test_*.py`文件全部移动到`tests`目录
2. **日志文件整理**：根目录下的`.log`文件应该移动到logs目录下对应的子目录
3. **数据库文件移动**：将根目录的`*.db`文件移动到`data`或`db`目录

### 运行脚本统一

1. **统一入口**: 
   - `run.py` - 主程序入口
   - `run_crawler.py` - 爬虫统一入口
   - `run_scheduler.py` - 调度任务入口

2. **CLI模块化**: 创建专门的CLI目录管理命令行接口

## 贡献

欢迎贡献代码或提出改进建议！请提交Issue或Pull Request。

## 许可

本项目使用MIT许可证。请参考LICENSE文件。

## 爬虫模式的主要参数

- `-s, --source`：爬虫来源，支持eastmoney, eastmoney_simple, sina, tencent等
- `-d, --days`：爬取最近几天的新闻，默认为1天
- `-p, --use-proxy`：是否使用代理
- `--db-path`：数据库路径，如不指定则使用默认路径
- `--source-db`：是否使用来源专用数据库
- `--log-level`：日志级别，可选值为DEBUG、INFO、WARNING、ERROR，默认为INFO
- `--log-dir`：日志存储目录，默认为./logs
- `--output-dir`：输出文件目录，默认为./data/output
- `--debug`：是否开启调试模式

### 东方财富网爬虫特有参数

- `--max-news`：每个分类最多爬取多少条新闻，默认10条
- `--categories`：要爬取的新闻分类，默认为财经和股票
- `--delay`：请求间隔时间(秒)，默认5秒
- `--max-retries`：最大重试次数，默认3次
- `--timeout`：请求超时时间(秒)，默认30秒
- `--use-selenium`：是否使用Selenium（仅适用于东方财富网爬虫）

## 爬虫支持的网站

- 东方财富网 (EastmoneyCrawler)
- 新浪财经 (SinaCrawler)
- 腾讯财经 (TencentCrawler)
- 网易财经 (NeteaseCrawler)
- 凤凰财经 (IfengCrawler)

## 详细文档

有关更详细的使用说明，请参阅以下文档：

- [使用统一入口](docs/使用统一入口.md) - 统一入口的详细使用说明
- [脚本整合说明](docs/脚本整合说明.md) - 运行脚本整合的背景和方案
- [数据库连接说明](docs/数据库连接说明.md) - 爬虫与数据库连接的详细说明

## 数据格式

爬取的新闻数据格式如下：

```json
{
    "id": "新闻ID",
    "title": "新闻标题",
    "content": "新闻内容",
    "pub_time": "发布时间",
    "author": "作者",
    "source": "来源",
    "url": "新闻URL",
    "keywords": "关键词",
    "sentiment": "情感倾向",
    "crawl_time": "爬取时间",
    "category": "新闻分类",
    "images": "图片URL",
    "related_stocks": "相关股票"
}
```

## 数据库优化

系统支持智能识别和使用多个数据库文件，确保您可以查看所有历史爬取的新闻数据。

### 多数据库支持功能

- **自动数据库发现**：系统会自动搜索可能的数据库目录，查找并使用所有可用的数据库文件
- **灵活的数据库位置**：支持多个可能的数据库位置，按优先级搜索：
  - `./data/db/` (项目根目录下的data/db目录)
  - `./db/` (项目根目录下的db目录)
  - 当前工作目录下的`data/db/`或`db/`目录
- **命令行参数**：通过`--db-dir`参数显式指定数据库目录
- **合并查询结果**：从多个数据库文件中查询并合并结果，提供完整的数据视图

### 如何使用多数据库功能

系统默认启用多数据库功能。在启动Web应用时，会自动搜索并使用所有可用的数据库文件：

```bash
# 使用自动检测的数据库目录
python run.py web

# 指定数据库目录
python run.py web --db-dir path/to/your/db
```

在控制台输出中，您可以看到系统找到了哪些数据库文件：

```
找到主数据库: /path/to/your/db/finance_news.db
找到 X 个数据库文件
```

### 数据库查找逻辑

1. 首先检查命令行参数`--db-dir`是否指定了数据库目录
2. 如果未指定，检查环境变量`DB_DIR`
3. 如果环境变量未设置，按优先级搜索可能的目录，寻找包含`.db`文件的第一个有效目录
4. 如果所有目录都不存在或不包含数据库文件，创建并使用默认目录

## 开发指南

### 添加新的爬虫

1. 在`app/crawlers/`目录下创建新的爬虫文件，如`example.py`
2. 在文件中定义爬虫类，继承自`BaseCrawler`
3. 实现必要的方法，如`crawl`、`extract_news_links`、`crawl_news_detail`等
4. 在`app/crawlers/__init__.py`中导入新的爬虫类，并添加到`CRAWLER_CLASSES`字典中

### 爬虫类模板

```python
from app.crawlers.base import BaseCrawler

class ExampleCrawler(BaseCrawler):
    """示例爬虫"""
    
    # 新闻分类URL
    CATEGORY_URLS = {
        '财经': 'https://example.com/finance',
        '股票': 'https://example.com/stock',
    }
    
    # 内容选择器
    CONTENT_SELECTOR = 'div.article-content'
    
    # 时间选择器
    TIME_SELECTOR = 'span.time'
    
    # 作者选择器
    AUTHOR_SELECTOR = 'span.author'
    
    def __init__(self, db_path=None, use_proxy=False, use_source_db=False):
        """初始化爬虫"""
        self.source = "示例网站"
        super().__init__(db_path, use_proxy, use_source_db)
    
    def crawl(self, days=1):
        """爬取新闻"""
        # 实现爬取逻辑
        pass
    
    def extract_news_links(self, html, category):
        """提取新闻链接"""
        # 实现提取新闻链接的逻辑
        pass
    
    def crawl_news_detail(self, url, category):
        """爬取新闻详情"""
        # 实现爬取新闻详情的逻辑
        pass
```

# NewsLook 项目优化总结与使用指南

*生成时间: 2025年3月24日20:09:07更新*

## 项目概述

NewsLook 是一个财经新闻爬虫系统，专注于抓取、处理、存储和展示财经新闻数据。本项目采用模块化设计，易于扩展和维护，支持多种运行模式，包括爬虫模式、调度器模式和Web应用模式。

## 项目结构优化

本项目最近完成了重大结构优化，现在使用模块化设计：

```
NewsLook/
├── newslook/         # 主模块包
│   ├── crawlers/     # 爬虫模块
│   ├── tasks/        # 任务调度模块
│   ├── utils/        # 工具函数
│   └── web/          # Web应用模块
├── data/             # 数据存储
│   └── db/           # 数据库文件
├── logs/             # 日志文件
├── scripts/          # 运行脚本
└── tests/            # 测试代码
```

### Web应用启动方法

使用以下命令启动Web应用：

```bash
# 开发环境启动
python run.py web --debug

# 生产环境启动
python run.py web
```

或者直接双击运行`start_web.bat`脚本。

### 数据库文件存储优化

系统现在使用以下数据库架构：

1. **主数据库**: `finance_news.db` - 用于存储聚合的新闻数据
2. **来源专用数据库**: 每个来源对应一个独立的数据库文件，如 `腾讯财经.db`、`新浪财经.db` 等

系统会自动发现并使用这些数据库文件，允许查看并管理所有爬取的新闻数据。

## 代码健康工具

为确保代码质量和项目健康，我们提供了一系列工具脚本：

### 1. 代码健康检查工具

检查代码风格、静态类型、安全漏洞等，并生成健康报告。

```bash
python scripts/utils/code_health_check.py [--fix]
```

参数:
- `--fix`: 尝试自动修复发现的问题

### 2. 依赖分析工具

分析项目中的依赖关系，生成依赖图，检测循环依赖。

```bash
python scripts/utils/dependency_analyzer.py [--output OUTPUT] [--format {png,svg,pdf}] [--mode {modules,packages,imports}]
```

参数:
- `--output`: 输出文件名前缀
- `--format`: 输出图形格式
- `--mode`: 分析模式

### 3. 性能分析工具

分析代码性能瓶颈，提供优化建议。

```bash
python scripts/utils/performance_profiler.py [--mode {cpu,memory,time,all}] [--target TARGET] [--output OUTPUT]
```

参数:
- `--mode`: 分析模式
- `--target`: 要分析的目标
- `--output`: 输出文件名前缀

### 4. 文档生成工具

从代码注释生成项目文档。

```bash
python scripts/utils/documentation_generator.py [--output OUTPUT] [--format {html,markdown}] [--title TITLE] [--source SOURCE]
```

参数:
- `--output`: 输出目录
- `--format`: 文档格式
- `--title`: 文档标题
- `--source`: 源代码目录

### 5. 依赖版本管理

冻结项目依赖版本，确保环境一致性。

```bash
python scripts/utils/freeze_requirements.py
```

## 配置系统

项目使用统一的配置管理系统，支持从命令行参数、环境变量和配置文件读取配置。优先级顺序为：命令行 > 环境变量 > 配置文件 > 默认值。

### 生成默认配置

```bash
python scripts/create_config.py
```

配置文件示例:

```ini
[Database]
db_directory = data/db
backup_directory = data/db/backup

[Crawler]
user_agent = Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36
timeout = 10
max_retries = 3
default_encoding = utf-8

[Web]
host = 0.0.0.0
port = 5000
debug = false
secret_key = your_secret_key_here
items_per_page = 20

[Logging]
log_level = INFO
log_file = logs/newslook.log
log_rotation = true
max_log_size = 10485760
backup_count = 5

[Scheduler]
interval = 3600
start_on_boot = true
scheduled_crawl = 08:00,20:00
```

## 使用方式

### 命令行参数

可以通过命令行参数指定运行模式和配置。

```bash
# 爬虫模式
python run.py crawler [--source SOURCE] [--days DAYS]

# 调度器模式
python run.py scheduler [--interval INTERVAL]

# Web应用模式
python run.py web [--host HOST] [--port PORT] [--debug]
```

### 数据库工具

项目提供了数据库管理工具:

```bash
# 检查未知来源
python scripts/db/check_unknown_sources.py

# 更新未知来源
python scripts/db/update_unknown_sources.py

# 合并数据库
python scripts/db/merge_databases.py
```

## 开发最佳实践

1. **使用相对导入**: 在包内使用相对导入，例如 `from ..utils import helper`
2. **为新包添加`__init__.py`文件**: 确保新创建的包包含此文件
3. **编写单元测试**: 为新功能编写单元测试
4. **使用配置管理**: 使用配置管理系统而不是硬编码值
5. **使用日志系统**: 使用统一的日志系统而不是print语句
6. **规范代码风格**: 遵循PEP 8编码规范

## 数据库维护

数据库文件存储在 `data/db` 目录下，备份存储在 `data/db/backup` 目录。详细的数据库维护指南请参阅 `docs/database/` 目录下的文档。

## 贡献代码

欢迎贡献代码，请确保贡献的代码遵循本项目的编码规范，并通过了单元测试。提交前请运行代码健康检查工具确保代码质量。

## 项目文件整理 (2025-03-25)

项目已完成文件整理，主要变动如下：

1. 数据库相关工具移至 `scripts/db_utils` 目录
   - 数据库检查工具
   - 数据库修复工具
   - 关键词修复工具

2. 搜索工具移至 `scripts/search_utils` 目录
   - 新闻搜索脚本
   - 内容获取脚本
   - 腾讯财经专用搜索工具

3. Web应用工具准备目录 `scripts/web_utils`
   - 未来将添加Web应用相关工具

4. 清理了临时文件和乱码数据库文件

每个工具目录下都添加了README.md文件，描述了目录中工具的用途和使用方法。
