# 使用指南

本文档提供了金融新闻爬虫系统的详细使用说明，包括命令行工具和配置选项的使用方法。

## 1. 命令行工具

金融新闻爬虫系统提供了几种主要的命令行工具，以下是它们的使用方法。

### 1.1 基本爬虫命令

#### 运行单个爬虫
```bash
python run_crawler.py --source 东方财富 --days 3 --max-news 100
```

参数说明：
- `--source` 或 `-s`: 爬虫名称，如 "东方财富"、"新浪财经" 等
- `--days` 或 `-d`: 爬取过去几天的新闻(默认1天)
- `--max-news`: 最多爬取的新闻数量(默认500条)

#### 运行特定类别的东方财富爬虫
```bash
python run_eastmoney.py --categories 期货 外汇 黄金
```

参数说明：
- `--categories`: 指定要爬取的新闻类别，可以指定多个类别

#### 使用简化版东方财富爬虫
```bash
python run_eastmoney_simple.py --days 1
```

### 1.2 日志控制

#### 设置日志级别
```bash
python run_crawler.py -s 东方财富 --log-level DEBUG
```

可选的日志级别：
- `DEBUG`: 详细的调试信息
- `INFO`: 一般信息(默认)
- `WARNING`: 警告
- `ERROR`: 错误
- `CRITICAL`: 严重错误

#### 设置日志存储目录
```bash
python run_crawler.py -s 东方财富 --log-dir /custom/log/path
```

### 1.3 代理设置

```bash
python run_crawler.py -s 东方财富 --use-proxy
```

### 1.4 调度器

运行调度器以定期执行爬虫任务：

```bash
python run_scheduler.py
```

## 2. 爬虫配置

### 2.1 配置文件

主要配置文件位于 `app/config/default.py`，包含以下主要配置：

- 数据库配置
- 代理配置
- 爬虫超时设置
- 用户代理设置
- 调度配置

### 2.2 自定义用户代理

修改 `app/config/default.py` 中的 `USER_AGENTS` 列表：

```python
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    # 添加更多用户代理...
]
```

### 2.3 调整请求超时

```python
# 请求超时设置（秒）
REQUEST_TIMEOUT = 30
```

## 3. 数据管理

### 3.1 查看爬取的数据

爬取的数据存储在SQLite数据库中，默认路径为 `data/finance_news.db`。您可以使用SQLite客户端查看：

```bash
sqlite3 data/finance_news.db
```

然后执行SQL查询：

```sql
SELECT * FROM news LIMIT 10;
```

### 3.2 导出数据

#### 导出为CSV
```bash
python scripts/export_data.py --format csv --output news_data.csv
```

#### 导出为JSON
```bash
python scripts/export_data.py --format json --output news_data.json
```

### 3.3 清理数据

清理特定日期之前的数据：

```bash
python scripts/cleanup_data.py --before 2023-01-01
```

## 4. 高级用法

### 4.1 自定义爬虫

如果您想开发自己的爬虫，可以通过继承 `BaseCrawler` 类来实现：

1. 在 `app/crawlers` 目录下创建新的Python文件
2. 导入 `BaseCrawler` 类
3. 定义您的爬虫类并实现必要的方法

示例：

```python
from app.crawlers.base import BaseCrawler

class MyCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(name="我的爬虫")
        
    def get_news_links(self, days=1):
        # 实现获取新闻链接的方法
        pass
        
    def parse_news(self, url):
        # 实现解析新闻内容的方法
        pass
```

### 4.2 并行爬取

使用 `--workers` 参数指定并行爬取的工作线程数：

```bash
python run_crawler.py -s 东方财富 --workers 5
```

### 4.3 调整爬取速率

使用 `--delay` 参数设置请求之间的延迟（秒）：

```bash
python run_crawler.py -s 东方财富 --delay 2
```

## 5. 定制开发

### 5.1 扩展新闻来源

在 `app/crawlers` 目录下添加新的爬虫类，然后在 `app/crawlers/__init__.py` 文件中注册您的爬虫：

```python
from app.crawlers.my_crawler import MyCrawler

CRAWLER_CLASSES = {
    # 现有爬虫...
    "我的爬虫": MyCrawler,
}
```

### 5.2 自定义数据处理

如果需要对爬取的数据进行自定义处理，可以在 `app/processors` 目录下添加新的处理器。

### 5.3 集成到其他系统

您可以使用API或者直接访问数据库的方式将爬虫系统与其他系统集成。

## 6. 故障排除

### 6.1 常见错误

#### 连接超时
```
问题: 连接到网站时超时
解决方案: 
- 检查网络连接
- 增加超时时间: --timeout 60
- 使用代理: --use-proxy
```

#### 解析错误
```
问题: 网页内容解析失败
解决方案:
- 检查网站是否改变了HTML结构
- 更新爬虫代码以适应新的结构
- 使用 --log-level DEBUG 获取更多信息
```

### 6.2 性能问题

如果爬虫运行缓慢，可以尝试以下优化：

- 增加工作线程数：`--workers 8`
- 减少爬取数量：`--max-news 100`
- 使用简化版爬虫：`run_eastmoney_simple.py`

### 6.3 日志分析

查看日志文件以排查问题：

```bash
tail -f logs/eastmoney/eastmoney_20230601.log
```

## 7. 实用示例

### 7.1 每日自动爬取

使用cron或任务计划程序设置每日自动爬取：

**Linux (cron):**
```
# 每天凌晨2点运行
0 2 * * * cd /path/to/crawler && python run_crawler.py -s 东方财富 --days 1
```

**Windows (任务计划程序):**
1. 创建批处理文件 `daily_crawl.bat`：
   ```
   cd C:\path\to\crawler
   python run_crawler.py -s 东方财富 --days 1
   ```
2. 使用Windows任务计划程序设置定时执行

### 7.2 组合爬取多个来源

创建批处理文件或shell脚本执行多个爬虫：

```bash
#!/bin/bash
python run_crawler.py -s 东方财富 --days 1
python run_crawler.py -s 新浪财经 --days 1
python run_crawler.py -s 其他来源 --days 1
```

### 7.3 分析爬取结果

使用Python脚本分析爬取的数据，例如统计关键词频率：

```python
import sqlite3
from collections import Counter
import jieba

# 连接到数据库
conn = sqlite3.connect("data/finance_news.db")
cursor = conn.cursor()

# 获取新闻内容
cursor.execute("SELECT content FROM news WHERE date > date('now', '-7 days')")
contents = [row[0] for row in cursor.fetchall() if row[0]]

# 分词和统计
words = []
for content in contents:
    words.extend(jieba.cut(content))

# 统计频率
word_counter = Counter(words)
top_words = word_counter.most_common(20)
print("最常见的词汇：", top_words)

conn.close()
```

## 8. 附录

### 8.1 完整命令行参数

```
--source, -s         爬虫来源名称
--days, -d           爬取过去几天的新闻
--max-news           最多爬取的新闻数量
--workers            并行工作线程数
--delay              请求之间的延迟(秒)
--timeout            请求超时时间(秒)
--log-level          日志级别(DEBUG/INFO/WARNING/ERROR/CRITICAL)
--log-dir            日志存储目录
--use-proxy          使用代理
--categories         新闻类别(仅适用于特定爬虫)
--quiet              安静模式，减少输出
--version            显示版本信息
--help               显示帮助信息
```

### 8.2 支持的爬虫

当前版本支持以下爬虫：

- 东方财富 (EastMoneyCrawler)
- 东方财富简化版 (EastMoneySimpleCrawler)
- 新浪财经 (SinaFinanceCrawler)
- 其他爬虫...

### 8.3 数据模型

新闻数据模型包含以下字段：

- `id`: 唯一标识符
- `title`: 新闻标题
- `content`: 新闻内容
- `url`: 新闻原始URL
- `date`: 发布日期
- `source`: 新闻来源
- `category`: 新闻类别
- `keywords`: 关键词
- `created_at`: 爬取时间 