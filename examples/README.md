# NewsLook 示例指南

本目录包含多个示例脚本，用于展示 NewsLook 财经新闻爬虫系统的核心功能和高级特性。以下是主要示例的介绍：

## 批处理爬虫示例 (batch_demo.py)

此示例演示如何使用增强型爬虫批量处理多个新闻源，并提供综合性能报告。

### 功能特点

- 并行爬取多个新闻源
- 线程池管理，可控制并行度
- 详细的时间统计与性能报告
- 错误处理与日志记录

### 使用方法

```bash
python examples/batch_demo.py [参数选项]
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--sources` | 要爬取的新闻源列表 | 所有支持的源 |
| `--days` | 爬取天数 | 1 |
| `--max-news` | 每个源最大爬取数量 | 20 |
| `--workers` | 最大并行爬取数 | 2 |
| `--output-dir` | 输出目录 | data/batch_demo |

### 示例

```bash
# 爬取所有支持的新闻源，每个最多50条新闻
python examples/batch_demo.py --max-news 50

# 仅爬取东方财富和新浪财经，使用3个并行线程
python examples/batch_demo.py --sources 东方财富 新浪财经 --workers 3

# 爬取过去3天的新闻
python examples/batch_demo.py --days 3
```

## 增强型爬虫示例 (enhanced_crawler_demo.py)

此示例展示增强型爬虫的高级特性，并提供与标准爬虫的性能对比。

### 功能特点

- 性能对比测试模式
- 可视化性能报告（图表生成）
- 灵活的配置选项
- 详细的统计信息输出

### 使用方法

```bash
python examples/enhanced_crawler_demo.py [参数选项]
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--mode` | 演示模式：example(使用示例)、test(性能测试)、both(两者) | example |
| `--source` | 要爬取的数据源 | 东方财富 |
| `--days` | 爬取天数 | 1 |
| `--max-news` | 最大爬取数量 | 20 |

### 示例

```bash
# 运行东方财富网的使用示例
python examples/enhanced_crawler_demo.py --mode example --source 东方财富

# 运行新浪财经的性能对比测试
python examples/enhanced_crawler_demo.py --mode test --source 新浪财经

# 运行网易财经的完整演示（示例和性能测试）
python examples/enhanced_crawler_demo.py --mode both --source 网易财经 --max-news 50
```

## 输出说明

所有示例脚本的输出文件（数据库和图表）将保存在相应的数据目录中：

- 批处理示例: `data/batch_demo/`
- 增强型爬虫示例: `data/enhanced_demo/`

数据库文件采用 SQLite 格式，可以使用任何 SQLite 浏览工具查看。 