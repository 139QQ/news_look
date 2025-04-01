# 财经新闻爬虫系统 (NewsLook)

一个用于爬取各大财经网站新闻的系统，包括东方财富、新浪财经、腾讯财经、网易财经和凤凰财经等网站。

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

## 最新更新

### 2025-03-30 更新
- 修复了新浪财经爬虫中的方法命名不一致问题
- 统一了私有方法的命名规范，使用下划线前缀
- 添加了缺失的模块导入（bs4.element.Comment, traceback）
- 增强了错误处理和日志记录功能
- 优化了内容提取逻辑，提高了爬取成功率

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

爬虫模式用于爬取财经新闻数据。

```bash
# 爬取所有来源的新闻
python run.py crawler

# 爬取特定来源的新闻（如新浪财经）
python run.py crawler --source 新浪财经

# 指定爬取天数
python run.py crawler --days 3

# 指定每个分类最多爬取的页数
python run.py crawler --max-pages 5

# 指定爬取特定分类的新闻（如基金）
python run.py crawler --category 基金

# 组合使用多个参数
python run.py crawler --source 新浪财经 --days 2 --max-pages 3 --category 基金

# 使用代理
python run.py crawler --use-proxy

# 显示详细日志
python run.py crawler --verbose
```

### 2. 调度器模式

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

## 开发最佳实践

1. **使用相对导入**: 在包内使用相对导入，例如 `from ..utils import helper`
2. **为新包添加`__init__.py`文件**: 确保新创建的包包含此文件
3. **编写单元测试**: 为新功能编写单元测试
4. **使用配置管理**: 使用配置管理系统而不是硬编码值
5. **使用日志系统**: 使用统一的日志系统而不是print语句
6. **规范代码风格**: 遵循PEP 8编码规范

## 贡献代码

欢迎贡献代码，请确保贡献的代码遵循本项目的编码规范，并通过了单元测试。提交前请运行代码健康检查工具确保代码质量。

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
- [使用 --category 参数爬取特定分类新闻](docs/使用 --category 参数爬取特定分类新闻.md) - 使用 --category 参数爬取特定分类新闻的详细说明
