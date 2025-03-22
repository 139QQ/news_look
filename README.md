# 财经新闻爬虫系统

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

## 系统架构

```
app/
  ├── crawlers/
  │   ├── __init__.py      # 爬虫包初始化文件，提供获取爬虫实例的接口
  │   ├── base.py          # 爬虫基类，封装通用功能
  │   ├── eastmoney.py     # 东方财富爬虫
  │   ├── sina.py          # 新浪财经爬虫
  │   ├── tencent.py       # 腾讯财经爬虫
  │   ├── netease.py       # 网易财经爬虫
  │   └── ifeng.py         # 凤凰财经爬虫
  ├── utils/
  │   ├── logger.py        # 日志工具
  │   ├── text_cleaner.py  # 文本清洗工具
  │   └── sentiment.py     # 情感分析工具
  └── db/
      └── database.py      # 数据库操作
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
# 爬取东方财富网最近3天的财经和股票新闻
python run.py crawler -s eastmoney -d 3 --categories 财经 股票

# 运行所有爬虫，爬取最近1天的新闻
python run.py crawler -d 1

# 使用代理爬取新浪财经的新闻
python run.py crawler -s sina -p --use-proxy
```

### 2. 调度模式

调度模式用于定时运行爬虫任务。

```bash
# 以守护进程方式运行调度器
python run.py scheduler --daemon

# 列出所有可用的调度任务
python run.py scheduler --list-tasks

# 运行特定的调度任务
python run.py scheduler --task eastmoney_daily
```

### 3. Web应用模式

Web应用模式用于启动Web界面，查看和管理爬虫数据。

```bash
# 启动Web应用
python run.py web

# 指定主机和端口
python run.py web --host 127.0.0.1 --port 8080

# 开启调试模式
python run.py web --debug
```

### 直接运行爬虫

如果需要更精细的爬虫控制，也可以直接使用 `run_crawler.py`：

```bash
# 运行东方财富爬虫
python run_crawler.py --source eastmoney --days 3

# 运行所有爬虫
python run_crawler.py --days 1

# 使用代理
python run_crawler.py --source sina --use-proxy
```

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

## 许可证

MIT

# 东方财富网爬虫

## Eastmoney爬虫

东方财富网爬虫是一个高效的财经新闻爬取工具，从各个财经类别中抓取最新的新闻和市场动态。

### 功能特点

- **多类别支持**：支持财经、股票、基金、债券、期货、外汇、黄金等多个金融新闻类别
- **高效请求**：使用requests库直接请求网页，无需浏览器自动化，性能提升300%
- **智能解析**：多级选择器和多种匹配策略，提高内容提取成功率
- **内容清洗**：精准过滤广告和无关内容，保证文本质量
- **情感分析**：对新闻内容进行情感分析，判断正面、负面或中性
- **数据存储**：支持将爬取结果存入数据库和文本文件

### 使用方法

```bash
# 爬取财经类别的新闻（默认）
python run_eastmoney.py

# 爬取指定类别的新闻
python run_eastmoney.py --categories 股票 基金

# 爬取所有类别的新闻
python run_eastmoney.py --categories all

# 指定最大爬取数量
python run_eastmoney.py --max-news 10

# 指定爬取几天内的新闻
python run_eastmoney.py --days 3

# 调试模式
python run_eastmoney.py --debug
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| --categories | 要爬取的新闻类别，支持：财经、股票、基金、债券、期货、外汇、黄金 | 财经 |
| --max-news | 每个类别最大爬取的新闻数量 | 20 |
| --days | 爬取几天内的新闻 | 7 |
| --debug | 是否开启调试模式 | False |
| --output-dir | 输出目录 | ./data/output |

### 输出示例

```json
{
  "id": "a1b2c3d4e5f6g7h8i9j0",
  "url": "https://finance.eastmoney.com/a/202501010123456789.html",
  "title": "市场分析：A股有望迎来开门红",
  "content": "分析师认为，随着政策利好不断释放，A股市场有望在新年伊始迎来一波上涨行情...",
  "pub_time": "2025-01-01 08:30:00",
  "author": "东方财富网",
  "keywords": "A股,政策,利好,上涨",
  "sentiment": "正面",
  "category": "股票",
  "crawl_time": "2025-01-01 09:15:30",
  "source": "东方财富网"
}
```

## 数据结构

爬取的新闻数据包含以下字段：

- `id`: 新闻ID（唯一标识）
- `url`: 新闻URL
- `title`: 新闻标题
- `content`: 新闻内容（纯文本）
- `content_html`: 新闻内容（HTML格式）
- `pub_time`: 发布时间
- `author`: 作者
- `keywords`: 关键词
- `images`: 图片URL列表
- `related_stocks`: 相关股票
- `sentiment`: 情感倾向（正面/负面/中性）
- `classification`: 新闻分类
- `crawl_time`: 爬取时间

## 反爬机制

本爬虫实现了多种反爬机制，以应对网站的反爬措施：

1. **随机User-Agent**：每次请求使用不同的浏览器标识
2. **随机Referer**：模拟从不同网站跳转
3. **随机Cookie**：生成随机的Cookie值
4. **请求延迟**：随机延迟请求，避免频繁访问
5. **指数退避策略**：请求失败时，采用指数退避策略增加等待时间
6. **多种请求方式**：支持普通请求、移动端请求和Selenium模拟浏览器
7. **智能重试**：遇到403、429等错误时智能重试
8. **内容检测**：检测响应内容是否包含反爬关键词

### 应对403 Forbidden错误

如果遇到403 Forbidden错误，可以尝试以下方法：

1. 增加请求延迟：`--delay 10`
2. 使用Selenium模拟浏览器：`--use-selenium`
3. 减少爬取数量：`--max-news 20`
4. 使用代理：`--use-proxy`

## 常见问题

### 无法提取发布时间

有些新闻页面的发布时间格式不统一，爬虫会尝试多种方式提取：

1. 从HTML元素中提取
2. 从URL中提取日期信息
3. 如果都失败，则使用当前时间

### 遇到403 Forbidden错误

这通常是因为网站的反爬机制，可以尝试以下解决方法：

1. 使用`--use-selenium`参数启用Selenium模拟浏览器
2. 增加`--delay`参数值，减少请求频率
3. 使用`--use-proxy`参数启用代理

## 开发者文档

主要文件说明：

- `run_eastmoney.py`: 主程序入口
- `app/crawlers/eastmoney.py`: 东方财富网爬虫实现
- `app/crawlers/base.py`: 爬虫基类
- `app/db/sqlite_manager.py`: SQLite数据库管理器

## 许可证

MIT License

## 最新更新

### 2025年3月 - 参数优化与代码精简

我们对系统进行了全面的参数和命名优化，主要改进包括：

- **代码精简**：移除了冗余参数和不必要的命名，减少了代码行数
- **参数结构优化**：统一了命令行参数的结构，提高了一致性
- **启动脚本改进**：简化了启动脚本，使其更加清晰直观
- **日志系统优化**：重构了日志设置代码，减少了重复内容

这些优化使代码更加简洁和可维护，同时也提高了系统的稳定性和性能。详细改进可以查看 `docs/项目优化汇总.md` 文件中的"参数和命名优化"部分。

## 使用说明
