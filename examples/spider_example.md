# NewsLook 爬虫使用示例 - 使用指南

## 简介

`spider_example.py` 是 NewsLook 财经新闻爬虫系统的示例脚本，用于演示如何使用三种不同的爬虫模式爬取财经新闻数据：
- 同步爬虫
- 基础异步爬虫
- 增强型异步爬虫

通过这个脚本，您可以比较不同爬虫模式的性能和效果，并了解如何集成 NewsLook 爬虫系统到您自己的应用中。

## 功能亮点

- 支持三种爬虫模式的灵活选择
- 可以指定数据源、天数、最大新闻数量和分类
- 自动保存爬取结果到 JSON 文件
- 提供爬取结果预览和性能统计
- 简单易用的命令行界面

## 支持的数据源

- 东方财富
- 新浪财经
- 网易财经
- 凤凰财经

## 使用方法

### 命令行参数

```
python examples/spider_example.py [选项]
```

| 参数 | 说明 | 默认值 | 可选值 |
|------|------|--------|--------|
| --mode | 爬虫模式 | all | sync(同步), async(异步), enhanced(增强), all(所有) |
| --source | 数据源名称 | 东方财富 | 东方财富, 新浪财经, 网易财经, 凤凰财经 |
| --days | 爬取天数 | 1 | 任意正整数 |
| --max-news | 最大爬取新闻数量 | 10 | 任意正整数 |
| --category | 新闻分类 | None | 取决于数据源支持的分类 |

### 使用示例

1. 使用所有爬虫模式爬取东方财富的新闻：
```
python examples/spider_example.py
```

2. 仅使用增强型异步爬虫爬取新浪财经的20条新闻：
```
python examples/spider_example.py --mode enhanced --source 新浪财经 --max-news 20
```

3. 使用同步模式爬取最近3天的网易财经新闻：
```
python examples/spider_example.py --mode sync --source 网易财经 --days 3
```

## 输出结果

脚本会创建 `data/spider_example/` 目录并在其中保存以下文件：

1. 数据库文件：
   - `{source}_sync.db`：同步爬虫结果
   - `{source}_async.db`：异步爬虫结果
   - `{source}_enhanced.db`：增强型爬虫结果

2. JSON 结果文件：
   - `{source}_sync_{timestamp}.json`
   - `{source}_async_{timestamp}.json`
   - `{source}_enhanced_{timestamp}.json`

## 爬虫模式对比

| 爬虫模式 | 特点 | 适用场景 |
|---------|------|----------|
| 同步爬虫 | 简单稳定，单线程执行 | 少量数据爬取，对性能要求不高 |
| 基础异步爬虫 | 使用异步IO提高性能 | 中等数据量，需要更快的爬取速度 |
| 增强型异步爬虫 | 高级并发控制，智能资源管理 | 大量数据爬取，需要最佳性能和稳定性 |

## 代码集成

您可以参考 `run_sync_spider()` 和 `run_async_spider()` 函数，了解如何将 NewsLook 爬虫系统集成到您自己的应用中。

关键步骤包括：
1. 创建 CrawlerFactory 实例
2. 使用工厂创建相应的爬虫实例
3. 调用爬虫的 crawl() 方法获取结果
4. 处理爬取结果

## 注意事项

1. 请遵守网站的爬虫规则和使用条款
2. 在生产环境中使用时，建议适当降低爬取频率
3. 对于大规模爬取任务，推荐使用增强型异步爬虫
4. 确保您的系统安装了所有必要的依赖项 