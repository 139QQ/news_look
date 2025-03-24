# 财经新闻爬虫系统脚本整合说明

## 整合背景

之前的系统中存在多个独立的运行脚本，造成了以下问题：

1. 入口分散，不利于统一管理和使用
2. 功能重复，多个脚本中存在相似代码
3. 配置分散，不同脚本使用不同的配置方式
4. 使用复杂，需要记住多个不同的脚本名称和参数

为了解决上述问题，我们对系统的运行脚本进行了整合，形成了统一的入口和清晰的模块划分。

## 整合方案

### 1. 三个主要入口

整合后的系统有三个主要入口：

- `run.py` - 系统主入口，支持选择不同的运行模式
- `run_crawler.py` - 爬虫统一入口，支持各种爬虫的运行
- `run_scheduler.py` - 调度任务入口，用于定时运行爬虫任务

### 2. 统一参数体系

我们对命令行参数进行了统一规划：

- 通用参数：如`--log-level`、`--db-path`等在不同模式下具有相同含义
- 特定参数：如东方财富网爬虫特有的`--categories`、`--max-news`等参数

### 3. 模块化设计

通过动态导入机制，实现了模块化设计：

- 主入口根据命令行参数动态调用相应的功能模块
- 爬虫入口根据爬虫类型选择相应的爬虫实现
- 调度入口根据配置执行相应的调度任务

### 4. 文件整理

- 将原有的独立脚本（如`run_eastmoney.py`、`run_eastmoney_simple.py`）移动到`scripts`目录，作为历史参考
- 创建统一的文档说明如何使用新的入口

## 代码结构变化

### 1. `run.py`

新的主入口支持三种运行模式：

```bash
python run.py crawler  # 爬虫模式
python run.py scheduler  # 调度模式
python run.py web  # Web应用模式
```

### 2. `run_crawler.py`

整合了各种爬虫的功能，通过`--source`参数指定要运行的爬虫类型：

```bash
python run_crawler.py --source eastmoney
python run_crawler.py --source eastmoney_simple
```

### 3. `run_scheduler.py`

增强了调度功能，支持查看可用任务和运行特定任务：

```bash
python run_scheduler.py --list-tasks
python run_scheduler.py --task eastmoney_daily
```

## 使用示例

### 1. 通过主入口运行爬虫

```bash
python run.py crawler -s eastmoney -d 3 --categories 财经 股票 --max-news 20
```

### 2. 通过主入口运行调度器

```bash
python run.py scheduler --daemon --log-level DEBUG
```

### 3. 通过主入口启动Web应用

```bash
python run.py web --debug --port 8080
```

## 设计思考

1. **命令行参数设计**：采用子命令模式（`crawler`、`scheduler`、`web`），使命令结构更清晰

2. **代码复用**：通过动态导入和参数传递，避免了代码复制粘贴

3. **灵活性**：保留了直接运行`run_crawler.py`和`run_scheduler.py`的能力，以兼容现有的脚本和调用方式

4. **扩展性**：新的爬虫可以方便地集成到统一入口中，只需实现相应的接口

## 后续建议

1. **配置文件**：未来可考虑使用统一的配置文件，减少命令行参数的数量

2. **插件系统**：可以考虑实现插件系统，使爬虫更容易扩展和定制

3. **服务化**：考虑将爬虫和调度功能做成微服务，通过API调用 