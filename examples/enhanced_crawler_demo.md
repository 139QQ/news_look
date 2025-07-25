# NewsLook 增强型爬虫演示 - 使用指南

## 简介

`enhanced_crawler_demo.py` 是 NewsLook 财经新闻爬虫系统的演示脚本，专门用于展示增强型异步爬虫的性能优势和使用方法。该脚本提供了与标准爬虫的性能对比功能，以及增强型爬虫的示例用法，帮助用户了解如何在实际应用中利用增强型爬虫的特性。

## 功能亮点

- 自动比较标准爬虫和增强型爬虫的性能差异
- 生成可视化性能对比报告（包括图表）
- 展示增强型爬虫的高级用法
- 支持多种财经新闻数据源
- 提供灵活的命令行参数配置

## 支持的数据源

- 东方财富
- 新浪财经
- 网易财经
- 凤凰财经

## 使用方法

### 命令行参数

```
python examples/enhanced_crawler_demo.py [选项]
```

| 参数 | 说明 | 默认值 | 可选值 |
|------|------|--------|--------|
| --mode | 运行模式 | both | example(示例), test(测试), both(两者) |
| --source | 数据源名称 | 东方财富 | 东方财富, 新浪财经, 网易财经, 凤凰财经 |
| --days | 爬取天数 | 1 | 任意正整数 |
| --max-news | 最大爬取新闻数量 | 20 | 任意正整数 |

### 使用示例

1. 使用默认参数运行完整演示（包括性能测试和示例）：
```
python examples/enhanced_crawler_demo.py
```

2. 仅运行性能测试，比较网易财经数据源的爬虫性能：
```
python examples/enhanced_crawler_demo.py --mode test --source 网易财经
```

3. 仅展示增强型爬虫的示例用法，使用凤凰财经数据源：
```
python examples/enhanced_crawler_demo.py --mode example --source 凤凰财经
```

4. 爬取最近3天的新浪财经新闻，最多50条：
```
python examples/enhanced_crawler_demo.py --source 新浪财经 --days 3 --max-news 50
```

## 输出内容

### 性能测试报告

当运行性能测试时，脚本会输出：

1. 运行配置信息
2. 标准爬虫和增强型爬虫的执行时间
3. 两种爬虫的成功/失败统计对比
4. 性能提升百分比
5. 可视化对比图表，保存在 `data/enhanced_demo/{source}_comparison_{timestamp}.png`

### 示例运行结果

当运行示例模式时，脚本会输出：

1. 增强型爬虫的配置信息
2. 爬取进度日志
3. 前3篇爬取到的文章预览
4. 总执行时间和成功/失败统计

## 增强型爬虫的特点

增强型爬虫相比标准爬虫具有以下优势：

1. **智能并发控制**：根据域名自动调整并发请求数
2. **自适应请求间隔**：分析网站响应动态调整请求频率
3. **高级错误恢复**：智能重试策略和错误处理机制
4. **内存优化**：更高效的资源管理和内存使用
5. **详细日志**：提供细粒度的执行日志和性能指标

## 性能测试说明

性能测试会在相同条件下运行标准爬虫和增强型爬虫，比较两者在以下方面的差异：

1. **总执行时间**：完成相同任务所需的时间
2. **成功率**：成功爬取的文章百分比
3. **平均处理速度**：每秒处理的文章数量
4. **资源使用效率**：CPU和内存使用情况

测试结果会直观地展示增强型爬虫相对于标准爬虫的性能提升。

## 注意事项

1. 增强型爬虫在爬取大量数据时优势更为明显
2. 测试时建议使用 `--max-news` 参数设置足够多的文章数量（如30以上）
3. 性能对比图表需要安装 `matplotlib` 库才能生成
4. 请遵守网站的爬虫政策和使用条款
5. 如果遇到网络限制，增强型爬虫的智能调节功能会自动适应 