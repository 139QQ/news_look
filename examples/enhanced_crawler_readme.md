# 增强型爬虫使用指南

## 简介

增强型爬虫是NewsLook财经新闻爬取系统的高级功能，针对网络爬取性能进行了特别优化。相比标准爬虫，增强型爬虫在处理大量并发请求、内存管理和域名访问控制方面具有显著优势，可以更高效地爬取多个新闻源。

## 功能特点

- **高效并发控制**：针对每个域名的独立并发限制，避免对单一网站造成过大压力
- **智能请求延迟**：支持按域名设置请求间隔，符合网站爬虫规范
- **批量任务处理**：通过分块处理大量URL，优化内存使用
- **性能数据统计**：提供爬取速度、成功率等统计数据
- **可视化性能对比**：直观展示与标准爬虫的性能差异
- **优化的内存管理**：减少大型爬取任务的内存占用

## 使用方法

### 通过run.py使用增强型爬虫

```bash
python run.py crawler --enhanced -s 东方财富 -d 2 -m 50 --domain-concurrency 5 --domain-delay 0.5
```

### 主要参数说明

- `--enhanced`：启用增强型爬虫
- `-s, --source`：指定新闻源（如：东方财富、新浪财经等）
- `-a, --all`：爬取所有支持的新闻源
- `-d, --days`：爬取最近几天的新闻（默认：1）
- `-m, --max`：每个源最多爬取的新闻数量（默认：100）
- `--concurrency`：最大并发请求数（默认：10）
- `--domain-concurrency`：每个域名的最大并发请求数（默认：5）
- `--domain-delay`：同域名请求间的延迟，单位秒（默认：0）

### 查看支持的新闻源

```bash
python run.py crawler --list
```

## 增强型爬虫示例脚本

项目提供了专门的示例脚本`enhanced_crawler_demo.py`，用于演示增强型爬虫的使用方法和性能对比。

### 运行示例

```bash
# 运行使用示例
python examples/enhanced_crawler_demo.py --mode example --source 东方财富

# 运行性能测试
python examples/enhanced_crawler_demo.py --mode test --source 新浪财经 --days 2 --max-news 30

# 同时运行示例和性能测试
python examples/enhanced_crawler_demo.py --mode both --source 网易财经
```

### 示例脚本参数

- `--mode`：运行模式，可选值：example（使用示例）、test（性能测试）、both（两者）
- `--source`：要爬取的数据源
- `--days`：爬取天数
- `--max-news`：最大爬取数量

## 增强型爬虫高级配置

通过`CrawlerFactory`创建增强型爬虫时，可以设置以下高级参数：

```python
options = {
    'concurrency_per_domain': 5,  # 每个域名最大并发请求数
    'domain_delay': 0.5,          # 同域名请求之间的延迟(秒)
    'chunk_size': 10,             # 分批处理的大小
    'timeout': 30                 # 请求超时时间(秒)
}

crawler = factory.create_enhanced_crawler(source, db_path, options)
```

## 性能对比

增强型爬虫通常能带来以下性能提升：

- 爬取速度提升30-50%（取决于网络条件和目标站点）
- 内存使用减少约25%（对于大型爬取任务）
- 网站友好性更佳，减少被封禁风险

## 注意事项

1. 增强型爬虫需要Python 3.7+和aiohttp库的支持
2. 过高的并发设置可能导致目标网站的反爬措施
3. 建议根据具体网站特性调整`domain_delay`和`concurrency_per_domain`参数
4. 性能对比图表默认保存在`data/enhanced_demo/`目录下 